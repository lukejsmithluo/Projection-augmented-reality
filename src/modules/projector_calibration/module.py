from __future__ import annotations

import json
import os
from typing import Any, Dict

from pydantic_settings import BaseSettings

from ...common.module_base import ModuleBase
from ...common.types import ModuleState
from .config import ProjectorCalibrationSettings
from .services.calibration_service import CalibrationService
from .services.camera_service import CameraService
from .services.capture_service import CaptureService
from .services.pattern_service import PatternService


class ProjectorCalibrationModule(ModuleBase):
    """Projector Calibration Module"""

    def __init__(self) -> None:
        self._state: ModuleState = ModuleState.STOPPED
        self._config: ProjectorCalibrationSettings = ProjectorCalibrationSettings()

        self._camera_service = CameraService()
        self._capture_service = CaptureService()
        self._calibration_service = CalibrationService()
        self._pattern_service = PatternService()

        self._current_capture_idx = 0

    def configure(self, config: BaseSettings) -> None:
        if isinstance(config, ProjectorCalibrationSettings):
            self._config = config

            # Configure capture service
            self._capture_service.output_dir = self._config.output_dir

    def start(self) -> None:
        # Just set state, services are started on demand
        self._state = ModuleState.RUNNING

    def stop(self) -> None:
        self._capture_service.close()
        self._state = ModuleState.STOPPED

    def status(self) -> dict:
        return {
            "state": self._state,
            "current_capture_idx": self._current_capture_idx,
            "config": self._config.model_dump(),
        }

    # --- Service Methods ---

    def get_camera_params(self) -> Dict[str, Any]:
        """Get ZED camera parameters and save to config file."""
        params = self._camera_service.get_camera_params()
        # Save to file as configured
        with open(self._config.camera_param_file, "w") as f:
            json.dump(params, f, indent=4)
        return params

    def start_capture_session(self) -> None:
        """Initialize capture session (open camera, window, generate patterns)."""
        self._capture_service.initialize(
            proj_width=self._config.proj_width,
            proj_height=self._config.proj_height,
            graycode_step=self._config.graycode_step,
            monitor_index=self._config.monitor_index,
        )
        # Find next available index
        idx = 0
        while os.path.exists(os.path.join(self._config.output_dir, f"capture_{idx}")):
            idx += 1
        self._current_capture_idx = idx

    def capture_next_pose(self) -> bool:
        """Capture the current pose."""
        success = self._capture_service.capture_pose(self._current_capture_idx)
        if success:
            self._current_capture_idx += 1
        return success

    def stop_capture_session(self) -> None:
        """Close capture session."""
        self._capture_service.close()

    def generate_patterns(
        self, width: int, height: int, step: int, output_dir: str
    ) -> list[str]:
        """Generate graycode patterns."""
        return self._pattern_service.generate_graycode_patterns(
            width=width, height=height, step=step, output_dir=output_dir
        )

    def run_calibration_task(self) -> Dict[str, Any]:
        """Run the calibration algorithm."""
        return self._calibration_service.run_calibration(
            input_dir=self._config.output_dir,
            camera_param_file=self._config.camera_param_file,
            proj_height=self._config.proj_height,
            proj_width=self._config.proj_width,
            chess_vert=self._config.chess_vert,
            chess_hori=self._config.chess_hori,
            chess_block_size=self._config.chess_block_size,
            graycode_step=self._config.graycode_step,
            black_thr=self._config.black_thr,
            white_thr=self._config.white_thr,
        )
