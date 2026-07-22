"""Gửi tin Zalo — hai đường:

- method = 'official_bot': Zalo Bot Platform (botapi.py). An toàn nhưng KHÔNG vào nhóm thường.
- method = 'personal': tài khoản cá nhân (phụ) qua dịch vụ Node zca-js (chạy ở localhost:8765).
  Đăng được vào nhóm Zalo thường. Có van an toàn né khóa ở phía Node.
"""
from __future__ import annotations

import re

import requests

from . import botapi
from .. import store

NODE_DEFAULT = "http://127.0.0.1:8765"


class ZaloNotReady(Exception):
    pass


def html_to_plain(text: str) -> str:
    t = re.sub(r"<[^>]+>", "", text or "")
    return t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").strip()


def _node_url() -> str:
    return (store.get_setting("zalo_service_url") or NODE_DEFAULT).rstrip("/")


def _node_send(thread_id: str, text: str, is_group: bool = True) -> None:
    try:
        r = requests.post(f"{_node_url()}/send",
                          json={"threadId": thread_id, "message": html_to_plain(text), "isGroup": is_group},
                          timeout=10)
        data = r.json()
    except Exception as e:  # noqa: BLE001
        raise ZaloNotReady(f"Dịch vụ Zalo (Node) chưa sẵn sàng: {e}")
    if not data.get("queued"):
        raise ZaloNotReady(f"Không xếp được tin để gửi: {data}")


def node_status() -> dict:
    try:
        return requests.get(f"{_node_url()}/status", timeout=5).json()
    except Exception as e:  # noqa: BLE001
        return {"state": "off", "error": str(e)}


def node_groups() -> dict:
    try:
        return requests.get(f"{_node_url()}/groups", timeout=30).json()
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


def send_group(zalo_account: dict, group_id: str, text: str) -> None:
    method = (zalo_account or {}).get("method", "official_bot")
    if method == "personal":
        _node_send(group_id, text, is_group=True)
        return
    token = (zalo_account or {}).get("bot_token", "")
    if not token:
        raise ZaloNotReady("Tài khoản Zalo chưa có token bot. Điền ở trang quản trị.")
    botapi.send_message(token, group_id, html_to_plain(text))


def send_user(zalo_account: dict, user_id: str, text: str) -> None:
    method = (zalo_account or {}).get("method", "official_bot")
    if method == "personal":
        _node_send(user_id, text, is_group=False)
        return
    token = (zalo_account or {}).get("bot_token", "")
    if not token:
        raise ZaloNotReady("Tài khoản Zalo chưa có token bot. Điền ở trang quản trị.")
    botapi.send_message(token, user_id, html_to_plain(text))
