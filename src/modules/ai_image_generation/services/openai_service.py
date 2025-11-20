from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any, Optional

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
        # Lazily initialized OpenAI client; avoid ImportError at import time in CI
        self._client: Optional[Any] = None

    def _ensure_client(self) -> None:
        if self._client is None:
            try:
                from openai import OpenAI  # type: ignore
            except ImportError as e:
                # Surface a controlled error so routes can return a friendly message
                raise RuntimeError("OPENAI_LIB_MISSING") from e
            # OpenAI client automatically reads OPENAI_API_KEY from env
            org_id = os.environ.get("OPENAI_ORG_ID")
            if org_id:
                self._client = OpenAI(organization=org_id)
            else:
                self._client = OpenAI()

    def has_api_key(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def edit_image(
        self, prompt: str, image_path: Path, size: Optional[str] = None
    ) -> Path:
        """Edit image using prompt; returns saved output image path.

        This uses the Images API 'edit' endpoint on model 'gpt-image-1'.
        """
        self._ensure_client()
        if not self._client:
            raise RuntimeError("OpenAI client not initialized")
        if not image_path.exists():
            raise FileNotFoundError(f"Input image not found: {image_path}")

        # Normalize size to commonly supported values to avoid API errors
        supported_sizes = {"256x256", "512x512", "1024x1024"}
        requested = (size or self._settings.default_size).lower()
        use_size = requested if requested in supported_sizes else self._settings.default_size
        logger.info(
            "Submitting image edit to OpenAI: model=%s size=%s",
            self._settings.model,
            use_size,
        )

        # Call the OpenAI Images API; result contains b64_json
        with image_path.open("rb") as img_file:
            try:
                # New OpenAI Python SDK uses `.images.edit(...)` for image edits
                result = self._client.images.edit(
                    model=self._settings.model,
                    prompt=prompt,
                    image=img_file,
                    size=use_size,
                )
            except Exception as e:
                # Map common 403 error for unverified organization to a friendly internal code
                msg = str(e).lower()
                if (
                    "error code: 403" in msg and "must be verified" in msg and "gpt-image-1" in msg
                ) or ("verify organization" in msg and "gpt-image-1" in msg):
                    logger.error("OpenAI org not verified for gpt-image-1")
                    raise RuntimeError("OPENAI_ORG_NOT_VERIFIED")
                logger.exception("OpenAI image edit failed: %s", e)
                raise

        if not result or not getattr(result, "data", None):
            raise RuntimeError("OpenAI returned no image data")

        b64 = result.data[0].b64_json  # type: ignore[attr-defined]
        img_bytes = base64.b64decode(b64)
        saved_path = self._storage.save_output_png(img_bytes)
        logger.info("Saved edited image: %s", saved_path)
        return saved_path
