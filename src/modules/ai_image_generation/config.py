from __future__ import annotations

from pydantic_settings import BaseSettings


class AIImageSettings(BaseSettings):
    """Settings for AI image generation module."""

    output_dir: str = "data/ai_images"
    model: str = "gpt-image-1"
    default_size: str = "1024x1024"