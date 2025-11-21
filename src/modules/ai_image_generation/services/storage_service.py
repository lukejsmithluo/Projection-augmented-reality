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
        # 保留原始文件名的主体与扩展名，生成唯一文件名，避免同名覆盖
        base = Path(filename).name
        stem = Path(base).stem or "upload"
        ext = Path(base).suffix or ".png"
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = self._uploads / f"{stem}_{ts}{ext}"
        # 极端情况下时间戳碰撞，追加序号确保唯一
        idx = 0
        while path.exists():
            idx += 1
            path = self._uploads / f"{stem}_{ts}_{idx}{ext}"
        path.write_bytes(content)
        return path

    def save_output_png(self, content: bytes) -> Path:
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self._outputs / f"gen_{ts}.png"
        path.write_bytes(content)
        return path
