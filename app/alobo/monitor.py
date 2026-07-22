"""Logic canh sân trống (thuần, kiểm tra được không cần mạng).

Nhận danh sách "slot" đã chuẩn hoá từ nguồn alobo, lọc ra những khung giờ ĐẸP còn
TRỐNG (theo sân + khung giờ + số ngày tới mà chủ cấu hình), rồi loại những slot đã
báo trước đó (chống gửi trùng).

Cấu trúc một slot (dict):
  {"court": "Sân 1", "date": "2026-07-17", "start": "18:00", "end": "19:00", "free": True}
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from .. import db


def parse_windows(raw: str) -> list[tuple[str, str]]:
    """'17:00-21:00, 06:00-08:00' → [('17:00','21:00'), ('06:00','08:00')]"""
    out = []
    for part in (raw or "").split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            a, b = a.strip(), b.strip()
            if a and b:
                out.append((a, b))
    return out


def parse_courts(raw: str) -> list[str]:
    return [c.strip() for c in (raw or "").split(",") if c.strip()]


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _in_windows(start: str, windows: list[tuple[str, str]]) -> bool:
    if not windows:
        return True
    s = _to_min(start)
    for a, b in windows:
        if _to_min(a) <= s < _to_min(b):
            return True
    return False


def slot_key(slot: dict) -> str:
    return f"{slot.get('venue','')}|{slot.get('court','')}|{slot.get('date','')}|{slot.get('start','')}"


def find_free_prime_slots(slots: list[dict], courts: list[str], windows: list[tuple[str, str]],
                          days_ahead: int = 1, today: Optional[str] = None) -> list[dict]:
    """Lọc slot còn trống, đúng sân, đúng khung giờ đẹp, trong N ngày tới."""
    today = today or date.today().isoformat()
    d0 = datetime.strptime(today, "%Y-%m-%d").date()
    dmax = d0 + timedelta(days=max(0, days_ahead))
    court_set = set(courts)
    out = []
    for s in slots:
        if not s.get("free"):
            continue
        try:
            sd = datetime.strptime(s["date"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            continue
        if not (d0 <= sd <= dmax):
            continue
        if court_set and s.get("court") not in court_set:
            continue
        if not _in_windows(s.get("start", "00:00"), windows):
            continue
        out.append(s)
    out.sort(key=lambda x: (x["date"], x["start"], x.get("court", "")))
    return out


def keep_new(slots: list[dict]) -> list[dict]:
    """Bỏ những slot đã từng báo (theo DB), trả về slot mới cần báo."""
    keys = [slot_key(s) for s in slots]
    new_keys = set(db.alobo_new_slots(keys))
    return [s for s in slots if slot_key(s) in new_keys]


def mark_notified(slots: list[dict]) -> None:
    db.alobo_mark_notified([(slot_key(s), s.get("date", "")) for s in slots])
    db.alobo_prune(date.today().isoformat())


# Nhiều biến thể câu mở/đóng để mỗi tin KHÁC nhau chút (né bộ lọc spam trùng lặp của Zalo).
_OPENERS = [
    "🏸 <b>Còn sân trống{where}!</b> Chốt nhanh kẻo hết nha cả nhà 👇",
    "🏸 Cập nhật sân trống{where} nè anh em ơi 👇",
    "🏸 <b>Sân{where} còn khung giờ đẹp!</b> Ai đi thì ới nhau 👇",
    "🏸 Ting ting! Vừa có sân trống{where} 👇",
    "🏸 <b>Lịch sân trống{where} hôm nay</b> — nhanh tay giữ chỗ 👇",
]
_CLOSERS = [
    "\nInbox hoặc gọi sân mình để giữ chỗ nhé! ☎️",
    "\nAnh em nhắn sân giữ chỗ kẻo hết nha ☎️",
    "\nGiữ sân thì ib mình liền tay nhé! 🤙",
    "\nAi chốt thì báo sân một tiếng nha ☎️",
    "\nNhanh tay đặt kẻo lỡ khung đẹp nhé! 🙌",
]


def free_ranges(slots: list[dict], courts: list[str] | None = None,
                from_time: str | None = None) -> list[tuple[str, str, str]]:
    """Gộp các khung TRỐNG liên tiếp cùng sân thành khoảng (court, start, end).

    - courts: nếu có → chỉ lấy các sân này (khớp tên chứa, cho linh hoạt).
    - from_time "HH:MM": chỉ lấy khung bắt đầu >= giờ này (dùng cho báo trong ngày).
    """
    court_order, by_court = [], {}
    for s in slots:
        c = s.get("court", "")
        if c not in by_court:
            by_court[c] = []
            court_order.append(c)
        by_court[c].append(s)
    fmin = _to_min(from_time) if from_time else None
    out = []
    for c in court_order:
        if courts and not any(w.lower() in c.lower() or c.lower() in w.lower() for w in courts):
            continue
        run = None
        for s in sorted(by_court[c], key=lambda x: x.get("start", "")):
            keep = s.get("free") and (fmin is None or _to_min(s.get("start", "00:00")) >= fmin)
            if keep:
                if run is None:
                    run = [s["start"], s["end"]]
                elif run[1] == s["start"]:        # chỉ nối khi LIỀN NHAU (không có khoảng hở)
                    run[1] = s["end"]
                else:                              # có khoảng hở → chốt khoảng cũ, mở khoảng mới
                    out.append((c, run[0], run[1])); run = [s["start"], s["end"]]
            elif run:
                out.append((c, run[0], run[1])); run = None
        if run:
            out.append((c, run[0], run[1]))
    return out


def compose_digest(venue_name: str, date_iso: str, ranges: list[tuple[str, str, str]],
                   when_label: str = "hôm nay") -> str:
    """Soạn tin 'toàn bộ lịch trống' cho MỘT sân (đổi nhẹ câu mở/đóng chống trùng)."""
    if not ranges:
        return ""
    import random
    from datetime import datetime as _dt
    d = _dt.strptime(date_iso, "%Y-%m-%d").strftime("%d/%m")
    opener = random.choice([
        f"🏸 LỊCH SÂN TRỐNG {when_label.upper()} — {venue_name} ({d}) 👇",
        f"🏸 {venue_name}: còn các khung trống {when_label} ({d}) nè cả nhà 👇",
        f"🏸 Cập nhật sân trống {when_label} tại {venue_name} ({d}) 👇",
    ])
    lines = [opener, ""]
    # gom theo sân
    by_court = {}
    order = []
    for court, a, b in ranges:
        if court not in by_court:
            by_court[court] = []; order.append(court)
        by_court[court].append(f"{a}-{b}")
    for court in order:
        lines.append(f"• {court}: {', '.join(by_court[court])}")
    return "\n".join(lines).strip()


ALOBO_BASE = "https://datlich.alobo.vn/san/"


def compose_combined_digest(items: list[tuple], date_iso: str,
                            when_label: str = "hôm nay") -> str:
    """Soạn MỘT tin gộp NHIỀU cơ sở. items = [(tên_cơ_sở, slug, ranges), ...].

    Mỗi cơ sở kèm LINK đặt lịch. Chỉ liệt kê cơ sở CÓ khung trống. Cả 3 kín → trả rỗng.
    """
    import random
    from datetime import datetime as _dt
    # tương thích cả dạng cũ (name, ranges) lẫn mới (name, slug, ranges)
    norm = []
    for it in items:
        if len(it) == 3:
            name, slug, rngs = it
        else:
            name, rngs = it; slug = ""
        norm.append((name, slug, rngs))
    have = [(name, slug, rngs) for name, slug, rngs in norm if rngs]
    if not have:
        return ""
    d = _dt.strptime(date_iso, "%Y-%m-%d").strftime("%d/%m")
    lines = [random.choice([
        f"🏸 LỊCH SÂN TRỐNG {when_label.upper()} ({d}) — VMH BADMINTON 👇",
        f"🏸 Sân trống {when_label} ({d}) — cập nhật cả 3 cơ sở VMH 👇",
        f"🏸 Cập nhật sân trống {when_label} ({d}) tại VMH 👇",
    ]), ""]
    for name, slug, rngs in have:
        lines.append(f"📍 {name}")
        by_court, order = {}, []
        for court, a, b in rngs:
            if court not in by_court:
                by_court[court] = []; order.append(court)
            by_court[court].append(f"{a}-{b}")
        for court in order:
            lines.append(f"   • {court}: {', '.join(by_court[court])}")
        if slug:
            lines.append(f"   🔗 Đặt sân: {ALOBO_BASE}{slug}")
        lines.append("")
    return "\n".join(lines).strip()


def compose_message(slots: list[dict], venue_name: str = "") -> str:
    """Soạn tin thông báo sân trống; đổi nhẹ câu chữ mỗi lần để tránh trùng lặp."""
    if not slots:
        return ""
    import random
    where = f" tại {venue_name}" if venue_name else ""
    lines = [random.choice(_OPENERS).format(where=where), ""]
    cur_date = None
    for s in slots:
        if s["date"] != cur_date:
            cur_date = s["date"]
            d = datetime.strptime(cur_date, "%Y-%m-%d")
            lines.append(f"📅 <b>{d.strftime('%d/%m')}</b>")
        court = s.get("court", "")
        lines.append(f"   • {s['start']}–{s['end']} {court}")
    lines.append(random.choice(_CLOSERS))
    return "\n".join(lines)


# ---------- Đọc cấu hình canh sân từ một dòng "sân" (bảng alobo_venues) ----------

def venue_config(v: dict) -> dict:
    return {
        "id": v.get("id"),
        "venue_name": v.get("name", ""),
        "slug": v.get("slug", ""),
        "court_index": int(v.get("court_index") or 0),
        "username": v.get("username", ""),
        "password": v.get("password", ""),
        "courts": parse_courts(v.get("courts", "")),
        "windows": parse_windows(v.get("windows", "") or "17:00-21:00"),
        "days_ahead": int(v.get("days_ahead") or 1),
        "notify_channel": v.get("notify_channel") or "telegram",
        "zalo_account_ref": v.get("zalo_account_ref"),
    }
