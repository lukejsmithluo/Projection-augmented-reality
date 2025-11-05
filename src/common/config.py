from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """应用配置：支持 .env 加载"""

    app_name: str = "XProjection API"
    load_hardware_modules: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
