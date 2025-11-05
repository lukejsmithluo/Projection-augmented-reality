from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings

from ...common.module_base import ModuleBase
from ...common.types import ModuleState
from .config import ProjectorCalibrationSettings


class ProjectorCalibrationModule(ModuleBase):
    """投影标定模块包装类：通过子进程调用现有脚本"""

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._state: ModuleState = ModuleState.STOPPED

    def configure(self, config: BaseSettings) -> None:
        # 保存基本参数（当前脚本未通过CLI接收，后续扩展）
        if isinstance(config, ProjectorCalibrationSettings):
            self._proj_height = config.proj_height
            self._proj_width = config.proj_width
            self._rounds = config.rounds

    def start(self) -> None:
        base_dir = Path("Projector-Calibration").resolve()
        script = base_dir / "calibrate_optimized.py"
        self._proc = subprocess.Popen([sys.executable, str(script)], cwd=str(base_dir))
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
