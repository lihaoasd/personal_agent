"""模型配置服务：读取数据库配置、构建并热更新 LLM 提供商。

存储策略：数据库 app_state 表（单用户本地应用）优先于 .env；
保存即调用 apply_config 热更新全局提供商，无需重启。
"""
from __future__ import annotations

from sqlite3 import Connection

from ..core import llm
from ..db import repos

MODEL_KEYS = ("llm_base_url", "llm_api_key", "llm_model")


def load_config(conn: Connection) -> dict:
    """读取数据库中的模型配置（未设置过的键为 None）。"""
    return {k: repos.state_get(conn, k) for k in MODEL_KEYS}


def save_config(conn: Connection, *, base_url: str, api_key: str, model: str) -> None:
    repos.state_set(conn, "llm_base_url", base_url)
    repos.state_set(conn, "llm_api_key", api_key)
    repos.state_set(conn, "llm_model", model)


def build_provider(cfg: dict) -> llm.OpenAICompatProvider | None:
    """无有效 key 时返回 None（对话接口将返回可读错误）。"""
    key = (cfg.get("llm_api_key") or "").strip()
    if not key:
        return None
    return llm.OpenAICompatProvider(
        base_url=(cfg.get("llm_base_url") or "").strip(),
        api_key=key,
        model=(cfg.get("llm_model") or "").strip(),
    )


def apply_config(cfg: dict) -> None:
    """按配置热更新全局 LLM 提供商。"""
    llm.set_provider(build_provider(cfg))
