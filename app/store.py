"""Kho cấu hình chung + danh sách Trang Facebook (đọc/ghi trong SQLite).

Trang quản trị localhost và phần cấu hình (config.py) đều dùng lớp này.
Cấu hình chung lưu ở bảng `settings`; mỗi Trang là một dòng ở bảng `pages`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from . import db

# Các khoá cấu hình chung + giá trị mặc định.
DEFAULTS = {
    "telegram_bot_token": "",
    "telegram_owner_chat_id": "",
    "anthropic_api_key": "",
    "anthropic_model": "claude-haiku-4-5-20251001",
    # Chọn "bộ não" AI: claude | gemini (đổi ở trang quản trị, không cần code)
    "ai_provider": "claude",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-flash",
    "fb_api_version": "v25.0",
    "ads_max_daily_budget_vnd": "500000",
    "ads_min_spend_for_advice_vnd": "100000",
    "ads_min_days_for_advice": "2",
    "tz": "Asia/Ho_Chi_Minh",
    "daily_ads_report_hour": "8",
    "daily_post_draft_hour": "7",
    "weekly_page_report_dow": "mon",
    # Chu kỳ canh sân alobo chung (phút) — dùng cho lịch chạy nền
    "alobo_check_interval_min": "30",
    # Báo lịch sân trống cố định theo giờ (sửa được): HÔM NAY vào 10h & 14h, NGÀY MAI vào 22h
    "alobo_report_today": "10:00,14:00",
    "alobo_report_tomorrow": "22:00",
    # Zalo Bot chính thức — địa chỉ API (sửa được nếu Zalo đổi)
    "zalo_bot_api_base": "https://bot-api.zaloplatforms.com",
    # Zalo tài khoản cá nhân (zca-js) — dịch vụ Node + VAN AN TOÀN né khóa
    "zalo_service_url": "http://127.0.0.1:8791",
    "zalo_min_gap_sec": "45",       # tối thiểu bao nhiêu giây giữa 2 tin chủ động
    "zalo_jitter_sec": "60",        # cộng thêm ngẫu nhiên tới bấy nhiêu giây
    "zalo_max_per_hour": "15",      # tối đa tin chủ động mỗi giờ
    "zalo_max_per_day": "100",      # tối đa tin chủ động mỗi ngày
    "zalo_allowed_hours": "7-22",   # chỉ gửi trong khung giờ này
    "zalo_warmup_days": "7",        # số ngày nên "làm ấm" tài khoản trước khi chạy mạnh
}

PAGE_FIELDS = [
    "name", "fb_page_id", "fb_page_token", "fb_ad_account_id", "fb_ads_token",
    "business_name", "business_desc", "brand_tone", "auto_post", "enabled",
]


# ---------- Cấu hình chung ----------

def get_setting(key: str, default: Optional[str] = None) -> str:
    with db.get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    if row and row["value"] is not None:
        return row["value"]
    if default is not None:
        return default
    return DEFAULTS.get(key, "")


def set_setting(key: str, value: str) -> None:
    with db.get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?,?)", (key, value or ""))


def all_settings() -> dict[str, str]:
    out = dict(DEFAULTS)
    with db.get_conn() as conn:
        for r in conn.execute("SELECT key, value FROM settings").fetchall():
            out[r["key"]] = r["value"]
    return out


def bootstrap_from_env() -> None:
    """Lần đầu: nếu DB chưa có cấu hình mà .env có, chép sang (tiện lúc khởi tạo)."""
    import os
    from dotenv import load_dotenv
    load_dotenv(db.DATA_DIR.parent / ".env")
    env_map = {
        "telegram_bot_token": "TELEGRAM_BOT_TOKEN",
        "telegram_owner_chat_id": "TELEGRAM_OWNER_CHAT_ID",
        "anthropic_api_key": "ANTHROPIC_API_KEY",
        "anthropic_model": "ANTHROPIC_MODEL",
        "fb_api_version": "FB_API_VERSION",
    }
    for skey, ekey in env_map.items():
        val = os.getenv(ekey, "").strip()
        if val and not get_setting(skey, ""):
            set_setting(skey, val)


# ---------- Trang Facebook ----------

def list_pages(only_enabled: bool = False) -> list[dict]:
    with db.get_conn() as conn:
        q = "SELECT * FROM pages"
        if only_enabled:
            q += " WHERE enabled=1"
        q += " ORDER BY id"
        rows = conn.execute(q).fetchall()
    return [dict(r) for r in rows]


def get_page(page_id: int) -> Optional[dict]:
    with db.get_conn() as conn:
        r = conn.execute("SELECT * FROM pages WHERE id=?", (page_id,)).fetchone()
    return dict(r) if r else None


def create_page(data: dict) -> int:
    row = {k: data.get(k, "") for k in PAGE_FIELDS}
    row["auto_post"] = int(bool(data.get("auto_post")))
    row["enabled"] = int(data.get("enabled", 1) in (1, "1", True, "on", "true"))
    with db.get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO pages({','.join(PAGE_FIELDS)}, created_at) "
            f"VALUES ({','.join(['?']*len(PAGE_FIELDS))}, ?)",
            tuple(row[k] for k in PAGE_FIELDS) + (datetime.now().isoformat(timespec="seconds"),),
        )
        return int(cur.lastrowid)


def update_page(page_id: int, data: dict) -> None:
    fields = {k: data[k] for k in PAGE_FIELDS if k in data}
    if "auto_post" in fields:
        fields["auto_post"] = int(bool(fields["auto_post"]))
    if "enabled" in fields:
        fields["enabled"] = int(fields["enabled"] in (1, "1", True, "on", "true"))
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    with db.get_conn() as conn:
        conn.execute(f"UPDATE pages SET {sets} WHERE id=?", tuple(fields.values()) + (page_id,))


def delete_page(page_id: int) -> None:
    with db.get_conn() as conn:
        conn.execute("DELETE FROM pages WHERE id=?", (page_id,))


# ---------- CRUD chung cho các bảng "nhiều tài khoản" ----------

def _list(table: str, only_enabled: bool = False) -> list[dict]:
    with db.get_conn() as conn:
        q = f"SELECT * FROM {table}"
        if only_enabled:
            q += " WHERE enabled=1"
        q += " ORDER BY id"
        return [dict(r) for r in conn.execute(q).fetchall()]


def _get(table: str, row_id: int) -> Optional[dict]:
    with db.get_conn() as conn:
        r = conn.execute(f"SELECT * FROM {table} WHERE id=?", (row_id,)).fetchone()
    return dict(r) if r else None


def _create(table: str, fields: list[str], data: dict) -> int:
    row = {k: data.get(k, "") for k in fields}
    with db.get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO {table}({','.join(fields)}, created_at) "
            f"VALUES ({','.join(['?']*len(fields))}, ?)",
            tuple(row[k] for k in fields) + (datetime.now().isoformat(timespec="seconds"),))
        return int(cur.lastrowid)


def _update(table: str, fields: list[str], row_id: int, data: dict) -> None:
    upd = {k: data[k] for k in fields if k in data}
    if not upd:
        return
    sets = ", ".join(f"{k}=?" for k in upd)
    with db.get_conn() as conn:
        conn.execute(f"UPDATE {table} SET {sets} WHERE id=?", tuple(upd.values()) + (row_id,))


def _delete(table: str, row_id: int) -> None:
    with db.get_conn() as conn:
        conn.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))


# ---------- Tài khoản Zalo (nhiều tài khoản) ----------
ZALO_FIELDS = ["name", "method", "bot_token", "phone", "group_ids", "auto_reply", "enabled", "persona"]


def _norm_flags(data: dict, flags=("auto_reply", "enabled")) -> dict:
    d = dict(data)
    for f in flags:
        if f in d:
            d[f] = int(d[f] in (1, "1", True, "on", "true"))
    return d


def list_zalo(only_enabled: bool = False) -> list[dict]:
    return _list("zalo_accounts", only_enabled)


def get_zalo(zid: int) -> Optional[dict]:
    return _get("zalo_accounts", zid)


def create_zalo(data: dict) -> int:
    return _create("zalo_accounts", ZALO_FIELDS, _norm_flags(data))


def update_zalo(zid: int, data: dict) -> None:
    _update("zalo_accounts", ZALO_FIELDS, zid, _norm_flags(data))


def delete_zalo(zid: int) -> None:
    _delete("zalo_accounts", zid)


# ---------- Sân alobo (nhiều sân) ----------
VENUE_FIELDS = ["name", "slug", "court_index", "username", "password", "courts", "windows",
                "days_ahead", "interval_min", "notify_channel", "zalo_account_ref", "enabled"]


def list_venues(only_enabled: bool = False) -> list[dict]:
    return _list("alobo_venues", only_enabled)


def get_venue(vid: int) -> Optional[dict]:
    return _get("alobo_venues", vid)


def create_venue(data: dict) -> int:
    return _create("alobo_venues", VENUE_FIELDS, _norm_flags(data, ("enabled",)))


def update_venue(vid: int, data: dict) -> None:
    _update("alobo_venues", VENUE_FIELDS, vid, _norm_flags(data, ("enabled",)))


def delete_venue(vid: int) -> None:
    _delete("alobo_venues", vid)


# ---------- Bộ não: kiến thức riêng (bot học từ chủ) ----------
KNOWLEDGE_FIELDS = ["title", "content", "tags", "enabled"]


def list_knowledge(only_enabled: bool = False) -> list[dict]:
    return _list("knowledge", only_enabled)


def get_knowledge(kid: int) -> Optional[dict]:
    return _get("knowledge", kid)


def create_knowledge(data: dict) -> int:
    return _create("knowledge", KNOWLEDGE_FIELDS, _norm_flags(data, ("enabled",)))


def update_knowledge(kid: int, data: dict) -> None:
    _update("knowledge", KNOWLEDGE_FIELDS, kid, _norm_flags(data, ("enabled",)))


def delete_knowledge(kid: int) -> None:
    _delete("knowledge", kid)


def _fmt_knowledge(k: dict) -> str:
    title = (k.get("title") or "").strip()
    return f"- {title + ': ' if title else ''}{(k.get('content') or '').strip()}"


def knowledge_text(query: str = "", max_chars: int = 6000) -> str:
    """Trả về khối kiến thức (đã bật) để nhét vào lời nhắc cho bot.

    Nếu tổng kiến thức nhỏ → đưa hết. Nếu lớn → chọn mục LIÊN QUAN nhất tới câu hỏi
    (đếm từ khoá trùng) cho tới khi đầy hạn mức ký tự.
    """
    items = list_knowledge(only_enabled=True)
    if not items:
        return ""
    total = sum(len(_fmt_knowledge(k)) for k in items)
    if total <= max_chars:
        chosen = items
    else:
        q = {w for w in (query or "").lower().split() if len(w) > 2}

        def score(k: dict) -> int:
            text = " ".join([k.get("title") or "", k.get("content") or "", k.get("tags") or ""]).lower()
            return sum(1 for w in q if w in text)

        chosen, used = [], 0
        for k in sorted(items, key=score, reverse=True):
            f = _fmt_knowledge(k)
            if used + len(f) > max_chars:
                break
            chosen.append(k)
            used += len(f)
    return "\n".join(_fmt_knowledge(k) for k in chosen)


# ---------- Lịch sử tin nhắn Zalo (làm trí nhớ hội thoại + kiến thức nhóm) ----------

def add_message(thread_id: str, text: str, sender: str = "", uid: str = "",
                is_group: bool = True, is_self: bool = False) -> None:
    """Lưu 1 tin nhắn (của khách hoặc của trợ lý) để bot nhớ ngữ cảnh + học nội dung nhóm."""
    if not (thread_id and (text or "").strip()):
        return
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO zalo_messages(thread_id, is_group, sender, uid, text, is_self, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (str(thread_id), 1 if is_group else 0, sender or "", uid or "",
             text.strip(), 1 if is_self else 0, datetime.now().isoformat(timespec="seconds")))


def recent_messages(thread_id: str, limit: int = 14) -> list[dict]:
    """Vài tin GẦN NHẤT trong luồng (để hiểu hội thoại nhiều lượt), thứ tự cũ → mới."""
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT sender, text, is_self FROM zalo_messages WHERE thread_id=? "
            "ORDER BY id DESC LIMIT ?", (str(thread_id), limit)).fetchall()
    return [dict(r) for r in reversed(rows)]


def search_messages(thread_id: str, query: str, limit: int = 6, exclude_recent: int = 14) -> list[dict]:
    """Tìm tin CŨ liên quan tới câu hỏi trong CHÍNH luồng đó (kiến thức nhóm).

    Bỏ qua nhóm tin gần nhất (đã đưa ở phần hội thoại) để không lặp.
    """
    words = [w for w in (query or "").lower().split() if len(w) > 2]
    if not words:
        return []
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT id, sender, text FROM zalo_messages WHERE thread_id=? AND is_self=0 "
            "ORDER BY id DESC LIMIT 400", (str(thread_id),)).fetchall()
    rows = [dict(r) for r in rows][exclude_recent:]  # bỏ phần mới nhất
    scored = []
    for r in rows:
        low = (r["text"] or "").lower()
        s = sum(1 for w in words if w in low)
        if s:
            scored.append((s, r))
    scored.sort(key=lambda x: (-x[0], -x[1]["id"]))
    return [r for _, r in scored[:limit]]


def prune_messages(thread_id: str, keep: int = 800) -> None:
    """Giữ lịch sử gọn: mỗi luồng chỉ giữ ~keep tin gần nhất."""
    with db.get_conn() as conn:
        conn.execute(
            "DELETE FROM zalo_messages WHERE thread_id=? AND id NOT IN "
            "(SELECT id FROM zalo_messages WHERE thread_id=? ORDER BY id DESC LIMIT ?)",
            (str(thread_id), str(thread_id), keep))


# ---------- Sổ tay nhớ từng khách (agent Zalo cá nhân hoá) ----------

def customer_memory(uid: str) -> Optional[dict]:
    if not uid:
        return None
    with db.get_conn() as conn:
        r = conn.execute("SELECT * FROM customer_memory WHERE uid=?", (str(uid),)).fetchone()
        return dict(r) if r else None


def remember_customer(uid: str, name: str, note: str, max_notes: int = 15) -> None:
    """Ghi thêm 1 điều cần nhớ về khách (theo uid). Giữ tối đa max_notes điều gần nhất, không trùng."""
    note = (note or "").strip()
    if not (uid and note):
        return
    with db.get_conn() as conn:
        r = conn.execute("SELECT name, notes FROM customer_memory WHERE uid=?", (str(uid),)).fetchone()
        old_name = r["name"] if r else ""
        notes = [n.strip() for n in ((r["notes"] if r else "") or "").split("\n") if n.strip()]
        if note not in notes:
            notes.append(note)
        notes = notes[-max_notes:]
        conn.execute("INSERT OR REPLACE INTO customer_memory(uid, name, notes, updated_at) VALUES (?,?,?,?)",
                     (str(uid), (name or old_name or "").strip(), "\n".join(notes), db._now()))


def customer_messages_since(iso_start: str) -> list[dict]:
    """Tin của KHÁCH (không phải bot) từ mốc thời gian iso_start → nay (cho bản tóm tắt cuối ngày)."""
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT sender, text, is_group, created_at FROM zalo_messages "
            "WHERE is_self=0 AND created_at>=? ORDER BY id", (str(iso_start),)).fetchall()
    return [dict(r) for r in rows]


def customer_memory_text(uid: str) -> str:
    """Khối 'sổ tay khách' để đưa vào ngữ cảnh agent (rỗng nếu chưa biết gì về khách này)."""
    m = customer_memory(uid)
    if not m or not (m.get("notes") or "").strip():
        return ""
    who = (m.get("name") or "").strip()
    head = f"KHÁCH QUEN{f' — tên {who}' if who else ''} (những điều ĐÃ BIẾT về khách này từ các lần trước, "
    head += "dùng để chăm sóc thân thiết & đúng nhu cầu, ĐỪNG hỏi lại những gì đã biết):"
    return head + "\n" + m["notes"]
