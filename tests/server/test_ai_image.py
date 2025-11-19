# [Test] 单元测试文件：AI图像生成路由（使用完可删除）
from __future__ import annotations

from fastapi.testclient import TestClient

from src.server.main import create_app


def test_ai_image_status():
    client = TestClient(create_app())
    resp = client.get("/ai-image/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["module"] == "ai_image_generation"
    assert "status" in data
    assert "state" in data["status"]
    assert "has_api_key" in data["status"]


def test_ai_image_edit_no_api_key(monkeypatch):
    # 确保环境中没有 OPENAI_API_KEY，避免真实外呼
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(create_app())
    files = {
        "image": ("test.png", b"\x89PNG\r\n\x1a\n", "image/png"),
    }
    data = {"prompt": "make it look like watercolor", "size": "512x512"}
    resp = client.post("/ai-image/edit", files=files, data=data)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["accepted"] is False
    assert payload["error_code"] == "NO_API_KEY"


def test_ai_image_edit_bad_content_type(monkeypatch):
    # 设置一个占位的 API KEY，使路由继续进行到类型校验
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    client = TestClient(create_app())
    files = {
        "image": ("test.txt", b"hello", "text/plain"),
    }
    data = {"prompt": "add soft color grading"}
    resp = client.post("/ai-image/edit", files=files, data=data)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["accepted"] is False
    assert payload["error_code"] == "BAD_CONTENT_TYPE"
