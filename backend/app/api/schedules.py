"""日程管理接口。"""
from __future__ import annotations

from sqlite3 import Connection
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..db import repos
from ..schemas.models import ScheduleCreate, ScheduleUpdate
from .deps import get_conn

router = APIRouter(prefix="/api/schedules", tags=["schedules"])
ConnDep = Annotated[Connection, Depends(get_conn)]


@router.get("")
def list_schedules(start: str, end: str, conn: ConnDep = None):
    if end <= start:
        raise HTTPException(status_code=400, detail="end 必须晚于 start")
    return repos.list_schedules_between(conn, start, end)


@router.post("")
def create_schedule(payload: ScheduleCreate, conn: ConnDep):
    if payload.goal_id and not repos.get_goal(conn, payload.goal_id):
        raise HTTPException(status_code=404, detail="目标不存在")
    schedule_id = repos.insert_schedule(
        conn, title=payload.title, start_at=payload.start_at, end_at=payload.end_at,
        goal_id=payload.goal_id, task_id=payload.task_id, remind_at=payload.remind_at,
    )
    return repos.get_schedule(conn, schedule_id)


@router.patch("/{schedule_id}")
def update_schedule(schedule_id: int, payload: ScheduleUpdate, conn: ConnDep):
    schedule = repos.update_schedule(conn, schedule_id, **payload.model_dump(exclude_none=True))
    if schedule is None:
        raise HTTPException(status_code=404, detail="日程不存在")
    return schedule
