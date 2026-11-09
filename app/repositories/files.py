"""File ownership and access through business references."""


def insert(conn, *, owner_id, storage_key, content_type, size_bytes, width, height, created_at):
    return conn.execute(
        "INSERT INTO files (owner_id, storage_key, content_type, size_bytes, "
        "width, height, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (owner_id, storage_key, content_type, size_bytes, width, height, created_at),
    ).lastrowid


def get_by_id(conn, file_id):
    return conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()


def publicly_visible(conn, file_id):
    return (
        conn.execute(
            "SELECT 1 FROM product_images i JOIN products p ON p.id = i.product_id "
            "WHERE i.file_id = ? AND p.status = 'PUBLISHED' LIMIT 1",
            (file_id,),
        ).fetchone()
        is not None
    )


def reviewable(conn, file_id):
    return (
        conn.execute(
            "SELECT 1 FROM products p WHERE p.status != 'DRAFT' AND ("
            "EXISTS (SELECT 1 FROM product_images i "
            "WHERE i.product_id = p.id AND i.file_id = ?) OR "
            "EXISTS (SELECT 1 FROM review_images ri JOIN product_reviews r ON r.id = ri.review_id "
            "WHERE r.product_id = p.id AND ri.file_id = ?)) LIMIT 1",
            (file_id, file_id),
        ).fetchone()
        is not None
    )


def order_visible(conn, file_id, user_id):
    return (
        conn.execute(
            "SELECT 1 FROM order_images i JOIN orders o ON o.id = i.order_id "
            "WHERE i.file_id = ? AND (o.buyer_id = ? OR o.seller_id = ?) LIMIT 1",
            (file_id, user_id, user_id),
        ).fetchone()
        is not None
    )


def case_access(conn, file_id, user_id):
    return conn.execute(
        "SELECT c.id FROM case_images i JOIN case_actions a ON a.id=i.action_id "
        "JOIN cases c ON c.id=a.case_id WHERE i.file_id=? AND "
        "(c.reporter_id=? OR c.respondent_id=? OR (c.handler_id=? AND c.status='PROCESSING' "
        "AND EXISTS (SELECT 1 FROM users h WHERE h.id=c.handler_id AND h.role='ADMIN'))) "
        "ORDER BY c.id LIMIT 1",
        (file_id, user_id, user_id, user_id),
    ).fetchone()
