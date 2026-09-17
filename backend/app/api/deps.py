"""API 公共依赖：请求级数据库连接（事务边界）。"""
from __future__ import annotations

from sqlite3 import Connection

from fastapi import Request


def get_conn(request: Request) -> Connection:
    db = request.app.state.db
    conn = db.connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
