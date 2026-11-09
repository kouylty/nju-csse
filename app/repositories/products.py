"""SQL for current products, ordered images and immutable review submissions."""

import json

from app.product_rules import FIELDS

SELECT_PRODUCT = (
    "SELECT p.*, p.product_type AS type, u.username AS seller_name "
    "FROM products p JOIN users u ON u.id = p.seller_id "
)
COLUMNS = {
    field: ("product_type" if field == "type" else field) for field in FIELDS - {"image_ids"}
}


def get_by_id(conn, product_id):
    return conn.execute(SELECT_PRODUCT + "WHERE p.id = ?", (product_id,)).fetchone()


def insert(conn, seller_id, data, at):
    fields = list(COLUMNS)
    columns = ", ".join(COLUMNS[field] for field in fields)
    placeholders = ", ".join("?" for _ in fields)
    cursor = conn.execute(
        f"INSERT INTO products (seller_id, {columns}, created_at, updated_at) "
        f"VALUES (?, {placeholders}, ?, ?)",
        [seller_id, *(data[field] for field in fields), at, at],
    )
    return cursor.lastrowid


def update(conn, product_id, fields, at):
    columns = {
        **COLUMNS,
        **{
            key: key
            for key in [
                "status",
                "moderation_reason",
                "rectification_note",
                "rectification_requested_at",
            ]
        },
    }
    assignments = ", ".join(f"{columns[key]} = ?" for key in fields)
    conn.execute(
        f"UPDATE products SET {assignments}, version = version + 1, updated_at = ? WHERE id = ?",
        [*fields.values(), at, product_id],
    )


def set_images(conn, product_id, image_ids):
    conn.execute("DELETE FROM product_images WHERE product_id = ?", (product_id,))
    conn.executemany(
        "INSERT INTO product_images (product_id, file_id, position) VALUES (?, ?, ?)",
        [(product_id, file_id, index) for index, file_id in enumerate(image_ids)],
    )


def images_for(conn, product_ids):
    if not product_ids:
        return {}
    marks = ",".join("?" for _ in product_ids)
    rows = conn.execute(
        "SELECT i.product_id, f.id, f.content_type, f.width, f.height "
        "FROM product_images i JOIN files f ON f.id = i.file_id "
        f"WHERE i.product_id IN ({marks}) ORDER BY i.position",
        product_ids,
    ).fetchall()
    result = {}
    for row in rows:
        result.setdefault(row["product_id"], []).append(
            {
                "id": row["id"],
                "url": f"/api/files/{row['id']}",
                "content_type": row["content_type"],
                "width": row["width"],
                "height": row["height"],
            }
        )
    return result


def search(conn, clauses, values, *, sort, limit, offset):
    order = {
        "latest": "p.id DESC",
        "price_asc": "p.price_cents ASC, p.id DESC",
        "price_desc": "p.price_cents DESC, p.id DESC",
    }[sort]
    where = " AND ".join(clauses) or "1 = 1"
    rows = conn.execute(
        SELECT_PRODUCT + f"WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?",
        [*values, limit, offset],
    ).fetchall()
    total = conn.execute(f"SELECT COUNT(*) FROM products p WHERE {where}", values).fetchone()[0]
    return rows, total


def submit_review(conn, product_id, snapshot, image_ids, at):
    review_id = conn.execute(
        "INSERT INTO product_reviews (product_id, submitted_json, submitted_at) VALUES (?, ?, ?)",
        (product_id, json.dumps(snapshot, ensure_ascii=False, sort_keys=True), at),
    ).lastrowid
    conn.executemany(
        "INSERT INTO review_images (review_id, file_id) VALUES (?, ?)",
        [(review_id, file_id) for file_id in image_ids],
    )
    return review_id


def decide_review(conn, product_id, reviewer_id, approve, reason, at):
    cursor = conn.execute(
        "UPDATE product_reviews SET result = ?, reviewer_id = ?, reason = ?, reviewed_at = ? "
        "WHERE product_id = ? AND result = 'PENDING'",
        ("APPROVED" if approve else "REJECTED", reviewer_id, reason, at, product_id),
    )
    return cursor.rowcount


def review_history(conn, product_id):
    return conn.execute(
        "SELECT * FROM product_reviews WHERE product_id = ? ORDER BY id DESC",
        (product_id,),
    ).fetchall()


def reserve_stock(conn, product_id, quantity, at):
    return conn.execute(
        "UPDATE products SET available_stock = available_stock - ?, version = version + 1, "
        "updated_at = ? WHERE id = ? AND status = 'PUBLISHED' AND available_stock >= ?",
        (quantity, at, product_id, quantity),
    ).rowcount


def release_stock(conn, product_id, quantity, at):
    return conn.execute(
        "UPDATE products SET available_stock = available_stock + ?, version = version + 1, "
        "updated_at = ? WHERE id = ?",
        (quantity, at, product_id),
    ).rowcount
