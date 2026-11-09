"""Append-only records for the business operations implemented so far."""

import json


def append(conn, *, actor_kind, actor_id, action, object_type, object_id, before, after, at):
    conn.execute(
        "INSERT INTO operation_logs "
        "(actor_kind, actor_id, action, object_type, object_id, "
        "before_json, after_json, occurred_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            actor_kind,
            actor_id,
            action,
            object_type,
            str(object_id),
            json.dumps(before, ensure_ascii=False, sort_keys=True),
            json.dumps(after, ensure_ascii=False, sort_keys=True),
            at,
        ),
    )
