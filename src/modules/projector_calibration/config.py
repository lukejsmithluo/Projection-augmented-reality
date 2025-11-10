from __future__ import annotations

from pydantic_settings import BaseSettings


class ProjectorCalibrationSettings(BaseSettings):
    """投影标定配置：用于传递基本参数（可扩展）"""

    proj_height: int = 1080
    proj_width: int = 1920
    rounds: int = 1
