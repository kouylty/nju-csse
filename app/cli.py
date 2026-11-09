"""Trusted local deployment commands, separate from public registration."""

import os
import secrets

import click
from flask import current_app

from app.db import get_db, initialize_database
from app.errors import BusinessError
from app.security import get_auth_service


def ensure_local_secret() -> None:
    if current_app.secret_key:
        return
    directory = current_app.config["INSTANCE_PATH"]
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "secret.key"
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        secret = path.read_text(encoding="utf-8").strip()
        if len(secret) < 32:
            raise click.ClickException("本地密钥文件不完整，请恢复有效密钥后重试。") from None
    else:
        secret = secrets.token_hex(32)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(secret)
    current_app.config["SECRET_KEY"] = secret


def register_cli(app) -> None:
    @app.cli.command("upgrade-db")
    def upgrade_db_command():
        """Upgrade a recognized database, preserving accounts, sessions and review history."""
        if not current_app.config["DATABASE"].is_file():
            raise click.ClickException("请先使用 init-db 创建数据库。")
        try:
            initialize_database(current_app.config["DATABASE"])
        except BusinessError as error:
            raise click.ClickException(error.message) from None
        click.echo("数据库已升级到当前版本；原有业务记录保持不变。")

    @app.cli.command("init-db")
    def init_db_command():
        """Create the schema and a persistent local cookie-signing secret."""
        try:
            initialize_database(current_app.config["DATABASE"])
            ensure_local_secret()
        except BusinessError as error:
            raise click.ClickException(error.message) from None
        click.echo("数据库初始化完成；已有业务记录予以保留。")

    @app.cli.command("create-admin")
    @click.option("--username", prompt="用户名")
    @click.password_option(prompt="密码", confirmation_prompt="确认密码")
    def create_admin_command(username, password):
        """Create the first admin. Password input is hidden."""
        try:
            actor = get_auth_service().create_admin(username, password)
        except BusinessError as error:
            raise click.ClickException(error.message) from None
        click.echo(f"管理员已建立：{actor.username}")

    @app.cli.command("set-admin")
    @click.option("--username", required=True)
    @click.option("--grant/--revoke", default=True, help="授予或撤销指定账号的管理员权限。")
    def set_admin_command(username, grant):
        """Manage roles using local deployment authority; preserve the last admin."""
        try:
            actor = get_auth_service().set_admin_role(username, grant=grant)
        except BusinessError as error:
            raise click.ClickException(error.message) from None
        click.echo(f"账号权限已设置：{actor.username} → {actor.role.value}")

    @app.cli.command("check-db")
    def check_db_command():
        """Verify an initialized database using SQLite's integrity check."""
        result = get_db().execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise click.ClickException(result)
        click.echo("数据库完整性检查通过。")
