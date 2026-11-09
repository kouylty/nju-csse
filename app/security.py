"""Flask adapters for sessions, CSRF and authenticated route entry."""

import secrets
from functools import wraps

from flask import current_app, g, request, session

from app.clock import now
from app.db import get_db
from app.errors import BusinessError
from app.services.auth import AuthService


def get_auth_service() -> AuthService:
    return AuthService(
        get_db(),
        clock=current_app.config.get("CLOCK", now),
        session_ttl_seconds=current_app.config["SESSION_TTL_SECONDS"],
    )


def csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def load_identity_and_check_csrf() -> None:
    if not request.path.startswith("/api/") or request.endpoint is None:
        return
    g.auth_session = None
    g.actor = None
    if request.endpoint == "health":
        return
    if request.endpoint == "files.upload":
        request.max_content_length = current_app.config["MAX_IMAGE_BYTES"] + 64 * 1024
    if not current_app.secret_key:
        raise BusinessError("SETUP_REQUIRED", "请先运行 make init-db 完成本地初始化。")
    token = session.get("auth_token")
    if token:
        g.auth_session = get_auth_service().resolve_session(token)
        if g.auth_session is None:
            session.clear()
        else:
            g.actor = g.auth_session.actor
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        expected = session.get("csrf_token", "")
        supplied = request.headers.get("X-CSRF-Token", "")
        if not expected or not secrets.compare_digest(expected.encode(), supplied.encode()):
            raise BusinessError("CSRF_FAILED", "会话校验已更新，请刷新页面后重试。")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.actor is None:
            raise BusinessError("AUTH_REQUIRED", "请先登录。")
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        g.actor.require_admin()
        return view(*args, **kwargs)

    return wrapped
