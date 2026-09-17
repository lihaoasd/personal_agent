"""数据层测试：建表、CRUD、级联与统计口径。"""
from __future__ import annotations

from app.db import repos
from app.db.database import connect, init_schema


def _conn(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    return conn


def test_goal_task_event_roundtrip(tmp_path):
    conn = _conn(tmp_path)
    gid = repos.insert_goal(conn, title="学习系统设计", category="learning")
    assert repos.get_goal(conn, gid)["category"] == "learning"
    assert repos.active_goals(conn)[0]["title"] == "学习系统设计"

    tid = repos.insert_task(conn, goal_id=gid, title="读完第 3 章", item_type="book")
    repos.update_task(conn, tid, status="done")
    assert repos.goal_progress(conn, gid) == {"done_tasks": 1, "total_tasks": 1}
    assert repos.get_task(conn, tid)["done_at"] is not None

    eid = repos.insert_event(conn, goal_id=gid, task_id=tid, content="读了 20 页",
                             event_type="reading", amount=20, unit="页", source="chat",
                             happened_on="2026-09-12")
    assert eid > 0
    assert repos.has_event_on(conn, "2026-09-12")
    assert not repos.has_event_on(conn, "2026-09-13")
    assert repos.distinct_days_between(conn, "2026-09-01", "2026-09-30") == 1
    assert repos.days_since_last_event(conn, "2026-09-13") == 1
    conn.close()


def test_cascade_delete_keeps_event_history(tmp_path):
    conn = _conn(tmp_path)
    gid = repos.insert_goal(conn, title="目标A")
    tid = repos.insert_task(conn, goal_id=gid, title="任务A")
    repos.insert_event(conn, goal_id=gid, task_id=tid, content="记录",
                       event_type=None, amount=None, unit=None, source="chat",
                       happened_on="2026-09-10")
    conn.execute("DELETE FROM goals WHERE id = ?", (gid,))
    conn.commit()
    assert repos.list_tasks(conn, gid) == []
    events = repos.recent_events(conn)
    assert len(events) == 1
    assert events[0]["goal_id"] is None  # 事件保留，关联置空
    conn.close()


def test_schedules_and_templates(tmp_path):
    conn = _conn(tmp_path)
    sid = repos.insert_schedule(conn, title="健身", start_at="2026-09-14T15:00:00+08:00")
    rows = repos.list_schedules_between(conn, "2026-09-14T00:00:00", "2026-09-15T00:00:00")
    assert [r["id"] for r in rows] == [sid]

    tid = repos.insert_template(conn, label="读书 30 页", event_type="reading",
                                amount=30, unit="页")
    assert [t["label"] for t in repos.list_templates(conn)] == ["读书 30 页"]
    assert repos.delete_template(conn, tid)
    assert repos.list_templates(conn) == []
    conn.close()


def test_state_and_profile_upsert(tmp_path):
    conn = _conn(tmp_path)
    repos.state_set(conn, "checkin_pending", "1")
    repos.state_set(conn, "checkin_pending", "0")
    assert repos.state_get(conn, "checkin_pending") == "0"
    repos.profile_set(conn, "last_ask_date", "2026-09-12")
    assert repos.profile_get(conn, "last_ask_date") == "2026-09-12"
    conn.close()
