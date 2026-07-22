#!/usr/bin/env python3
"""Kéo kho 'bộ não bot' (Obsidian) từ GitHub về máy chủ — chạy định kỳ bởi systemd timer.

- git pull --ff-only vào <data>/bot-kb.
- Nếu KÉO LỖI kéo dài → cảnh báo chủ qua Telegram (tối đa 1 lần/giờ, tránh spam).
- Kéo lại được sau khi lỗi → báo đã hồi phục.
Bot đọc kho này qua setting `bot_kb_dir`; nếu kho thiếu/cũ bot vẫn chạy với kiến thức đã có.
"""
import fcntl
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import db, store  # noqa: E402

KB = db.DATA_DIR / "bot-kb"
STATE = db.DATA_DIR / ".kb_sync_state"
_LOCK = db.DATA_DIR / ".kb_sync.lock"
_ALERT_EVERY = 3600  # giây: tối đa 1 cảnh báo/giờ


def _tg(msg: str) -> None:
    tok = store.get_setting("telegram_bot_token")
    chat = store.get_setting("telegram_owner_chat_id")
    if not (tok and chat):
        return
    try:
        import requests
        requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                      json={"chat_id": chat, "text": msg}, timeout=15)
    except Exception:  # noqa: BLE001
        pass


def main() -> int:
    if not (KB / ".git").is_dir():
        return 0  # chưa clone kho → chưa làm gì
    # Khoá chống chạy chồng (2 tiến trình git cùng lúc = đụng nhau, báo lỗi nhầm). Đang bận → bỏ qua.
    lock = open(_LOCK, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 0
    # Lỗi xác thực/mạng phải fail NHANH (không treo chờ nhập mật khẩu), và mọi lỗi đều đi qua đường cảnh báo.
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0",
           "GIT_SSH_COMMAND": "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20"}

    def _git(*args):
        return subprocess.run(["git", "-C", str(KB), *args],
                              capture_output=True, text=True, timeout=120, env=env)

    ok, err = False, ""
    try:
        f = _git("fetch", "--quiet", "origin")
        if f.returncode != 0:
            err = f.stderr or f.stdout or "git fetch lỗi"
        else:
            # Bản MIRROR chỉ-đọc: ép về đúng bản trên GitHub → không bao giờ "kẹt" vì phân kỳ/không ff được.
            r = _git("reset", "--hard", "origin/main")
            ok = r.returncode == 0
            err = "" if ok else (r.stderr or r.stdout or "git reset lỗi")
    except subprocess.TimeoutExpired:
        err = "git chạy quá lâu (timeout)"
    except Exception as e:  # noqa: BLE001
        err = f"{type(e).__name__}: {e}"

    prev = STATE.read_text().strip() if STATE.exists() else ""
    if ok:
        if prev.startswith("fail"):
            _tg("✅ Bộ não bot (Obsidian) đã đồng bộ lại bình thường.")
        try:
            STATE.write_text("ok")
        except OSError:
            pass
        return 0
    # thất bại (fetch/reset/timeout) → cảnh báo có tiết chế (tối đa 1 lần/giờ)
    now = int(time.time())
    last = 0
    if prev.startswith("fail:"):
        try:
            last = int(prev.split(":", 1)[1])
        except ValueError:
            last = 0
    if now - last > _ALERT_EVERY:
        _tg("⚠️ Bộ não bot (Obsidian): KHÔNG kéo được kho kiến thức mới từ GitHub.\n"
            f"Lỗi: {(err or '')[:300]}\n"
            "Bot vẫn dùng kiến thức đã có. Anh kiểm tra giúp nhé (mạng/kho GitHub).")
        try:
            STATE.write_text(f"fail:{now}")
        except OSError:
            pass
    return 1


if __name__ == "__main__":
    sys.exit(main())
