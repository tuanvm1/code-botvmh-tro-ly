"""Giám sát dịch vụ Node của Zalo (zca-js).

Chỉ chạy khi có tài khoản Zalo kiểu 'personal' đang bật. Truyền các thông số VAN
AN TOÀN (giãn tin, giới hạn/giờ, /ngày, khung giờ) qua biến môi trường cho Node.
Tự bật lại nếu dịch vụ chết.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from .. import store

ROOT = Path(__file__).resolve().parent.parent.parent
SERVICE_DIR = ROOT / "zalo_service"
LOG = ROOT / "data" / "zalo_service.log"

_proc: subprocess.Popen | None = None
_should_run = False
_lock = threading.Lock()
_monitor_on = False


def _node_bin() -> str | None:
    # Ưu tiên node trong PATH, rồi ~/.local/node/bin/node
    n = shutil.which("node")
    if n:
        return n
    cand = Path.home() / ".local" / "node" / "bin" / "node"
    return str(cand) if cand.exists() else None


def _env() -> dict:
    e = dict(os.environ)
    node_dir = str(Path(_node_bin()).parent) if _node_bin() else ""
    if node_dir:
        e["PATH"] = node_dir + os.pathsep + e.get("PATH", "")
    e.update({
        "PYTHON_URL": "http://127.0.0.1:8760",
        "ZALO_PORT": "8791",
        "ZALO_MIN_GAP_SEC": store.get_setting("zalo_min_gap_sec"),
        "ZALO_JITTER_SEC": store.get_setting("zalo_jitter_sec"),
        "ZALO_MAX_PER_HOUR": store.get_setting("zalo_max_per_hour"),
        "ZALO_MAX_PER_DAY": store.get_setting("zalo_max_per_day"),
        "ZALO_ALLOWED_HOURS": store.get_setting("zalo_allowed_hours"),
    })
    return e


def _has_personal() -> bool:
    return any(z.get("method") == "personal" and z.get("enabled")
               for z in store.list_zalo())


def _spawn() -> subprocess.Popen | None:
    node = _node_bin()
    if not node:
        return None
    LOG.parent.mkdir(exist_ok=True)
    fh = open(LOG, "a")
    return subprocess.Popen([node, str(SERVICE_DIR / "index.js")], cwd=str(SERVICE_DIR),
                            stdout=fh, stderr=fh, env=_env())


def _ensure_monitor():
    global _monitor_on
    if _monitor_on:
        return
    _monitor_on = True

    def loop():
        global _proc
        while True:
            time.sleep(6)
            try:
                with _lock:
                    want = _should_run and _has_personal()
                    if want and (_proc is None or _proc.poll() is not None):
                        _proc = _spawn()
                    elif not want and _proc is not None and _proc.poll() is None:
                        _proc.terminate()
                        _proc = None
            except Exception as e:  # noqa: BLE001
                # Một lỗi tạm thời (vd DB bận) KHÔNG được giết vòng canh, nếu không
                # dịch vụ Zalo chết mà không ai bật lại — đúng kiểu "chết âm thầm".
                try:
                    LOG.parent.mkdir(exist_ok=True)
                    with open(LOG, "a") as fh:
                        fh.write(f"[supervisor] vòng canh gặp lỗi (bỏ qua, chạy tiếp): {e}\n")
                except Exception:  # noqa: BLE001
                    pass
    threading.Thread(target=loop, daemon=True).start()


def start():
    global _proc, _should_run
    with _lock:
        _should_run = True
        if _has_personal() and (_proc is None or _proc.poll() is not None):
            _proc = _spawn()
    _ensure_monitor()


def stop():
    global _proc, _should_run
    with _lock:
        _should_run = False
        if _proc and _proc.poll() is None:
            _proc.terminate()
            try:
                _proc.wait(timeout=8)
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


def node_available() -> bool:
    return _node_bin() is not None
