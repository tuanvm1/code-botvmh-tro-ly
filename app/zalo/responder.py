"""Bộ quyết định trả lời trong nhóm Zalo (Giai đoạn 2).

Phần "nghĩ ra câu trả lời" dùng chung bộ não chuyên gia cầu lông (ai/badminton.py).
Phần GỬI/NHẬN tin trong nhóm Zalo (qua Zalo Bot chính thức hoặc zca-js với tài khoản
phụ) sẽ nối khi bạn chuẩn bị xong tài khoản phụ — xem transport.py.

is_tagged() là hàm thuần (kiểm tra được): xác định tin nhắn có gọi trợ lý không.
"""
from __future__ import annotations

from ..ai import badminton

# Các cách gọi trợ lý (chỉ dùng cho đường Zalo Bot CHÍNH THỨC — app/bot/jobs.py, hiện tạm
# nghỉ). Đường tài khoản cá nhân (zca-js) KHÔNG dùng bộ này: nó chỉ trả lời khi @nhắc đích danh.
TRIGGERS = ["@trợ lý", "@tro ly", "@hlv", "trợ lý ơi", "hlv ơi", "@bot"]


def is_tagged(text: str, extra_triggers: list[str] | None = None) -> bool:
    if not text:
        return False
    low = text.lower()
    for t in (TRIGGERS + (extra_triggers or [])):
        if t.lower() in low:
            return True
    return False


def strip_tag(text: str, extra_triggers: list[str] | None = None) -> str:
    """Bỏ phần gọi tên để còn lại câu hỏi thật."""
    out = text
    for t in (TRIGGERS + (extra_triggers or [])):
        out = out.replace(t, "").replace(t.lower(), "").replace(t.title(), "")
    return out.strip(" ,:@").strip()


def reply(text: str, asker_name: str = "", extra_triggers: list[str] | None = None) -> str:
    """Soạn câu trả lời cầu lông cho một câu hỏi trong nhóm."""
    question = strip_tag(text, extra_triggers) or text
    return badminton.answer(question, asker_name)
