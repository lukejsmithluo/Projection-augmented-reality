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
            # 运行模式
            self._build_mesh = config.build_mesh
            self._save_texture = config.save_texture

            # 输入与分辨率
            self._input_svo_file = config.input_svo_file
            self._ip_address = config.ip_address
            self._resolution = config.resolution

            # 空间映射与导出
            self._mesh_filter = config.mesh_filter
            self._units = config.units
            self._mapping_resolution = config.mapping_resolution
            self._mapping_range = config.mapping_range
            self._max_memory_usage = config.max_memory_usage
            self._update_rate_ms = config.update_rate_ms
            self._depth_mode = config.depth_mode
        else:
            # 默认值
            self._zed_env_python = Path(
                "Pre-scanned point cloud/zed_env/Scripts/python.exe"
            ).resolve()
            self._build_mesh = True
            self._save_texture = True
            self._input_svo_file = ""
            self._ip_address = ""
            self._resolution = ""
            self._mesh_filter = "MEDIUM"
            self._units = "CENTIMETER"
            self._mapping_resolution = "MEDIUM"
            self._mapping_range = "MEDIUM"
            self._max_memory_usage = 2048
            self._update_rate_ms = 700
            self._depth_mode = "NEURAL_PLUS"

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
        # 输入与分辨率
        if getattr(self, "_input_svo_file", ""):
            args.extend(["--input_svo_file", self._input_svo_file])
        elif getattr(self, "_ip_address", ""):
            args.extend(["--ip_address", self._ip_address])
        if getattr(self, "_resolution", ""):
            args.extend(["--resolution", self._resolution])
        # 空间映射与导出
        if getattr(self, "_mesh_filter", None):
            args.extend(["--mesh_filter", self._mesh_filter])
        if getattr(self, "_units", None):
            args.extend(["--units", self._units])
        if getattr(self, "_mapping_resolution", None):
            args.extend(["--mapping_resolution", self._mapping_resolution])
        if getattr(self, "_mapping_range", None):
            args.extend(["--mapping_range", self._mapping_range])
        if getattr(self, "_max_memory_usage", None) is not None:
            args.extend(["--max_memory_usage", str(self._max_memory_usage)])
        elif getattr(self, "_max_memory_mb", None) is not None:
            args.extend(["--max_memory_mb", str(self._max_memory_mb)])
        if getattr(self, "_update_rate_ms", None) is not None:
            args.extend(["--update_rate_ms", str(self._update_rate_ms)])
        if getattr(self, "_depth_mode", None):
            args.extend(["--depth_mode", self._depth_mode])
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
