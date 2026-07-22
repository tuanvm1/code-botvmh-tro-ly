"""Cấu hình chung — đọc từ kho (SQLite) để trang quản trị chỉnh sửa được.

Cấu hình từng Trang Facebook nằm ở bảng `pages` (xem store.py), không ở đây.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import db
from . import store

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = db.DATA_DIR


def _int(key: str) -> int:
    try:
        return int(store.get_setting(key))
    except (ValueError, TypeError):
        return int(store.DEFAULTS.get(key, "0") or 0)


class Config:
    # --- Chung ---
    @property
    def telegram_bot_token(self) -> str: return store.get_setting("telegram_bot_token")

    @property
    def telegram_owner_chat_id(self) -> str: return store.get_setting("telegram_owner_chat_id")

    @property
    def anthropic_api_key(self) -> str: return store.get_setting("anthropic_api_key")

    @property
    def anthropic_model(self) -> str: return store.get_setting("anthropic_model")

    @property
    def fb_api_version(self) -> str: return store.get_setting("fb_api_version")

    # --- Chốt an toàn quảng cáo ---
    @property
    def ads_max_daily_budget_vnd(self) -> int: return _int("ads_max_daily_budget_vnd")

    @property
    def ads_min_spend_for_advice_vnd(self) -> int: return _int("ads_min_spend_for_advice_vnd")

    @property
    def ads_min_days_for_advice(self) -> int: return _int("ads_min_days_for_advice")

    # --- Giờ giấc ---
    @property
    def tz(self) -> str: return store.get_setting("tz")

    @property
    def daily_ads_report_hour(self) -> int: return _int("daily_ads_report_hour")

    @property
    def daily_post_draft_hour(self) -> int: return _int("daily_post_draft_hour")

    @property
    def weekly_page_report_dow(self) -> str: return store.get_setting("weekly_page_report_dow")

    # --- Tiện ích ---
    def owner_chat_id_int(self) -> Optional[int]:
        try:
            return int(self.telegram_owner_chat_id)
        except (TypeError, ValueError):
            return None

    def missing_for(self, feature: str) -> list[str]:
        need = {
            "telegram": [("telegram_bot_token", "Mã bot Telegram"),
                         ("telegram_owner_chat_id", "Telegram của bạn")],
            "ai": [("anthropic_api_key", "Khoá Claude API")],
        }
        out = []
        for attr, human in need.get(feature, []):
            if not getattr(self, attr, ""):
                out.append(human)
        return out

    def status_report(self) -> str:
        def mark(ok: bool) -> str:
            return "✅" if ok else "❌ chưa có"
        pages = store.list_pages()
        n_ok_post = sum(1 for p in pages if p.get("fb_page_id") and p.get("fb_page_token"))
        n_ok_ads = sum(1 for p in pages if p.get("fb_ad_account_id") and p.get("fb_ads_token"))
        lines = ["<b>Trạng thái hệ thống</b>", ""]
        lines.append(f"• Telegram: {mark(bool(self.telegram_bot_token and self.telegram_owner_chat_id))}")
        lines.append(f"• Claude AI: {mark(bool(self.anthropic_api_key))}")
        lines.append(f"• Số Trang đã thêm: <b>{len(pages)}</b>")
        lines.append(f"   - Đăng bài sẵn sàng: {n_ok_post}/{len(pages)}")
        lines.append(f"   - Quảng cáo sẵn sàng: {n_ok_ads}/{len(pages)}")
        lines.append("\nSửa chìa khoá tại trang quản trị: <code>http://127.0.0.1:8760</code>")
        return "\n".join(lines)


config = Config()
