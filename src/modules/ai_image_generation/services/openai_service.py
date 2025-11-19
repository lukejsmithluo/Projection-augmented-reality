from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Optional

from openai import OpenAI

from ..config import AIImageSettings
from .storage_service import StorageService


logger = logging.getLogger(__name__)


class OpenAIImageService:
    """Service wrapper around OpenAI Images API.

    Supports image edit with a prompt and an input image.
    """

    def __init__(self, settings: AIImageSettings, storage: StorageService) -> None:
        self._settings = settings
        self._storage = storage
        self._client: Optional[OpenAI] = None

    def _ensure_client(self) -> None:
        if self._client is None:
            # OpenAI client automatically reads OPENAI_API_KEY from env
            self._client = OpenAI()

    def has_api_key(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def edit_image(self, prompt: str, image_path: Path, size: Optional[str] = None) -> Path:
        """Edit image using prompt; returns saved output image path.

        This uses the Images API 'edits' endpoint (if available) on model 'gpt-image-1'.
        """
        self._ensure_client()
        if not self._client:
            raise RuntimeError("OpenAI client not initialized")
        if not image_path.exists():
            raise FileNotFoundError(f"Input image not found: {image_path}")

        use_size = size or self._settings.default_size
        logger.info("Submitting image edit to OpenAI: model=%s size=%s", self._settings.model, use_size)

        # Call the OpenAI Images API; result contains b64_json
        with image_path.open("rb") as img_file:
            try:
                result = self._client.images.edits(
                    model=self._settings.model,
                    prompt=prompt,
                    image=img_file,
                    size=use_size,
                )
            except Exception as e:
                logger.exception("OpenAI image edit failed: %s", e)
                raise

        if not result or not getattr(result, "data", None):
            raise RuntimeError("OpenAI returned no image data")

        b64 = result.data[0].b64_json  # type: ignore[attr-defined]
        img_bytes = base64.b64decode(b64)
        saved_path = self._storage.save_output_png(img_bytes)
        logger.info("Saved edited image: %s", saved_path)
        return saved_path