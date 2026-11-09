"""Participant-scoped communication, verified-trade evaluations and personal notices."""

import re

from app.clock import now, timestamp
from app.db import read_transaction, write_transaction
from app.errors import BusinessError
from app.product_rules import integer, text
from app.repositories import orders, products, social, users
from app.services.activity import notify_in_tx
from app.validation import pagination


def page_filters(filters, allowed=()):
    if filters.keys() - {"limit", "offset", *allowed}:
        raise BusinessError("INVALID_INPUT", "查询包含未知条件。")
    return pagination(filters.get("limit", 25), filters.get("offset", 0))


def message_filters(filters):
    if filters.keys() - {"before_id", "after_id", "limit"} or (
        "before_id" in filters and "after_id" in filters
    ):
        raise BusinessError("INVALID_INPUT", "请选择单一消息查询方向。")
    limit, _ = pagination(filters.get("limit", 50), 0)
    result = {"limit": limit}
    for key in ("before_id", "after_id"):
        if key in filters:
            value = str(filters[key])
            if not value.isascii() or not value.isdecimal() or len(value) > 16:
                raise BusinessError("INVALID_INPUT", "消息位置须为非负整数。")
            result[key] = integer(int(value), key)
    return result


class SocialService:
    def __init__(self, conn, *, clock=now):
        self.conn, self.clock = conn, clock

    def _conversation(self, actor, conversation_id):
        row = social.conversation(self.conn, conversation_id)
        if row is None or actor.id not in {row["buyer_id"], row["seller_id"]}:
            raise BusinessError("NOT_FOUND", "会话不存在或当前不可访问。")
        return row

    @staticmethod
    def _related_order(row, order):
        if order is None or any(
            row[key] != order[key] for key in ("product_id", "buyer_id", "seller_id")
        ):
            raise BusinessError("INVALID_INPUT", "请选择本会话双方就此商品形成的订单。")

    def open_conversation(self, actor, product_id, order_id=None):
        integer(product_id, "product_id", minimum=1)
        if order_id is not None:
            integer(order_id, "order_id", minimum=1)
        with write_transaction(self.conn):
            product = products.get_by_id(self.conn, product_id)
            if product is None:
                raise BusinessError("NOT_FOUND", "商品不存在。")
            buyer_id = actor.id
            if order_id is not None:
                order = orders.get_by_id(self.conn, order_id)
                if (
                    order is None
                    or order["product_id"] != product_id
                    or actor.id not in {order["buyer_id"], order["seller_id"]}
                ):
                    raise BusinessError("NOT_FOUND", "订单不存在或当前不可访问。")
                buyer_id = order["buyer_id"]
            if buyer_id == product["seller_id"]:
                raise BusinessError("INVALID_INPUT", "请选择其他用户进行沟通。")
            row = social.for_product(self.conn, product_id, buyer_id)
            if row is None:
                if product["status"] != "PUBLISHED" and order_id is None:
                    raise BusinessError("PRODUCT_UNAVAILABLE", "当前商品已关闭新的咨询入口。")
                at = timestamp(self.clock())
                conversation_id = social.create_conversation(
                    self.conn, product_id, buyer_id, product["seller_id"], at
                )
                row = social.conversation(self.conn, conversation_id)
            return dict(row)

    def list_conversations(self, actor, filters):
        limit, offset = page_filters(filters)
        with read_transaction(self.conn):
            rows, total = social.conversations(self.conn, actor.id, limit, offset)
            return {
                "items": [dict(row) for row in rows],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

    def list_messages(self, actor, conversation_id, filters):
        options = message_filters(filters)
        with read_transaction(self.conn):
            row = self._conversation(actor, conversation_id)
            items, more = social.messages(self.conn, conversation_id, **options)
            return {
                "conversation": dict(row),
                "related_orders": [dict(order) for order in social.related_orders(self.conn, row)]
                if not ({"before_id", "after_id"} & filters.keys())
                else [],
                "items": items,
                "has_more": more,
                "limit": options["limit"],
            }

    def send_message(self, actor, conversation_id, *, body, client_key, order_id=None):
        body = text(body, "body", 2000, required=True)
        if (
            not isinstance(client_key, str)
            or re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", client_key) is None
        ):
            raise BusinessError("INVALID_INPUT", "请使用有效的消息请求标识。")
        if order_id is not None:
            integer(order_id, "order_id", minimum=1)
        with write_transaction(self.conn):
            row = self._conversation(actor, conversation_id)
            original = social.by_client_key(self.conn, actor.id, client_key)
            if original is not None:
                if any(
                    original[key] != value
                    for key, value in {
                        "conversation_id": conversation_id,
                        "order_id": order_id,
                        "body": body,
                    }.items()
                ):
                    raise BusinessError("REQUEST_KEY_REUSED", "消息请求标识已用于其他内容。")
                return {"id": original["id"], "replayed": True}
            if order_id is not None:
                self._related_order(row, orders.get_by_id(self.conn, order_id))
            at = timestamp(self.clock())
            message_id = social.add_message(
                self.conn, conversation_id, actor.id, order_id, body, client_key, at
            )
            recipient = row["seller_id"] if actor.id == row["buyer_id"] else row["buyer_id"]
            notify_in_tx(
                self.conn,
                recipient,
                kind="MESSAGE",
                title="收到新消息",
                body="你有一条新的站内消息。",
                object_type="CONVERSATION",
                object_id=conversation_id,
                event_key=f"message:{message_id}",
                at=at,
            )
            return {"id": message_id, "replayed": False}

    def evaluate_order(self, actor, order_id, *, rating, body):
        integer(rating, "rating", minimum=1, maximum=5)
        body = text(body, "body", 1000, required=True)
        with write_transaction(self.conn):
            order = orders.get_by_id(self.conn, order_id)
            if order is None or actor.id not in {order["buyer_id"], order["seller_id"]}:
                raise BusinessError("NOT_FOUND", "订单不存在或当前不可访问。")
            if order["status"] != "COMPLETED":
                raise BusinessError("INVALID_STATE", "请在交易完成后评价。")
            if social.evaluation(self.conn, order_id, actor.id) is not None:
                raise BusinessError("ALREADY_EVALUATED", "你已评价过这笔订单。")
            recipient = order["seller_id"] if actor.id == order["buyer_id"] else order["buyer_id"]
            at = timestamp(self.clock())
            evaluation_id = social.add_evaluation(
                self.conn, order_id, actor.id, recipient, rating, body, at
            )
            notify_in_tx(
                self.conn,
                recipient,
                kind="EVALUATION",
                title="收到交易评价",
                body="一笔已完成订单收到新的评价。",
                object_type="ORDER",
                object_id=order_id,
                event_key=f"evaluation:{evaluation_id}",
                at=at,
            )
            return {
                "id": evaluation_id,
                "order_id": order_id,
                "author_id": actor.id,
                "recipient_id": recipient,
                "rating": rating,
                "body": body,
                "created_at": at,
            }

    def list_evaluations(self, filters, *, product_id=None, user_id=None):
        limit, offset = page_filters(filters)
        with read_transaction(self.conn):
            if user_id is not None and users.get_by_id(self.conn, user_id) is None:
                raise BusinessError("NOT_FOUND", "账号不存在。")
            if product_id is not None:
                product = products.get_by_id(self.conn, product_id)
                if product is None or product["status"] != "PUBLISHED":
                    raise BusinessError("NOT_FOUND", "商品不存在或当前不可访问。")
            rows, total = social.evaluations(
                self.conn, product_id=product_id, recipient_id=user_id, limit=limit, offset=offset
            )
            return {
                "items": [dict(row) for row in rows],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

    def order_evaluations(self, actor, order_id):
        with read_transaction(self.conn):
            order = orders.get_by_id(self.conn, order_id)
            if order is None or actor.id not in {order["buyer_id"], order["seller_id"]}:
                raise BusinessError("NOT_FOUND", "订单不存在或当前不可访问。")
            return {"items": [dict(row) for row in social.order_evaluations(self.conn, order_id)]}

    def list_notifications(self, actor, filters):
        limit, offset = page_filters(filters, {"unread"})
        if filters.get("unread", "false") not in {"true", "false"}:
            raise BusinessError("INVALID_INPUT", "unread 须为 true 或 false。")
        with read_transaction(self.conn):
            rows, total, count = social.notifications(
                self.conn, actor.id, filters.get("unread") == "true", limit, offset
            )
            return {
                "items": [dict(row) for row in rows],
                "total": total,
                "unread_count": count,
                "limit": limit,
                "offset": offset,
            }

    def mark_notification_read(self, actor, notification_id):
        with write_transaction(self.conn):
            if social.mark_read(self.conn, actor.id, notification_id, timestamp(self.clock())) != 1:
                raise BusinessError("NOT_FOUND", "通知不存在或当前不可访问。")
        return {"id": notification_id, "read": True}
