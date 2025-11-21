from __future__ import annotations

import logging
from typing import Optional

from pydantic_settings import BaseSettings

from ...common.module_base import ModuleBase
from ...common.types import ModuleState
from .config import AIImageSettings
from .services.openai_service import OpenAIImageService
from .services.gemini_service import GeminiImageService
from .services.storage_service import StorageService

logger = logging.getLogger(__name__)


class AIImageGenerationModule(ModuleBase):
    """AI Image Generation module wrapper.

    Manages image operations and storage for multiple providers.
    """

    def __init__(self) -> None:
        self._state: ModuleState = ModuleState.STOPPED
        self._settings = AIImageSettings()
        self._storage = StorageService(self._settings)
        self._svc_openai = OpenAIImageService(self._settings, self._storage)
        self._svc_gemini = GeminiImageService(self._storage)
        self._last_output: Optional[str] = None

    def configure(self, config: BaseSettings) -> None:
        if isinstance(config, AIImageSettings):
            self._settings = config
            self._storage = StorageService(self._settings)
            self._svc_openai = OpenAIImageService(self._settings, self._storage)
            self._svc_gemini = GeminiImageService(self._storage)
            logger.info(
                "AIImageGenerationModule configured: output_dir=%s model=%s",
                config.output_dir,
                config.model,
            )

    def start(self) -> None:
        self._state = ModuleState.RUNNING

    def stop(self) -> None:
        self._state = ModuleState.STOPPED

    def status(self) -> dict:
        return {
            "state": self._state,
            "last_output": self._last_output,
            # For compatibility, expose OpenAI key presence
            "has_api_key": self._svc_openai.has_api_key(),
        }

    def save_upload(self, upload_name: str, content: bytes) -> str:
        """保存上传文件到 uploads 目录并返回路径字符串。"""
        path = self._storage.save_upload(upload_name, content)
        return str(path)

    # Convenience for routes
    def edit_image(
        self,
        prompt: str,
        upload_name: str,
        content: bytes,
        size: Optional[str] = None,
        model: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        image_resolution: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> str:
        up_path = self._storage.save_upload(upload_name, content)
        prov = (provider or "openai").strip().lower()
        if prov == "gemini" or (model or "").lower().startswith("gemini") or (model or "").lower().startswith("imagen"):
            out_path = self._svc_gemini.edit_image(
                prompt=prompt, image_path=up_path, size=size, model=model, aspect_ratio=aspect_ratio, image_size=image_resolution
            )
        else:
            out_path = self._svc_openai.edit_image(
                prompt=prompt, image_path=up_path, size=size, model=model
            )
        self._last_output = str(out_path)
        return str(out_path)
