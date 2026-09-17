"""主动问询服务：防疲劳核心机制。"""
from __future__ import annotations

from datetime import date, timedelta
from sqlite3 import Connection

from ..db import repos


def nightly_checkin(conn: Connection, today: date | None = None) -> dict:
    """每晚定时触发：今日已记录则不打扰，否则置 pending。"""
    today = today or date.today()
    if repos.has_event_on(conn, today.isoformat()):
        repos.state_set(conn, "checkin_pending", "0")
        return {"pending": False, "reason": "already_recorded"}
    repos.state_set(conn, "checkin_pending", "1")
    repos.state_set(conn, "last_ask_date", today.isoformat())
    return {"pending": True, "reason": "no_record_today"}


def checkin_status(conn: Connection, today: date | None = None) -> dict:
    """前端轮询的当前状态；pending 仅当天有效。"""
    today = today or date.today()
    last_ask = repos.state_get(conn, "last_ask_date")
    pending = repos.state_get(conn, "checkin_pending") == "1" and last_ask == today.isoformat()
    week_start = today - timedelta(days=today.weekday())
    week_days = repos.distinct_days_between(conn, week_start.isoformat(), today.isoformat())
    return {
        "pending": pending,
        "today_done": repos.has_event_on(conn, today.isoformat()),
        "last_ask_date": last_ask,
        "week_days": week_days,
    }


def dismiss(conn: Connection) -> None:
    repos.state_set(conn, "checkin_pending", "0")
