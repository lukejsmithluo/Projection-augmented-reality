from fastapi import APIRouter, Depends

from ....common.registry import ModuleRegistry
from ....modules.pre_scanned_point_cloud.config import SpatialMappingSettings
from ..deps import get_registry
from ..schemas.mapping import MappingStartRequest, MappingStopResponse

router = APIRouter(tags=["mapping"])


@router.post("/start")
def start_mapping(
    req: MappingStartRequest, registry: ModuleRegistry = Depends(get_registry)
):
    """开始空间映射：配置并启动模块包装类"""
    mod = registry.get("spatial_mapping")
    if mod is None:
        return {"accepted": False, "error": "Module not registered"}
    mod.configure(
        SpatialMappingSettings(build_mesh=req.build_mesh, save_texture=req.save_texture)
    )
    mod.start()
    return {"accepted": True}


@router.post("/stop", response_model=MappingStopResponse)
def stop_mapping(registry: ModuleRegistry = Depends(get_registry)):
    """停止空间映射并返回保存文件列表"""
    mod = registry.get("spatial_mapping")
    if mod is not None:
        mod.stop()
    # 收集输出文件
    from pathlib import Path

    data_dir = Path("Pre-scanned point cloud/data").resolve()
    saved = []
    if data_dir.exists():
        for p in data_dir.glob("*.*"):
            if p.suffix.lower() in {".obj", ".mtl", ".png"}:
                saved.append(str(p))
    return MappingStopResponse(saved_files=saved)


@router.get("/status")
def status(registry: ModuleRegistry = Depends(get_registry)):
    """返回映射模块状态"""
    mod = registry.get("spatial_mapping")
    return {"module": "spatial_mapping", "status": mod.status() if mod else None}
