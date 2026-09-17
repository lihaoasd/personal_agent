"""主动问询状态接口（前端轮询 + Electron 通知）。"""
from __future__ import annotations

from datetime import date
from sqlite3 import Connection
from typing import Annotated

from fastapi import APIRouter, Depends

from ..services import checkin_service
from .deps import get_conn

router = APIRouter(prefix="/api/checkin", tags=["checkin"])
ConnDep = Annotated[Connection, Depends(get_conn)]


@router.get("/status")
def status(conn: ConnDep = None):
    return checkin_service.checkin_status(conn, date.today())


@router.post("/dismiss")
def dismiss(conn: ConnDep):
    checkin_service.dismiss(conn)
    return {"ok": True}
