"""LLM 提供商：OpenAI 兼容 Chat Completions；支持多轮消息和 function calling。"""
from __future__ import annotations

import json
from typing import Any, Protocol

import httpx


class LLMError(Exception):
    """LLM 调用或解析失败。"""


class Provider(Protocol):
    def chat(self, *, system: str, user: str, json_mode: bool = False) -> str: ...
    def chat_messages(self, messages: list[dict[str, Any]], tools: list[dict] | None = None) -> dict: ...


class OpenAICompatProvider:
    """通过 HTTP 调用任意 OpenAI 兼容 /v1/chat/completions 端点。"""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def chat(self, *, system: str, user: str, json_mode: bool = False) -> str:
        if not self.api_key:
            raise LLMError("未配置 LLM API Key（OPENAI_API_KEY）")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.3,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60,
        )
        if resp.status_code != 200:
            raise LLMError(f"LLM 返回 {resp.status_code}: {resp.text[:200]}")
        return resp.json()["choices"][0]["message"]["content"]

    def chat_messages(self, messages: list[dict[str, Any]], tools: list[dict] | None = None) -> dict:
        """多轮对话，支持 function calling。返回完整 message 对象。"""
        if not self.api_key:
            raise LLMError("未配置 LLM API Key（OPENAI_API_KEY）")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "thinking": {"type": "enabled"},  # 开启推理模式
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60,
        )
        if resp.status_code != 200:
            raise LLMError(f"LLM 返回 {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        # 返回完整 data，包含 choices[0].message 和 usage
        return data


_provider: Provider | None = None


def set_provider(provider: Provider | None) -> None:
    global _provider
    _provider = provider


def get_provider() -> Provider | None:
    """返回当前提供商（测试与配置页检测用）。"""
    return _provider


def _current() -> Provider:
    if _provider is None:
        raise LLMError("LLM 提供商未配置")
    return _provider


def chat_json(system: str, user: str) -> dict:
    """请求 JSON 模式输出；解析失败重试一次，仍失败抛 LLMError。"""
    last_error: Exception | None = None
    for _ in range(2):
        text = _current().chat(system=system, user=user, json_mode=True)
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError as exc:
            last_error = exc
    raise LLMError(f"LLM 返回非法 JSON: {last_error}")


def chat_text(system: str, user: str) -> str:
    return _current().chat(system=system, user=user)


def chat_messages(messages: list[dict[str, Any]], tools: list[dict] | None = None) -> dict:
    """多轮对话，支持 function calling。"""
    return _current().chat_messages(messages, tools=tools)
