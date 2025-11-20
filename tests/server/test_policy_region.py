# [Test] 单元测试文件：地区策略与路由（使用完可删除）
from __future__ import annotations

from fastapi.testclient import TestClient

from src.server.api.deps import get_region_policy
from src.server.main import create_app


class _StubPolicyAllowed:
    def evaluate(self):
        from src.common.policy.region_policy import RegionCheckResult

        return RegionCheckResult(
            allowed=True,
            policy_mode="hybrid",
            country="United States",
            country_code="US",
            subdivision=None,
            city="San Francisco",
            exit_ip="203.0.113.1",
            connectivity_ok=True,
            reason=None,
            checked_at=0.0,
        )


class _StubPolicyBlocked:
    def evaluate(self):
        from src.common.policy.region_policy import RegionCheckResult

        return RegionCheckResult(
            allowed=False,
            policy_mode="hybrid",
            country="",
            country_code="ZZ",
            subdivision=None,
            city="",
            exit_ip="203.0.113.2",
            connectivity_ok=True,
            reason="not in allowed list",
            checked_at=0.0,
        )


def test_region_status_endpoint():
    app = create_app()
    # 覆盖依赖以避免外部网络调用
    app.dependency_overrides[get_region_policy] = lambda: _StubPolicyAllowed()
    client = TestClient(app)
    resp = client.get("/policy/region/status")
    assert resp.status_code == 200
    data = resp.json()
    # 仅校验应答结构与关键字段存在
    assert "allowed" in data
    assert "country_code" in data
    assert "policy_mode" in data


def test_ai_image_edit_region_blocked(monkeypatch):
    # 设置占位 API KEY 以通过前置校验
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    app = create_app()
    app.dependency_overrides[get_region_policy] = lambda: _StubPolicyBlocked()
    client = TestClient(app)
    files = {
        "image": ("test.png", b"\x89PNG\r\n\x1a\n", "image/png"),
    }
    data = {"prompt": "make it look like watercolor", "size": "512x512"}
    resp = client.post("/ai-image/edit", files=files, data=data)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["accepted"] is False
    assert payload["error_code"] == "REGION_BLOCKED"
