"""Số liệu Trang Facebook cho một Trang cụ thể: chụp mỗi ngày + báo cáo.

Mỗi hàm nhận `page` (dict Trang). Lịch sử lưu theo page_ref = page['id'].
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from .. import db
from . import client

_DAILY_INSIGHT_METRICS = [
    "page_impressions",
    "page_impressions_unique",
    "page_post_engagements",
    "page_views_total",
]

_LABELS = {
    "followers_count": "Người theo dõi",
    "fan_count": "Lượt thích Trang",
    "page_impressions": "Lượt hiển thị",
    "page_impressions_unique": "Tiếp cận",
    "page_post_engagements": "Tương tác",
    "page_views_total": "Lượt xem Trang",
}


def metric_label(metric: str) -> str:
    return _LABELS.get(metric, metric)


def _creds(page: dict) -> tuple[str, str]:
    pid = page.get("fb_page_id")
    token = page.get("fb_page_token")
    if not pid or not token:
        raise client.FacebookError(
            f"Trang '{page.get('name','?')}' chưa có ID Trang hoặc token. Vào trang quản trị điền giúp.")
    return pid, token


def fetch_page_snapshot(page: dict, day: Optional[str] = None) -> dict:
    pid, token = _creds(page)
    day = day or date.today().isoformat()
    metrics: dict[str, float] = {}

    try:
        node = client.get(pid, token, {"fields": "followers_count,fan_count"})
        for k in ("followers_count", "fan_count"):
            if node.get(k) is not None:
                metrics[k] = float(node[k])
    except client.FacebookError:
        pass

    for m in _DAILY_INSIGHT_METRICS:
        try:
            res = client.get(f"{pid}/insights", token,
                            {"metric": m, "period": "day", "date_preset": "yesterday"})
            data = res.get("data", [])
            if data and data[0].get("values"):
                val = data[0]["values"][-1].get("value", 0)
                if isinstance(val, dict):
                    val = sum(float(v) for v in val.values())
                metrics[m] = float(val)
        except client.FacebookError:
            continue

    if metrics and page.get("id") is not None:
        db.save_page_metrics(page["id"], day, metrics)
    return metrics


def weekly_report_data(page: dict, days: int = 14) -> dict[str, list[tuple[str, float]]]:
    out: dict[str, list[tuple[str, float]]] = {}
    if page.get("id") is None:
        return out
    for m in ["followers_count", "page_impressions_unique", "page_post_engagements"]:
        series = db.page_metric_series(page["id"], m, limit_days=days)
        if series:
            out[m] = series
    return out
