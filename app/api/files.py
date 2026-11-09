"""Multipart pictures and authorized binary responses."""

from flask import Blueprint, current_app, g, request, send_file

from app.api.common import success
from app.clock import now
from app.db import get_db
from app.errors import BusinessError
from app.files import FileService
from app.security import login_required

bp = Blueprint("files", __name__, url_prefix="/api/files")


def service():
    return FileService(
        get_db(),
        current_app.config["UPLOAD_DIR"],
        clock=current_app.config.get("CLOCK", now),
        max_bytes=current_app.config["MAX_IMAGE_BYTES"],
        max_pixels=current_app.config["MAX_IMAGE_PIXELS"],
    )


@bp.post("")
@login_required
def upload():
    if set(request.files) != {"file"} or len(request.files.getlist("file")) != 1 or request.form:
        raise BusinessError("INVALID_INPUT", "请以 file 字段提交一张图片。")
    return success(service().upload(g.actor, request.files["file"].stream), 201)


@bp.get("/<int:file_id>")
def read(file_id):
    path, mime = service().open_for(g.actor, file_id)
    response = send_file(path, mimetype=mime, conditional=False)
    response.headers["Cache-Control"] = "no-store"
    return response
