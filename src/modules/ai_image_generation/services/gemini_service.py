from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from .storage_service import StorageService

logger = logging.getLogger(__name__)


class GeminiImageService:
    """Service wrapper around Google Gemini/Imagen image generation APIs.

    Supports image edit (text + image → image) using Gemini Image models,
    and saves the output into the module's storage.
    """

    def __init__(self, storage: StorageService) -> None:
        self._storage = storage
        # Lazy import client to avoid hard dependency during import in CI
        self._client = None

    def _ensure_client(self) -> None:
        if self._client is None:
            try:
                from google import genai  # type: ignore
                from google.genai import types  # noqa: F401
            except Exception as e:  # ImportError or other
                raise RuntimeError("GEMINI_LIB_MISSING") from e
            # Prefer explicit API key envs; the client auto-picks GEMINI_API_KEY/GOOGLE_API_KEY
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            try:
                # Construct client; pass api_key if available to avoid ambiguity
                self._client = genai.Client(api_key=api_key)  # type: ignore
            except Exception as e:
                logger.exception("Failed to initialize Gemini client: %s", e)
                raise

    def has_api_key(self) -> bool:
        return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))

    def edit_image(
        self,
        prompt: str,
        image_path: Path,
        size: Optional[str] = None,
        model: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        image_size: Optional[str] = None,
    ) -> Path:
        """Edit an image with a text prompt using Gemini Image models.

        Uses `models.generate_content` with response modality set to IMAGE.
        """
        self._ensure_client()
        if not self._client:
            raise RuntimeError("Gemini client not initialized")
        if not image_path.exists():
            raise FileNotFoundError(f"Input image not found: {image_path}")

        # Resolve model & aspect ratio
        chosen_model = (model or "gemini-2.5-flash-image").strip() or "gemini-2.5-flash-image"
        # Resolve aspect ratio preference: explicit > derived from size > default
        ar = (aspect_ratio or "").strip()
        if not ar:
            ar = "1:1"
            try:
                if size:
                    s = size.lower().strip()
                    if "x" in s:
                        w_str, h_str = s.split("x", 1)
                        w = int(w_str)
                        h = int(h_str)
                        # Simple mapping based on common sizes
                        if w == h:
                            ar = "1:1"
                        elif w * 9 == h * 16:
                            ar = "16:9"
                        elif w * 16 == h * 9:
                            ar = "9:16"
                        elif w * 3 == h * 4:
                            ar = "3:4"
                        elif w * 4 == h * 3:
                            ar = "4:3"
            except Exception:
                ar = "1:1"

        # Normalize image_size for Gemini 3 Pro Image: expects 1K/2K/4K
        img_size = (image_size or "").strip().upper() or None
        if img_size and img_size not in {"1K", "2K", "4K"}:
            img_size = None

        logger.info(
            "Submitting image edit to Gemini: model=%s aspect_ratio=%s image_size=%s",
            chosen_model,
            ar,
            img_size,
        )

        # Build contents: text prompt + input image
        try:
            from PIL import Image  # type: ignore
            from google.genai import types  # type: ignore
        except Exception as e:
            raise RuntimeError("PIL_OR_GEMINI_TYPES_MISSING") from e

        # Build contents: text + inline image bytes (robust across SDK versions)
        # Determine mime from extension
        ext = image_path.suffix.lower()
        mime = "image/png" if ext not in (".jpg", ".jpeg") else "image/jpeg"
        data = image_path.read_bytes()
        blob = types.Blob(mime_type=mime, data=data)
        parts = [
            types.Part(text=prompt),
            types.Part(inline_data=blob),
        ]
        # Wrap into a user content to satisfy SDKs expecting role-based contents
        contents = [types.Content(role="user", parts=parts)]

        try:
            img_cfg = types.ImageConfig(aspect_ratio=ar)
            if img_size:
                img_cfg = types.ImageConfig(aspect_ratio=ar, image_size=img_size)
            response = self._client.models.generate_content(  # type: ignore[attr-defined]
                model=chosen_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=img_cfg,
                ),
            )
        except Exception as e:
            logger.exception("Gemini image edit failed: %s", e)
            raise

        # Extract the first inline image blob from candidates → content → parts
        try:
            from io import BytesIO
            from PIL import Image  # type: ignore

            candidates = getattr(response, "candidates", [])
            for cand in candidates:
                content = getattr(cand, "content", None)
                parts = getattr(content, "parts", []) if content is not None else []
                for part in parts:
                    inline = getattr(part, "inline_data", None)
                    if inline is not None:
                        data_field = getattr(inline, "data", None)
                        if data_field:
                            # Bytes payload; save directly as PNG output
                            saved_path = self._storage.save_output_png(data_field)
                            logger.info("Saved edited image (Gemini): %s", saved_path)
                            return saved_path
                        # Fallback: if SDK provides convenience method
                        as_image = getattr(part, "as_image", None)
                        if callable(as_image):
                            out_img = as_image()
                            buf = BytesIO()
                            out_img.save(buf, format="PNG")
                            saved_path = self._storage.save_output_png(buf.getvalue())
                            logger.info("Saved edited image (Gemini): %s", saved_path)
                            return saved_path
        except Exception as e:
            logger.exception("Failed to parse Gemini image output: %s", e)
            raise RuntimeError("GEMINI_NO_IMAGE_DATA") from e

        raise RuntimeError("GEMINI_NO_IMAGE_DATA")