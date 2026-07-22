"""Gọi Zalo Bot Platform (API chính thức, kiểu Telegram).

Đã xác minh 7/2026:
- Base URL: https://bot-api.zaloplatforms.com/bot{TOKEN}/{method} (POST). Sửa được ở admin
  qua khoá 'zalo_bot_api_base' nếu Zalo đổi địa chỉ.
- Token dạng 'id_số:chuỗi_bí_mật'. Tin tối đa 2000 ký tự.
- Nhận tin: getUpdates (long/short-polling) hoặc webhook (loại trừ nhau). Ta dùng getUpdates.
- Nhóm đang Beta: gửi được nếu bot đã ở trong nhóm và có chat_id nhóm.
Nguồn: https://bot.zaloplatforms.com/docs/
"""
from __future__ import annotations

from typing import Optional

import requests

from .. import store

DEFAULT_BASE = "https://bot-api.zaloplatforms.com"
TIMEOUT = 40


class ZaloBotError(Exception):
    pass


def _base() -> str:
    return (store.get_setting("zalo_bot_api_base") or DEFAULT_BASE).rstrip("/")


def _call(token: str, method: str, payload: Optional[dict] = None, timeout: int = TIMEOUT) -> dict:
    if not token:
        raise ZaloBotError("Thiếu token Zalo Bot.")
    url = f"{_base()}/bot{token}/{method}"
    try:
        resp = requests.post(url, json=payload or {}, timeout=timeout)
        data = resp.json()
    except ValueError:
        raise ZaloBotError(f"Zalo trả về dữ liệu không đọc được (HTTP {resp.status_code}).")
    except requests.RequestException as e:
        raise ZaloBotError(f"Không gọi được Zalo Bot API: {e}")
    if not data.get("ok", False):
        raise ZaloBotError(f"Zalo Bot lỗi: {data.get('description') or data}")
    return data.get("result", {})


def get_me(token: str) -> dict:
    """Kiểm tra token; trả về thông tin bot (id, account_name, can_join_groups...)."""
    return _call(token, "getMe", timeout=15)


def check(token: str) -> tuple[bool, str]:
    try:
        me = get_me(token)
        can_group = me.get("can_join_groups")
        extra = " · vào nhóm: " + ("được" if can_group else "chưa bật") if can_group is not None else ""
        return True, f"OK: {me.get('account_name', me.get('id',''))}{extra}"
    except ZaloBotError as e:
        return False, str(e)


def send_message(token: str, chat_id: str, text: str, parse_mode: Optional[str] = None) -> dict:
    """Gửi tin tới một chat_id (người hoặc nhóm). Cắt còn 2000 ký tự."""
    payload = {"chat_id": str(chat_id), "text": text[:2000]}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    return _call(token, "sendMessage", payload)


def get_updates(token: str, offset: Optional[int] = None, timeout: int = 0) -> list[dict]:
    """Đọc tin mới. Nếu không có tin / mạng chờ lâu → trả [] (không ném lỗi)."""
    payload: dict = {"timeout": timeout}
    if offset is not None:
        payload["offset"] = offset
    try:
        res = _call(token, "getUpdates", payload, timeout=timeout + 25)
    except ZaloBotError:
        return []
    if isinstance(res, list):
        return res
    return res.get("updates", []) if isinstance(res, dict) else []


def find_group_chats(token: str) -> list[dict]:
    """Dò các nhóm mà bot đã nhận được tin, trả về [{chat_id, title}]."""
    seen: dict[str, str] = {}
    for u in get_updates(token):
        msg = u.get("message") or u.get("edited_message") or {}
        chat = msg.get("chat") or {}
        ctype = (chat.get("chat_type") or chat.get("type") or "").upper()
        if "GROUP" in ctype and chat.get("id") is not None:
            seen[str(chat["id"])] = chat.get("title") or chat.get("name") or "(nhóm)"
    return [{"chat_id": k, "title": v} for k, v in seen.items()]
