"""对话服务：调用 Agent 核心并处理主动问询状态。"""
from __future__ import annotations

from datetime import date
from sqlite3 import Connection

from ..core import agent
from ..db import repos


def handle_message(conn: Connection, message: str, today: date | None = None,
                   session_id: int = 1) -> dict:
    """处理消息；若产生记录则清除主动问询 pending。"""
    result = agent.handle_chat(conn, message, today, session_id=session_id)
    if result["created_event_ids"]:
        today = today or date.today()
        repos.state_set(conn, "checkin_pending", "0")
        repos.profile_set(conn, "last_ask_date", today.isoformat())
    return result
