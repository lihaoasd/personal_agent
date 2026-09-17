"""测试公共设施：临时数据库 + 脚本化假 LLM 提供商。"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# 必须在导入 app.main 前设置：关闭定时器、隔离数据目录
os.environ["PA_ENABLE_SCHEDULER"] = "0"
os.environ["PA_DATA_DIR"] = tempfile.mkdtemp(prefix="pa_test_data_")

import pytest  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings  # noqa: E402
from app.core import llm  # noqa: E402
from app.main import create_app  # noqa: E402


class FakeProvider:
    """按脚本依次返回预设响应；脚本用尽后回退默认响应。脚本项可为异常以模拟失败。"""

    def __init__(self, script=None):
        self.script = list(script or [])
        self.calls = []

    def chat(self, *, system: str, user: str, json_mode: bool = False) -> str:
        self.calls.append({"system": system, "user": user, "json_mode": json_mode})
        if self.script:
            item = self.script.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        if json_mode:
            return json.dumps({
                "intent": "chat", "goal_id": None, "task_id": None, "event": None,
                "happened_on": None, "schedule": None, "goal": None, "need_clarify": None,
            }, ensure_ascii=False)
        return "好的，已记录。继续保持！"


def checkin_json(*, goal_id=1, task_id=None, event_type="reading", amount=20, unit="页",
                 happened_on=None, intent="checkin"):
    return json.dumps({
        "intent": intent, "goal_id": goal_id, "task_id": task_id,
        "event": {"event_type": event_type, "amount": amount, "unit": unit},
        "happened_on": happened_on, "schedule": None, "goal": None, "need_clarify": None,
    }, ensure_ascii=False)


def chat_json_text(text: str = "已记录，继续保持！"):
    return text


@pytest.fixture()
def settings(tmp_path) -> Settings:
    return Settings(
        db_path=str(tmp_path / "test.db"),
        llm_base_url="http://mock", llm_api_key="", llm_model="mock",
        enable_scheduler=False,
    )


@pytest.fixture()
def app(settings):
    application = create_app(settings)
    application.state.fake_provider = FakeProvider()
    llm.set_provider(application.state.fake_provider)
    yield application
    llm.set_provider(None)


@pytest.fixture()
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def seed_goal(app):
    """预置一个进行中的学习目标与两个子任务。"""
    from app.db import repos

    conn = app.state.db.connect()
    try:
        gid = repos.insert_goal(conn, title="9 月完成系统设计学习", category="learning")
        t1 = repos.insert_task(conn, goal_id=gid, title="读完第 3 章", item_type="book")
        t2 = repos.insert_task(conn, goal_id=gid, title="背 20 个单词", item_type="practice")
        conn.commit()
    finally:
        conn.close()
    return gid, t1, t2
