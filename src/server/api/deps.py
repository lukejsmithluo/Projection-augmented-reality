from fastapi import Request

from ...common.policy.region_policy import RegionPolicyService
from ...common.registry import ModuleRegistry


def get_registry(request: Request) -> ModuleRegistry:
    """提供模块注册中心依赖"""
    return request.app.state.registry  # type: ignore[attr-defined]


def get_region_policy(request: Request) -> RegionPolicyService:
    """提供地区策略服务依赖"""
    return request.app.state.region_policy  # type: ignore[attr-defined]
