from fastapi import APIRouter, Depends, HTTPException

from ....common.registry import ModuleRegistry
from ....modules.projector_calibration.config import ProjectorCalibrationSettings
from ..deps import get_registry
from ..schemas.calibration import (
    CalibrationConfig,
    CaptureSessionRequest,
    PatternGenerationRequest,
)

router = APIRouter(tags=["calibration"])


def get_module(registry: ModuleRegistry):
    mod = registry.get("projector_calibration")
    if mod is None:
        raise HTTPException(
            status_code=404, detail="Projector Calibration module not found"
        )
    return mod


@router.get("/status")
def get_status(registry: ModuleRegistry = Depends(get_registry)):
    mod = get_module(registry)
    return mod.status()


@router.post("/camera/params")
def get_camera_params(registry: ModuleRegistry = Depends(get_registry)):
    """Retrieve and save ZED camera parameters"""
    mod = get_module(registry)
    try:
        params = mod.get_camera_params()
        return {"success": True, "params": params}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capture/start")
def start_capture_session(
    req: CaptureSessionRequest, registry: ModuleRegistry = Depends(get_registry)
):
    """Start a capture session (open camera, window)"""
    mod = get_module(registry)
    # Update config
    settings = ProjectorCalibrationSettings(
        proj_height=req.proj_height,
        proj_width=req.proj_width,
        graycode_step=req.graycode_step,
        monitor_index=req.monitor_index,
        output_dir=req.output_dir,
    )
    mod.configure(settings)
    try:
        mod.start_capture_session()
        return {"success": True, "message": "Capture session started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pattern/generate")
def generate_patterns(
    req: PatternGenerationRequest, registry: ModuleRegistry = Depends(get_registry)
):
    """Generate graycode patterns"""
    mod = get_module(registry)
    try:
        files = mod.generate_patterns(
            width=req.proj_width,
            height=req.proj_height,
            step=req.graycode_step,
            output_dir=req.output_dir,
        )
        return {
            "success": True,
            "message": f"Generated {len(files)} patterns",
            "files": files,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capture/shot")
def capture_next_pose(registry: ModuleRegistry = Depends(get_registry)):
    """Capture the current pose (project patterns and save)"""
    mod = get_module(registry)
    try:
        success = mod.capture_next_pose()
        if success:
            return {"success": True, "message": "Pose captured successfully"}
        else:
            return {"success": False, "message": "Failed to capture pose"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capture/stop")
def stop_capture_session(registry: ModuleRegistry = Depends(get_registry)):
    """Stop the capture session"""
    mod = get_module(registry)
    mod.stop_capture_session()
    return {"success": True, "message": "Capture session stopped"}


@router.post("/run")
def run_calibration(
    req: CalibrationConfig, registry: ModuleRegistry = Depends(get_registry)
):
    """Run the calibration algorithm"""
    mod = get_module(registry)
    # Update config with calibration params
    # Note: we use model_dump(exclude_unset=True) to update only provided fields if needed,
    # but here we construct a full settings object.
    settings = ProjectorCalibrationSettings(**req.model_dump())
    mod.configure(settings)

    try:
        result = mod.run_calibration_task()
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result")
def calibration_result(registry: ModuleRegistry = Depends(get_registry)):
    """返回最新标定结果"""
    # For now, just return status or last result if stored in memory?
    # The run_calibration endpoint returns the result directly.
    # We can assume the result is saved to disk (calibration_result.xml) and return that if needed.
    mod = get_module(registry)
    return {"module": "projector_calibration", "status": mod.status()}
