"""Product publication workflow, permissions, revision checks and scoped search."""

import json

from app import product_rules as rules
from app.clock import now, timestamp
from app.db import write_transaction
from app.domain import PRODUCT_CATEGORIES, ProductStatus, Role
from app.errors import BusinessError
from app.repositories import files, logs, orders, products
from app.services.activity import notify_in_tx
from app.validation import pagination


class ProductService:
    def __init__(self, conn, *, clock=now):
        self.conn = conn
        self.clock = clock

    def _row(self, product_id):
        row = products.get_by_id(self.conn, product_id)
        if row is None:
            raise BusinessError("NOT_FOUND", "商品不存在。")
        return row

    def _editable(self, actor, product_id, version):
        row = self._row(product_id)
        if actor.id != row["seller_id"]:
            raise BusinessError("FORBIDDEN", "只能管理本人发布的商品。")
        self._version(row, version)
        return row

    @staticmethod
    def _version(row, version):
        rules.integer(version, "version", minimum=1)
        if row["version"] != version:
            raise BusinessError("STALE_VERSION", "商品已更新，请刷新后重新操作。")

    def _data(self, row):
        data = {key: row[key] for key in rules.FIELDS - {"image_ids"}}
        for key in ["allow_post", "allow_meet", "free_shipping"]:
            data[key] = bool(data[key])
        data["image_ids"] = [
            image["id"] for image in products.images_for(self.conn, [row["id"]]).get(row["id"], [])
        ]
        return data

    def _check_images(self, actor, image_ids):
        for file_id in image_ids:
            image = files.get_by_id(self.conn, file_id)
            if image is None or image["owner_id"] != actor.id:
                raise BusinessError("FORBIDDEN", "请使用本人上传的商品图片。")

    def create(self, actor, patch):
        data = rules.merge_product(rules.DEFAULTS, patch)
        with write_transaction(self.conn):
            self._check_images(actor, data["image_ids"])
            product_id = products.insert(self.conn, actor.id, data, timestamp(self.clock()))
            products.set_images(self.conn, product_id, data["image_ids"])
            self._log(actor, "PRODUCT_CREATED", product_id, {}, data)
        return self.get_detail(actor, product_id)

    def update(self, actor, product_id, version, patch):
        with write_transaction(self.conn):
            row = self._editable(actor, product_id, version)
            if row["status"] == ProductStatus.PENDING:
                raise BusinessError("INVALID_STATE", "审核期间请等待审核结果后再编辑。")
            before = self._data(row)
            data = rules.merge_product(before, patch)
            if data["available_stock"] + orders.held_quantity(self.conn, product_id) > 2**31 - 1:
                rules.invalid("可售量与订单占用量合计超出库存范围。", "available_stock")
            self._check_images(actor, data["image_ids"])
            needs_review = row["status"] == ProductStatus.PUBLISHED and any(
                data[key] != before[key] for key in rules.REVIEW_FIELDS
            )
            if row["status"] == ProductStatus.PUBLISHED:
                rules.require_complete(data, positive_stock=needs_review)
            fields = {key: data[key] for key in rules.FIELDS - {"image_ids"}}
            if needs_review:
                fields["status"] = ProductStatus.PENDING.value
            if row["status"] == ProductStatus.BLOCKED:
                fields["rectification_requested_at"] = None
            products.update(self.conn, product_id, fields, timestamp(self.clock()))
            products.set_images(self.conn, product_id, data["image_ids"])
            if needs_review:
                self._submit_snapshot(product_id, data)
            self._log(
                actor,
                "PRODUCT_UPDATED",
                product_id,
                before,
                {
                    **data,
                    "status": fields.get("status", row["status"]),
                },
            )
        return self.get_detail(actor, product_id)

    def submit_review(self, actor, product_id, version):
        with write_transaction(self.conn):
            row = self._editable(actor, product_id, version)
            if row["status"] not in {
                ProductStatus.DRAFT,
                ProductStatus.REJECTED,
                ProductStatus.OFFLINE,
            }:
                raise BusinessError("INVALID_STATE", "当前商品不能直接提交审核。")
            self._to_pending(actor, row, "PRODUCT_SUBMITTED")
        return self.get_detail(actor, product_id)

    def _to_pending(self, actor, row, action):
        data = self._data(row)
        rules.require_complete(data)
        self._submit_snapshot(row["id"], data)
        products.update(
            self.conn,
            row["id"],
            {
                "status": ProductStatus.PENDING.value,
                "rectification_requested_at": None,
                "moderation_reason": "",
            },
            timestamp(self.clock()),
        )
        self._log(actor, action, row["id"], {"status": row["status"]}, {"status": "PENDING"})

    def _submit_snapshot(self, product_id, data):
        products.submit_review(
            self.conn, product_id, data, data["image_ids"], timestamp(self.clock())
        )

    def review(self, actor, product_id, version, *, approve, reason=""):
        actor.require_admin()
        if type(approve) is not bool:
            rules.invalid("审核结果须为布尔值。", "approve")
        reason = rules.text(reason, "reason", required=not approve)
        with write_transaction(self.conn):
            row = self._row(product_id)
            self._version(row, version)
            if row["seller_id"] == actor.id:
                raise BusinessError("FORBIDDEN", "请由其他管理员审核本人商品。")
            if row["status"] != ProductStatus.PENDING:
                raise BusinessError("INVALID_STATE", "商品当前不在待审核状态。")
            if (
                products.decide_review(
                    self.conn, product_id, actor.id, approve, reason, timestamp(self.clock())
                )
                != 1
            ):
                raise BusinessError("INVALID_STATE", "没有可处理的审核提交。")
            status = ProductStatus.PUBLISHED if approve else ProductStatus.REJECTED
            products.update(
                self.conn, product_id, {"status": status.value}, timestamp(self.clock())
            )
            self._log(
                actor,
                "PRODUCT_REVIEWED",
                product_id,
                {"status": "PENDING"},
                {
                    "status": status.value,
                    "reason": reason,
                },
            )
        return self.get_detail(actor, product_id)

    def take_down(self, actor, product_id, version, *, violation=False, reason=""):
        if violation:
            actor.require_admin()
        reason = rules.text(reason, "reason", required=violation)
        with write_transaction(self.conn):
            row = self._row(product_id) if violation else self._editable(actor, product_id, version)
            self._version(row, version)
            if row["status"] != ProductStatus.PUBLISHED:
                raise BusinessError("INVALID_STATE", "仅已发布商品可以下架。")
            status = ProductStatus.BLOCKED if violation else ProductStatus.OFFLINE
            products.update(
                self.conn,
                product_id,
                {"status": status.value, "moderation_reason": reason if violation else ""},
                timestamp(self.clock()),
            )
            self._log(
                actor,
                "PRODUCT_BLOCKED" if violation else "PRODUCT_OFFLINE",
                product_id,
                {"status": row["status"]},
                {"status": status.value, "reason": reason},
            )
        return self.get_detail(actor, product_id)

    def request_rectification(self, actor, product_id, version, note):
        note = rules.text(note, "note", required=True)
        with write_transaction(self.conn):
            row = self._editable(actor, product_id, version)
            if row["status"] != ProductStatus.BLOCKED:
                raise BusinessError("INVALID_STATE", "仅违规下架商品需要整改复核。")
            products.update(
                self.conn,
                product_id,
                {
                    "rectification_note": note,
                    "rectification_requested_at": timestamp(self.clock()),
                },
                timestamp(self.clock()),
            )
            self._log(actor, "RECTIFICATION_REQUESTED", product_id, {}, {"note": note})
        return self.get_detail(actor, product_id)

    def reopen_review(self, actor, product_id, version):
        actor.require_admin()
        with write_transaction(self.conn):
            row = self._row(product_id)
            self._version(row, version)
            if row["status"] != ProductStatus.BLOCKED or not row["rectification_requested_at"]:
                raise BusinessError("INVALID_STATE", "请等待卖家提交整改说明。")
            if row["seller_id"] == actor.id:
                raise BusinessError("FORBIDDEN", "请由其他管理员复核本人商品。")
            self._to_pending(actor, row, "RECTIFICATION_APPROVED")
        return self.get_detail(actor, product_id)

    def get_detail(self, actor, product_id):
        row = self._row(product_id)
        owner = actor is not None and actor.id == row["seller_id"]
        manager = (
            actor is not None and actor.role == Role.ADMIN and row["status"] != ProductStatus.DRAFT
        )
        if row["status"] != ProductStatus.PUBLISHED and not (owner or manager):
            raise BusinessError("NOT_FOUND", "商品不存在或当前不可访问。")
        result = self._present(
            row, products.images_for(self.conn, [product_id]).get(product_id, [])
        )
        result["allowed_actions"] = []
        if owner and row["status"] != ProductStatus.PENDING:
            result["allowed_actions"].append("edit")
            if row["status"] in {
                ProductStatus.DRAFT,
                ProductStatus.REJECTED,
                ProductStatus.OFFLINE,
            }:
                result["allowed_actions"].append("submit")
            if row["status"] == ProductStatus.PUBLISHED:
                result["allowed_actions"].append("take_down")
            if row["status"] == ProductStatus.BLOCKED:
                result["allowed_actions"].append("rectify")
        if manager and not owner:
            if row["status"] == ProductStatus.PENDING:
                result["allowed_actions"].append("review")
            if row["status"] == ProductStatus.PUBLISHED:
                result["allowed_actions"].append("block")
            if row["status"] == ProductStatus.BLOCKED and row["rectification_requested_at"]:
                result["allowed_actions"].append("reopen")
        if owner or manager:
            result["reviews"] = [
                {**dict(review), "submitted": json.loads(review["submitted_json"])}
                for review in products.review_history(self.conn, product_id)
            ]
            for review in result["reviews"]:
                del review["submitted_json"]
            result["rectification_note"] = row["rectification_note"]
            result["moderation_reason"] = row["moderation_reason"]
            result["rectification_requested_at"] = row["rectification_requested_at"]
        return result

    @staticmethod
    def _present(row, images):
        data = {key: row[key] for key in rules.FIELDS - {"image_ids"}}
        for key in ["allow_post", "allow_meet", "free_shipping"]:
            data[key] = bool(data[key])
        return {
            **data,
            "id": row["id"],
            "seller_id": row["seller_id"],
            "seller_name": row["seller_name"],
            "status": row["status"],
            "version": row["version"],
            "images": images,
            "image_ids": [image["id"] for image in images],
            "availability": "available" if row["available_stock"] else "sold_out",
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def search(self, actor, filters, *, scope="public"):
        allowed = {
            "q",
            "category",
            "type",
            "min_price_cents",
            "max_price_cents",
            "availability",
            "status",
            "sort",
            "limit",
            "offset",
        }
        if filters.keys() - allowed:
            rules.invalid("查询中包含未知条件。", "filters")
        clauses, values = [], []
        if scope == "public":
            clauses.append("p.status = 'PUBLISHED'")
            if filters.get("status", "PUBLISHED") != "PUBLISHED":
                rules.invalid("公开查询仅提供已发布商品。", "status")
        elif scope == "mine":
            if actor is None:
                raise BusinessError("AUTH_REQUIRED", "请先登录。")
            clauses.append("p.seller_id = ?")
            values.append(actor.id)
        else:
            actor.require_admin()
            clauses.append("(p.status != 'DRAFT' OR p.seller_id = ?)")
            values.append(actor.id)
        status = filters.get("status")
        if status:
            if status not in {item.value for item in ProductStatus}:
                rules.invalid("商品状态无效。", "status")
            clauses.append("p.status = ?")
            values.append(status)
        for key, column, choices in [
            ("category", "category", PRODUCT_CATEGORIES),
            ("type", "product_type", ("GOODS", "SERVICE")),
        ]:
            if filters.get(key):
                if filters[key] not in choices:
                    rules.invalid("筛选条件无效。", key)
                clauses.append(f"p.{column} = ?")
                values.append(filters[key])
        bounds = {}
        for key, operator in [("min_price_cents", ">="), ("max_price_cents", "<=")]:
            if filters.get(key) not in (None, ""):
                raw = str(filters[key])
                if not raw.isascii() or not raw.isdecimal() or len(raw) > 16:
                    rules.invalid("价格筛选须为整数分。", key)
                bounds[key] = rules.integer(int(raw), key)
                clauses.append(f"p.price_cents {operator} ?")
                values.append(bounds[key])
        if bounds.get("min_price_cents", 0) > bounds.get("max_price_cents", rules.MAX_MONEY):
            rules.invalid("最低价格不能超过最高价格。", "min_price_cents")
        keyword = rules.text(filters.get("q", ""), "q", 100)
        if keyword:
            pattern = (
                "%" + keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            )
            clauses.append("(p.title LIKE ? ESCAPE '\\' OR p.description LIKE ? ESCAPE '\\')")
            values.extend([pattern, pattern])
        availability = filters.get("availability", "available" if scope == "public" else "all")
        if availability not in {"available", "sold_out", "all"}:
            rules.invalid("库存筛选无效。", "availability")
        if availability != "all":
            clauses.append(
                "p.available_stock > 0" if availability == "available" else "p.available_stock = 0"
            )
        sort = filters.get("sort", "latest")
        if sort not in {"latest", "price_asc", "price_desc"}:
            rules.invalid("排序条件无效。", "sort")
        limit, offset = pagination(filters.get("limit", 25), filters.get("offset", 0))
        rows, total = products.search(
            self.conn, clauses, values, sort=sort, limit=limit, offset=offset
        )
        images = products.images_for(self.conn, [row["id"] for row in rows])
        return {
            "items": [self._present(row, images.get(row["id"], [])) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def _log(self, actor, action, product_id, before, after):
        logs.append(
            self.conn,
            actor_kind="USER",
            actor_id=actor.id,
            action=action,
            object_type="PRODUCT",
            object_id=product_id,
            before=before,
            after=after,
            at=timestamp(self.clock()),
        )
        if action in {"PRODUCT_REVIEWED", "PRODUCT_BLOCKED", "RECTIFICATION_APPROVED"}:
            row = products.get_by_id(self.conn, product_id)
            notify_in_tx(
                self.conn,
                row["seller_id"],
                kind="PRODUCT",
                title="商品处理结果",
                body=after.get("reason") or f"商品当前状态：{after.get('status', row['status'])}。",
                object_type="PRODUCT",
                object_id=product_id,
                event_key=f"product:{product_id}:{action}:{row['version']}",
                at=timestamp(self.clock()),
            )

    def take_down_in_tx(self, actor, product_id, reason):
        actor.require_admin()
        if not self.conn.in_transaction:
            raise RuntimeError("Case moderation requires the caller's transaction")
        row = self._row(product_id)
        if actor.id == row["seller_id"]:
            raise BusinessError("FORBIDDEN", "请由第三方管理员处理。")
        if row["status"] not in {"PUBLISHED", "BLOCKED"}:
            raise BusinessError("INVALID_STATE", "商品状态已变化，请核对后记录处理意见。")
        if row["status"] == "PUBLISHED":
            products.update(
                self.conn,
                product_id,
                {"status": "BLOCKED", "moderation_reason": reason},
                timestamp(self.clock()),
            )
            self._log(
                actor,
                "PRODUCT_BLOCKED",
                product_id,
                {"status": row["status"]},
                {"status": "BLOCKED", "reason": reason},
            )

    def reserve_stock_in_tx(self, product_id, quantity):
        if not self.conn.in_transaction:
            raise RuntimeError("Inventory reservation requires the caller's transaction")
        rules.integer(quantity, "quantity", minimum=1, maximum=2**31 - 1)
        if products.reserve_stock(self.conn, product_id, quantity, timestamp(self.clock())) != 1:
            raise BusinessError("OUT_OF_STOCK", "可售库存不足，请刷新商品后重试。")

    def release_stock_in_tx(self, product_id, quantity):
        if not self.conn.in_transaction:
            raise RuntimeError("Inventory release requires the caller's transaction")
        rules.integer(quantity, "quantity", minimum=1, maximum=2**31 - 1)
        if products.release_stock(self.conn, product_id, quantity, timestamp(self.clock())) != 1:
            raise BusinessError("INVARIANT_VIOLATION", "库存记录不完整，本次操作已撤销。")
