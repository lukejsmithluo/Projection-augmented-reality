from pydantic import BaseModel
from typing import Optional, Dict, Any

class CalibrationConfig(BaseModel):
    """Configuration for running calibration"""
    proj_height: int = 720
    proj_width: int = 1280
    chess_vert: int = 6
    chess_hori: int = 9
    chess_block_size: float = 20.0
    graycode_step: int = 1
    black_thr: int = 40
    white_thr: int = 5
    monitor_index: int = 1
    output_dir: str = "data/calibration/captures"

class CaptureSessionRequest(BaseModel):
    """Configuration for starting a capture session"""
    proj_height: int = 720
    proj_width: int = 1280
    graycode_step: int = 1
    monitor_index: int = 1
    output_dir: str = "data/calibration/captures"

class PatternGenerationRequest(BaseModel):
    """Configuration for generating graycode patterns"""
    proj_height: int = 720
    proj_width: int = 1280
    graycode_step: int = 1
    output_dir: str = "data/calibration/patterns"

class CalibrationRunRequest(BaseModel):
    """Legacy request (kept for compatibility if needed, but mapped to CalibrationConfig)"""
    proj_height: int
    proj_width: int
    rounds: int = 1
