"""Account and authentication-session persistence."""

import sqlite3


def get_by_id(conn, user_id):
    return conn.execute(
        "SELECT id,username,role,created_at FROM users WHERE id=?", (user_id,)
    ).fetchone()


def get_by_key(conn: sqlite3.Connection, key: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM users WHERE username_key = ?", (key,)).fetchone()


def insert(conn, *, username, username_key, password_hash, role, created_at) -> int:
    cursor = conn.execute(
        "INSERT INTO users (username, username_key, password_hash, role, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (username, username_key, password_hash, role, created_at),
    )
    return cursor.lastrowid


def count_admins(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM users WHERE role = 'ADMIN'").fetchone()[0]


def set_role(conn, user_id: int, role: str) -> None:
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))


def list_users(conn, limit: int, offset: int) -> tuple[list[sqlite3.Row], int]:
    rows = conn.execute(
        "SELECT id, username, role, created_at FROM users ORDER BY id LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    return rows, total


def insert_session(conn, *, token_hash, user_id, created_at, expires_at) -> None:
    conn.execute(
        "INSERT INTO auth_sessions (token_hash, user_id, created_at, expires_at) "
        "VALUES (?, ?, ?, ?)",
        (token_hash, user_id, created_at, expires_at),
    )


def get_session(conn, token_hash: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT users.id, users.username, users.role, auth_sessions.expires_at "
        "FROM auth_sessions JOIN users ON users.id = auth_sessions.user_id "
        "WHERE token_hash = ?",
        (token_hash,),
    ).fetchone()


def delete_session(conn, token_hash: str) -> None:
    conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))


def delete_expired_sessions(conn, now: str) -> None:
    conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now,))
