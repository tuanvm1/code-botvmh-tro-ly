"""'Bộ não bot' đọc từ THƯ MỤC ghi chú markdown (kho Obsidian).

Chủ viết kiến thức (giá sân, thông số vợt, cơ sở, câu chốt sale, hỏi đáp...) thành các ghi chú
.md trong kho Obsidian; kho được đồng bộ (git) về máy chủ; bot đọc để trả lời khách. Đây là
kiến thức RIÊNG của VMH — ưu tiên hơn kiến thức nền cứng trong code.

- Đường dẫn: setting 'bot_kb_dir' (mặc định <project>/data/bot-kb — nơi git kéo kho về).
- Chọn phần liên quan câu hỏi giống store.knowledge_text (nhỏ → đưa hết; lớn → chọn mục hợp nhất).
- Bỏ cú pháp Obsidian: frontmatter (--- ... ---), [[liên kết]], dấu # tiêu đề, ** __ `.
- BỎ QUA file/thư mục ẩn/nháp: tên bắt đầu bằng '.' hoặc '_' (gồm cả thư mục '.obsidian').
  → Chủ muốn để dành ghi chú nào chưa cho bot dùng thì đặt tên bắt đầu bằng '_'.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .. import db, store

_cache: dict = {}  # str(dir) -> (chữ_ký_mtime, list_notes)


def kb_dir() -> Path | None:
    raw = (store.get_setting("bot_kb_dir", "") or "").strip()
    p = Path(raw) if raw else (db.DATA_DIR / "bot-kb")
    return p if p.is_dir() else None


_MAX_FILE = 512 * 1024  # bỏ qua file .md > 512KB (tránh nạp file khổng lồ → tràn RAM VPS)


def _strip_md(md: str) -> str:
    t = (md or "").replace("\r\n", "\n")
    t = re.sub(r"\A---\n.*?\n---[ \t]*(\n|\Z)", "", t, flags=re.S)  # frontmatter YAML (kể cả thiếu newline cuối)
    t = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", t)          # [[link|hiển thị]] -> hiển thị
    t = re.sub(r"\[\[([^\]]+)\]\]", r"\1", t)                     # [[link]] -> link
    t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)           # bỏ dấu # tiêu đề, giữ chữ
    t = t.replace("**", "").replace("__", "")
    t = re.sub(r"`{1,3}", "", t)
    return t.strip()


def _title_of(text: str, fallback: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s:
            return s[:80]
    return fallback


def _iter_md(root: Path):
    """Duyệt các file .md HỢP LỆ trong kho: cắt nhánh thư mục ẩn/nháp ('.'/'_'); BỎ symlink và
    file trỏ RA NGOÀI kho (chặn lộ /etc/passwd, .env... qua symlink)."""
    root_r = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith((".", "_"))]  # không đi vào .git/.obsidian/_*
        for fn in filenames:
            if not fn.endswith(".md") or fn.startswith((".", "_")):
                continue
            p = Path(dirpath) / fn
            if p.is_symlink():
                continue
            try:
                if not p.resolve().is_relative_to(root_r):
                    continue
            except OSError:
                continue
            yield p


def _read_notes() -> list[dict]:
    root = kb_dir()
    if not root:
        return []
    files = sorted(_iter_md(root), key=str)
    try:
        sig = tuple((str(p), p.stat().st_mtime, p.stat().st_size) for p in files)
    except OSError:
        sig = None
    c = _cache.get(str(root))
    if c and sig is not None and c[0] == sig:
        return c[1]
    notes = []
    for p in files:
        try:
            if p.stat().st_size > _MAX_FILE:  # file quá lớn → bỏ (an toàn RAM)
                continue
            content = _strip_md(p.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        if content:
            notes.append({"title": _title_of(content, p.stem), "content": content, "tags": p.stem})
    if sig is not None:
        _cache[str(root)] = (sig, notes)
    return notes


def _fmt(n: dict) -> str:
    return f"[{n['title']}]\n{n['content']}"


def knowledge_text(query: str = "", max_chars: int = 6000) -> str:
    """Khối kiến thức từ kho Obsidian, chọn phần liên quan câu hỏi (nhỏ→hết; lớn→hợp nhất).

    Ghi chú LỚN hơn ngân sách còn lại → CẮT BỚT (không bỏ hẳn) để kiến thức liên quan nhất không biến mất.
    """
    notes = _read_notes()
    if not notes:
        return ""
    if sum(len(_fmt(n)) for n in notes) <= max_chars:
        return "\n\n".join(_fmt(n) for n in notes)
    q = {w for w in (query or "").lower().split() if len(w) > 2}

    def score(n: dict) -> int:
        text = (n["title"] + " " + n["content"] + " " + n["tags"]).lower()
        return sum(1 for w in q if w in text)

    parts, used = [], 0
    for n in sorted(notes, key=score, reverse=True):
        room = max_chars - used
        if room < 300:
            break
        f = _fmt(n)
        if len(f) <= room:
            parts.append(f)
            used += len(f) + 2
        else:  # ghi chú dài hơn chỗ còn lại → cắt bớt thay vì bỏ (đừng để mất kiến thức chính)
            parts.append(f[:room].rstrip() + " …(còn nữa)")
            used = max_chars
    return "\n\n".join(parts)


def combined_knowledge(query: str = "", max_chars: int = 6000) -> str:
    """Gộp kiến thức: kho Obsidian (ưu tiên, đưa trước) + trang 'Kiến thức' cũ (dự phòng)."""
    folder = knowledge_text(query, max_chars)
    remain = max_chars - len(folder)
    dbtext = store.knowledge_text(query, remain) if remain > 300 else ""
    if folder and dbtext:
        return folder + "\n\n" + dbtext
    return folder or dbtext
