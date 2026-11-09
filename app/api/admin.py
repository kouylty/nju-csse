"""The first real admin resource; later stages add review and case endpoints."""

from flask import Blueprint, g, request

from app.api.common import json_body, success
from app.api.products import service as product_service
from app.db import get_db
from app.security import admin_required, get_auth_service
from app.services.queries import QueryService

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@bp.get("/todos")
@admin_required
def todos():
    return success(QueryService(get_db()).admin_todos(g.actor))


@bp.get("/logs")
@admin_required
def logs():
    return success(QueryService(get_db()).search_logs(g.actor, dict(request.args), admin=True))


@bp.get("/users")
@admin_required
def list_users():
    return success(
        get_auth_service().list_users(
            g.actor, limit=request.args.get("limit", "25"), offset=request.args.get("offset", "0")
        )
    )


@bp.get("/products")
@admin_required
def list_products():
    return success(product_service().search(g.actor, dict(request.args), scope="admin"))


@bp.post("/products/<int:product_id>/review")
@admin_required
def review_product(product_id):
    return success(
        product_service().review(
            g.actor, product_id, **json_body(required={"version", "approve"}, optional={"reason"})
        )
    )


@bp.post("/products/<int:product_id>/take-down")
@admin_required
def block_product(product_id):
    return success(
        product_service().take_down(
            g.actor, product_id, violation=True, **json_body(required={"version", "reason"})
        )
    )


@bp.post("/products/<int:product_id>/reopen")
@admin_required
def reopen_product(product_id):
    return success(
        product_service().reopen_review(g.actor, product_id, **json_body(required={"version"}))
    )
