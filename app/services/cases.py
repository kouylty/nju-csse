"""Reports and disputes coordinate evidence, orders, money and feedback atomically."""

from app.clock import now, timestamp
from app.db import read_transaction, write_transaction
from app.domain import Role
from app.errors import BusinessError
from app.product_rules import integer, text
from app.repositories import cases, files, logs, orders, products, social
from app.services.activity import notify_in_tx
from app.services.orders import OrderService
from app.services.products import ProductService
from app.services.social import message_filters, page_filters

KINDS = {"PRODUCT_REPORT", "CHAT_REPORT", "DISPUTE"}
STATUSES = {"OPEN", "PROCESSING", "RESOLVED"}


class CaseService:
    def __init__(self, conn, *, clock=now):
        self.conn, self.clock = conn, clock
        self.orders = OrderService(conn, clock=clock)
        self.products = ProductService(conn, clock=clock)

    def _visible(self, actor, case_id):
        row = cases.get(self.conn, case_id)
        if row is None or not (
            actor.id in {row["reporter_id"], row["respondent_id"]}
            or (actor.role == Role.ADMIN and actor.id == row["handler_id"])
        ):
            raise BusinessError("NOT_FOUND", "案件不存在或当前不可访问。")
        return row

    @staticmethod
    def _handler(actor, row):
        actor.require_admin()
        if row["handler_id"] != actor.id or row["status"] != "PROCESSING":
            raise BusinessError("FORBIDDEN", "请由当前受理管理员处理案件。")

    def _images(self, actor, image_ids):
        if not isinstance(image_ids, list) or len(image_ids) > 6:
            raise BusinessError("INVALID_INPUT", "每次最多提交六张证据图片。")
        for image_id in image_ids:
            integer(image_id, "image_ids", minimum=1)
            row = files.get_by_id(self.conn, image_id)
            if row is None or row["owner_id"] != actor.id:
                raise BusinessError("FORBIDDEN", "请使用本人上传的证据图片。")
        if len(set(image_ids)) != len(image_ids):
            raise BusinessError("INVALID_INPUT", "证据图片不能重复。")

    def submit(self, actor, *, kind, target_id, reason, image_ids=None):
        if not isinstance(kind, str) or kind not in KINDS:
            raise BusinessError("INVALID_INPUT", "请选择商品举报、聊天举报或订单纠纷。")
        integer(target_id, "target_id", minimum=1)
        reason = text(reason, "reason", 2000, required=True)
        image_ids = [] if image_ids is None else image_ids
        with write_transaction(self.conn):
            self._images(actor, image_ids)
            target = {"product_id": None, "conversation_id": None, "order_id": None}
            if kind == "PRODUCT_REPORT":
                product = products.get_by_id(self.conn, target_id)
                if product is None or product["status"] != "PUBLISHED":
                    raise BusinessError("NOT_FOUND", "商品不存在或当前不可举报。")
                respondent = product["seller_id"]
                target["product_id"] = target_id
            elif kind == "CHAT_REPORT":
                conversation = social.conversation(self.conn, target_id)
                if conversation is None or actor.id not in {
                    conversation["buyer_id"],
                    conversation["seller_id"],
                }:
                    raise BusinessError("NOT_FOUND", "会话不存在或当前不可访问。")
                respondent = (
                    conversation["seller_id"]
                    if actor.id == conversation["buyer_id"]
                    else conversation["buyer_id"]
                )
                target.update(product_id=conversation["product_id"], conversation_id=target_id)
            else:
                order = orders.get_by_id(self.conn, target_id)
                if order is None or actor.id not in {order["buyer_id"], order["seller_id"]}:
                    raise BusinessError("NOT_FOUND", "订单不存在或当前不可访问。")
                if cases.active_dispute(self.conn, target_id):
                    raise BusinessError("ACTIVE_CASE_EXISTS", "这笔订单已有处理中纠纷。")
                self.orders.mark_disputed_in_tx(target_id)
                respondent = (
                    order["seller_id"] if actor.id == order["buyer_id"] else order["buyer_id"]
                )
                conversation = social.for_product(self.conn, order["product_id"], order["buyer_id"])
                target.update(
                    product_id=order["product_id"],
                    order_id=target_id,
                    conversation_id=conversation["id"] if conversation else None,
                )
            if respondent == actor.id:
                raise BusinessError("INVALID_INPUT", "请针对其他用户的具体行为提交。")
            at = timestamp(self.clock())
            case_id = cases.insert(
                self.conn,
                {
                    "kind": kind,
                    "reporter_id": actor.id,
                    "respondent_id": respondent,
                    **target,
                    "reason": reason,
                    "created_at": at,
                },
            )
            cases.add_action(self.conn, case_id, actor.id, "SUBMITTED", reason, {}, at, image_ids)
            self._activity(actor, "CASE_SUBMITTED", case_id, {}, {"status": "OPEN", "kind": kind})
            self._notify(
                cases.get(self.conn, case_id),
                "SUBMITTED",
                "案件已提交",
                "请在案件详情查看进度并补充说明。",
            )
        return self.get_detail(actor, case_id)

    def list_cases(self, actor, filters, *, admin=False):
        if admin:
            actor.require_admin()
        limit, offset = page_filters(filters, {"kind", "status"})
        kind, status = filters.get("kind", ""), filters.get("status", "")
        if (kind and kind not in KINDS | {"REPORTS"}) or (
            status and status not in STATUSES | {"ACTIVE"}
        ):
            raise BusinessError("INVALID_INPUT", "案件类型或状态无效。")
        with read_transaction(self.conn):
            rows, total = cases.list_cases(
                self.conn,
                actor.id,
                admin=admin,
                kind=kind,
                status=status,
                limit=limit,
                offset=offset,
            )
            return {
                "items": [dict(row) for row in rows],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

    def get_detail(self, actor, case_id):
        with read_transaction(self.conn):
            row = self._visible(actor, case_id)
            return {
                **dict(row),
                "actions": cases.actions(self.conn, case_id),
                "can_handle": actor.role == Role.ADMIN
                and row["handler_id"] == actor.id
                and row["status"] == "PROCESSING",
            }

    def claim(self, actor, case_id):
        actor.require_admin()
        with write_transaction(self.conn):
            row = cases.get(self.conn, case_id)
            if row is None:
                raise BusinessError("NOT_FOUND", "案件不存在。")
            if actor.id in {row["reporter_id"], row["respondent_id"]}:
                raise BusinessError("FORBIDDEN", "请由第三方管理员受理此案件。")
            if row["status"] == "PROCESSING" and row["handler_id"] == actor.id:
                return self.get_detail(actor, case_id)
            if row["status"] != "OPEN":
                raise BusinessError("INVALID_STATE", "案件已受理或已结案，请刷新。")
            cases.update(
                self.conn, case_id, row["version"], {"handler_id": actor.id, "status": "PROCESSING"}
            )
            cases.add_action(
                self.conn,
                case_id,
                actor.id,
                "CLAIMED",
                "管理员已受理。",
                {},
                timestamp(self.clock()),
            )
            self._activity(
                actor, "CASE_CLAIMED", case_id, {"status": "OPEN"}, {"status": "PROCESSING"}
            )
            self._notify(
                cases.get(self.conn, case_id), "CLAIMED", "案件已受理", "管理员已开始处理案件。"
            )
        return self.get_detail(actor, case_id)

    def comment(self, actor, case_id, *, body, image_ids=None):
        body = text(body, "body", 2000, required=True)
        with write_transaction(self.conn):
            row = self._visible(actor, case_id)
            if row["status"] == "RESOLVED":
                raise BusinessError("INVALID_STATE", "案件已结案，可查看历史处理记录。")
            self._images(actor, [] if image_ids is None else image_ids)
            action_id = cases.add_action(
                self.conn,
                case_id,
                actor.id,
                "COMMENT",
                body,
                {},
                timestamp(self.clock()),
                image_ids or [],
            )
            cases.touch(self.conn, case_id)
            self._notify(
                row, f"COMMENT:{action_id}", "案件有新说明", "请查看案件详情中的补充说明。"
            )
        return self.get_detail(actor, case_id)

    def context(self, actor, case_id, filters):
        options = message_filters(filters)
        with write_transaction(self.conn):
            row = self._visible(actor, case_id)
            if actor.id not in {row["reporter_id"], row["respondent_id"]}:
                self._handler(actor, row)
                self._activity(
                    actor,
                    "CASE_CONTEXT_VIEWED",
                    case_id,
                    {},
                    {"order_id": row["order_id"], "conversation_id": row["conversation_id"]},
                )
            order = (
                self.orders.case_context_in_tx(row["order_id"], actor) if row["order_id"] else None
            )
            conversation_id = row["conversation_id"]
            if row["kind"] == "DISPUTE" and conversation_id is None:
                order_row = orders.get_by_id(self.conn, row["order_id"])
                conversation = social.for_product(
                    self.conn, row["product_id"], order_row["buyer_id"]
                )
                conversation_id = conversation["id"] if conversation else None
            items, more = (
                social.messages(self.conn, conversation_id, **options)
                if conversation_id
                else ([], False)
            )
            return {
                "order": order,
                "conversation_id": conversation_id,
                "messages": items,
                "has_more": more,
            }

    def resolve(
        self, actor, case_id, *, version, decision, reason, restore_stock=None, confirmation_plan=""
    ):
        actor.require_admin()
        integer(version, "version", minimum=1)
        if not isinstance(decision, str):
            raise BusinessError("INVALID_INPUT", "请选择有效的案件处置。")
        reason = text(reason, "reason", 2000, required=True)
        confirmation_plan = text(confirmation_plan, "confirmation_plan", 1000)
        request = {
            "decision": decision,
            "reason": reason,
            "restore_stock": restore_stock,
            "confirmation_plan": confirmation_plan,
        }
        with write_transaction(self.conn):
            row = self._visible(actor, case_id)
            if row["status"] == "RESOLVED":
                previous = cases.actions(self.conn, case_id)[-1]
                if row["handler_id"] == actor.id and previous["result"].get("request") == request:
                    return self.get_detail(actor, case_id)
                raise BusinessError("INVALID_STATE", "案件已结案，请查看已有结果。")
            self._handler(actor, row)
            if version != row["version"]:
                raise BusinessError("STALE_VERSION", "案件已更新，请刷新后处理。")
            if row["kind"] == "DISPUTE":
                result = self.orders.apply_resolution_in_tx(
                    actor,
                    row["order_id"],
                    decision,
                    restore_stock=restore_stock,
                    confirmation_plan=confirmation_plan,
                )
            elif row["kind"] == "PRODUCT_REPORT":
                if (
                    decision not in {"REJECT", "RECORD", "RECTIFY", "BLOCK"}
                    or restore_stock is not None
                    or confirmation_plan
                ):
                    raise BusinessError("INVALID_INPUT", "请选择有效的商品举报处理结果。")
                result = {"product_id": row["product_id"]}
                if decision in {"RECTIFY", "BLOCK"}:
                    self.products.take_down_in_tx(actor, row["product_id"], reason)
                    result["product_status"] = "BLOCKED"
            else:
                if (
                    decision not in {"REJECT", "RECORD"}
                    or restore_stock is not None
                    or confirmation_plan
                ):
                    raise BusinessError("INVALID_INPUT", "聊天举报支持驳回或记录处理意见。")
                result = {"conversation_id": row["conversation_id"]}
            at = timestamp(self.clock())
            cases.update(
                self.conn,
                case_id,
                row["version"],
                {
                    "status": "RESOLVED",
                    "decision": decision,
                    "resolution": reason,
                    "resolved_at": at,
                },
            )
            cases.add_action(
                self.conn,
                case_id,
                actor.id,
                "RESOLVED",
                reason,
                {"request": request, "execution": result},
                at,
            )
            self._activity(
                actor,
                "CASE_RESOLVED",
                case_id,
                {"status": row["status"]},
                {"status": "RESOLVED", "decision": decision, **result},
            )
            self._notify(row, "RESOLVED", "案件已处理", reason)
        return self.get_detail(actor, case_id)

    def _activity(self, actor, action, case_id, before, after):
        logs.append(
            self.conn,
            actor_kind="USER",
            actor_id=actor.id,
            action=action,
            object_type="CASE",
            object_id=case_id,
            before=before,
            after=after,
            at=timestamp(self.clock()),
        )

    def _notify(self, row, event, title, body):
        for user_id in {row["reporter_id"], row["respondent_id"], row["handler_id"]} - {None}:
            notify_in_tx(
                self.conn,
                user_id,
                kind="CASE",
                title=title,
                body=body,
                object_type="CASE",
                object_id=row["id"],
                event_key=f"case:{row['id']}:{event}",
                at=timestamp(self.clock()),
            )
