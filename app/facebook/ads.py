"""Đọc số liệu quảng cáo và điều khiển chiến dịch cho một Trang cụ thể.

Mỗi hàm nhận `page` (dict Trang, có fb_ad_account_id + fb_ads_token). Chốt an toàn:
không đặt ngân sách vượt trần; mọi thay đổi ghi nhật ký kèm page_ref.
"""
from __future__ import annotations

from typing import Optional

from ..config import config
from .. import db
from . import client

_RESULT_PREFERENCE = [
    ("onsite_conversion.messaging_conversation_started_7d", "Tin nhắn"),
    ("onsite_conversion.purchase", "Mua hàng"),
    ("offsite_conversion.fb_pixel_purchase", "Mua hàng"),
    ("lead", "Khách tiềm năng"),
    ("onsite_conversion.lead_grouped", "Khách tiềm năng"),
    ("link_click", "Click liên kết"),
    ("post_engagement", "Tương tác bài"),
]

_INSIGHT_FIELDS = "campaign_id,campaign_name,spend,impressions,reach,clicks,ctr,cpc,cpm,frequency,actions"


def _creds(page: dict) -> tuple[str, str]:
    acct = page.get("fb_ad_account_id")
    token = page.get("fb_ads_token")
    if not acct or not token:
        raise client.FacebookError(
            f"Trang '{page.get('name','?')}' chưa có tài khoản quảng cáo hoặc token quảng cáo. "
            "Vào trang quản trị điền giúp nhé.")
    return acct, token


def _extract_results(actions: Optional[list]) -> tuple[int, str]:
    if not actions:
        return 0, ""
    by_type = {a.get("action_type"): float(a.get("value", 0)) for a in actions}
    for key, label in _RESULT_PREFERENCE:
        if key in by_type:
            return int(by_type[key]), label
    return 0, ""


def fetch_campaign_insights(page: dict, date_preset: str = "yesterday") -> list[dict]:
    acct, token = _creds(page)
    res = client.get(
        f"{acct}/insights", token,
        {"level": "campaign", "fields": _INSIGHT_FIELDS, "date_preset": date_preset, "limit": 200},
    )
    out = []
    for row in res.get("data", []):
        results, result_type = _extract_results(row.get("actions"))
        out.append({
            "campaign_id": row.get("campaign_id"),
            "campaign_name": row.get("campaign_name"),
            "spend": float(row.get("spend", 0) or 0),
            "impressions": int(float(row.get("impressions", 0) or 0)),
            "reach": int(float(row.get("reach", 0) or 0)),
            "clicks": int(float(row.get("clicks", 0) or 0)),
            "ctr": float(row.get("ctr", 0) or 0),
            "cpc": float(row.get("cpc", 0) or 0),
            "cpm": float(row.get("cpm", 0) or 0),
            "frequency": float(row.get("frequency", 0) or 0),
            "results": results,
            "result_type": result_type,
        })
    return out


def list_campaigns(page: dict) -> list[dict]:
    acct, token = _creds(page)
    res = client.get(
        f"{acct}/campaigns", token,
        {"fields": "id,name,status,effective_status,daily_budget,lifetime_budget", "limit": 200},
    )
    out = []
    for c in res.get("data", []):
        out.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "status": c.get("status"),
            "effective_status": c.get("effective_status"),
            "daily_budget": int(c.get("daily_budget")) if c.get("daily_budget") else None,
            "lifetime_budget": int(c.get("lifetime_budget")) if c.get("lifetime_budget") else None,
        })
    return out


def set_campaign_status(page: dict, campaign_id: str, active: bool, actor: str = "owner") -> dict:
    _, token = _creds(page)
    new_status = "ACTIVE" if active else "PAUSED"
    res = client.post(campaign_id, token, {"status": new_status})
    db.log_action(actor, "set_campaign_status", campaign_id, f"→ {new_status}", page_ref=page.get("id"))
    return res


def set_campaign_daily_budget(page: dict, campaign_id: str, daily_budget_vnd: int, actor: str = "owner") -> dict:
    _, token = _creds(page)
    if daily_budget_vnd > config.ads_max_daily_budget_vnd:
        raise client.FacebookError(
            f"⛔ Từ chối: {daily_budget_vnd:,}đ vượt trần an toàn "
            f"{config.ads_max_daily_budget_vnd:,}đ/ngày. Muốn tăng trần thì sửa ở trang quản trị.")
    if daily_budget_vnd <= 0:
        raise client.FacebookError("Ngân sách phải lớn hơn 0.")
    res = client.post(campaign_id, token, {"daily_budget": int(daily_budget_vnd)})
    db.log_action(actor, "set_campaign_budget", campaign_id, f"→ {daily_budget_vnd:,}đ/ngày", page_ref=page.get("id"))
    return res
