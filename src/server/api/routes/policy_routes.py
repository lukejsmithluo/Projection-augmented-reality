from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_region_policy

router = APIRouter(tags=["policy"])


@router.get("/region/status")
def region_status(policy=Depends(get_region_policy)):
    """返回地区策略当前评估结果（缓存内）。"""
    res = policy.evaluate()
    return {
        "allowed": res.allowed,
        "policy_mode": res.policy_mode,
        "country": res.country,
        "country_code": res.country_code,
        "subdivision": res.subdivision,
        "city": res.city,
        "exit_ip": res.exit_ip,
        "connectivity_ok": res.connectivity_ok,
        "reason": res.reason,
        "checked_at": res.checked_at,
    }
