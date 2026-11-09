"""Order persistence with conditional transitions and durable request uniqueness."""

SELECT_ORDER = (
    "SELECT o.*, b.username AS buyer_name, s.username AS seller_name FROM orders o "
    "JOIN users b ON b.id = o.buyer_id JOIN users s ON s.id = o.seller_id "
)


def get_by_id(conn, order_id):
    return conn.execute(SELECT_ORDER + "WHERE o.id = ?", (order_id,)).fetchone()


def by_request(conn, buyer_id, request_key):
    return conn.execute(
        "SELECT * FROM orders WHERE buyer_id = ? AND request_key = ?", (buyer_id, request_key)
    ).fetchone()


def unpaid_for(conn, buyer_id, product_id):
    return conn.execute(
        "SELECT * FROM orders WHERE buyer_id = ? AND product_id = ? AND status = 'UNPAID'",
        (buyer_id, product_id),
    ).fetchone()


def insert(conn, values):
    fields = tuple(values)
    return conn.execute(
        f"INSERT INTO orders ({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})",
        [values[field] for field in fields],
    ).lastrowid


def bind_images(conn, order_id, image_ids):
    conn.executemany(
        "INSERT INTO order_images (order_id, file_id) VALUES (?, ?)",
        [(order_id, file_id) for file_id in image_ids],
    )


def transition(conn, order_id, expected_status, fields):
    allowed = {
        "status",
        "reservation_state",
        "paid_at",
        "delivered_at",
        "auto_confirm_at",
        "completed_at",
        "closed_at",
        "close_reason",
        "dispute_open",
    }
    if not fields or fields.keys() - allowed:
        raise ValueError("Unsupported order transition fields")
    assignments = ", ".join(f"{field} = ?" for field in fields)
    return conn.execute(
        f"UPDATE orders SET {assignments} WHERE id = ? AND status = ?",
        [*fields.values(), order_id, expected_status],
    ).rowcount


def expired(conn, at, *, product_id=None, actor_id=None):
    clauses = ["status = 'UNPAID'", "pay_due_at <= ?"]
    values = [at]
    if product_id is not None:
        clauses.append("product_id = ?")
        values.append(product_id)
    if actor_id is not None:
        clauses.append("(buyer_id = ? OR seller_id = ?)")
        values.extend([actor_id, actor_id])
    return conn.execute(
        "SELECT * FROM orders WHERE " + " AND ".join(clauses) + " ORDER BY id", values
    ).fetchall()


def held_quantity(conn, product_id):
    return conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM orders "
        "WHERE product_id = ? AND reservation_state = 'HELD'",
        (product_id,),
    ).fetchone()[0]


def list_orders(conn, actor_id, direction, status, limit, offset):
    column = "buyer_id" if direction == "buy" else "seller_id"
    clause, values = f"o.{column} = ?", [actor_id]
    if status:
        clause += " AND o.status = ?"
        values.append(status)
    rows = conn.execute(
        SELECT_ORDER + f"WHERE {clause} ORDER BY o.id DESC LIMIT ? OFFSET ?",
        [*values, limit, offset],
    ).fetchall()
    total = conn.execute(f"SELECT COUNT(*) FROM orders o WHERE {clause}", values).fetchone()[0]
    return rows, total
