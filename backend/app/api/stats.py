"""看板统计接口（宽容口径：本周 X/7，无连续天数）。"""
from __future__ import annotations

from datetime import date, timedelta
from sqlite3 import Connection
from typing import Annotated

from fastapi import APIRouter, Depends

from ..db import repos
from .deps import get_conn

router = APIRouter(prefix="/api/stats", tags=["stats"])
ConnDep = Annotated[Connection, Depends(get_conn)]


@router.get("/dashboard")
def dashboard(conn: ConnDep = None):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = today + timedelta(days=6 - today.weekday())
    month_start = today.replace(day=1)

    goals = repos.list_goals(conn)
    goal_progress = []
    total_tasks_done = 0
    total_tasks = 0
    active_goals = 0
    for g in goals:
        p = repos.goal_progress(conn, g["id"])
        goal_progress.append({
            "goal_id": g["id"], "title": g["title"], "category": g["category"],
            "status": g["status"], "done_tasks": p["done_tasks"], "total_tasks": p["total_tasks"],
        })
        total_tasks_done += p["done_tasks"]
        total_tasks += p["total_tasks"]
        if g["status"] == "active":
            active_goals += 1

    return {
        "today_checkins": repos.count_events_between(conn, today.isoformat(), today.isoformat()),
        "week_days": repos.distinct_days_between(conn, week_start.isoformat(), week_end.isoformat()),
        "week_checkin_rate": round(repos.distinct_days_between(conn, week_start.isoformat(), week_end.isoformat()) / 7, 2),
        "total_events": repos.count_events(conn),
        "active_goals": active_goals,
        "total_tasks_done": total_tasks_done,
        "total_tasks": total_tasks,
        "goal_progress": goal_progress,
        "event_type_breakdown": repos.event_type_breakdown(conn, month_start.isoformat()),
        "recent_events": repos.recent_events(conn, 20),
    }
