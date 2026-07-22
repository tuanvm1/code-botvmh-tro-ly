"""Đọc lịch sân THẬT từ alobo cho MỘT sân.

alobo là app Flutter, dữ liệu bị mã hoá + đòi chữ ký → không đọc bằng lệnh gọi thường.
Cách CHẮC CHẮN (đã kiểm chứng): cho Chrome ẩn tự mở trang, đi vào "Đặt lịch", chọn loại
sân + ngày, chụp lưới lịch; rồi ĐỌC MÀU từng ô (trắng=trống, đỏ=đã đặt, xám=khoá).

Hình học lưới đã canh chỉnh cho viewport 2000x1400 — xem tasks/ALOBO-API.md.
Chuẩn hoá slot: {"court","date","start","end","free"} (đúng cái monitor.py chờ).
"""
from __future__ import annotations

import fcntl
import os
import signal
import shutil
import subprocess
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

_DIR = Path(__file__).resolve().parent
_READER = _DIR / "reader.mjs"
_LOCKFILE = "/tmp/alobo_reader.lock"   # khoá liên-tiến-trình: chỉ 1 Chrome đọc lịch tại một thời điểm
_CACHE_TTL = 300                        # nhớ tạm 5 phút (nhanh cho chat, mà không quá cũ để hớ khách)
_cache: dict = {}                       # (slug, court_index, date) -> (mốc thời gian, slots)

# ---- Hình học lưới (px, viewport 2000x1400) ----
GRID_LEFT = 59
COL_W = 50
N_COLS = 38            # 5:00 .. 24:00
START_MIN = 5 * 60
STEP_MIN = 30
ROW0_Y = 221
ROW_H = 40
MAX_ROWS = 16
LABEL_X = 30


class AloboError(Exception):
    pass


def _node_bin() -> str | None:
    n = shutil.which("node")
    if n:
        return n
    cand = Path.home() / ".local" / "node" / "bin" / "node"
    return str(cand) if cand.exists() else None


def _hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def _patch(px, cx, cy, rad=4):
    rs = gs = bs = n = 0
    for x in range(cx - rad, cx + rad + 1):
        for y in range(cy - rad, cy + rad + 1):
            r, g, b = px[x, y]
            rs += r; gs += g; bs += b; n += 1
    return rs // n, gs // n, bs // n


def _classify(r, g, b) -> str:
    if r > 225 and g < 165 and b < 165:
        return "booked"                      # đỏ = đã đặt
    if abs(r - g) < 22 and abs(g - b) < 22 and 135 < r < 210:
        return "locked"                      # xám = khoá
    if r > 245 and g > 245 and b > 238:
        return "free"                        # trắng = trống
    return "booked"                          # không chắc → coi như đã đặt (an toàn)


