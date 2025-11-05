from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings

from ...common.module_base import ModuleBase
from ...common.types import ModuleState
from .config import SpatialMappingSettings


class SpatialMappingModule(ModuleBase):
    """空间映射模块包装类：通过子进程调用现有脚本"""

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._state: ModuleState = ModuleState.STOPPED
        self._zed_env_python: Optional[Path] = None

    def configure(self, config: BaseSettings) -> None:
        # 读取配置参数
        if isinstance(config, SpatialMappingSettings):
            if config.zed_env_python:
                self._zed_env_python = Path(config.zed_env_python).resolve()
            self._build_mesh = config.build_mesh
            self._save_texture = config.save_texture
        else:
            # 默认值
            self._zed_env_python = Path(
                "Pre-scanned point cloud/zed_env/Scripts/python.exe"
            ).resolve()
            self._build_mesh = True
            self._save_texture = True

    def start(self) -> None:
        if self._proc and self._proc.poll() is None:
            return
        python_exe = (
            str(self._zed_env_python) if self._zed_env_python else sys.executable
        )
        script_dir = Path("Pre-scanned point cloud/src").resolve()
        script = script_dir / "spatial_mapping.py"
        # 构建参数
        args = [python_exe, str(script)]
        if getattr(self, "_build_mesh", True):
            args.append("--build_mesh")
        if getattr(self, "_save_texture", True):
            args.append("--save_texture")
        # 使用虚拟环境运行（强制规则）
        self._proc = subprocess.Popen(args, cwd=str(script_dir))
        self._state = ModuleState.RUNNING

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()
        self._state = ModuleState.STOPPED

    def status(self) -> dict:
        return {"state": self._state}
