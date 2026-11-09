"""Application factory. Importing the package does not initialize the database."""

from flask import Flask, send_from_directory

from app.api import register_api
from app.api.common import register_error_handlers, success
from app.cli import register_cli
from app.config import PROJECT_ROOT, load_config
from app.db import SCHEMA_VERSION, close_db, get_db
from app.security import load_identity_and_check_csrf


def create_app(test_config: dict | None = None) -> Flask:
    config = load_config(test_config)
    app = Flask(
        __name__,
        instance_path=str(config["INSTANCE_PATH"]),
        static_folder=str(PROJECT_ROOT / "web"),
        static_url_path="/static",
    )
    app.config.update(config)
    app.teardown_appcontext(close_db)
    app.before_request(load_identity_and_check_csrf)
    register_error_handlers(app)
    register_api(app)
    register_cli(app)

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/api/health")
    def health():
        get_db().execute("SELECT 1 FROM users LIMIT 1")
        return success({"status": "ok", "schema_version": SCHEMA_VERSION})

    @app.after_request
    def response_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob:; object-src 'none'; "
            "base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        if response.mimetype == "application/json":
            response.headers["Cache-Control"] = "no-store"
        return response

    return app
