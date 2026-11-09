"""Append-only simulated money events for a single order."""


def insert(conn, *, order_id, kind, amount_cents, actor_id, created_at):
    return conn.execute(
        "INSERT INTO fund_transactions (order_id, kind, amount_cents, "
        "operation_key, actor_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (order_id, kind, amount_cents, f"order:{order_id}:{kind}", actor_id, created_at),
    ).lastrowid


def list_for(conn, order_id):
    return conn.execute(
        "SELECT id, kind, amount_cents, created_at FROM fund_transactions "
        "WHERE order_id = ? ORDER BY id",
        (order_id,),
    ).fetchall()


def by_kind(conn, order_id, kind):
    return conn.execute(
        "SELECT * FROM fund_transactions WHERE order_id = ? AND kind = ?", (order_id, kind)
    ).fetchone()
