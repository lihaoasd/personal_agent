"""复盘接口。"""
from __future__ import annotations

from datetime import date
from sqlite3 import Connection
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..core import llm, reviewer
from ..db import repos
from ..schemas.models import ReviewGenerateRequest
from .deps import get_conn

router = APIRouter(prefix="/api/reviews", tags=["reviews"])
ConnDep = Annotated[Connection, Depends(get_conn)]


@router.get("")
def list_reviews(period_type: str = "weekly", limit: int = 10, conn: ConnDep = None):
    limit = max(1, min(limit, 50))
    return repos.list_reviews(conn, period_type=period_type, limit=limit)


@router.post("/generate")
def generate(payload: ReviewGenerateRequest, conn: ConnDep):
    try:
        return reviewer.generate_review(
            conn, period_start=payload.period_start,
            period_end=payload.period_end, today=date.today(),
        )
    except llm.LLMError as exc:
        raise HTTPException(status_code=502, detail=f"LLM 不可用：{exc}")
