from fastapi import APIRouter, Depends

from ....common.registry import ModuleRegistry
from ....modules.projector_calibration.config import \
    ProjectorCalibrationSettings
from ..deps import get_registry
from ..schemas.calibration import CalibrationRunRequest

router = APIRouter(tags=["calibration"])


@router.post("/run")
def run_calibration(
    req: CalibrationRunRequest, registry: ModuleRegistry = Depends(get_registry)
):
    """运行投影标定：配置并启动模块包装类"""
    mod = registry.get("projector_calibration")
    if mod is None:
        return {"accepted": False, "error": "Module not registered"}
    mod.configure(
        ProjectorCalibrationSettings(
            proj_height=req.proj_height, proj_width=req.proj_width, rounds=req.rounds
        )
    )
    mod.start()
    return {"accepted": True}


@router.get("/result")
def calibration_result(registry: ModuleRegistry = Depends(get_registry)):
    """返回最新标定结果（占位）"""
    # TODO: 解析标定输出文件，当前返回占位信息
    mod = registry.get("projector_calibration")
    return {"module": "projector_calibration", "running": mod.status() if mod else None}
