from __future__ import annotations

import logging
from typing import Optional

from pydantic_settings import BaseSettings

from ...common.module_base import ModuleBase
from ...common.types import ModuleState
from .config import AIImageSettings
from .services.openai_service import OpenAIImageService
from .services.storage_service import StorageService

logger = logging.getLogger(__name__)


class AIImageGenerationModule(ModuleBase):
    """AI Image Generation module wrapper.

    Manages OpenAI image operations and storage.
    """

    def __init__(self) -> None:
        self._state: ModuleState = ModuleState.STOPPED
        self._settings = AIImageSettings()
        self._storage = StorageService(self._settings)
        self._svc = OpenAIImageService(self._settings, self._storage)
        self._last_output: Optional[str] = None

    def configure(self, config: BaseSettings) -> None:
        if isinstance(config, AIImageSettings):
            self._settings = config
            self._storage = StorageService(self._settings)
            self._svc = OpenAIImageService(self._settings, self._storage)
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
            "has_api_key": self._svc.has_api_key(),
        }

    # Convenience for routes
    def edit_image(
        self, prompt: str, upload_name: str, content: bytes, size: Optional[str] = None
    ) -> str:
        up_path = self._storage.save_upload(upload_name, content)
        out_path = self._svc.edit_image(prompt=prompt, image_path=up_path, size=size)
        self._last_output = str(out_path)
        return str(out_path)
