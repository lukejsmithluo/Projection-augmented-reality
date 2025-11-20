from __future__ import annotations

from typing import Literal, Set

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAIRegionPolicySettings(BaseSettings):
    """OpenAI 地区策略配置（允许国家/地区白名单 + 模式）。

    - policy_mode: "hybrid"（只允许官网支持国家与地区；其他全部阻止）
    - admin_override_enabled: 管理员覆盖（默认关闭）
    - allowed_countries: ISO 3166-1 alpha-2 国家/地区代码白名单
    - blocked_subdivisions: 特定次国家地区代码（如 UA-43 克里米亚等）
    - cache_ttl_seconds: 地理定位与连通性结果缓存时间
    """

    policy_mode: Literal["hybrid", "strict"] = "hybrid"
    # 是否在运行时动态获取官方支持国家与地区列表（默认启用）
    use_official_list: bool = True
    admin_override_enabled: bool = False
    # 允许国家/地区（默认基于 OpenAI 官网支持列表的常见集；可通过环境变量覆盖）
    allowed_countries: Set[str] = set(
        (
            # North America
            "US",
            "CA",
            "MX",
            # Europe (non-exhaustive, updateable via env)
            "GB",
            "IE",
            "FR",
            "DE",
            "NL",
            "BE",
            "LU",
            "CH",
            "AT",
            "ES",
            "PT",
            "IT",
            "SE",
            "NO",
            "DK",
            "FI",
            "PL",
            "CZ",
            "SK",
            "HU",
            "RO",
            "BG",
            "GR",
            "SI",
            "HR",
            "EE",
            "LV",
            "LT",
            "IS",
            "MT",
            "CY",
            # Asia-Pacific
            "JP",
            "KR",
            "SG",
            "HK",
            "TW",
            "AU",
            "NZ",
            # Middle East
            "AE",
            "SA",
            "QA",
            "KW",
            "BH",
            "OM",
            "IL",
            # Americas (additional)
            "AR",
            "BR",
            "CL",
            "CO",
            "PE",
            "UY",
            "EC",
            "PA",
        )
    )
    # 特定次国家地区（示例：乌克兰受限地区）
    blocked_subdivisions: Set[str] = {"UA-43", "UA-14", "UA-09"}
    cache_ttl_seconds: int = 600

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="OPENAI_"
    )

    @field_validator("allowed_countries", "blocked_subdivisions", mode="before")
    @classmethod
    def _parse_set(cls, v):
        # 支持逗号分隔字符串或 JSON/list
        if isinstance(v, str):
            parts = [p.strip() for p in v.split(",") if p.strip()]
            # 统一为大写代码
            return set(p.upper() for p in parts)
        if isinstance(v, (list, set, tuple)):
            return set(str(p).upper() for p in v)
        return v


class AppSettings(BaseSettings):
    """应用配置：支持 .env 加载"""

    app_name: str = "XProjection API"
    load_hardware_modules: bool = False
    # OpenAI 地区策略配置
    region_policy: "OpenAIRegionPolicySettings" = OpenAIRegionPolicySettings()  # type: ignore[assignment]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# 注意：region_policy 已在类体内提供默认实例，避免 BaseSettings 验证 None 值
