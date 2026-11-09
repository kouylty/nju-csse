"""JSON contracts and error-to-HTTP translation shared by API modules."""

import sqlite3

from flask import current_app, jsonify, request
from werkzeug.exceptions import HTTPException

from app.errors import BusinessError

ERROR_STATUS = {
    "INVALID_INPUT": 400,
    "INVALID_CREDENTIALS": 401,
    "AUTH_REQUIRED": 401,
    "FORBIDDEN": 403,
    "CSRF_FAILED": 403,
    "NOT_FOUND": 404,
    "USERNAME_TAKEN": 409,
    "ADMIN_EXISTS": 409,
    "LAST_ADMIN": 409,
    "SETUP_REQUIRED": 503,
    "SCHEMA_MISMATCH": 503,
    "INVALID_STATE": 409,
    "STALE_VERSION": 409,
    "INVALID_IMAGE": 400,
    "IMAGE_TOO_LARGE": 413,
    "REQUEST_KEY_REUSED": 409,
    "PENDING_ORDER_EXISTS": 409,
    "SELF_PURCHASE": 409,
    "PRODUCT_UNAVAILABLE": 409,
    "DELIVERY_UNAVAILABLE": 409,
    "OUT_OF_STOCK": 409,
    "PRICE_CHANGED": 409,
    "PAYMENT_EXPIRED": 409,
    "INVARIANT_VIOLATION": 500,
    "ALREADY_EVALUATED": 409,
    "ACTIVE_CASE_EXISTS": 409,
}


def success(data, status=200):
    return jsonify(data=data), status


def credentials_body() -> dict:
    return json_body(required={"username", "password"})


def json_body(*, required=(), optional=()) -> dict:
    if not request.is_json:
        from werkzeug.exceptions import UnsupportedMediaType

        raise UnsupportedMediaType()
    body = request.get_json()
    if not isinstance(body, dict):
        raise BusinessError("INVALID_INPUT", "请求内容须为 JSON 对象。")
    missing = set(required) - body.keys()
    unknown = body.keys() - (set(required) | set(optional))
    if missing or unknown:
        raise BusinessError(
            "INVALID_INPUT",
            "请核对请求字段。",
            {"missing_fields": sorted(missing), "unknown_fields": sorted(unknown)},
        )
    return body


def failure(code, message, status, details=None):
    return jsonify(error={"code": code, "message": message, "details": details or {}}), status


def register_error_handlers(app) -> None:
    @app.errorhandler(BusinessError)
    def business_error(error):
        return failure(error.code, error.message, ERROR_STATUS.get(error.code, 400), error.details)

    @app.errorhandler(HTTPException)
    def http_error(error):
        names = {
            400: ("INVALID_INPUT", "请求格式不正确。"),
            404: ("NOT_FOUND", "请求的资源不存在。"),
            405: ("METHOD_NOT_ALLOWED", "此接口不支持该请求方法。"),
            413: ("PAYLOAD_TOO_LARGE", "请求内容超过允许大小。"),
            415: ("UNSUPPORTED_MEDIA_TYPE", "请使用 application/json 提交数据。"),
        }
        code, message = names.get(error.code, ("HTTP_ERROR", "请求未能完成。"))
        return failure(code, message, error.code)

    @app.errorhandler(Exception)
    def unexpected_error(error):
        if isinstance(error, sqlite3.OperationalError):
            code = getattr(error, "sqlite_errorcode", 0)
            if code & 0xFF in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}:
                return failure("DATABASE_BUSY", "当前操作较多，请稍后重试。", 503)
        current_app.logger.exception("API request failed")
        return failure("INTERNAL_ERROR", "本次操作未完成，请稍后重试。", 500)
