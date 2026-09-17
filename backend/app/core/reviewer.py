"""周期复盘生成：聚合数据 + 心理框架 + LLM 写作。"""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from sqlite3 import Connection

from ..db import repos
from . import llm, prompts, psychology


def last_week_range(today: date | None = None) -> tuple[str, str]:
    """返回上周一 ~ 上周日（含端点）。"""
    today = today or date.today()
    monday_this = today - timedelta(days=today.weekday())
    start = monday_this - timedelta(days=7)
    end = monday_this - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def aggregate(events: list[dict], goals: list[dict]) -> dict:
    """把事件与目标聚合成复盘统计。"""
    days = len({e["happened_on"] for e in events})
    types = Counter(e.get("event_type") or "other" for e in events)
    goal_rows = []
    for g in goals:
        goal_rows.append({
            "title": g["title"], "status": g["status"],
            "done_tasks": g.get("_done", 0), "total_tasks": g.get("_total", 0),
        })
    return {
        "days": days,
        "event_count": len(events),
        "done_tasks": sum(g["_done"] for g in goals),
        "event_types": [{"event_type": k, "count": v} for k, v in types.most_common()],
        "goals": goal_rows,
    }


def generate_review(conn: Connection, *, period_start: str | None = None,
                    period_end: str | None = None, today: date | None = None) -> dict:
    """生成一篇周复盘并落库；同区间重复调用生成新记录（允许手动补复盘）。"""
    today = today or date.today()
    start, end = period_start, period_end
    if not start or not end:
        start, end = last_week_range(today)

    events = repos.events_between(conn, start, end)
    goals = repos.list_goals(conn)
    for g in goals:
        p = repos.goal_progress(conn, g["id"])
        g["_done"], g["_total"] = p["done_tasks"], p["total_tasks"]

    stats = aggregate(events, goals)
    stats["period_start"], stats["period_end"] = start, end
    framing = psychology.review_framing(stats)
    content = llm.chat_text(prompts.REVIEW_SYSTEM, prompts.build_review_user(stats, framing))
    review_id = repos.insert_review(conn, period_type="weekly", period_start=start,
                                    period_end=end, content=content, stats=stats)
    return {"id": review_id, "period_start": start, "period_end": end,
            "content": content, "stats": stats}
