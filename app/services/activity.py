"""Notifications participate in the caller's business transaction."""

from app.clock import now, timestamp
from app.repositories import social


def notify_in_tx(conn, user_id, *, kind, title, body, object_type, object_id, event_key, at=None):
    if not conn.in_transaction:
        raise RuntimeError("Notifications require the caller's transaction")
    social.notify(
        conn,
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        object_type=object_type,
        object_id=object_id,
        event_key=event_key,
        created_at=at or timestamp(now()),
    )
