"""Resolve application configuration without creating business data."""

import os
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def project_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def load_config(overrides: dict | None = None) -> dict:
    instance = project_path(os.environ.get("YUXIAN_INSTANCE_PATH", "instance"))
    config = {
        "INSTANCE_PATH": instance,
        "DATABASE": os.environ.get("YUXIAN_DATABASE", instance / "yuxian.sqlite3"),
        "SECRET_KEY": os.environ.get("YUXIAN_SECRET_KEY"),
        "SESSION_TTL_SECONDS": int(os.environ.get("YUXIAN_SESSION_TTL_SECONDS", "28800")),
        "SESSION_COOKIE_NAME": "yuxian_session",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": False,
        "SESSION_REFRESH_EACH_REQUEST": False,
        "MAX_CONTENT_LENGTH": 16 * 1024,
        "DATABASE_TIMEOUT_SECONDS": 5,
        "UPLOAD_DIR": os.environ.get("YUXIAN_UPLOAD_DIR"),
        "MAX_IMAGE_BYTES": 5 * 1024 * 1024,
        "MAX_IMAGE_PIXELS": 20_000_000,
    }
    config.update(overrides or {})
    config["INSTANCE_PATH"] = project_path(config["INSTANCE_PATH"])
    config["DATABASE"] = project_path(config["DATABASE"])
    config["UPLOAD_DIR"] = project_path(config["UPLOAD_DIR"] or config["INSTANCE_PATH"] / "uploads")
    ttl = config["SESSION_TTL_SECONDS"]
    if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl <= 0:
        raise ValueError("SESSION_TTL_SECONDS must be a positive integer")
    config["PERMANENT_SESSION_LIFETIME"] = timedelta(seconds=ttl)
    secret_file = config["INSTANCE_PATH"] / "secret.key"
    if not config["SECRET_KEY"] and secret_file.is_file():
        config["SECRET_KEY"] = secret_file.read_text(encoding="utf-8").strip()
    return config
