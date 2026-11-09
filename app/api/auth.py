"""Account endpoints; signed cookies contain a revocable session token."""

from flask import Blueprint, g, session

from app.api.common import credentials_body, success
from app.clock import timestamp
from app.security import csrf_token, get_auth_service, login_required

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def session_data(auth_session=None) -> dict:
    return {
        "user": auth_session.actor.to_dict() if auth_session else None,
        "expires_at": timestamp(auth_session.expires_at) if auth_session else None,
        "csrf_token": csrf_token(),
    }


@bp.get("/session")
def current_session():
    return success(session_data(g.auth_session))


@bp.post("/register")
def register():
    user = get_auth_service().register(**credentials_body())
    return success({"user": user.to_dict()}, 201)


@bp.post("/login")
def login():
    result = get_auth_service().login(
        **credentials_body(), previous_token=session.get("auth_token")
    )
    session.clear()
    session.permanent = True
    session["auth_token"] = result.token
    return success(session_data(result.session))


@bp.post("/logout")
@login_required
def logout():
    get_auth_service().logout(session.get("auth_token"))
    session.clear()
    return success(session_data())


@bp.get("/me")
@login_required
def me():
    return success({"user": g.actor.to_dict()})
