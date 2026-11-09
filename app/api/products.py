"""Public discovery and owner-only product maintenance."""

from flask import Blueprint, current_app, g, request

from app.api.common import json_body, success
from app.clock import now
from app.db import get_db
from app.domain import PRODUCT_CATEGORIES, ProductStatus
from app.product_rules import FIELDS
from app.security import login_required
from app.services.products import ProductService

bp = Blueprint("products", __name__, url_prefix="/api/products")


def service():
    return ProductService(get_db(), clock=current_app.config.get("CLOCK", now))


@bp.get("/options")
def options():
    return success(
        {
            "categories": PRODUCT_CATEGORIES,
            "types": ["GOODS", "SERVICE"],
            "statuses": [status.value for status in ProductStatus],
        }
    )


@bp.get("")
def search():
    return success(service().search(g.actor, dict(request.args)))


@bp.get("/mine")
@login_required
def mine():
    return success(service().search(g.actor, dict(request.args), scope="mine"))


@bp.get("/<int:product_id>")
def detail(product_id):
    return success(service().get_detail(g.actor, product_id))


@bp.post("")
@login_required
def create():
    return success(service().create(g.actor, json_body(optional=FIELDS)), 201)


@bp.patch("/<int:product_id>")
@login_required
def update(product_id):
    body = json_body(required={"version"}, optional=FIELDS)
    version = body.pop("version")
    return success(service().update(g.actor, product_id, version, body))


@bp.post("/<int:product_id>/submit")
@login_required
def submit(product_id):
    return success(service().submit_review(g.actor, product_id, **json_body(required={"version"})))


@bp.post("/<int:product_id>/take-down")
@login_required
def take_down(product_id):
    return success(service().take_down(g.actor, product_id, **json_body(required={"version"})))


@bp.post("/<int:product_id>/rectification")
@login_required
def rectify(product_id):
    return success(
        service().request_rectification(
            g.actor, product_id, **json_body(required={"version", "note"})
        )
    )
