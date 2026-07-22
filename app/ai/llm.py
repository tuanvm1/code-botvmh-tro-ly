"""Một cửa gọi AI — tự chọn Claude hay Gemini theo cài đặt của chủ.

Chủ chọn "bộ não" ở trang quản trị (ai_provider = claude | gemini). Mọi phần trò chuyện
đi qua hàm chat() này, nên đổi nhà cung cấp KHÔNG cần sửa code ở nơi khác.

- Claude: dùng SDK anthropic (đã có sẵn).
- Gemini: gọi thẳng REST (không cần cài thêm thư viện) — endpoint generateContent.

messages: danh sách [{"role": "user"|"assistant", "content": "..."}]
"""
from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager

import requests

from .. import store
from .content import AIError


# ---- HÀNG ĐỢI AI: giới hạn số lời gọi AI ĐỒNG THỜI (chống 100 người hỏi cùng lúc làm quá hạn mức Anthropic) ----
# Số dư vượt giới hạn sẽ XẾP HÀNG CHỜ TỚI LƯỢT — xử lý lần lượt từng người, KHÔNG bỏ cuộc, KHÔNG báo bận.
_AI_MAX = max(1, int(os.environ.get("AI_MAX_CONCURRENT", "8")))      # số lời gọi AI song song tối đa
_AI_GATE = threading.BoundedSemaphore(_AI_MAX)


class AIBusy(Exception):
    """(Không dùng nữa) — giữ lại để code cũ tham chiếu không lỗi."""


@contextmanager
def ai_slot():
    _AI_GATE.acquire()   # chờ tới lượt (chặn cho tới khi có chỗ) — ai cũng được xử lý, chỉ là theo thứ tự
    try:
        yield
    finally:
        _AI_GATE.release()


_RETRY_CODES = {408, 409, 425, 429, 500, 502, 503, 504, 529}


def _is_retryable(e: Exception) -> bool:
    """Lỗi TẠM THỜI (nên thử lại): quá tải/nghẽn/hết hạn mức/mạng chập chờn/5xx.

    Ưu tiên đọc MÃ TRẠNG THÁI (chính xác) rồi mới tới cụm từ (tránh khớp nhầm như
    'rate' nằm trong 'generate', hay số '500' nằm trong con số khác).
    """
    code = getattr(e, "status_code", None)
    if not isinstance(code, int):
        code = getattr(getattr(e, "response", None), "status_code", None)
    if isinstance(code, int):
        return code in _RETRY_CODES
    s = f"{type(e).__name__} {e}".lower()
    phrases = ("overload", "rate limit", "too many request", "timeout", "timed out",
               "connection", "temporarily", "unavailable", "internal server error",
               "báo lỗi 429", "báo lỗi 500", "báo lỗi 502", "báo lỗi 503", "báo lỗi 504", "báo lỗi 529")
    return any(p in s for p in phrases)


def provider() -> str:
    p = (store.get_setting("ai_provider") or "claude").strip().lower()
    return "gemini" if p == "gemini" else "claude"


def active_label() -> str:
    if provider() == "gemini":
        return f"Gemini ({store.get_setting('gemini_model') or 'gemini-2.5-flash'})"
    return f"Claude ({store.get_setting('anthropic_model') or 'claude'})"


def chat(system: str, messages: list[dict], max_tokens: int = 700) -> str:
    """Gửi hội thoại cho AI đang chọn, trả về chữ thuần.

    Tự THỬ LẠI tối đa 3 lần khi gặp lỗi tạm thời (Claude/Gemini quá tải, mạng chập chờn)
    để khách không bị "im lặng" chỉ vì server AI nghẽn nhất thời.
    """
    use_gemini = provider() == "gemini"
    last = None
    for attempt in range(3):
        try:
            return _gemini(system, messages, max_tokens) if use_gemini \
                else _claude(system, messages, max_tokens)
        except Exception as e:  # noqa: BLE001
            last = e
            if _is_retryable(e) and attempt < 2:
                time.sleep(1.5 * (attempt + 1))  # 1.5s, 3s
                continue
            raise
    raise last


# ---------------- Claude ----------------
def _claude(system: str, messages: list[dict], max_tokens: int) -> str:
    from .content import _client
    from ..config import config
    client = _client()
    with ai_slot():   # xếp hàng nếu đang có quá nhiều lời gọi AI cùng lúc
        msg = client.messages.create(
            model=config.anthropic_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages],
        )
    return "".join(b.text for b in msg.content if b.type == "text").strip()


# ---------------- Gemini (REST) ----------------
def _gemini(system: str, messages: list[dict], max_tokens: int) -> str:
    key = store.get_setting("gemini_api_key")
    if not key:
        raise AIError("Chưa có khoá Gemini API. Vào trang quản trị điền giúp.")
    model = store.get_setting("gemini_model") or "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    contents = [{
        "role": "model" if m["role"] == "assistant" else "user",
        "parts": [{"text": m["content"]}],
    } for m in messages]
    body = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    try:
        with ai_slot():   # xếp hàng chung với Claude
            r = requests.post(url, params={"key": key}, json=body, timeout=40)
    except AIBusy:
        raise
    except Exception as e:  # noqa: BLE001
        raise AIError(f"Gọi Gemini lỗi mạng: {e}")
    if r.status_code != 200:
        raise AIError(f"Gemini báo lỗi {r.status_code}: {r.text[:200]}")
    data = r.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError):
        # Có thể bị chặn nội dung hoặc rỗng
        return ""


def check_provider() -> tuple[bool, str]:
    """Kiểm tra nhanh AI đang chọn có gọi được không (cho nút Kiểm tra ở quản trị)."""
    try:
        out = chat("Bạn là trợ lý. Trả lời đúng 1 từ.",
                   [{"role": "user", "content": "Nói: OK"}], max_tokens=20)
        return (bool(out), f"{active_label()} → “{out[:40]}”" if out else f"{active_label()} trả lời rỗng")
    except Exception as e:  # noqa: BLE001
        return (False, f"{active_label()} lỗi: {e}")
