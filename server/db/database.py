# -*- coding: utf-8 -*-
"""
数据库层：SQLite（本地/Render）和 PostgreSQL（Supabase）双模式自动切换。
- 无 DATABASE_URL 环境变量 → SQLite，文件在 db/local.db
- 有 DATABASE_URL → psycopg2 连 PostgreSQL
"""

import os
import secrets
import string
from contextlib import contextmanager
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "")
_USE_SQLITE = not bool(DATABASE_URL)

# ---------------------------------------------------------------------------
# 连接管理
# ---------------------------------------------------------------------------
if _USE_SQLITE:
    import sqlite3

    _DB_PATH = Path(os.getenv("SQLITE_DB_PATH", str(Path(__file__).parent / "local.db")))

    def _sqlite_connect():
        conn = sqlite3.connect(str(_DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    @contextmanager
    def get_conn():
        conn = _sqlite_connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

else:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    def _pg_connect():
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

    @contextmanager
    def get_conn():
        conn = _pg_connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# 占位符适配
# ---------------------------------------------------------------------------
def _ph(n):
    """SQLite 用 ?, PostgreSQL 用 %s"""
    return "?" if _USE_SQLITE else "%s"


def _use_sqlite():
    return _USE_SQLITE


# ---------------------------------------------------------------------------
# 查询 / 执行
# ---------------------------------------------------------------------------
def _adapt_sql(sql: str) -> str:
    """SQLite 模式下把 %s 占位符自动转成 ?"""
    if _USE_SQLITE:
        return sql.replace("%s", "?")
    return sql


def fetchone(conn, sql: str, params=()):
    cur = conn.cursor()
    cur.execute(_adapt_sql(sql), params)
    row = cur.fetchone()
    if row is None:
        return None
    if _USE_SQLITE:
        return dict(row)
    return row


def fetchall(conn, sql: str, params=()):
    cur = conn.cursor()
    cur.execute(_adapt_sql(sql), params)
    rows = cur.fetchall()
    if _USE_SQLITE:
        return [dict(r) for r in rows]
    return rows


def execute(conn, sql: str, params=()):
    cur = conn.cursor()
    cur.execute(_adapt_sql(sql), params)
    return cur.rowcount


# ---------------------------------------------------------------------------
# 邀请码生成
# ---------------------------------------------------------------------------
def generate_code(prefix: str = "QCC") -> str:
    chars = string.ascii_uppercase + string.digits
    parts = ["".join(secrets.choice(chars) for _ in range(4)) for _ in range(3)]
    return f"{prefix}-{parts[0]}-{parts[1]}-{parts[2]}"


# ---------------------------------------------------------------------------
# 建表（仅 SQLite 模式在启动时调用）
# ---------------------------------------------------------------------------
_SCHEMA_SQLITE = [
    """
    CREATE TABLE IF NOT EXISTS users (
        phone      TEXT PRIMARY KEY,
        username   TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS codes (
        code       TEXT PRIMARY KEY,
        status     TEXT NOT NULL DEFAULT 'unused',
        remark     TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        bound_at   TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bindings (
        code           TEXT PRIMARY KEY,
        license_id     TEXT NOT NULL UNIQUE,
        phone          TEXT NOT NULL,
        device_id      TEXT NOT NULL UNIQUE,
        bound_at       TEXT DEFAULT (datetime('now')),
        last_verify    TEXT,
        revoked_since  TEXT,
        revoked_at     TEXT,
        FOREIGN KEY (code) REFERENCES codes(code),
        FOREIGN KEY (phone) REFERENCES users(phone)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_bindings_device ON bindings(device_id)",
    "CREATE INDEX IF NOT EXISTS idx_codes_status    ON codes(status)",
]


def init_tables():
    if not _USE_SQLITE:
        return  # PostgreSQL 直接在 Supabase 控制台跑 SQL

    with get_conn() as conn:
        for ddl in _SCHEMA_SQLITE:
            conn.execute(ddl)
