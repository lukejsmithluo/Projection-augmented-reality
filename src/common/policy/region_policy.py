from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from ..config import OpenAIRegionPolicySettings


@dataclass
class RegionCheckResult:
    allowed: bool
    policy_mode: str
    country: Optional[str] = None
    country_code: Optional[str] = None
    subdivision: Optional[str] = None
    city: Optional[str] = None
    exit_ip: Optional[str] = None
    connectivity_ok: Optional[bool] = None
    reason: Optional[str] = None
    checked_at: float = 0.0


class RegionPolicyService:
    """OpenAI 地区策略服务（hybrid 模式）。

    规则：
    - 仅允许官网支持的国家与地区（白名单）
    - 其余全部阻止（不使用连通性豁免）
    - 用户使用 VPN 时，依据出口 IP 的地理定位判定
    - 结果带缓存，避免每次请求都探测外网
    """

    def __init__(self, settings: OpenAIRegionPolicySettings):
        self.settings = settings
        self._cache: Optional[RegionCheckResult] = None
        self._cache_expire_at: float = 0.0
        self._official_names: Optional[set[str]] = None
        self._official_names_expire_at: float = 0.0

    def _now(self) -> float:
        return time.time()

    def _get_exit_ip(self) -> Optional[str]:
        try:
            r = requests.get(
                "https://api.ipify.org", params={"format": "json"}, timeout=3
            )
            if r.ok:
                return r.json().get("ip")
        except Exception:
            pass
        return None

    def _geoip(self) -> Dict[str, Any]:
        # 首选 ipapi.co，其次 ip-api.com；都失败返回空
        try:
            r = requests.get("https://ipapi.co/json", timeout=3)
            if r.ok:
                j = r.json()
                return {
                    "country": j.get("country_name"),
                    "country_code": j.get("country_code"),
                    "subdivision": j.get("region_code"),
                    "city": j.get("city"),
                }
        except Exception:
            pass
        try:
            r = requests.get(
                "http://ip-api.com/json",
                params={"fields": "status,country,countryCode,region,city"},
                timeout=3,
            )
            if r.ok and r.json().get("status") == "success":
                j = r.json()
                return {
                    "country": j.get("country"),
                    "country_code": j.get("countryCode"),
                    "subdivision": j.get("region"),
                    "city": j.get("city"),
                }
        except Exception:
            pass
        return {}

    def _probe_connectivity(self) -> bool:
        # 仅做诊断展示，不参与放行判定
        try:
            r = requests.get("https://openai.com/robots.txt", timeout=3)
            return r.ok
        except Exception:
            return False

    def _fetch_official_names(self) -> Optional[set[str]]:
        # 尝试从两个页面获取官方支持国家与地区名称列表；解析 <li> 文本
        import re

        sources = [
            "https://help.openai.com/en/articles/5347006-openai-api-supported-countries-and-territories",
            "https://platform.openai.com/docs/supported-countries",
        ]
        names: set[str] = set()
        for url in sources:
            try:
                resp = requests.get(url, timeout=5)
                if not resp.ok:
                    continue
                html = resp.text
                # 简单提取列表项文本
                for m in re.findall(r"<li[^>]*>(.*?)</li>", html, flags=re.I | re.S):
                    # 去HTML标签
                    text = re.sub(r"<[^>]+>", " ", m)
                    text = re.sub(r"\s+", " ", text).strip()
                    if 2 <= len(text) <= 64:
                        # 排除非国家项（例如段落说明）。
                        # 经验性过滤：包含字母且不含 ':'
                        if any(c.isalpha() for c in text) and ":" not in text:
                            names.add(text)
            except Exception:
                continue
        return names or None

    def _get_official_names(self) -> Optional[set[str]]:
        now = self._now()
        if self._official_names and now < self._official_names_expire_at:
            return self._official_names
        names = self._fetch_official_names()
        if names:
            # 规范化部分别名
            normalized = set()
            alias = {
                "United States of America": "United States",
                "United Kingdom": "United Kingdom",
                "Korea, Republic of": "South Korea",
                "Korea": "South Korea",
                "Hong Kong SAR China": "Hong Kong",
                "Macao SAR China": "Macau",
                "Russian Federation": "Russia",
            }
            for n in names:
                normalized.add(alias.get(n, n))
            self._official_names = normalized
            # 官方列表缓存 24 小时
            self._official_names_expire_at = now + 24 * 3600
        return self._official_names

    def evaluate(self, force: bool = False) -> RegionCheckResult:
        # 返回缓存
        now = self._now()
        if not force and self._cache and now < self._cache_expire_at:
            return self._cache

        ip = self._get_exit_ip()
        geo = self._geoip()
        cc = (geo.get("country_code") or "").upper() or None
        country_name = geo.get("country") or None
        subdivision = geo.get("subdivision") or None

        # 判定是否在白名单
        allowed = False
        reason = None
        if self.settings.use_official_list:
            official = self._get_official_names()
            if official and country_name:
                allowed = country_name in official
                reason = (
                    None if allowed else f"country {country_name} not in official list"
                )
            else:
                # 官方获取失败，退化到代码白名单
                if cc and cc in self.settings.allowed_countries:
                    allowed = True
                else:
                    allowed = False
                    reason = f"country {cc or 'UNKNOWN'} not in allowed list"
        elif cc and cc in self.settings.allowed_countries:
            # 次国家地区受限（如 UA-43 等）
            if subdivision and subdivision in self.settings.blocked_subdivisions:
                allowed = False
                reason = f"subdivision {subdivision} blocked"
            else:
                allowed = True
        else:
            allowed = False
            reason = f"country {cc or 'UNKNOWN'} not in allowed list"

        connectivity = self._probe_connectivity()

        res = RegionCheckResult(
            allowed=allowed,
            policy_mode=self.settings.policy_mode,
            country=country_name,
            country_code=cc,
            subdivision=subdivision,
            city=geo.get("city"),
            exit_ip=ip,
            connectivity_ok=connectivity,
            reason=reason,
            checked_at=now,
        )

        # 写缓存
        self._cache = res
        self._cache_expire_at = now + max(1, self.settings.cache_ttl_seconds)
        return res
