"""SQLite connections and explicit transaction ownership."""

import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from flask import current_app, g

from app.errors import BusinessError

SCHEMA_VERSION = 4
MIGRATIONS = {2: "002_products.sql", 3: "003_orders.sql", 4: "004_community.sql"}


def connect_db(path: Path, *, create: bool = False, timeout: float = 5) -> sqlite3.Connection:
    path = Path(path)
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
    elif not path.is_file():
        raise BusinessError("SETUP_REQUIRED", "请先运行 make init-db 初始化数据库。")
    conn = sqlite3.connect(path, isolation_level=None, timeout=timeout)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if not create and conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
        conn.close()
        raise BusinessError("SCHEMA_MISMATCH", "数据库结构版本不匹配，请检查初始化或升级步骤。")
    return conn


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect_db(
            current_app.config["DATABASE"],
            timeout=current_app.config["DATABASE_TIMEOUT_SECONDS"],
        )
    return g.db


def close_db(_error: BaseException | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


@contextmanager
def write_transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """The outer service owns commit; helpers share its connection."""
    if conn.in_transaction:
        raise RuntimeError("A write transaction is already active")
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


@contextmanager
def read_transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Read related records from one consistent snapshot without reserving a writer."""
    if conn.in_transaction:
        yield conn
        return
    conn.execute("BEGIN")
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


def initialize_database(path: Path) -> None:
    conn = connect_db(path, create=True)
    try:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version == SCHEMA_VERSION:
            return
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        if 1 <= version < SCHEMA_VERSION:
            required = {"users", "auth_sessions", "operation_logs"}
            if version >= 2:
                required.update({"products", "files", "product_reviews", "review_images"})
            if version >= 3:
                required.update({"orders", "order_images", "fund_transactions"})
            if not required.issubset({row[0] for row in tables}):
                raise BusinessError("SCHEMA_MISMATCH", "数据库缺少该版本的基础表，请检查原始数据。")
            backup = path.with_name(f"{path.stem}.v{version}-{secrets.token_hex(4)}.backup.sqlite3")
            with closing(sqlite3.connect(backup)) as target:
                conn.backup(target)
            _upgrade(conn)
            return
        if version != 0 or tables:
            raise BusinessError("SCHEMA_MISMATCH", "已有数据库需要明确升级，初始化保留原有数据。")
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        try:
            conn.executescript(f"BEGIN IMMEDIATE;\n{schema}\nPRAGMA user_version = 1;\nCOMMIT;")
            _upgrade(conn)
        except BaseException:
            conn.rollback()
            raise
    finally:
        conn.close()


def _upgrade(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    directory = Path(__file__).parent / "migrations"
    script = "\n".join(
        (directory / MIGRATIONS[target]).read_text(encoding="utf-8")
        for target in range(version + 1, SCHEMA_VERSION + 1)
    )
    try:
        conn.executescript(
            f"BEGIN IMMEDIATE;\n{script}\nPRAGMA user_version = {SCHEMA_VERSION};\nCOMMIT;"
        )
    except BaseException:
        conn.rollback()
        raise
