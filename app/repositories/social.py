"""Persistence for conversations, immutable messages, evaluations and notifications."""

CONVERSATION = (
    "SELECT c.*, p.title AS product_title, b.username AS buyer_name, s.username AS seller_name "
    "FROM conversations c JOIN products p ON p.id=c.product_id "
    "JOIN users b ON b.id=c.buyer_id JOIN users s ON s.id=c.seller_id "
)


def conversation(conn, conversation_id):
    return conn.execute(CONVERSATION + "WHERE c.id=?", (conversation_id,)).fetchone()


def for_product(conn, product_id, buyer_id):
    return conn.execute(
        CONVERSATION + "WHERE c.product_id=? AND c.buyer_id=?", (product_id, buyer_id)
    ).fetchone()


def create_conversation(conn, product_id, buyer_id, seller_id, at):
    return conn.execute(
        "INSERT INTO conversations (product_id,buyer_id,seller_id,created_at,updated_at) "
        "VALUES (?,?,?,?,?)",
        (product_id, buyer_id, seller_id, at, at),
    ).lastrowid


def conversations(conn, actor_id, limit, offset):
    where = "WHERE c.buyer_id=? OR c.seller_id=?"
    rows = conn.execute(
        CONVERSATION + where + " ORDER BY c.updated_at DESC,c.id DESC LIMIT ? OFFSET ?",
        (actor_id, actor_id, limit, offset),
    ).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) FROM conversations c " + where, (actor_id, actor_id)
    ).fetchone()[0]
    return rows, total


def by_client_key(conn, sender_id, client_key):
    return conn.execute(
        "SELECT * FROM messages WHERE sender_id=? AND client_key=?", (sender_id, client_key)
    ).fetchone()


def add_message(conn, conversation_id, sender_id, order_id, body, client_key, at):
    message_id = conn.execute(
        "INSERT INTO messages (conversation_id,sender_id,order_id,body,client_key,created_at) "
        "VALUES (?,?,?,?,?,?)",
        (conversation_id, sender_id, order_id, body, client_key, at),
    ).lastrowid
    conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (at, conversation_id))
    return message_id


def messages(conn, conversation_id, *, after_id=None, before_id=None, limit=50):
    clause, values = "m.conversation_id=?", [conversation_id]
    if after_id is not None:
        clause += " AND m.id>?"
        values.append(after_id)
    if before_id is not None:
        clause += " AND m.id<?"
        values.append(before_id)
    rows = conn.execute(
        "SELECT m.id,m.conversation_id,m.sender_id,u.username AS sender_name,"
        "m.order_id,m.body,m.created_at FROM messages m JOIN users u ON u.id=m.sender_id WHERE "
        + clause
        + (" ORDER BY m.id ASC" if after_id is not None else " ORDER BY m.id DESC")
        + " LIMIT ?",
        [*values, limit + 1],
    ).fetchall()
    more = len(rows) > limit
    rows = rows[:limit]
    return (
        [dict(row) for row in rows]
        if after_id is not None
        else [dict(row) for row in reversed(rows)]
    ), more


def evaluation(conn, order_id, author_id):
    return conn.execute(
        "SELECT * FROM evaluations WHERE order_id=? AND author_id=?", (order_id, author_id)
    ).fetchone()


def add_evaluation(conn, order_id, author_id, recipient_id, rating, body, at):
    return conn.execute(
        "INSERT INTO evaluations (order_id,author_id,recipient_id,rating,body,created_at) "
        "VALUES (?,?,?,?,?,?)",
        (order_id, author_id, recipient_id, rating, body, at),
    ).lastrowid


def evaluations(conn, *, product_id=None, recipient_id=None, limit=25, offset=0):
    clause, values = (
        ("o.product_id=? AND e.author_id=o.buyer_id", [product_id])
        if product_id is not None
        else ("e.recipient_id=?", [recipient_id])
    )
    source = "FROM evaluations e JOIN orders o ON o.id=e.order_id JOIN users u ON u.id=e.author_id "
    rows = conn.execute(
        "SELECT e.id,e.order_id,e.author_id,u.username AS author_name,e.recipient_id,"
        "e.rating,e.body,e.created_at,o.product_id "
        + source
        + "WHERE "
        + clause
        + " ORDER BY e.id DESC LIMIT ? OFFSET ?",
        [*values, limit, offset],
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) " + source + "WHERE " + clause, values).fetchone()[0]
    return rows, total


def notify(conn, **values):
    columns = tuple(values)
    conn.execute(
        f"INSERT INTO notifications ({','.join(columns)}) "
        f"VALUES ({','.join('?' for _ in columns)}) "
        "ON CONFLICT(user_id,event_key) DO NOTHING",
        list(values.values()),
    )


def notifications(conn, user_id, unread, limit, offset):
    clause = "user_id=?" + (" AND read_at IS NULL" if unread else "")
    rows = conn.execute(
        "SELECT id,kind,title,body,object_type,object_id,created_at,read_at "
        "FROM notifications WHERE " + clause + " ORDER BY id DESC LIMIT ? OFFSET ?",
        (user_id, limit, offset),
    ).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE " + clause, (user_id,)
    ).fetchone()[0]
    count = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id=? AND read_at IS NULL", (user_id,)
    ).fetchone()[0]
    return rows, total, count


def mark_read(conn, user_id, notification_id, at):
    return conn.execute(
        "UPDATE notifications SET read_at=COALESCE(read_at,?) WHERE id=? AND user_id=?",
        (at, notification_id, user_id),
    ).rowcount


def order_evaluations(conn, order_id):
    return conn.execute(
        "SELECT e.id,e.author_id,u.username AS author_name,e.rating,e.body,e.created_at "
        "FROM evaluations e JOIN users u ON u.id=e.author_id "
        "WHERE e.order_id=? ORDER BY e.id",
        (order_id,),
    ).fetchall()


def related_orders(conn, conversation):
    return conn.execute(
        "SELECT id,order_no FROM orders WHERE product_id=? AND buyer_id=? AND seller_id=? "
        "ORDER BY id DESC LIMIT 100",
        (conversation["product_id"], conversation["buyer_id"], conversation["seller_id"]),
    ).fetchall()
