from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Union

try:
    # Pydantic v2: BaseSettings moved to pydantic_settings
    from pydantic_settings import BaseSettings  # type: ignore
except Exception:
    from pydantic import BaseModel as BaseSettings  # 兼容占位，避免导入失败

try:
    from fastapi import APIRouter  # type: ignore
except Exception:  # FastAPI 可能未安装时占位
    APIRouter = Any  # type: ignore


class ModuleBase(ABC):
    """模块抽象基类：约束模块生命周期与对外接口"""

    @abstractmethod
    def configure(self, config: BaseSettings) -> None:
        """加载模块配置。"""

    @abstractmethod
    def start(self) -> None:
        """启动模块。"""

    @abstractmethod
    def stop(self) -> None:
        """停止模块并清理资源。"""

    @abstractmethod
    def status(self) -> dict:
        """返回模块运行状态。"""

    def get_routes(self) -> Union["APIRouter", List["APIRouter"], None]:
        """（可选）提供对外API路由。"""
        return None
