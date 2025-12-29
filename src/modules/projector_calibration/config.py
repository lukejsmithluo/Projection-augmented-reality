from __future__ import annotations

from pydantic_settings import BaseSettings


class ProjectorCalibrationSettings(BaseSettings):
    """投影标定配置：用于传递基本参数（可扩展）"""

    proj_height: int = 720  # Default to 720p as per user manual
    proj_width: int = 1280
    
    # Calibration Board Params
    chess_vert: int = 6  # Number of internal corners (rows)
    chess_hori: int = 9  # Number of internal corners (cols)
    chess_block_size: float = 20.0  # mm
    
    # Graycode Params
    graycode_step: int = 1
    black_thr: int = 40
    white_thr: int = 5
    
    # System Params
    monitor_index: int = 1
    output_dir: str = "data/calibration/captures"
    camera_param_file: str = "data/calibration/camera_config.json"
