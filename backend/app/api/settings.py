"""模型配置接口：读取 / 保存 / 测试连接（保存即热更新生效）。"""
from __future__ import annotations

import time
from sqlite3 import Connection
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..core import llm
from ..schemas.models import ModelConfigRequest
from ..services import model_config_service
from .deps import get_conn

router = APIRouter(prefix="/api/settings", tags=["settings"])
ConnDep = Annotated[Connection, Depends(get_conn)]


def _masked(key: str) -> str:
    """脱敏：保留首 2 尾 2 字符，其余打码。"""
    if not key:
        return ""
    if len(key) <= 4:
        return "*" * len(key)
    return key[:2] + "*" * (len(key) - 4) + key[-2:]


def _view(cfg: dict) -> dict:
    key = (cfg.get("llm_api_key") or "").strip()
    return {
        "base_url": (cfg.get("llm_base_url") or "").strip(),
        "api_key_set": bool(key),
        "api_key_masked": _masked(key),
        "model": (cfg.get("llm_model") or "").strip(),
        "provider_ready": bool(key),
    }


@router.get("/model")
def get_model(conn: ConnDep):
    """返回当前模型配置（API Key 仅返回脱敏与是否已设置）。"""
    return _view(model_config_service.load_config(conn))


@router.post("/model")
def save_model(payload: ModelConfigRequest, conn: ConnDep):
    """保存模型配置并立即热更新提供商；api_key 为空时保留已存值。"""
    base_url = (payload.base_url or "").strip()
    model = (payload.model or "").strip()
    if not base_url or not model:
        raise HTTPException(status_code=400, detail="Base URL 与模型名不能为空")

    saved = model_config_service.load_config(conn)
    api_key = (payload.api_key or "").strip() or (saved.get("llm_api_key") or "").strip()

    cfg = {"llm_base_url": base_url, "llm_api_key": api_key, "llm_model": model}
    model_config_service.save_config(
        conn, base_url=base_url, api_key=api_key, model=model,
    )
    model_config_service.apply_config(cfg)
    return _view(cfg)


@router.post("/model/test")
def test_model(conn: ConnDep):
    """用当前提供商做一次最小调用，返回耗时与结果（不改变配置）。"""
    t0 = time.perf_counter()
    try:
        reply = llm.chat_text(
            system="你是一个连接测试助手",
            user="请只回复四个字：连接成功",
        )
    except llm.LLMError as exc:
        return {"ok": False, "error": str(exc), "latency_ms": None}
    return {
        "ok": True,
        "latency_ms": int((time.perf_counter() - t0) * 1000),
        "reply": (reply or "")[:100],
    }