def _read_png(path: str, date_iso: str) -> list[dict]:
    from PIL import Image
    im = Image.open(path).convert("RGB")
    W, H = im.size
    px = im.load()

    # Kiểm chứng LƯỚI ĐÃ MỞ ĐÚNG: dải header trục giờ phải là màu xanh nhạt. Nếu không
    # (hộp thoại còn mở, alobo đổi giao diện...) → BÁO LỖI thay vì đọc bừa ra toàn sân "kín".
    hdr = 0
    for hx in (300, 700, 1100, 1500):
        if hx < W:
            r, g, b = _patch(px, hx, 192, 2)
            if b > 235 and g > 215 and r < 215:
                hdr += 1
    if hdr < 2:
        raise AloboError("chưa mở đúng lưới lịch (giao diện alobo có thể đã đổi) — thử lại sau.")

    def is_row(r: int) -> bool:
        # Hàng sân tồn tại nếu ô 5:00 KHÔNG phải nền "mint" (nền trang khi hết sân).
        # (Không dùng cột nhãn vì chữ "C.Lông" làm lệch màu trung bình.)
        y = ROW0_Y + ROW_H * r
        if y >= H - 2:
            return False
        rr, gg, bb = _patch(px, GRID_LEFT + COL_W // 2, y)
        is_mint = 228 <= rr <= 244 and gg >= 246 and 238 <= bb <= 250
        return not is_mint

    n_rows = 0
    for r in range(MAX_ROWS):
        if is_row(r):
            n_rows = r + 1
        else:
            break
    if n_rows == 0:
        raise AloboError("không nhận ra lưới lịch trong ảnh (có thể alobo đổi giao diện)")

    slots = []
    for r in range(n_rows):
        cy = ROW0_Y + ROW_H * r
        court = f"Sân {r + 1}"
        for c in range(N_COLS):
            cx = GRID_LEFT + c * COL_W + COL_W // 2
            state = _classify(*_patch(px, cx, cy))
            start = START_MIN + c * STEP_MIN
            slots.append({"court": court, "date": date_iso,
                          "start": _hhmm(start), "end": _hhmm(start + STEP_MIN),
                          "free": state == "free"})
    return slots


def fetch_schedule(cfg: dict, day_offset: int = 0, date_iso: str | None = None,
                   use_cache: bool = False) -> list[dict]:
    """Đọc lịch một sân cho ngày (day_offset: 0=hôm nay, 1=ngày mai).

    use_cache=True: nếu vừa đọc sân này trong 5 phút (_CACHE_TTL) thì DÙNG LẠI (cho phần chat nhanh).
    Các mốc báo tự động thì đọc TƯƠI (use_cache=False) và cũng cập nhật nhớ tạm.
    """
    slug = (cfg.get("slug") or "").strip()
    if not slug:
        raise AloboError(f"Sân '{cfg.get('venue_name','?')}' chưa có Mã sân (slug) — điền ở trang quản trị.")
    node = _node_bin()
    if not node:
        raise AloboError("Máy chưa có Node.js để chạy bộ đọc lịch.")
    court_idx = int(cfg.get("court_index") or 0)
    if date_iso is None:
        date_iso = (date.today() + timedelta(days=max(0, day_offset))).isoformat()

    key = (slug, court_idx, date_iso)
    if use_cache:
        c = _cache.get(key)
        if c and (time.monotonic() - c[0]) < _CACHE_TTL:
            return c[1]

    out = tempfile.mktemp(suffix=".png")
    try:
        # Khoá liên-tiến-trình: chỉ 1 Chrome đọc lịch cùng lúc (tránh tràn RAM VPS nhỏ).
        with open(_LOCKFILE, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                # Vừa chờ khoá xong: nếu tiến trình khác VỪA đọc & nhớ tạm → dùng lại, khỏi đọc trùng.
                if use_cache:
                    c = _cache.get(key)
                    if c and (time.monotonic() - c[0]) < _CACHE_TTL:
                        return c[1]
                # Nhóm tiến trình riêng (start_new_session) để khi timeout diệt được LUÔN Chrome con.
                proc = subprocess.Popen(
                    [node, str(_READER), slug, str(court_idx), str(day_offset), out],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    start_new_session=True)
                try:
                    stdout, stderr = proc.communicate(timeout=120)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)  # diệt node + Chrome mồ côi
                    except OSError:
                        pass
                    try:
                        proc.communicate(timeout=10)
                    except Exception:  # noqa: BLE001
                        pass
                    raise AloboError("đọc lịch alobo quá lâu (timeout) — thử lại sau.")
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)
        tag = (stdout or "").strip()
        if not tag.startswith("OK") or not os.path.exists(out):
            raise AloboError(f"đọc lịch alobo thất bại: {tag or (stderr or '')[:150]}")
        slots = _read_png(out, date_iso)
        _cache[key] = (time.monotonic(), slots)
        return slots
    finally:
        try:
            if os.path.exists(out):
                os.unlink(out)
        except OSError:
            pass


def mock_schedule(today: str | None = None) -> list[dict]:
    """Lịch giả để kiểm tra logic (không cần mạng)."""
    d0 = date.fromisoformat(today) if today else date.today()
    d1 = (d0 + timedelta(days=1)).isoformat()
    d0s = d0.isoformat()
    return [
        {"court": "Sân 1", "date": d0s, "start": "18:00", "end": "19:00", "free": True},
        {"court": "Sân 1", "date": d0s, "start": "19:00", "end": "20:00", "free": False},
        {"court": "Sân 2", "date": d0s, "start": "17:00", "end": "18:00", "free": True},
        {"court": "Sân 2", "date": d0s, "start": "12:00", "end": "13:00", "free": True},
        {"court": "Sân 3", "date": d1,  "start": "20:00", "end": "21:00", "free": True},
    ]
