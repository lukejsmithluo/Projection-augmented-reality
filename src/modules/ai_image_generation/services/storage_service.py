from __future__ import annotations

import datetime as dt
from pathlib import Path

from ..config import AIImageSettings


class StorageService:
    """Simple storage helper for AI images outputs and uploads."""

    def __init__(self, settings: AIImageSettings) -> None:
        self._root = Path(settings.output_dir).resolve()
        self._outputs = self._root / "outputs"
        self._uploads = self._root / "uploads"
        self._outputs.mkdir(parents=True, exist_ok=True)
        self._uploads.mkdir(parents=True, exist_ok=True)

    @property
    def uploads_dir(self) -> Path:
        return self._uploads

    def save_upload(self, filename: str, content: bytes) -> Path:
        path = self._uploads / filename
        path.write_bytes(content)
        return path

    def save_output_png(self, content: bytes) -> Path:
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self._outputs / f"gen_{ts}.png"
        path.write_bytes(content)
        return path