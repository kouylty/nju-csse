"""Case entry points shared by parties and assigned administrators."""

from flask import Blueprint, current_app, g, request

from app.api.common import json_body, success
from app.clock import now
from app.db import get_db
from app.security import admin_required, login_required
from app.services.cases import CaseService

bp = Blueprint("cases", __name__, url_prefix="/api")


def service():
    return CaseService(get_db(), clock=current_app.config.get("CLOCK", now))


@bp.post("/cases")
@login_required
def submit():
    return success(
        service().submit(
            g.actor, **json_body(required={"kind", "target_id", "reason"}, optional={"image_ids"})
        ),
        201,
    )


@bp.get("/cases")
@login_required
def list_cases():
    return success(service().list_cases(g.actor, dict(request.args)))


@bp.get("/cases/<int:case_id>")
@login_required
def detail(case_id):
    return success(service().get_detail(g.actor, case_id))


@bp.post("/cases/<int:case_id>/comments")
@login_required
def comment(case_id):
    return success(
        service().comment(g.actor, case_id, **json_body(required={"body"}, optional={"image_ids"})),
        201,
    )


@bp.get("/cases/<int:case_id>/context")
@login_required
def context(case_id):
    return success(service().context(g.actor, case_id, dict(request.args)))


@bp.get("/admin/cases")
@admin_required
def admin_list():
    return success(service().list_cases(g.actor, dict(request.args), admin=True))


@bp.post("/admin/cases/<int:case_id>/claim")
@admin_required
def claim(case_id):
    json_body()
    return success(service().claim(g.actor, case_id))


@bp.post("/admin/cases/<int:case_id>/resolve")
@admin_required
def resolve(case_id):
    return success(
        service().resolve(
            g.actor,
            case_id,
            **json_body(
                required={"version", "decision", "reason"},
                optional={"restore_stock", "confirmation_plan"},
            ),
        )
    )
