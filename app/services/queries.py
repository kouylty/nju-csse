"""Seller statistics, administrator queues and object-scoped audit history."""

import json
from datetime import UTC, datetime, timedelta

from app.clock import timestamp
from app.db import read_transaction
from app.errors import BusinessError
from app.repositories import queries
from app.services.social import page_filters


def date_bounds(filters):
    bounds = []
    for key in ("start", "end"):
        value = filters.get(key, "")
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC) if value else None
            if parsed and parsed.strftime("%Y-%m-%d") != value:
                raise ValueError
            if key == "end" and parsed:
                parsed += timedelta(days=1)
            bounds.append(timestamp(parsed) if parsed else None)
        except (ValueError, TypeError, OverflowError):
            raise BusinessError("INVALID_INPUT", "日期请使用 YYYY-MM-DD。") from None
    if all(bounds) and bounds[0] >= bounds[1]:
        raise BusinessError("INVALID_INPUT", "开始日期不能晚于结束日期。")
    return bounds


class QueryService:
    def __init__(self, conn):
        self.conn = conn

    def seller_summary(self, actor, filters):
        limit, offset = page_filters(filters, {"start", "end"})
        start, end = date_bounds(filters)
        with read_transaction(self.conn):
            return queries.seller_summary(self.conn, actor.id, start, end, limit, offset)

    def admin_todos(self, actor):
        actor.require_admin()
        with read_transaction(self.conn):
            return queries.todos(self.conn)

    def search_logs(self, actor, filters, *, admin=False):
        if admin:
            actor.require_admin()
        limit, offset = page_filters(
            filters, {"start", "end", "actor", "product_id", "order_no", "action"}
        )
        start, end = date_bounds(filters)
        clauses, values = [], []
        if not admin:
            clauses.append(
                "(l.actor_id=? OR (l.object_type='PRODUCT' AND EXISTS "
                "(SELECT 1 FROM products p WHERE CAST(p.id AS TEXT)=l.object_id "
                "AND p.seller_id=?)) OR (l.object_type='ORDER' AND EXISTS "
                "(SELECT 1 FROM orders o WHERE CAST(o.id AS TEXT)=l.object_id "
                "AND (o.buyer_id=? OR o.seller_id=?))) OR (l.object_type='CASE' AND EXISTS "
                "(SELECT 1 FROM cases c WHERE CAST(c.id AS TEXT)=l.object_id "
                "AND (c.reporter_id=? OR c.respondent_id=?))) "
                "OR (l.object_type='USER' AND l.object_id=?))"
            )
            values.extend([actor.id] * 6 + [str(actor.id)])
        for bound, operator in [(start, ">="), (end, "<")]:
            if bound:
                clauses.append(f"l.occurred_at{operator}?")
                values.append(bound)
        for key, column in [("actor", "u.username"), ("action", "l.action")]:
            if filters.get(key):
                if not isinstance(filters[key], str) or len(filters[key]) > 100:
                    raise BusinessError("INVALID_INPUT", "日志筛选文本过长。")
                clauses.append(f"{column}=?")
                values.append(filters[key])
        if filters.get("product_id"):
            raw = str(filters["product_id"])
            if not raw.isascii() or not raw.isdecimal() or len(raw) > 16 or int(raw) < 1:
                raise BusinessError("INVALID_INPUT", "商品编号须为正整数。")
            clauses.append(
                "((l.object_type='PRODUCT' AND l.object_id=?) OR (l.object_type='ORDER' "
                "AND EXISTS (SELECT 1 FROM orders o WHERE CAST(o.id AS TEXT)=l.object_id "
                "AND o.product_id=?)) OR (l.object_type='CASE' AND EXISTS "
                "(SELECT 1 FROM cases c WHERE CAST(c.id AS TEXT)=l.object_id AND c.product_id=?)))"
            )
            values.extend([str(int(raw)), int(raw), int(raw)])
        if filters.get("order_no"):
            value = filters["order_no"]
            if not isinstance(value, str) or len(value) > 100:
                raise BusinessError("INVALID_INPUT", "订单号格式无效。")
            clauses.append(
                "((l.object_type='ORDER' AND EXISTS (SELECT 1 FROM orders o "
                "WHERE CAST(o.id AS TEXT)=l.object_id AND o.order_no=?)) OR "
                "(l.object_type='CASE' AND EXISTS (SELECT 1 FROM cases c "
                "JOIN orders o ON o.id=c.order_id "
                "WHERE CAST(c.id AS TEXT)=l.object_id AND o.order_no=?)))"
            )
            values.extend([value, value])
        with read_transaction(self.conn):
            rows, total = queries.search_logs(self.conn, clauses, values, limit, offset)
            items = []
            for row in rows:
                item = dict(row)
                item["before"] = json.loads(item.pop("before_json"))
                item["after"] = json.loads(item.pop("after_json"))
                items.append(item)
            return {"items": items, "total": total, "limit": limit, "offset": offset}
