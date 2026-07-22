"""Dựng và cấu hình ứng dụng bot Telegram."""
from __future__ import annotations

import datetime as dt
import logging

from telegram import Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

from ..config import config
from .. import db, store
from . import handlers, jobs

log = logging.getLogger("trolytudong")


def _tzinfo():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(config.tz)
    except Exception:  # noqa: BLE001
        return dt.timezone(dt.timedelta(hours=7))  # dự phòng: giờ VN (UTC+7)


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    log.exception("Lỗi khi xử lý update", exc_info=ctx.error)
    try:
        owner = config.owner_chat_id_int()
        if owner is not None:
            await ctx.bot.send_message(owner, f"⚠️ Có lỗi nhỏ bên trong: {ctx.error}")
    except Exception:  # noqa: BLE001
        pass


def _register_jobs(app: Application) -> None:
    jq = app.job_queue
    tz = _tzinfo()
    jq.run_daily(jobs.job_daily_post_draft,
                 time=dt.time(hour=config.daily_post_draft_hour, tzinfo=tz), name="post_draft")
    jq.run_daily(jobs.job_daily_ads_report,
                 time=dt.time(hour=config.daily_ads_report_hour, tzinfo=tz), name="ads_report")
    # Chụp số liệu Trang mỗi ngày lúc 23:30 (chốt số cuối ngày)
    jq.run_daily(jobs.job_daily_page_snapshot,
                 time=dt.time(hour=23, minute=30, tzinfo=tz), name="page_snapshot")
    # Báo cáo Trang: chạy mỗi sáng, bên trong tự lọc đúng thứ trong tuần
    jq.run_daily(jobs.job_weekly_page_report,
                 time=dt.time(hour=9, tzinfo=tz), name="weekly_page_report")
    # Kiểm tra sức khoẻ token mỗi ngày 8:30
    jq.run_daily(jobs.job_token_health,
                 time=dt.time(hour=8, minute=30, tzinfo=tz), name="token_health")
    # Báo lịch sân trống alobo CỐ ĐỊNH theo giờ (sửa ở quản trị):
    #   HÔM NAY vào các giờ alobo_report_today (mặc định 10:00, 14:00)
    #   NGÀY MAI vào các giờ alobo_report_tomorrow (mặc định 22:00)
    def _times(key: str) -> list[dt.time]:
        out = []
        for part in (store.get_setting(key) or "").split(","):
            part = part.strip()
            if ":" in part:
                try:
                    h, m = part.split(":"); out.append(dt.time(hour=int(h), minute=int(m), tzinfo=tz))
                except ValueError:
                    pass
        return out
    for i, t in enumerate(_times("alobo_report_today")):
        jq.run_daily(jobs.job_alobo_report_today, time=t, name=f"alobo_today_{i}")
    for i, t in enumerate(_times("alobo_report_tomorrow")):
        jq.run_daily(jobs.job_alobo_report_tomorrow, time=t, name=f"alobo_tomorrow_{i}")
    # Trợ lý cầu lông Zalo: đọc tin & tự trả lời khi bị tag (poll mỗi 15 giây)
    jq.run_repeating(jobs.job_zalo_poll, interval=15, first=30, name="zalo_poll")
    # Cuối ngày: tóm tắt hoạt động khách Zalo gửi CHỦ (mặc định 21:30; sửa qua setting zalo_summary_time)
    _st = (store.get_setting("zalo_summary_time") or "21:30").strip()
    try:
        _sh, _sm = _st.split(":")
        _sumt = dt.time(hour=int(_sh), minute=int(_sm), tzinfo=tz)
    except ValueError:
        _sumt = dt.time(hour=21, minute=30, tzinfo=tz)
    jq.run_daily(jobs.job_daily_zalo_summary, time=_sumt, name="zalo_summary")


def build_application() -> Application:
    db.init_db()
    store.bootstrap_from_env()  # lần đầu: chép chìa khoá từ .env vào kho (nếu có)

    if not config.telegram_bot_token:
        raise SystemExit(
            "Chưa có mã bot Telegram. Mở trang quản trị http://127.0.0.1:8760 để điền,\n"
            "hoặc nhắn Claude để được hướng dẫn tạo bot Telegram (khoảng 3 phút)."
        )

    app = Application.builder().token(config.telegram_bot_token).build()

    app.add_handler(CommandHandler("start", handlers.cmd_start))
    app.add_handler(CommandHandler(["menu", "help"], handlers.cmd_menu))
    app.add_handler(CommandHandler("trangthai", handlers.cmd_trangthai))
    app.add_handler(CommandHandler(["chontrang", "trangfb"], handlers.cmd_chontrang))
    app.add_handler(CommandHandler("ghinho", handlers.cmd_ghinho))
    app.add_handler(CommandHandler("kienthuc", handlers.cmd_kienthuc))
    app.add_handler(CommandHandler("vietbai", handlers.cmd_vietbai))
    app.add_handler(CommandHandler("baocao", handlers.cmd_baocao))
    app.add_handler(CommandHandler("quangcao", handlers.cmd_quangcao))
    app.add_handler(CommandHandler("trang", handlers.cmd_trang))
    app.add_handler(CallbackQueryHandler(handlers.on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.on_text))
    app.add_error_handler(on_error)

    _register_jobs(app)
    return app
