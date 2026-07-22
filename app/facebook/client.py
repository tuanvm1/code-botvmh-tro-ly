"""Lớp gọi Facebook Graph API (dùng chung cho đăng bài, quảng cáo, báo cáo Trang).

Xử lý lỗi thân thiện: khi token hết hạn/đứt (mã lỗi 190) sẽ ném ra thông báo
tiếng Việt kèm gợi ý cách khắc phục, để bot báo cho chủ sân.
"""
from __future__ import annotations

from typing import Any, Optional

import requests

from ..config import config

GRAPH = "https://graph.facebook.com"
TIMEOUT = 30


class FacebookError(Exception):
    """Lỗi từ Facebook, kèm thông báo dễ hiểu cho chủ sân."""

    def __init__(self, friendly: str, code: Optional[int] = None, raw: Any = None):
        super().__init__(friendly)
        self.friendly = friendly
        self.code = code
        self.raw = raw

    @property
    def is_token_problem(self) -> bool:
        return self.code in (190, 102, 463, 467)


def _friendly_from_error(err: dict) -> FacebookError:
    code = err.get("code")
    msg = err.get("message", "Lỗi không rõ")
    if code in (190, 102, 463, 467):
        friendly = (
            "🔑 Kết nối Facebook đã hết hạn hoặc bị ngắt (thường do đổi mật khẩu "
            "hoặc Facebook yêu cầu xác minh lại). Cần lấy lại token — nhắn Claude để "
            "được hướng dẫn nối lại trong ~5 phút."
        )
    elif code == 200 or code == 10 or (code == 3):
        friendly = ("⛔ Thiếu quyền để làm việc này. Có thể app chưa được cấp đủ quyền "
                    "cho Trang/tài khoản quảng cáo. Nhắn Claude kiểm tra lại quyền.")
    elif code in (4, 17, 32, 613):
        friendly = ("⏳ Đang gọi Facebook hơi dày, bị giới hạn tốc độ tạm thời. "
                    "Hệ thống sẽ tự thử lại sau.")
    else:
        friendly = f"⚠️ Facebook báo lỗi: {msg} (mã {code})."
    return FacebookError(friendly, code=code, raw=err)


def _handle(resp: requests.Response) -> dict:
    try:
        data = resp.json()
    except ValueError:
        raise FacebookError(f"⚠️ Facebook trả về dữ liệu không đọc được (HTTP {resp.status_code}).")
    if isinstance(data, dict) and data.get("error"):
        raise _friendly_from_error(data["error"])
    if resp.status_code >= 400:
        raise FacebookError(f"⚠️ Facebook lỗi HTTP {resp.status_code}.", raw=data)
    return data


def _url(path: str) -> str:
    path = path.lstrip("/")
    return f"{GRAPH}/{config.fb_api_version}/{path}"


def get(path: str, token: str, params: Optional[dict] = None) -> dict:
    params = dict(params or {})
    params["access_token"] = token
    resp = requests.get(_url(path), params=params, timeout=TIMEOUT)
    return _handle(resp)


def post(path: str, token: str, data: Optional[dict] = None,
         files: Optional[dict] = None) -> dict:
    data = dict(data or {})
    data["access_token"] = token
    resp = requests.post(_url(path), data=data, files=files, timeout=TIMEOUT)
    return _handle(resp)


def check_token(token: str) -> tuple[bool, str]:
    """Kiểm tra nhanh token còn sống không. Trả về (ok, thông báo)."""
    try:
        me = get("me", token, {"fields": "id,name"})
        return True, f"OK: {me.get('name', me.get('id',''))}"
    except FacebookError as e:
        return False, e.friendly
