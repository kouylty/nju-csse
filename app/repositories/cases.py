"""Case metadata, assigned handling and immutable evidence history."""

import json

SELECT_CASE = (
    "SELECT c.*,r.username AS reporter_name,t.username AS respondent_name,"
    "h.username AS handler_name,p.title AS product_title FROM cases c "
    "JOIN users r ON r.id=c.reporter_id JOIN users t ON t.id=c.respondent_id "
    "LEFT JOIN users h ON h.id=c.handler_id JOIN products p ON p.id=c.product_id "
)


def get(conn, case_id):
    return conn.execute(SELECT_CASE + "WHERE c.id=?", (case_id,)).fetchone()


def active_dispute(conn, order_id):
    return conn.execute(
        "SELECT id FROM cases WHERE order_id=? AND kind='DISPUTE' AND status!='RESOLVED'",
        (order_id,),
    ).fetchone()


def insert(conn, values):
    columns = tuple(values)
    return conn.execute(
        f"INSERT INTO cases ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
        list(values.values()),
    ).lastrowid


def add_action(conn, case_id, actor_id, kind, body, result, at, image_ids=()):
    action_id = conn.execute(
        "INSERT INTO case_actions (case_id,actor_id,kind,body,result_json,created_at) "
        "VALUES (?,?,?,?,?,?)",
        (case_id, actor_id, kind, body, json.dumps(result, ensure_ascii=False, sort_keys=True), at),
    ).lastrowid
    conn.executemany(
        "INSERT INTO case_images (action_id,file_id) VALUES (?,?)",
        [(action_id, image_id) for image_id in image_ids],
    )
    return action_id


def actions(conn, case_id):
    result = []
    for row in conn.execute(
        "SELECT a.*,u.username AS actor_name FROM case_actions a "
        "JOIN users u ON u.id=a.actor_id WHERE a.case_id=? ORDER BY a.id",
        (case_id,),
    ):
        item = dict(row)
        item["result"] = json.loads(item.pop("result_json"))
        item["images"] = [
            {"id": image[0], "url": f"/api/files/{image[0]}"}
            for image in conn.execute(
                "SELECT file_id FROM case_images WHERE action_id=? ORDER BY file_id", (row["id"],)
            )
        ]
        result.append(item)
    return result


def update(conn, case_id, version, fields):
    allowed = {"status", "handler_id", "resolution", "decision", "resolved_at"}
    if not fields or fields.keys() - allowed:
        raise ValueError("Unsupported case fields")
    return conn.execute(
        "UPDATE cases SET "
        + ",".join(f"{key}=?" for key in fields)
        + ",version=version+1 WHERE id=? AND version=?",
        [*fields.values(), case_id, version],
    ).rowcount


def touch(conn, case_id):
    conn.execute("UPDATE cases SET version=version+1 WHERE id=?", (case_id,))


def list_cases(conn, actor_id, *, admin, kind, status, limit, offset):
    clauses, values = [], []
    if not admin:
        clauses.append("(c.reporter_id=? OR c.respondent_id=?)")
        values.extend([actor_id, actor_id])
    if kind == "REPORTS":
        clauses.append("c.kind!='DISPUTE'")
    elif kind:
        clauses.append("c.kind=?")
        values.append(kind)
    if status == "ACTIVE":
        clauses.append("c.status!='RESOLVED'")
    elif status:
        clauses.append("c.status=?")
        values.append(status)
    clause = " AND ".join(clauses) or "1=1"
    rows = conn.execute(
        SELECT_CASE + "WHERE " + clause + " ORDER BY c.id DESC LIMIT ? OFFSET ?",
        [*values, limit, offset],
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM cases c WHERE " + clause, values).fetchone()[0]
    return rows, total
