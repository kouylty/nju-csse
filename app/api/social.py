"""Communication and feedback HTTP adapters; permissions remain in services."""

from flask import Blueprint, current_app, g, request

from app.api.common import json_body, success
from app.clock import now
from app.db import get_db
from app.security import login_required
from app.services.queries import QueryService
from app.services.social import SocialService

bp = Blueprint("social", __name__, url_prefix="/api")


def service():
    return SocialService(get_db(), clock=current_app.config.get("CLOCK", now))


@bp.post("/conversations")
@login_required
def open_conversation():
    return success(
        service().open_conversation(
            g.actor, **json_body(required={"product_id"}, optional={"order_id"})
        )
    )


@bp.get("/conversations")
@login_required
def list_conversations():
    return success(service().list_conversations(g.actor, dict(request.args)))


@bp.get("/conversations/<int:conversation_id>/messages")
@login_required
def list_messages(conversation_id):
    return success(service().list_messages(g.actor, conversation_id, dict(request.args)))


@bp.post("/conversations/<int:conversation_id>/messages")
@login_required
def send_message(conversation_id):
    result = service().send_message(
        g.actor,
        conversation_id,
        **json_body(required={"body", "client_key"}, optional={"order_id"}),
    )
    return success(result, 200 if result["replayed"] else 201)


@bp.post("/orders/<int:order_id>/evaluations")
@login_required
def evaluate(order_id):
    return success(
        service().evaluate_order(g.actor, order_id, **json_body(required={"rating", "body"})), 201
    )


@bp.get("/orders/<int:order_id>/evaluations")
@login_required
def order_evaluations(order_id):
    return success(service().order_evaluations(g.actor, order_id))


@bp.get("/products/<int:product_id>/evaluations")
def product_evaluations(product_id):
    return success(service().list_evaluations(dict(request.args), product_id=product_id))


@bp.get("/users/<int:user_id>/evaluations")
def user_evaluations(user_id):
    return success(service().list_evaluations(dict(request.args), user_id=user_id))


@bp.get("/notifications")
@login_required
def notifications():
    return success(service().list_notifications(g.actor, dict(request.args)))


@bp.post("/notifications/<int:notification_id>/read")
@login_required
def read_notification(notification_id):
    json_body()
    return success(service().mark_notification_read(g.actor, notification_id))


@bp.get("/me/summary")
@login_required
def seller_summary():
    return success(QueryService(get_db()).seller_summary(g.actor, dict(request.args)))


@bp.get("/me/logs")
@login_required
def my_logs():
    return success(QueryService(get_db()).search_logs(g.actor, dict(request.args)))
