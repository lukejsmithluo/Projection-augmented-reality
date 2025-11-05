from fastapi import Request

from ...common.registry import ModuleRegistry


def get_registry(request: Request) -> ModuleRegistry:
    """提供模块注册中心依赖"""
    return request.app.state.registry  # type: ignore[attr-defined]
