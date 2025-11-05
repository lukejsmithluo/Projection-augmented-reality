# [Test] 单元测试文件：FastAPI健康检查（使用完可删除）
from fastapi.testclient import TestClient

from src.server.main import create_app


def test_health():
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
