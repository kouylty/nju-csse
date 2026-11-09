"""Account rules and revocable sessions. All write operations own one transaction."""

import hashlib
import secrets
import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from app import validation
from app.clock import now, timestamp
from app.db import write_transaction
from app.domain import Actor, AuthenticatedSession, LoginResult, Role
from app.errors import BusinessError
from app.repositories import logs, users

# A missing account still performs a password hash check.
_DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(32))


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def actor_from(row) -> Actor:
    return Actor(row["id"], row["username"], Role(row["role"]))


class AuthService:
    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        clock: Callable[[], datetime] = now,
        session_ttl_seconds: int = 28800,
    ):
        self.conn = conn
        self.clock = clock
        self.session_ttl = timedelta(seconds=session_ttl_seconds)

    def register(self, username: object, password: object) -> Actor:
        return self._create_user(username, password, Role.USER)

    def create_admin(self, username: object, password: object) -> Actor:
        """Bootstrap the first administrator through a trusted local command."""
        return self._create_user(username, password, Role.ADMIN)

    def _create_user(self, username: object, password: object, role: Role) -> Actor:
        name = validation.username(username)
        hashed = generate_password_hash(validation.password(password))
        try:
            with write_transaction(self.conn):
                if role == Role.ADMIN and users.count_admins(self.conn):
                    raise BusinessError(
                        "ADMIN_EXISTS", "首个管理员已建立，后续账号请使用 set-admin。"
                    )
                user_id = users.insert(
                    self.conn,
                    username=name,
                    username_key=validation.username_key(name),
                    password_hash=hashed,
                    role=role.value,
                    created_at=timestamp(self.clock()),
                )
                actor = Actor(user_id, name, role)
                self._log(
                    "ADMIN_CREATED" if role == Role.ADMIN else "USER_REGISTERED",
                    actor,
                    after=actor.to_dict(),
                    local=role == Role.ADMIN,
                )
        except sqlite3.IntegrityError as error:
            if error.sqlite_errorname == "SQLITE_CONSTRAINT_UNIQUE":
                raise BusinessError("USERNAME_TAKEN", "此用户名已被使用。") from None
            raise
        return actor

    def authenticate(self, username: object, password: object) -> Actor:
        try:
            name = validation.username(username)
        except BusinessError:
            name = ""
        candidate = password if isinstance(password, str) and 0 < len(password) <= 128 else ""
        row = users.get_by_key(self.conn, validation.username_key(name))
        valid = check_password_hash(row["password_hash"] if row else _DUMMY_HASH, candidate)
        if row is None or not valid:
            raise BusinessError("INVALID_CREDENTIALS", "用户名或密码不正确。")
        return actor_from(row)

    def login(self, username: object, password: object, *, previous_token: str | None = None):
        actor = self.authenticate(username, password)
        token = secrets.token_urlsafe(32)
        created = self.clock()
        expires = created + self.session_ttl
        with write_transaction(self.conn):
            if previous_token:
                users.delete_session(self.conn, token_hash(previous_token))
            users.delete_expired_sessions(self.conn, timestamp(created))
            users.insert_session(
                self.conn,
                token_hash=token_hash(token),
                user_id=actor.id,
                created_at=timestamp(created),
                expires_at=timestamp(expires),
            )
            self._log("USER_LOGGED_IN", actor)
        return LoginResult(AuthenticatedSession(actor, expires), token)

    def resolve_session(self, token: object) -> AuthenticatedSession | None:
        if not isinstance(token, str) or not 20 <= len(token) <= 128:
            return None
        row = users.get_session(self.conn, token_hash(token))
        if row is None:
            return None
        expires = datetime.fromisoformat(row["expires_at"])
        if self.clock() >= expires:
            return None
        return AuthenticatedSession(actor_from(row), expires)

    def logout(self, token: str | None) -> None:
        if not token:
            return
        with write_transaction(self.conn):
            row = users.get_session(self.conn, token_hash(token))
            if row is not None:
                users.delete_session(self.conn, token_hash(token))
                self._log("USER_LOGGED_OUT", actor_from(row))

    def set_admin_role(self, username: object, *, grant: bool) -> Actor:
        """Local deployment authority; ordinary HTTP callers cannot invoke this action."""
        name = validation.username(username)
        with write_transaction(self.conn):
            row = users.get_by_key(self.conn, validation.username_key(name))
            if row is None:
                raise BusinessError("NOT_FOUND", "指定账号不存在。")
            actor = actor_from(row)
            target = Role.ADMIN if grant else Role.USER
            if actor.role == target:
                return actor
            if target == Role.USER and users.count_admins(self.conn) == 1:
                raise BusinessError("LAST_ADMIN", "请保留至少一个管理员账号。")
            users.set_role(self.conn, actor.id, target.value)
            updated = Actor(actor.id, actor.username, target)
            self._log(
                "ADMIN_GRANTED" if grant else "ADMIN_REVOKED",
                updated,
                before=actor.to_dict(),
                after=updated.to_dict(),
                local=True,
            )
        return updated

    def list_users(self, actor: Actor, *, limit: object = 25, offset: object = 0) -> dict:
        actor.require_admin()
        size, start = validation.pagination(limit, offset)
        rows, total = users.list_users(self.conn, size, start)
        return {
            "items": [dict(row) for row in rows],
            "total": total,
            "limit": size,
            "offset": start,
        }

    def _log(self, action, actor, *, before=None, after=None, local=False):
        logs.append(
            self.conn,
            actor_kind="LOCAL_COMMAND" if local else "USER",
            actor_id=None if local else actor.id,
            action=action,
            object_type="USER",
            object_id=actor.id,
            before=before or {},
            after=after or {},
            at=timestamp(self.clock()),
        )
