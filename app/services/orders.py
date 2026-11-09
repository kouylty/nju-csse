"""Order commands serialize checks, inventory, money and audit records in one transaction."""

import json
import secrets
from datetime import datetime, timedelta

from app.clock import now, timestamp
from app.db import read_transaction, write_transaction
from app.domain import OrderStatus, PlacementResult, ProductStatus
from app.errors import BusinessError
from app.order_rules import PlaceOrderInput
from app.product_rules import MAX_MONEY, integer
from app.repositories import logs, orders, products
from app.services.activity import notify_in_tx
from app.services.funds import FundService
from app.services.products import ProductService
from app.validation import pagination


class OrderService:
    def __init__(self, conn, *, clock=now):
        self.conn, self.clock = conn, clock
        self.products = ProductService(conn, clock=clock)
        self.funds = FundService(conn, clock=clock)

    def place_order(self, actor, command: PlaceOrderInput) -> PlacementResult:
        fingerprint = command.fingerprint()
        failure = None
        with write_transaction(self.conn):
            original = orders.by_request(self.conn, actor.id, command.request_key)
            if original is not None:
                if original["request_fingerprint"] != fingerprint:
                    raise BusinessError(
                        "REQUEST_KEY_REUSED", "此请求标识已用于不同购买，请重新确认。"
                    )
                return PlacementResult(original["id"], False)
            at = self.clock()
            self._expire_in_tx(timestamp(at), product_id=command.product_id)
            try:
                product, total = self._prepare(actor, command)
            except BusinessError as error:
                failure = error
            if failure is None:
                self.products.reserve_stock_in_tx(command.product_id, command.quantity)
                images = products.images_for(self.conn, [command.product_id]).get(
                    command.product_id, []
                )
                snapshot = {
                    field: product[field]
                    for field in [
                        "title",
                        "description",
                        "category",
                        "type",
                        "seller_name",
                        "meeting_description",
                    ]
                }
                snapshot["images"] = images
                snapshot.update(
                    {
                        "unit_price_cents": product["price_cents"],
                        "quantity": command.quantity,
                        "postage_cents": 0,
                        "total_cents": total,
                        "delivery_mode": "MEET",
                    }
                )
                order_id = orders.insert(
                    self.conn,
                    {
                        "order_no": f"YX{at:%Y%m%d}{secrets.token_hex(12).upper()}",
                        "buyer_id": actor.id,
                        "seller_id": product["seller_id"],
                        "product_id": product["id"],
                        "request_key": command.request_key,
                        "request_fingerprint": fingerprint,
                        "quantity": command.quantity,
                        "unit_price_cents": product["price_cents"],
                        "postage_cents": 0,
                        "total_cents": total,
                        "delivery_mode": "MEET",
                        "snapshot_json": json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
                        "status": OrderStatus.UNPAID.value,
                        "reservation_state": "HELD",
                        "created_at": timestamp(at),
                        "pay_due_at": timestamp(at + timedelta(minutes=15)),
                    },
                )
                orders.bind_images(self.conn, order_id, [image["id"] for image in images])
                self._log(
                    actor,
                    "ORDER_CREATED",
                    order_id,
                    {},
                    {
                        "status": "UNPAID",
                        "quantity": command.quantity,
                        "total_cents": total,
                        "available_stock": product["available_stock"] - command.quantity,
                    },
                )
        if failure is not None:
            raise failure
        return PlacementResult(order_id, True)

    def _prepare(self, actor, command):
        pending = orders.unpaid_for(self.conn, actor.id, command.product_id)
        if pending is not None:
            raise BusinessError(
                "PENDING_ORDER_EXISTS",
                "请先付款或关闭已有待付款订单。",
                {"order_id": pending["id"]},
            )
        product = products.get_by_id(self.conn, command.product_id)
        if product is None:
            raise BusinessError("NOT_FOUND", "商品不存在。")
        if product["seller_id"] == actor.id:
            raise BusinessError("SELF_PURCHASE", "不能购买本人发布的商品。")
        if product["status"] != ProductStatus.PUBLISHED:
            raise BusinessError("PRODUCT_UNAVAILABLE", "商品当前未在出售，请刷新后重新选择。")
        if product["type"] != "GOODS" or not product["allow_meet"]:
            raise BusinessError("DELIVERY_UNAVAILABLE", "请选择支持当面交付的物品。")
        if command.quantity > product["available_stock"]:
            raise BusinessError("OUT_OF_STOCK", "可售库存不足，请刷新后重试。")
        if (
            command.expected_unit_price_cents != product["price_cents"]
            or command.expected_postage_cents != 0
        ):
            raise BusinessError(
                "PRICE_CHANGED",
                "商品金额已变化，请刷新并重新确认。",
                {"unit_price_cents": product["price_cents"], "postage_cents": 0},
            )
        total = product["price_cents"] * command.quantity
        integer(total, "total_cents", minimum=1, maximum=MAX_MONEY)
        return product, total

    def pay(self, actor, order_id):
        expired = False
        with write_transaction(self.conn):
            row = self._visible(actor, order_id)
            self._require_party(actor, row, "buyer_id")
            if row["status"] == OrderStatus.CLOSED:
                raise BusinessError("INVALID_STATE", "已关闭的订单不能付款。")
            if row["status"] == OrderStatus.UNPAID:
                if self.clock() >= datetime.fromisoformat(row["pay_due_at"]):
                    self._close_in_tx(row, "PAYMENT_TIMEOUT")
                    expired = True
                else:
                    self._require_clear(row)
                    self.funds.record_payment_in_tx(row, actor.id)
                    self._transition(
                        row, {"status": "WAITING_DELIVERY", "paid_at": timestamp(self.clock())}
                    )
                    self._log(
                        actor,
                        "ORDER_PAID",
                        order_id,
                        {"status": "UNPAID"},
                        {"status": "WAITING_DELIVERY"},
                    )
            elif self.funds.get_escrow(order_id)["paid_cents"] != row["total_cents"]:
                raise BusinessError("INVARIANT_VIOLATION", "订单付款记录不完整。")
        if expired:
            # The close and stock release have committed before reporting expiry.
            raise BusinessError(
                "PAYMENT_EXPIRED", "付款期限已到，订单已关闭并释放库存。", {"order_id": order_id}
            )
        return self.get_detail(actor, order_id)

    def deliver(self, actor, order_id):
        with write_transaction(self.conn):
            row = self._visible(actor, order_id)
            self._require_party(actor, row, "seller_id")
            if row["status"] not in {OrderStatus.DELIVERED, OrderStatus.COMPLETED}:
                if row["status"] != OrderStatus.WAITING_DELIVERY:
                    raise BusinessError("INVALID_STATE", "请在付款完成后标记实际交付。")
                self._require_clear(row)
                at = self.clock()
                self._transition(
                    row,
                    {
                        "status": "DELIVERED",
                        "delivered_at": timestamp(at),
                        "auto_confirm_at": timestamp(at + timedelta(days=7)),
                    },
                )
                self._log(
                    actor,
                    "ORDER_DELIVERED",
                    order_id,
                    {"status": row["status"]},
                    {"status": "DELIVERED"},
                )
        return self.get_detail(actor, order_id)

    def confirm(self, actor, order_id):
        with write_transaction(self.conn):
            row = self._visible(actor, order_id)
            self._require_party(actor, row, "buyer_id")
            if row["status"] != OrderStatus.COMPLETED:
                if row["status"] != OrderStatus.DELIVERED:
                    raise BusinessError("INVALID_STATE", "请在卖家交付后确认完成。")
                self._require_clear(row)
                self.funds.settle_in_tx(row, actor.id)
                self._transition(
                    row,
                    {
                        "status": "COMPLETED",
                        "reservation_state": "CONSUMED",
                        "completed_at": timestamp(self.clock()),
                    },
                )
                self._log(
                    actor,
                    "ORDER_COMPLETED",
                    order_id,
                    {"status": "DELIVERED"},
                    {"status": "COMPLETED", "settled_cents": row["total_cents"]},
                )
        return self.get_detail(actor, order_id)

    def close_unpaid(self, actor, order_id):
        with write_transaction(self.conn):
            row = self._visible(actor, order_id)
            self._require_party(actor, row, "buyer_id")
            if row["status"] != OrderStatus.CLOSED:
                if row["status"] != OrderStatus.UNPAID:
                    raise BusinessError("INVALID_STATE", "已付款订单需通过取消协商处理。")
                expired = self.clock() >= datetime.fromisoformat(row["pay_due_at"])
                self._close_in_tx(
                    row,
                    "PAYMENT_TIMEOUT" if expired else "BUYER_CANCELLED",
                    None if expired else actor,
                )
        return self.get_detail(actor, order_id)

    def close_expired(self):
        with write_transaction(self.conn):
            return self._expire_in_tx(timestamp(self.clock()))

    def mark_disputed_in_tx(self, order_id):
        self._require_transaction()
        row = orders.get_by_id(self.conn, order_id)
        if (
            row is None
            or row["status"] == "UNPAID"
            or self.funds.get_escrow(order_id)["paid_cents"] == 0
        ):
            raise BusinessError("INVALID_STATE", "请针对已付款交易申请纠纷；未付款订单可直接关闭。")
        if row["dispute_open"]:
            raise BusinessError("ACTIVE_CASE_EXISTS", "这笔订单已有处理中纠纷。")
        self._transition(row, {"dispute_open": 1})

    def case_context_in_tx(self, order_id, actor):
        self._require_transaction()
        row = orders.get_by_id(self.conn, order_id)
        return {**self._present(row, actor), "funds": self.funds.get_escrow(order_id)}

    def apply_resolution_in_tx(
        self, actor, order_id, decision, *, restore_stock=None, confirmation_plan=""
    ):
        self._require_transaction()
        actor.require_admin()
        row = orders.get_by_id(self.conn, order_id)
        if row is None or not row["dispute_open"]:
            raise BusinessError("INVALID_STATE", "订单当前没有进行中的纠纷。")
        if decision not in {"CONTINUE", "REFUND", "COMPLETE", "RECORD"}:
            raise BusinessError("INVALID_INPUT", "请选择有效的订单处置。")
        if decision != "REFUND" and restore_stock is not None:
            raise BusinessError("INVALID_INPUT", "库存恢复选项用于退款关闭。")
        if decision != "CONTINUE" and confirmation_plan:
            raise BusinessError("INVALID_INPUT", "确认安排用于继续履约。")
        changes = {"dispute_open": 0}
        if decision == "CONTINUE":
            if row["status"] in {"COMPLETED", "CLOSED"} or not confirmation_plan:
                raise BusinessError(
                    "INVALID_INPUT", "继续履约须为未完成交易，并明确后续手动确认安排。"
                )
            changes["auto_confirm_at"] = None
            action = "ORDER_RESUMED"
        elif decision == "REFUND":
            if (
                row["status"]
                not in {"WAITING_DELIVERY", "DELIVERED", "SERVICE_READY", "SERVICE_ACTIVE"}
                or type(restore_stock) is not bool
            ):
                raise BusinessError(
                    "INVALID_INPUT", "请选择未完成的已付款订单，并明确库存是否恢复。"
                )
            self.funds.refund_all_in_tx(row, actor.id)
            if restore_stock:
                self.products.release_stock_in_tx(row["product_id"], row["quantity"])
            changes.update(
                status="CLOSED",
                reservation_state="RELEASED" if restore_stock else "CONSUMED",
                closed_at=timestamp(self.clock()),
                close_reason="CASE_REFUND",
                auto_confirm_at=None,
            )
            action = "ORDER_REFUNDED"
        elif decision == "COMPLETE":
            if row["status"] != "DELIVERED":
                raise BusinessError("INVALID_STATE", "请在实际交付后确认完成。")
            self.funds.settle_in_tx(row, actor.id)
            changes.update(
                status="COMPLETED",
                reservation_state="CONSUMED",
                completed_at=timestamp(self.clock()),
            )
            action = "ORDER_COMPLETED"
        else:
            if row["status"] not in {"COMPLETED", "CLOSED"}:
                raise BusinessError("INVALID_STATE", "未完成交易请选择明确的履约或资金处置。")
            action = "ORDER_AFTERCARE_RECORDED"
        self._transition(row, changes)
        self._log(actor, action, order_id, {"status": row["status"], "dispute_open": True}, changes)
        return {
            "order_id": order_id,
            **changes,
            "restore_stock": restore_stock,
            "confirmation_plan": confirmation_plan,
        }

    def _require_transaction(self):
        if not self.conn.in_transaction:
            raise RuntimeError("Case order commands require the caller's transaction")

    def _expire_in_tx(self, at, **filters):
        rows = orders.expired(self.conn, at, **filters)
        for row in rows:
            self._close_in_tx(row, "PAYMENT_TIMEOUT")
        return len(rows)

    def _close_in_tx(self, row, reason, actor=None):
        self._transition(
            row,
            {
                "status": "CLOSED",
                "reservation_state": "RELEASED",
                "closed_at": timestamp(self.clock()),
                "close_reason": reason,
            },
        )
        self.products.release_stock_in_tx(row["product_id"], row["quantity"])
        self._log(
            actor,
            "ORDER_CLOSED",
            row["id"],
            {"status": row["status"]},
            {"status": "CLOSED", "reason": reason, "released_quantity": row["quantity"]},
        )

    def get_detail(self, actor, order_id):
        row = self._visible(actor, order_id)
        if row["status"] == OrderStatus.UNPAID and self.clock() >= datetime.fromisoformat(
            row["pay_due_at"]
        ):
            with write_transaction(self.conn):
                row = self._visible(actor, order_id)
                if row["status"] == OrderStatus.UNPAID and self.clock() >= datetime.fromisoformat(
                    row["pay_due_at"]
                ):
                    self._close_in_tx(row, "PAYMENT_TIMEOUT")
        with read_transaction(self.conn):
            row = self._visible(actor, order_id)
            return {**self._present(row, actor), "funds": self.funds.get_escrow(order_id)}

    def list_orders(self, actor, filters):
        if filters.keys() - {"direction", "status", "limit", "offset"}:
            raise BusinessError("INVALID_INPUT", "订单查询包含未知条件。")
        direction, status = filters.get("direction", "buy"), filters.get("status", "")
        if direction not in {"buy", "sell"} or (
            status and status not in {s.value for s in OrderStatus}
        ):
            raise BusinessError("INVALID_INPUT", "订单方向或状态无效。")
        limit, offset = pagination(filters.get("limit", 25), filters.get("offset", 0))
        with write_transaction(self.conn):
            self._expire_in_tx(timestamp(self.clock()), actor_id=actor.id)
        with read_transaction(self.conn):
            rows, total = orders.list_orders(self.conn, actor.id, direction, status, limit, offset)
            return {
                "items": [self._present(row, actor) for row in rows],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

    def _visible(self, actor, order_id):
        row = orders.get_by_id(self.conn, order_id)
        if row is None or actor.id not in {row["buyer_id"], row["seller_id"]}:
            raise BusinessError("NOT_FOUND", "订单不存在或当前不可访问。")
        return row

    @staticmethod
    def _require_party(actor, row, party):
        if actor.id != row[party]:
            raise BusinessError("FORBIDDEN", "此操作需要对应的订单参与者。")

    @staticmethod
    def _require_clear(row):
        if row["dispute_open"]:
            raise BusinessError("INVALID_STATE", "订单正在处理纠纷，当前操作暂停。")

    def _transition(self, row, fields):
        if orders.transition(self.conn, row["id"], row["status"], fields) != 1:
            raise BusinessError("INVALID_STATE", "订单状态已变化，请刷新后重试。")

    def _present(self, row, actor):
        result = {
            key: row[key]
            for key in [
                "id",
                "order_no",
                "buyer_id",
                "buyer_name",
                "seller_id",
                "seller_name",
                "product_id",
                "quantity",
                "unit_price_cents",
                "postage_cents",
                "total_cents",
                "delivery_mode",
                "status",
                "reservation_state",
                "created_at",
                "pay_due_at",
                "paid_at",
                "delivered_at",
                "auto_confirm_at",
                "completed_at",
                "closed_at",
                "close_reason",
            ]
        }
        result["snapshot"] = json.loads(row["snapshot_json"])
        result["dispute_open"] = bool(row["dispute_open"])
        result["allowed_actions"] = []
        if actor.id == row["buyer_id"] and row["status"] == OrderStatus.UNPAID:
            result["allowed_actions"] = ["close"]
            if self.clock() < datetime.fromisoformat(row["pay_due_at"]) and not row["dispute_open"]:
                result["allowed_actions"].append("pay")
        if not row["dispute_open"]:
            if actor.id == row["seller_id"] and row["status"] == OrderStatus.WAITING_DELIVERY:
                result["allowed_actions"].append("deliver")
            if actor.id == row["buyer_id"] and row["status"] == OrderStatus.DELIVERED:
                result["allowed_actions"].append("confirm")
        return result

    def _log(self, actor, action, order_id, before, after):
        logs.append(
            self.conn,
            actor_kind="USER" if actor else "SYSTEM",
            actor_id=actor.id if actor else None,
            action=action,
            object_type="ORDER",
            object_id=order_id,
            before=before,
            after=after,
            at=timestamp(self.clock()),
        )
        row = orders.get_by_id(self.conn, order_id)
        for user_id in {row["buyer_id"], row["seller_id"]}:
            notify_in_tx(
                self.conn,
                user_id,
                kind="ORDER",
                title="订单进度已更新",
                body=f"订单 {row['order_no']} 的状态已更新，请查看详情。",
                object_type="ORDER",
                object_id=order_id,
                event_key=f"order:{order_id}:{action}",
                at=timestamp(self.clock()),
            )
