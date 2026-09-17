"""目标 / 学习计划接口。"""
from __future__ import annotations

from sqlite3 import Connection
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..core import llm, planner
from ..db import repos
from ..schemas.models import GoalCreate, GoalPlanRequest, GoalUpdate, TaskCreate, TaskUpdate
from .deps import get_conn

router = APIRouter(prefix="/api/goals", tags=["goals"])
ConnDep = Annotated[Connection, Depends(get_conn)]


def _serialize(conn: Connection, goal: dict) -> dict:
    out = dict(goal)
    out["tasks"] = repos.list_tasks(conn, goal["id"])
    out["progress"] = repos.goal_progress(conn, goal["id"])
    return out


@router.get("")
def list_goals(category: str | None = None, status: str | None = None, conn: ConnDep = None):
    goals = repos.list_goals(conn, category=category, status=status)
    return [_serialize(conn, g) for g in goals]


@router.post("")
def create_goal(payload: GoalCreate, conn: ConnDep):
    goal_id = repos.insert_goal(
        conn, title=payload.title, description=payload.description, reason=payload.reason,
        category=payload.category, target_date=payload.target_date,
    )
    for t in payload.tasks:
        repos.insert_task(conn, goal_id=goal_id, title=t.title,
                          item_type=t.item_type, planned_date=t.planned_date)
    return _serialize(conn, repos.get_goal(conn, goal_id))


@router.post("/plan")
def plan_goal(payload: GoalPlanRequest, conn: ConnDep):
    """目标设置向导：根据描述生成标题与子任务（不落库，供确认）。"""
    try:
        return planner.plan_tasks(payload.description)
    except llm.LLMError as exc:
        raise HTTPException(status_code=502, detail=f"LLM 不可用：{exc}")


@router.post("/from-plan")
def create_goal_from_plan(payload: GoalPlanRequest, conn: ConnDep):
    """向导确认后落库：描述 → 拆解 → 建目标 + 子任务（单事务）。"""
    try:
        return planner.create_goal_with_plan(conn, description=payload.description,
                                             category=payload.category, reason=payload.reason)
    except llm.LLMError as exc:
        raise HTTPException(status_code=502, detail=f"LLM 不可用：{exc}")


@router.patch("/{goal_id}")
def update_goal(goal_id: int, payload: GoalUpdate, conn: ConnDep):
    goal = repos.update_goal(conn, goal_id, **payload.model_dump(exclude_none=True))
    if goal is None:
        raise HTTPException(status_code=404, detail="目标不存在")
    return _serialize(conn, goal)


@router.delete("/{goal_id}")
def delete_goal(goal_id: int, conn: ConnDep):
    if not repos.delete_goal(conn, goal_id):
        raise HTTPException(status_code=404, detail="目标不存在")
    return {"ok": True}


@router.post("/{goal_id}/tasks")
def create_task(goal_id: int, payload: TaskCreate, conn: ConnDep):
    if not repos.get_goal(conn, goal_id):
        raise HTTPException(status_code=404, detail="目标不存在")
    task_id = repos.insert_task(conn, goal_id=goal_id, title=payload.title,
                                item_type=payload.item_type, planned_date=payload.planned_date)
    return repos.get_task(conn, task_id)


@router.patch("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskUpdate, conn: ConnDep):
    task = repos.update_task(conn, task_id, **payload.model_dump(exclude_none=True))
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, conn: ConnDep):
    if not repos.delete_task(conn, task_id):
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"ok": True}
