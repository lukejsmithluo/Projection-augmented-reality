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
    """地区策略服务（provider-aware，hybrid 模式）。

    规则：
    - 仅允许所选提供者（OpenAI/Gemini）的官方支持国家与地区（白名单）
    - 其余全部阻止（不使用连通性豁免）
    - 用户使用 VPN 时，依据出口 IP 的地理定位判定
    - 结果带缓存，避免每次请求都探测外网
    """

    def __init__(self, settings: OpenAIRegionPolicySettings):
        self.settings = settings
        self._cache: Optional[RegionCheckResult] = None
        self._cache_expire_at: float = 0.0
        # 官方国家名缓存按提供者区分
        self._official_names_map: dict[str, set[str]] = {}
        self._official_expire_map: dict[str, float] = {}

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

    def _fetch_official_names_openai(self) -> Optional[set[str]]:
        # OpenAI：尝试从两个页面获取官方支持国家与地区名称列表；解析 <li> 文本
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

    def _fetch_official_names_gemini(self) -> Optional[set[str]]:
        # Gemini：从官方“可用区域”页面解析国家与地区列表
        # https://ai.google.dev/gemini-api/docs/available-regions
        import re

        try:
            url = "https://ai.google.dev/gemini-api/docs/available-regions"
            resp = requests.get(url, timeout=5)
            if not resp.ok:
                return None
            html = resp.text
            names: set[str] = set()
            # 尝试解析 <li> 项；若无则以换行分割并过滤
            for m in re.findall(r"<li[^>]*>(.*?)</li>", html, flags=re.I | re.S):
                text = re.sub(r"<[^>]+>", " ", m)
                text = re.sub(r"\s+", " ", text).strip()
                if 2 <= len(text) <= 64 and any(c.isalpha() for c in text):
                    names.add(text)
            if not names:
                # 备选：抓取正文中的国家名（粗略解析，去除非国家描述）
                # 依据官方页面结构，该页主体为国家/地区名的长列表
                lines = [s.strip() for s in re.split(r"\r?\n", html) if s.strip()]
                for ln in lines:
                    # 过滤导航/版权等非国家文本
                    if len(ln) < 2 or any(
                        tag in ln.lower()
                        for tag in (
                            "<",
                            ">",
                            "gemini",
                            "api",
                            "studio",
                            "vertex",
                            "政策",
                            "可用区域",
                        )
                    ):
                        continue
                    # 大多数国家名为首字母大写的单词或短语；进行经验性过滤
                    if any(ch.isalpha() for ch in ln) and ":" not in ln:
                        # 避免过长句子
                        if len(ln) <= 64:
                            names.add(ln)
            return names or None
        except Exception:
            return None

    def _get_official_names(self, provider: str) -> Optional[set[str]]:
        now = self._now()
        prov = (provider or "openai").strip().lower()
        cached = self._official_names_map.get(prov)
        exp = self._official_expire_map.get(prov, 0.0)
        if cached and now < exp:
            return cached

        if prov == "gemini":
            names = self._fetch_official_names_gemini()
        else:
            names = self._fetch_official_names_openai()

        if names:
            # 规范化部分别名（两家共有的常见别名）
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
            self._official_names_map[prov] = normalized
            # 官方列表缓存 24 小时
            self._official_expire_map[prov] = now + 24 * 3600
        return self._official_names_map.get(prov)

    def evaluate(
        self, provider: str = "openai", force: bool = False
    ) -> RegionCheckResult:
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
            official = self._get_official_names(provider)
            if official and country_name:
                allowed = country_name in official
                reason = (
                    None
                    if allowed
                    else f"country {country_name} not in official list for {provider}"
                )
            else:
                # 官方获取失败，退化到代码白名单
                if cc and cc in self.settings.allowed_countries:
                    allowed = True
                else:
                    allowed = False
                    reason = (
                        f"country {cc or 'UNKNOWN'} not in allowed list for {provider}"
                    )
        elif cc and cc in self.settings.allowed_countries:
            # 次国家地区受限（如 UA-43 等）
            if subdivision and subdivision in self.settings.blocked_subdivisions:
                allowed = False
                reason = f"subdivision {subdivision} blocked"
            else:
                allowed = True
        else:
            allowed = False
            reason = f"country {cc or 'UNKNOWN'} not in allowed list for {provider}"

        connectivity = self._probe_connectivity()

        res = RegionCheckResult(
            allowed=allowed,
            policy_mode=f"{self.settings.policy_mode}/{provider}",
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
