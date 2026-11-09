"""Authenticated order commands and participant-scoped reads."""

from flask import Blueprint, current_app, g, request

from app.api.common import json_body, success
from app.clock import now
from app.db import get_db
from app.order_rules import PlaceOrderInput
from app.security import login_required
from app.services.orders import OrderService

bp = Blueprint("orders", __name__, url_prefix="/api/orders")


def service():
    return OrderService(get_db(), clock=current_app.config.get("CLOCK", now))


@bp.post("")
@login_required
def place_order():
    command = PlaceOrderInput.parse(json_body(required=set(PlaceOrderInput.__dataclass_fields__)))
    instance = service()
    placed = instance.place_order(g.actor, command)
    return success(
        {"order": instance.get_detail(g.actor, placed.order_id), "replayed": not placed.created},
        201 if placed.created else 200,
    )


@bp.get("")
@login_required
def list_orders():
    return success(service().list_orders(g.actor, dict(request.args)))


@bp.get("/<int:order_id>")
@login_required
def get_order(order_id):
    return success(service().get_detail(g.actor, order_id))


def _action(order_id, name):
    json_body()
    return success(getattr(service(), name)(g.actor, order_id))


@bp.post("/<int:order_id>/pay")
@login_required
def pay(order_id):
    return _action(order_id, "pay")


@bp.post("/<int:order_id>/deliver")
@login_required
def deliver(order_id):
    return _action(order_id, "deliver")


@bp.post("/<int:order_id>/confirm")
@login_required
def confirm(order_id):
    return _action(order_id, "confirm")


@bp.post("/<int:order_id>/close")
@login_required
def close(order_id):
    return _action(order_id, "close_unpaid")
