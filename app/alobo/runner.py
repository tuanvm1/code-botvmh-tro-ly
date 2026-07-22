"""Điều phối canh sân cho TỪNG SÂN (bảng alobo_venues).

Tách khỏi phần gửi (Telegram/Zalo) để kiểm tra được logic bằng dữ liệu giả.
"""
from __future__ import annotations

from typing import Optional

from . import monitor, source


def check_venue(venue_row: dict, use_mock: bool = False, today: Optional[str] = None) -> Optional[str]:
    """Canh một sân. Trả về nội dung tin cần gửi (nếu có giờ trống MỚI), hoặc None."""
    cfg = monitor.venue_config(venue_row)

    if use_mock:
        slots = source.mock_schedule(today)
    else:
        slots = source.fetch_schedule(cfg)  # có thể ném AloboError

    # Gắn tên sân vào từng slot để chống trùng theo từng sân
    for s in slots:
        s.setdefault("venue", cfg["venue_name"])

    prime = monitor.find_free_prime_slots(
        slots, cfg["courts"], cfg["windows"], cfg["days_ahead"], today)
    new = monitor.keep_new(prime)
    if not new:
        return None
    msg = monitor.compose_message(new, cfg["venue_name"])
    monitor.mark_notified(new)
    return msg
