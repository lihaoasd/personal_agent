"""快捷模板接口。"""
from __future__ import annotations

from sqlite3 import Connection
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..db import repos
from ..schemas.models import TemplateCreate
from .deps import get_conn

router = APIRouter(prefix="/api/templates", tags=["templates"])
ConnDep = Annotated[Connection, Depends(get_conn)]


@router.get("")
def list_templates(conn: ConnDep = None):
    return repos.list_templates(conn)


@router.post("")
def create_template(payload: TemplateCreate, conn: ConnDep):
    if payload.goal_id and not repos.get_goal(conn, payload.goal_id):
        raise HTTPException(status_code=404, detail="目标不存在")
    template_id = repos.insert_template(
        conn, label=payload.label, event_type=payload.event_type,
        amount=payload.amount, unit=payload.unit, goal_id=payload.goal_id,
        sort_order=payload.sort_order,
    )
    return repos.list_templates(conn)  # 返回全量，前端直接刷新


@router.delete("/{template_id}")
def delete_template(template_id: int, conn: ConnDep):
    if not repos.delete_template(conn, template_id):
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"ok": True}
