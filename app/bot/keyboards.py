"""Các bàn phím nút bấm (inline keyboard) cho Telegram."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def draft_actions(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Đăng ngay", callback_data=f"post:approve:{draft_id}"),
         InlineKeyboardButton("🔁 Viết lại", callback_data=f"post:regen:{draft_id}")],
        [InlineKeyboardButton("🗑 Bỏ", callback_data=f"post:cancel:{draft_id}")],
    ])


def campaign_row(campaign: dict) -> list[InlineKeyboardButton]:
    cid = campaign["id"]
    running = (campaign.get("status") == "ACTIVE")
    if running:
        toggle = InlineKeyboardButton("⏸ Tắt", callback_data=f"ads:pause:{cid}")
    else:
        toggle = InlineKeyboardButton("▶️ Bật", callback_data=f"ads:enable:{cid}")
    return [toggle, InlineKeyboardButton("💰 Ngân sách", callback_data=f"ads:budget:{cid}")]


def confirm(action: str, target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Chắc chắn", callback_data=f"confirm:{action}:{target}"),
         InlineKeyboardButton("❌ Thôi", callback_data="confirm:cancel:_")],
    ])


def pages_list(pages: list[dict], active_id: int | None = None) -> InlineKeyboardMarkup:
    rows = []
    for p in pages:
        mark = "🔵 " if active_id == p["id"] else ""
        rows.append([InlineKeyboardButton(f"{mark}{p['name']}", callback_data=f"page:select:{p['id']}")])
    if not rows:
        rows = [[InlineKeyboardButton("➕ Chưa có Trang nào — thêm ở trang quản trị", callback_data="page:none:_")]]
    return InlineKeyboardMarkup(rows)


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏷 Chọn Trang", callback_data="menu:chontrang")],
        [InlineKeyboardButton("✍️ Viết bài mới", callback_data="menu:vietbai")],
        [InlineKeyboardButton("📊 Báo cáo quảng cáo", callback_data="menu:baocao")],
        [InlineKeyboardButton("🎯 Quản lý chiến dịch", callback_data="menu:quangcao")],
        [InlineKeyboardButton("📈 Báo cáo Trang", callback_data="menu:trang")],
        [InlineKeyboardButton("⚙️ Trạng thái hệ thống", callback_data="menu:trangthai")],
    ])
