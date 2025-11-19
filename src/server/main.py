from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from ..common.config import AppSettings
from ..common.logging import setup_logging
from ..common.registry import ModuleRegistry
from ..modules.ai_image_generation.module import AIImageGenerationModule
from ..modules.pre_scanned_point_cloud.module import SpatialMappingModule
from ..modules.projector_calibration.module import ProjectorCalibrationModule
from .api.routes import ai_image_routes, calibration_routes, mapping_routes

settings = AppSettings()
setup_logging()


def create_app() -> FastAPI:
    """创建FastAPI应用（健康检查与路由注册）"""
    app = FastAPI(title=settings.app_name)

    # 注册模块路由（占位，后续模块包装类接入）
    app.include_router(mapping_routes.router, prefix="/mapping")
    app.include_router(calibration_routes.router, prefix="/calibration")
    app.include_router(ai_image_routes.router, prefix="/ai-image")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    # 根路径跳转至交互文档，便于非开发者直接使用
    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/docs")

    # 模块注册中心实例与模块注册
    registry = ModuleRegistry()
    registry.register("spatial_mapping", SpatialMappingModule())
    registry.register("projector_calibration", ProjectorCalibrationModule())
    registry.register("ai_image_generation", AIImageGenerationModule())
    app.state.registry = registry
    return app


app = create_app()
