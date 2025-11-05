from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings


class SpatialMappingSettings(BaseSettings):
    """空间映射配置：与运行参数对齐"""

    build_mesh: bool = True
    save_texture: bool = True
    zed_env_python: Optional[str] = "Pre-scanned point cloud/zed_env/Scripts/python.exe"