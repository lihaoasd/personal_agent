"""Agent 编排测试：打卡、目标、日程、温和重启、澄清、查询。"""
from __future__ import annotations

import json
from datetime import date

from app.core import agent, psychology
from app.db import repos
from tests.conftest import checkin_json


def _conn(app):
    return app.state.db.connect()


def test_checkin_creates_event_and_updates_task(app, seed_goal):
    gid, t1, t2 = seed_goal
    app.state.fake_provider.script = [
        checkin_json(goal_id=gid, task_id=t1),
        "已记录！目标「9 月完成系统设计学习」进度 1/2，继续保持。",
    ]
    conn = _conn(app)
    result = agent.handle_chat(conn, "今天读完第 3 章", date(2026, 9, 13))
    assert len(result["created_event_ids"]) == 1
    events = repos.events_between(conn, "2026-09-13", "2026-09-13")
    assert events[0]["goal_id"] == gid
    assert events[0]["source"] == "chat"
    assert repos.get_task(conn, t1)["status"] == "done"
    assert result["reply"].startswith("已记录")
    conn.close()


def test_backfill_intent_uses_happened_on(app, seed_goal):
    gid, t1, t2 = seed_goal
    app.state.fake_provider.script = [
        checkin_json(goal_id=gid, happened_on="2026-09-11", intent="backfill"),
        "已补记到 09-11。",
    ]
    conn = _conn(app)
    result = agent.handle_chat(conn, "前天读了 20 页", date(2026, 9, 13))
    events = repos.events_between(conn, "2026-09-11", "2026-09-11")
    assert len(events) == 1
    assert events[0]["source"] == "backfill"
    assert result["created_event_ids"] == [events[0]["id"]]
    conn.close()


def test_gentle_restart_after_3_days_gap(app):
    conn = _conn(app)
    gid = repos.insert_goal(conn, title="读书")
    repos.insert_event(conn, goal_id=gid, task_id=None, content="4 天前",
                       event_type="reading", amount=None, unit=None, source="chat",
                       happened_on="2026-09-09")
    assert psychology.decide_tone(conn, "2026-09-13", "chat") == "gentle_restart"
    assert psychology.decide_tone(conn, "2026-09-13", "checkin") == "gentle_restart"
    conn.close()


def test_goal_manage_creates_goal(app):
    app.state.fake_provider.script = [json.dumps({
        "intent": "goal_manage", "goal_id": None, "task_id": None, "event": None,
        "happened_on": None, "schedule": None,
        "goal": {"title": "学完系统设计", "category": "learning"}, "need_clarify": None,
    }, ensure_ascii=False)]
    conn = _conn(app)
    result = agent.handle_chat(conn, "我想学完系统设计", date(2026, 9, 13))
    assert repos.active_goals(conn)[0]["title"] == "学完系统设计"
    assert "已创建目标" in result["reply"]
    conn.close()


def test_schedule_creates_schedule(app):
    app.state.fake_provider.script = [json.dumps({
        "intent": "schedule", "goal_id": None, "task_id": None, "event": None,
        "happened_on": None,
        "schedule": {"title": "健身", "start_at": "2026-09-14T15:00:00+08:00", "end_at": None},
        "goal": None, "need_clarify": None,
    }, ensure_ascii=False)]
    conn = _conn(app)
    result = agent.handle_chat(conn, "明天下午 3 点健身", date(2026, 9, 13))
    rows = repos.list_schedules_between(conn, "2026-09-14T00:00:00", "2026-09-15T00:00:00")
    assert rows[0]["title"] == "健身"
    assert "已安排" in result["reply"]
    conn.close()


def test_unmatched_goal_triggers_clarify(app):
    app.state.fake_provider.script = [checkin_json(goal_id=999)]
    conn = _conn(app)
    result = agent.handle_chat(conn, "今天读了 20 页", date(2026, 9, 13))
    assert result["created_event_ids"] == []
    assert "目标" in result["reply"]
    conn.close()


def test_query_reports_real_data(app, seed_goal):
    gid, t1, t2 = seed_goal
    conn = _conn(app)
    repos.insert_event(conn, goal_id=gid, task_id=None, content="今天读了 20 页",
                       event_type="reading", amount=20, unit="页", source="chat",
                       happened_on="2026-09-13")
    conn.commit()
    app.state.fake_provider.script = [
        json.dumps({
            "intent": "query", "goal_id": None, "task_id": None, "event": None,
            "happened_on": None, "schedule": None, "goal": None, "need_clarify": None,
        }, ensure_ascii=False),
        "本周已打卡 1 天。",
    ]
    result = agent.handle_chat(conn, "我这周学了多少？", date(2026, 9, 13))
    assert "本周已打卡 1 天" in result["reply"]
    conn.close()
