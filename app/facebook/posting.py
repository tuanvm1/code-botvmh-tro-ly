"""Đăng bài lên một Trang Facebook cụ thể (chữ + ảnh), hỗ trợ hẹn giờ.

Mỗi hàm nhận `page` — một dict Trang lấy từ store (có fb_page_id, fb_page_token).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import client

MIN_SCHEDULE_AHEAD = 10 * 60
MAX_SCHEDULE_AHEAD = 30 * 24 * 60 * 60


def _creds(page: dict) -> tuple[str, str]:
    pid = page.get("fb_page_id")
    token = page.get("fb_page_token")
    if not pid or not token:
        raise client.FacebookError(
            f"Trang '{page.get('name','?')}' chưa có ID Trang hoặc token đăng bài. "
            "Vào trang quản trị điền giúp nhé.")
    return pid, token


def post_text(page: dict, message: str, scheduled_ts: Optional[int] = None) -> str:
    pid, token = _creds(page)
    data: dict = {"message": message}
    if scheduled_ts:
        data.update(published="false", scheduled_publish_time=int(scheduled_ts))
    res = client.post(f"{pid}/feed", token, data=data)
    return res.get("id", "")


def post_photo(page: dict, message: str, image_path: str, scheduled_ts: Optional[int] = None) -> str:
    pid, token = _creds(page)
    p = Path(image_path)
    if not p.exists():
        raise client.FacebookError(f"Không tìm thấy ảnh: {image_path}")
    data: dict = {"caption": message}
    if scheduled_ts:
        data.update(published="false", scheduled_publish_time=int(scheduled_ts))
    with p.open("rb") as fh:
        files = {"source": (p.name, fh)}
        res = client.post(f"{pid}/photos", token, data=data, files=files)
    return res.get("post_id") or res.get("id", "")


def publish_draft(page: dict, text: str, image_path: Optional[str] = None,
                  scheduled_ts: Optional[int] = None) -> str:
    if image_path:
        return post_photo(page, text, image_path, scheduled_ts)
    return post_text(page, text, scheduled_ts)


def post_permalink(page: dict, post_id: str) -> str:
    try:
        pid, token = _creds(page)
        res = client.get(post_id, token, {"fields": "permalink_url"})
        return res.get("permalink_url", "")
    except client.FacebookError:
        return ""
