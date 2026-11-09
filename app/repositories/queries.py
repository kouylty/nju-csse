"""Scoped aggregate and audit SQL; all filter values remain bound parameters."""


def seller_summary(conn, actor_id, start, end, limit, offset):
    completed = "o.seller_id=? AND o.status='COMPLETED'"
    settlements = "o.seller_id=? AND f.kind='SETTLEMENT'"
    order_values, fund_values = [actor_id], [actor_id]
    for bound, operator in [(start, ">="), (end, "<")]:
        if bound:
            completed += f" AND o.completed_at{operator}?"
            settlements += f" AND f.created_at{operator}?"
            order_values.append(bound)
            fund_values.append(bound)
    count, turnover = conn.execute(
        "SELECT COUNT(*),COALESCE(SUM(o.total_cents),0) FROM orders o WHERE " + completed,
        order_values,
    ).fetchone()
    fund_source = "FROM fund_transactions f JOIN orders o ON o.id=f.order_id WHERE " + settlements
    fund_count, settled = conn.execute(
        "SELECT COUNT(*),COALESCE(SUM(f.amount_cents),0) " + fund_source, fund_values
    ).fetchone()
    order_rows = conn.execute(
        "SELECT o.id,o.order_no,o.total_cents,o.completed_at FROM orders o WHERE "
        + completed
        + " ORDER BY o.completed_at DESC,o.id DESC LIMIT ? OFFSET ?",
        [*order_values, limit, offset],
    ).fetchall()
    fund_rows = conn.execute(
        "SELECT o.id AS order_id,o.order_no,f.amount_cents,f.created_at "
        + fund_source
        + " ORDER BY f.id DESC LIMIT ? OFFSET ?",
        [*fund_values, limit, offset],
    ).fetchall()
    return {
        "completed_order_count": count,
        "turnover_cents": turnover,
        "settled_cents": settled,
        "settlement_count": fund_count,
        "completed_orders": [dict(row) for row in order_rows],
        "settlements": [dict(row) for row in fund_rows],
        "limit": limit,
        "offset": offset,
    }


def todos(conn):
    products = conn.execute("SELECT COUNT(*) FROM products WHERE status='PENDING'").fetchone()[0]
    reports = conn.execute(
        "SELECT COUNT(*) FROM cases WHERE kind!='DISPUTE' AND status!='RESOLVED'"
    ).fetchone()[0]
    disputes = conn.execute(
        "SELECT COUNT(*) FROM cases WHERE kind='DISPUTE' AND status!='RESOLVED'"
    ).fetchone()[0]
    return {"pending_products": products, "pending_reports": reports, "pending_disputes": disputes}


def search_logs(conn, clauses, values, limit, offset):
    where = " AND ".join(clauses) or "1=1"
    source = "FROM operation_logs l LEFT JOIN users u ON u.id=l.actor_id WHERE " + where
    rows = conn.execute(
        "SELECT l.*,u.username AS actor_name " + source + " ORDER BY l.id DESC LIMIT ? OFFSET ?",
        [*values, limit, offset],
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) " + source, values).fetchone()[0]
    return rows, total
