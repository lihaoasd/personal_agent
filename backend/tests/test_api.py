"""API 集成测试。"""
from __future__ import annotations

from datetime import date

from tests.conftest import checkin_json


def test_chat_checkin_flow(client, seed_goal, app):
    gid, t1, t2 = seed_goal
    app.state.fake_provider.script = [checkin_json(goal_id=gid), "已记录，进度 1/2。"]
    resp = client.post("/api/chat", json={"message": "今天读完第 3 章"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["created_event_ids"]
    assert "进度" in data["reply"]


def test_chat_llm_error_returns_502(client, app):
    from app.core import llm

    app.state.fake_provider.script = [llm.LLMError("boom")]
    resp = client.post("/api/chat", json={"message": "今天读了 20 页"})
    assert resp.status_code == 502


def test_backfill_api_rejects_future(client, app):
    resp = client.post("/api/checkin/backfill",
                       json={"content": "读 20 页", "happened_on": "2099-01-01"})
    assert resp.status_code == 400


def test_goals_crud_and_plan(client, app):
    resp = client.post("/api/goals", json={
        "title": "学习系统设计", "category": "learning",
        "tasks": [{"title": "读完第 3 章", "item_type": "book"}],
    })
    assert resp.status_code == 200
    gid = resp.json()["id"]
    assert resp.json()["progress"] == {"done_tasks": 0, "total_tasks": 1}

    app.state.fake_provider.script = [
        '{"title": "9 月学完系统设计", "target_date": "2026-09-30", "tasks": [{"title": "学第 1 章", "item_type": "book"}]}'
    ]
    resp = client.post("/api/goals/plan", json={"description": "学完系统设计", "category": "learning"})
    assert resp.status_code == 200
    assert resp.json()["tasks"][0]["title"] == "学第 1 章"
    assert client.get("/api/goals").json()[0]["title"] == "学习系统设计"  # plan 不落库

    app.state.fake_provider.script = [
        '{"title": "学完系统设计", "target_date": null, "tasks": [{"title": "学第 1 章", "item_type": "book"}]}'
    ]
    resp = client.post("/api/goals/from-plan", json={"description": "学完系统设计", "category": "learning"})
    assert resp.status_code == 200
    assert resp.json()["goal_id"] > gid

    resp = client.patch("/api/goals/tasks/1", json={"status": "done"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"


def test_schedules_api(client, app):
    resp = client.post("/api/schedules",
                       json={"title": "健身", "start_at": "2026-09-14T15:00:00+08:00"})
    assert resp.status_code == 200
    sid = resp.json()["id"]
    resp = client.get("/api/schedules",
                      params={"start": "2026-09-14T00:00:00", "end": "2026-09-15T00:00:00"})
    assert len(resp.json()) == 1
    resp = client.patch(f"/api/schedules/{sid}", json={"status": "done"})
    assert resp.json()["status"] == "done"
    resp = client.get("/api/schedules", params={"start": "2026-09-15T00:00:00", "end": "2026-09-14T00:00:00"})
    assert resp.status_code == 400


def test_templates_api(client, app):
    resp = client.post("/api/templates", json={
        "label": "读书 30 页", "event_type": "reading", "amount": 30, "unit": "页",
    })
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    tid = resp.json()[0]["id"]
    assert client.delete(f"/api/templates/{tid}").json() == {"ok": True}


def test_checkin_status_lifecycle(client, app):
    from app.db import repos
    from app.services import checkin_service

    assert client.get("/api/checkin/status").json()["pending"] is False

    conn = app.state.db.connect()
    checkin_service.nightly_checkin(conn, date(2026, 9, 13))
    conn.commit()
    conn.close()
    assert client.get("/api/checkin/status").json()["pending"] is True

    conn = app.state.db.connect()
    gid = repos.insert_goal(conn, title="读书")
    conn.commit()
    conn.close()
    app.state.fake_provider.script = [checkin_json(goal_id=gid), "已记录。"]
    client.post("/api/chat", json={"message": "今天读了 20 页"})
    assert client.get("/api/checkin/status").json()["pending"] is False


def test_dashboard_stats_consistency(client, app, seed_goal):
    from app.db import repos

    gid, t1, t2 = seed_goal
    conn = app.state.db.connect()
    repos.insert_event(conn, goal_id=gid, task_id=None, content="今天读了 20 页",
                       event_type="reading", amount=20, unit="页", source="chat",
                       happened_on="2026-09-13")
    conn.commit()
    conn.close()

    data = client.get("/api/stats/dashboard").json()
    assert data["today_checkins"] == 1
    assert data["week_days"] == 1
    assert data["week_checkin_rate"] == round(1 / 7, 2)
    assert data["goal_progress"][0]["total_tasks"] == 2
    assert data["event_type_breakdown"][0]["event_type"] == "reading"


def test_reviews_generate_and_list(client, app, seed_goal):
    from app.db import repos

    gid, t1, t2 = seed_goal
    conn = app.state.db.connect()
    repos.insert_event(conn, goal_id=gid, task_id=None, content="读 20 页",
                       event_type="reading", amount=20, unit="页", source="chat",
                       happened_on="2026-09-02")  # 上周区间
    conn.commit()
    conn.close()

    app.state.fake_provider.script = ["## 本周概览\n记录 1 天。"]
    resp = client.post("/api/reviews/generate", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert "本周概览" in body["content"]
    assert body["stats"]["event_count"] >= 1
    assert len(client.get("/api/reviews").json()) >= 1
