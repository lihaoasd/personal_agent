"""复盘接口。"""
from __future__ import annotations

from datetime import date
from sqlite3 import Connection
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..core import llm, reviewer
from ..db import repos
from ..schemas.models import ReviewGenerateRequest, ReviewCreateRequest
from .deps import get_conn

router = APIRouter(prefix="/api/reviews", tags=["reviews"])
ConnDep = Annotated[Connection, Depends(get_conn)]


@router.get("")
def list_reviews(period_type: str = "all", limit: int = 50, conn: ConnDep = None):
    limit = max(1, min(limit, 50))
    if period_type == "all":
        return repos.list_reviews(conn, limit=limit)
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


@router.post("")
def create_review(payload: ReviewCreateRequest, conn: ConnDep):
    """用户手动写复盘。"""
    # 自动生成标题：从内容第一行提取
    title = ""
    for line in payload.content.split('\n'):
        line = line.strip().lstrip('#').strip()
        if line and len(line) < 30:
            title = line
            break
    if not title:
        title = f"{payload.period_start} ~ {payload.period_end}"
    review_id = repos.insert_review(
        conn, title=title, period_type="manual", period_start=payload.period_start,
        period_end=payload.period_end, content=payload.content, stats={},
    )
    return {"id": review_id, "title": title, "period_start": payload.period_start,
            "period_end": payload.period_end, "content": payload.content}
