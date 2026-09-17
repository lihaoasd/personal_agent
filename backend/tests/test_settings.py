"""模型配置 API 测试：脱敏读取、保存热更新、空 key 保留、连接测试。"""
from __future__ import annotations

from app.core import llm


def test_get_model_default_empty(client):
    data = client.get("/api/settings/model").json()
    assert data["api_key_set"] is False
    assert data["provider_ready"] is False
    assert data["api_key_masked"] == ""


def test_save_model_persists_and_hot_applies(client):
    resp = client.post("/api/settings/model", json={
        "base_url": "http://mock", "api_key": "sk-test-123456", "model": "test-model",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["api_key_set"] is True
    assert body["provider_ready"] is True
    assert "sk-test-123456" not in body["api_key_masked"]  # 不泄露完整 key
    assert body["api_key_masked"].startswith("sk")

    # 热更新：全局提供商已被替换为 OpenAI 兼容 Provider
    provider = llm.get_provider()
    assert isinstance(provider, llm.OpenAICompatProvider)
    assert provider.model == "test-model"

    # 持久化：重新读取仍生效
    again = client.get("/api/settings/model").json()
    assert again["api_key_set"] is True
    assert again["model"] == "test-model"


def test_save_without_key_keeps_existing(client):
    client.post("/api/settings/model", json={
        "base_url": "http://mock", "api_key": "sk-keep-1234", "model": "m1",
    })
    resp = client.post("/api/settings/model", json={"base_url": "http://mock", "model": "m2"})
    body = resp.json()
    assert body["model"] == "m2"
    assert body["api_key_set"] is True  # key 被保留


def test_save_requires_base_url_and_model(client):
    assert client.post("/api/settings/model", json={"model": "x"}).status_code == 400
    assert client.post("/api/settings/model", json={"base_url": "http://x"}).status_code == 400


def test_model_test_with_provider(client, app):
    llm.set_provider(app.state.fake_provider)
    resp = client.post("/api/settings/model/test")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["latency_ms"] is not None


def test_model_test_without_provider(client, app):
    llm.set_provider(None)
    resp = client.post("/api/settings/model/test")
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert "未配置" in resp.json()["error"]
