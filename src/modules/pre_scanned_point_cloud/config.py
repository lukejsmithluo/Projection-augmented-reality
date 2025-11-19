from __future__ import annotations

from typing import Literal, Optional

from pydantic_settings import BaseSettings


class SpatialMappingSettings(BaseSettings):
    """空间映射配置：与运行参数对齐"""

    # 运行模式
    build_mesh: bool = True
    save_texture: bool = True

    # 输入与分辨率
    input_svo_file: str = ""
    ip_address: str = ""
    resolution: str = ""

    # 空间映射与导出
    mesh_filter: Literal["NONE", "LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    units: Literal["METER", "CENTIMETER"] = "CENTIMETER"
    mapping_resolution: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    mapping_range: Literal["SHORT", "MEDIUM", "LONG"] = "MEDIUM"
    max_memory_usage: int = 2048
    update_rate_ms: int = 700
    depth_mode: Literal["NEURAL", "NEURAL_PLUS"] = "NEURAL_PLUS"

    # 运行环境
    zed_env_python: Optional[str] = "Pre-scanned point cloud/zed_env/Scripts/python.exe"
