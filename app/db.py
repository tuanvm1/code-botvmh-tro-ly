"""Kho dữ liệu SQLite.

Hỗ trợ NHIỀU TRANG Facebook cùng lúc: mọi số liệu lịch sử đều gắn với page_ref
(id nội bộ của Trang). Ngoài ra lưu cấu hình chung + danh sách Trang (để trang
quản trị localhost chỉnh sửa) và nhật ký hành động, bản nháp bài.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DEFAULT_DB = DATA_DIR / "trolydb.sqlite3"

# Đường dẫn DB hiện hành (selftest có thể đổi tạm).
_db_path = DEFAULT_DB


def set_db_path(p: Path) -> None:
    global _db_path
    _db_path = p


def db_path() -> Path:
    return _db_path


_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key    TEXT PRIMARY KEY,
    value  TEXT
);

CREATE TABLE IF NOT EXISTS pages (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               TEXT NOT NULL,
    fb_page_id         TEXT,
    fb_page_token      TEXT,
    fb_ad_account_id   TEXT,
    fb_ads_token       TEXT,
    business_name      TEXT,
    business_desc      TEXT,
    brand_tone         TEXT,
    auto_post          INTEGER DEFAULT 0,   -- 1 = tự gửi bản nháp mỗi sáng
    enabled            INTEGER DEFAULT 1,
    created_at         TEXT
);

CREATE TABLE IF NOT EXISTS page_daily (
    page_ref     INTEGER NOT NULL,
    day          TEXT NOT NULL,
    metric       TEXT NOT NULL,
    value        REAL NOT NULL,
    captured_at  TEXT NOT NULL,
    PRIMARY KEY (page_ref, day, metric)
);

CREATE TABLE IF NOT EXISTS ads_daily (
    page_ref       INTEGER NOT NULL,
    day            TEXT NOT NULL,
    campaign_id    TEXT NOT NULL,
    campaign_name  TEXT,
    spend          REAL DEFAULT 0,
    impressions    INTEGER DEFAULT 0,
    reach          INTEGER DEFAULT 0,
    clicks         INTEGER DEFAULT 0,
    ctr            REAL DEFAULT 0,
    cpc            REAL DEFAULT 0,
    cpm            REAL DEFAULT 0,
    frequency      REAL DEFAULT 0,
    results        INTEGER DEFAULT 0,
    result_type    TEXT,
    captured_at    TEXT NOT NULL,
    PRIMARY KEY (page_ref, day, campaign_id)
);

CREATE TABLE IF NOT EXISTS action_log (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL,
    page_ref INTEGER,
    actor    TEXT NOT NULL,
    action   TEXT NOT NULL,
    target   TEXT,
    detail   TEXT
);

CREATE TABLE IF NOT EXISTS post_drafts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    page_ref     INTEGER,
    created_at   TEXT NOT NULL,
    status       TEXT NOT NULL,
    text         TEXT NOT NULL,
    image_path   TEXT,
    scheduled_ts INTEGER,
    fb_post_id   TEXT,
    updated_at   TEXT
);

CREATE TABLE IF NOT EXISTS alobo_notified (
    slot_key    TEXT PRIMARY KEY,   -- 'venue|san|YYYY-MM-DD|HH:MM'
    day         TEXT NOT NULL,
    notified_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT,
    content     TEXT NOT NULL,
    tags        TEXT,
    enabled     INTEGER DEFAULT 1,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS zalo_accounts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    method       TEXT DEFAULT 'official_bot',   -- official_bot | personal
    bot_token    TEXT,                           -- nếu dùng Zalo Bot chính thức
    phone        TEXT,                           -- SIM tài khoản phụ (ghi nhớ)
    group_ids    TEXT,                           -- id nhóm, cách nhau dấu phẩy
    auto_reply   INTEGER DEFAULT 0,              -- tự trả lời cầu lông khi bị tag
    enabled      INTEGER DEFAULT 1,
    created_at   TEXT
);

CREATE TABLE IF NOT EXISTS alobo_venues (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL,
    username         TEXT,
    password         TEXT,
    courts           TEXT,               -- "Sân 1, Sân 3" — trống = tất cả
    windows          TEXT,               -- "17:00-21:00"
    days_ahead       INTEGER DEFAULT 1,
    interval_min     INTEGER DEFAULT 30,
    notify_channel   TEXT DEFAULT 'telegram',  -- telegram | zalo
    zalo_account_ref INTEGER,            -- báo qua tài khoản Zalo nào (nếu chọn zalo)
    enabled          INTEGER DEFAULT 1,
    created_at       TEXT
);

CREATE TABLE IF NOT EXISTS zalo_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id   TEXT NOT NULL,       -- id nhóm hoặc id người (1-1)
    is_group    INTEGER DEFAULT 1,
    sender      TEXT,                -- tên hiển thị người gửi
    uid         TEXT,                -- uid người gửi (rỗng nếu là bot)
    text        TEXT NOT NULL,
    is_self     INTEGER DEFAULT 0,   -- 1 = tin do trợ lý gửi
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_zalo_msg_thread ON zalo_messages(thread_id, id);
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def init_db() -> None:
    with sqlite3.connect(_db_path) as conn:
        conn.executescript(_SCHEMA)
        _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    """Thêm cột mới cho bảng cũ mà không mất dữ liệu (bỏ qua nếu đã có)."""
    add = [("zalo_accounts", "persona", "TEXT"),
           ("alobo_venues", "slug", "TEXT"),
           ("alobo_venues", "court_index", "INTEGER DEFAULT 0")]
    for table, col, typ in add:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError:
            pass  # cột đã tồn tại
    # Sổ tay nhớ từng khách (agent Zalo cá nhân hoá). Tạo nếu chưa có (không mất dữ liệu cũ).
    conn.execute("""CREATE TABLE IF NOT EXISTS customer_memory (
        uid TEXT PRIMARY KEY, name TEXT, notes TEXT, updated_at TEXT)""")


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ---------- Số liệu Trang (theo từng Trang) ----------

def save_page_metrics(page_ref: int, day: str, metrics: dict[str, float]) -> None:
    ts = _now()
    with get_conn() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO page_daily(page_ref, day, metric, value, captured_at) VALUES (?,?,?,?,?)",
            [(page_ref, day, k, float(v), ts) for k, v in metrics.items()],
        )


def page_metric_series(page_ref: int, metric: str, limit_days: int = 90) -> list[tuple[str, float]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT day, value FROM page_daily WHERE page_ref=? AND metric=? ORDER BY day DESC LIMIT ?",
            (page_ref, metric, limit_days),
        ).fetchall()
    return [(r["day"], r["value"]) for r in reversed(rows)]


# ---------- Số liệu Quảng cáo (theo từng Trang) ----------

def save_ads_rows(page_ref: int, day: str, rows: Iterable[dict]) -> None:
    ts = _now()
    cols = ["page_ref", "day", "campaign_id", "campaign_name", "spend", "impressions", "reach",
            "clicks", "ctr", "cpc", "cpm", "frequency", "results", "result_type", "captured_at"]
    payload = []
    for r in rows:
        payload.append(tuple(
            [page_ref, day] + [r.get(c) for c in cols[2:-1]] + [ts]
        ))
    with get_conn() as conn:
        conn.executemany(
            f"INSERT OR REPLACE INTO ads_daily({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})",
            payload,
        )


def campaign_spend_series(page_ref: int, campaign_id: str, limit_days: int = 30) -> list[tuple[str, float]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT day, spend FROM ads_daily WHERE page_ref=? AND campaign_id=? ORDER BY day DESC LIMIT ?",
            (page_ref, campaign_id, limit_days),
        ).fetchall()
    return [(r["day"], r["spend"]) for r in reversed(rows)]


# ---------- Nhật ký hành động ----------

def log_action(actor: str, action: str, target: str = "", detail: str = "",
               page_ref: Optional[int] = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO action_log(ts, page_ref, actor, action, target, detail) VALUES (?,?,?,?,?,?)",
            (_now(), page_ref, actor, action, target, detail),
        )


def recent_actions(limit: int = 10, page_ref: Optional[int] = None) -> list[dict]:
    with get_conn() as conn:
        if page_ref is None:
            rows = conn.execute("SELECT * FROM action_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM action_log WHERE page_ref=? ORDER BY id DESC LIMIT ?",
                                (page_ref, limit)).fetchall()
    return [dict(r) for r in rows]


# ---------- Bản nháp bài đăng ----------

def create_draft(page_ref: int, text: str, image_path: Optional[str] = None,
                 scheduled_ts: Optional[int] = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO post_drafts(page_ref, created_at, status, text, image_path, scheduled_ts, updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (page_ref, _now(), "draft", text, image_path, scheduled_ts, _now()),
        )
        return int(cur.lastrowid)


def get_draft(draft_id: int) -> Optional[dict]:
    with get_conn() as conn:
        r = conn.execute("SELECT * FROM post_drafts WHERE id=?", (draft_id,)).fetchone()
    return dict(r) if r else None


def update_draft(draft_id: int, **fields) -> None:
    if not fields:
        return
    fields["updated_at"] = _now()
    sets = ", ".join(f"{k}=?" for k in fields)
    with get_conn() as conn:
        conn.execute(f"UPDATE post_drafts SET {sets} WHERE id=?",
                     tuple(fields.values()) + (draft_id,))


# ---------- Chống gửi trùng thông báo sân trống (alobo) ----------

def alobo_new_slots(slot_keys: list[str]) -> list[str]:
    """Trả về những slot CHƯA từng báo (để chỉ báo giờ trống mới)."""
    if not slot_keys:
        return []
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT slot_key FROM alobo_notified WHERE slot_key IN ({','.join(['?']*len(slot_keys))})",
            tuple(slot_keys),
        ).fetchall()
    seen = {r["slot_key"] for r in rows}
    return [k for k in slot_keys if k not in seen]


def alobo_mark_notified(pairs: list[tuple[str, str]]) -> None:
    """pairs: danh sách (slot_key, day)."""
    ts = _now()
    with get_conn() as conn:
        conn.executemany("INSERT OR REPLACE INTO alobo_notified(slot_key, day, notified_at) VALUES (?,?,?)",
                         [(k, d, ts) for k, d in pairs])


def alobo_prune(before_day: str) -> None:
    """Dọn các slot đã báo của những ngày đã qua."""
    with get_conn() as conn:
        conn.execute("DELETE FROM alobo_notified WHERE day < ?", (before_day,))
