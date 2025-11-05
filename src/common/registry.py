from __future__ import annotations

from typing import Dict, Optional

from .module_base import ModuleBase


class ModuleRegistry:
    """模块注册中心：管理模块实例与生命周期"""

    def __init__(self) -> None:
        self._modules: Dict[str, ModuleBase] = {}

    def register(self, name: str, module: ModuleBase) -> None:
        """注册模块，名称不可重复。"""
        if name in self._modules:
            raise ValueError(f"Module '{name}' already registered")
        self._modules[name] = module

    def get(self, name: str) -> Optional[ModuleBase]:
        """获取模块。"""
        return self._modules.get(name)

    def all(self) -> Dict[str, ModuleBase]:
        """返回所有模块字典的副本。"""
        return dict(self._modules)

    def start_all(self) -> None:
        """启动全部模块。"""
        for m in self._modules.values():
            m.start()

    def stop_all(self) -> None:
        """停止全部模块。"""
        for m in self._modules.values():
            m.stop()
