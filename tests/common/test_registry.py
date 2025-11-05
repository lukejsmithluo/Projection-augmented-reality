# [Test] 单元测试文件：模块注册中心（使用完可删除）
from pydantic_settings import BaseSettings

from src.common.module_base import ModuleBase
from src.common.registry import ModuleRegistry


class DummyModule(ModuleBase):
    def configure(self, config: BaseSettings) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def status(self) -> dict:
        return {"ok": True}


def test_register_and_get():
    reg = ModuleRegistry()
    dm = DummyModule()
    reg.register("dummy", dm)
    assert reg.get("dummy") is dm
    assert "dummy" in reg.all()
