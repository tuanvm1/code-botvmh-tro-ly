"""Giám sát tiến trình bot: cho phép trang quản trị BẬT / TẮT / KHỞI ĐỘNG LẠI bot.

Nhờ vậy khi chủ sân đổi chìa khoá/tài khoản trên trang quản trị, chỉ cần bấm
"Khởi động lại" là hệ thống nạp thông tin mới và chạy tiếp — không cần code lại.

Bot chạy như tiến trình con (python main.py). Có luồng nền tự bật lại nếu bot chết.
"""
from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LOG = ROOT / "data" / "bot.log"

_proc: subprocess.Popen | None = None
_should_run = False
_lock = threading.Lock()
_monitor_on = False


def _spawn() -> subprocess.Popen:
    LOG.parent.mkdir(exist_ok=True)
    fh = open(LOG, "a")
    return subprocess.Popen([sys.executable, str(ROOT / "main.py")], cwd=str(ROOT),
                            stdout=fh, stderr=fh)


def _ensure_monitor():
    global _monitor_on
    if _monitor_on:
        return
    _monitor_on = True

    def loop():
        global _proc
        while True:
            time.sleep(5)
            with _lock:
                if _should_run and (_proc is None or _proc.poll() is not None):
                    try:
                        _proc = _spawn()
                    except Exception:  # noqa: BLE001
                        pass
    threading.Thread(target=loop, daemon=True).start()


def start():
    global _proc, _should_run
    with _lock:
        _should_run = True
        if _proc is None or _proc.poll() is not None:
            _proc = _spawn()
    _ensure_monitor()


def stop():
    global _proc, _should_run
    with _lock:
        _should_run = False
        if _proc and _proc.poll() is None:
            _proc.terminate()
            try:
                _proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                _proc.kill()
        _proc = None


def restart():
    stop()
    time.sleep(1)
    start()


def is_running() -> bool:
    with _lock:
        return _proc is not None and _proc.poll() is None
