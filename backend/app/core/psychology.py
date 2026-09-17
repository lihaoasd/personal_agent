"""心理学策略库：把实证原则落成可测试的规则，与 Prompt 解耦。"""
from __future__ import annotations

from sqlite3 import Connection

from ..db import repos

# 中断多少天后触发「温和重启」话术
RESTART_THRESHOLD_DAYS = 3
# 同一类型事件达到里程碑的次数
MILESTONES = (7, 30)


def decide_tone(conn: Connection, today: str, intent: str) -> str:
    """决定本次回复的心理学基调：温和重启 / 积极反馈 / 中性。

    中断检查优先：无论什么意图，超过阈值天数都触发温和重启（用户回归场景）。
    """
    days = repos.days_since_last_event(conn, today)
    if days is not None and days >= RESTART_THRESHOLD_DAYS:
        return "gentle_restart"
    if intent in ("checkin", "template", "backfill"):
        return "positive_feedback"
    return "neutral"


def milestone_info(conn: Connection, event_type: str | None) -> dict | None:
    """同一事件类型累计次数命中里程碑时返回庆祝信息。"""
    if not event_type:
        return None
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE event_type = ?", (event_type,)).fetchone()
    count = row["n"] or 0
    for m in MILESTONES:
        if count == m:
            return {"count": count, "milestone": m}
    return None


def review_framing(stats: dict) -> str:
    """复盘心理框架：过程归因 + 低密度说明。"""
    lines = ["归因原则：把结果归因于过程与可控因素，不贴标签、不自我批评。"]
    if stats.get("days", 0) <= 2 and stats.get("event_count", 0) > 0:
        lines.append("本周记录较少，复盘以轻量说明为主，不施压。")
    if stats.get("event_count", 0) == 0:
        lines.append("本周无记录：不指责，重点帮助用户设计下周最小启动动作。")
    return "；".join(lines)
