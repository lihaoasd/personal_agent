"""意图抽取测试：意图识别与日期归一化。"""
from __future__ import annotations

import json
from datetime import date

from app.core import extractor


def _extract(app, user_message: str, script_json: dict) -> dict:
    app.state.fake_provider.script = [json.dumps(script_json, ensure_ascii=False)]
    return extractor.extract_intent(
        messages=[{"role": "user", "content": user_message}],
        goals=[], templates=[], today=date(2026, 9, 13),
    )


def test_extract_checkin(app):
    parsed = _extract(app, "今天读了 20 页书", {
        "intent": "checkin", "goal_id": 1, "task_id": None,
        "event": {"event_type": "reading", "amount": 20, "unit": "页"},
        "happened_on": None, "schedule": None, "goal": None, "need_clarify": None,
    })
    assert parsed["intent"] == "checkin"
    assert parsed["event"]["amount"] == 20


def test_extract_backfill_resolves_date(app):
    parsed = _extract(app, "昨天读了 20 页", {
        "intent": "backfill", "goal_id": None, "task_id": None,
        "event": {"event_type": "reading", "amount": 20, "unit": "页"},
        "happened_on": "2026-09-12", "schedule": None, "goal": None, "need_clarify": None,
    })
    assert parsed["intent"] == "backfill"
    assert parsed["happened_on"] == "2026-09-12"


def test_extract_future_date_normalized_to_none(app):
    parsed = _extract(app, "后天读 20 页", {
        "intent": "backfill", "goal_id": None, "task_id": None,
        "event": {"event_type": "reading", "amount": 20, "unit": "页"},
        "happened_on": "2026-09-15", "schedule": None, "goal": None, "need_clarify": None,
    })
    assert parsed["happened_on"] is None  # 未来日期按无效处理


def test_extract_unknown_intent_falls_back_to_chat(app):
    parsed = _extract(app, "随便聊聊", {
        "intent": "hacking", "goal_id": None, "task_id": None, "event": None,
        "happened_on": None, "schedule": None, "goal": None, "need_clarify": None,
    })
    assert parsed["intent"] == "chat"
