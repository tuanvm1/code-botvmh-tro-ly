"""Việc chạy tự động theo lịch (đa-Trang)."""
from __future__ import annotations

import asyncio
from datetime import date, datetime

from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ..config import config
from .. import store
from ..facebook import page as fb_page
from ..facebook import client as fb_client
from ..alobo import runner as alobo_runner
from ..alobo import monitor as alobo_monitor
from ..alobo import source as alobo_source
from ..alobo.source import AloboError
from ..zalo import botapi as zalo_botapi
from ..zalo import responder as zalo_responder
from . import handlers

WEEKDAY = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def _owner() -> int | None:
    return config.owner_chat_id_int()


def _has_post(p: dict) -> bool:
    return bool(p.get("fb_page_id") and p.get("fb_page_token"))


def _has_ads(p: dict) -> bool:
    return bool(p.get("fb_ad_account_id") and p.get("fb_ads_token"))


async def job_daily_post_draft(ctx: ContextTypes.DEFAULT_TYPE):
    chat = _owner()
    if chat is None or config.missing_for("ai"):
        return
    for p in store.list_pages(only_enabled=True):
        if p.get("auto_post") and _has_post(p):
            await handlers._make_and_send_draft(ctx, chat, p)


async def job_daily_ads_report(ctx: ContextTypes.DEFAULT_TYPE):
    chat = _owner()
    if chat is None:
        return
    for p in store.list_pages(only_enabled=True):
        if _has_ads(p):
            await handlers.send_ads_report(ctx, chat, p, date_preset="yesterday")


async def job_daily_zalo_summary(ctx: ContextTypes.DEFAULT_TYPE):
    """Cuối ngày: tóm tắt hoạt động khách Zalo gửi CHỦ (để chủ chủ động chăm khách chưa chốt)."""
    chat = _owner()
    if chat is None:
        return
    start = datetime.now().strftime("%Y-%m-%dT00:00:00")
    msgs = store.customer_messages_since(start)
    if not msgs:
        return  # không có khách nhắn → không làm phiền chủ
    from ..ai import zalo_agent
    text = await asyncio.to_thread(zalo_agent.owner_daily_summary, msgs)
    if (text or "").strip():
        try:
            await ctx.bot.send_message(chat, text, parse_mode=ParseMode.HTML)
        except Exception:  # noqa: BLE001
            await ctx.bot.send_message(chat, text)  # HTML lỗi → gửi thô


async def job_daily_page_snapshot(ctx: ContextTypes.DEFAULT_TYPE):
    for p in store.list_pages(only_enabled=True):
        if _has_post(p):
            try:
                fb_page.fetch_page_snapshot(p, date.today().isoformat())
            except fb_client.FacebookError:
                pass


async def job_weekly_page_report(ctx: ContextTypes.DEFAULT_TYPE):
    chat = _owner()
    if chat is None:
        return
    if datetime.now().weekday() != WEEKDAY.get(config.weekly_page_report_dow, 0):
        return
    for p in store.list_pages(only_enabled=True):
        if _has_post(p):
            await handlers.send_page_report(ctx, chat, p)


async def job_alobo_check(ctx: ContextTypes.DEFAULT_TYPE):
    """Canh sân trống cho TẤT CẢ các sân đã bật; báo giờ đẹp còn trống (mới)."""
    chat = _owner()
    if chat is None:
        return
    for venue in store.list_venues(only_enabled=True):
        try:
            msg = alobo_runner.check_venue(venue)
        except AloboError:
            continue  # chưa hoàn thiện nguồn alobo cho sân này — im lặng
        except Exception:  # noqa: BLE001
            continue
        if not msg:
            continue
        await _deliver_slot_message(ctx, chat, venue, msg)


async def job_alobo_report_today(ctx: ContextTypes.DEFAULT_TYPE):
    await _alobo_report(ctx, 0)


async def job_alobo_report_tomorrow(ctx: ContextTypes.DEFAULT_TYPE):
    await _alobo_report(ctx, 1)


async def _alobo_report(ctx, day_offset: int):
    """Đọc lịch trống TẤT CẢ các sân đã bật, gộp thành MỘT tin/nhóm, gửi 1 lần.

    Mỗi lần báo = gộp cả các cơ sở (cùng một nhóm nhận) vào 1 tin cho gọn, đỡ spam.
    """
    from datetime import timedelta
    chat = _owner()
    target = (date.today() + timedelta(days=day_offset)).isoformat()
    when = "hôm nay" if day_offset == 0 else "ngày mai"
    from_time = datetime.now().strftime("%H:%M") if day_offset == 0 else None  # hôm nay: bỏ giờ đã qua

    # Gom các cơ sở theo ĐÍCH NHẬN (kênh + tài khoản Zalo) → mỗi đích 1 tin gộp.
    groups: dict = {}
    n_venues = n_err = 0
    for venue in store.list_venues(only_enabled=True):
        cfg = alobo_monitor.venue_config(venue)
        if not cfg.get("slug"):
            continue
        n_venues += 1
        try:
            slots = await asyncio.to_thread(alobo_source.fetch_schedule, cfg, day_offset, target)
        except Exception as e:  # noqa: BLE001  (AloboError / mạng / Chrome) → bỏ qua cơ sở này
            print(f"[alobo] đọc '{cfg['venue_name']}' lỗi: {e}")
            n_err += 1
            continue
        ranges = alobo_monitor.free_ranges(slots, cfg["courts"], from_time=from_time)
        key = (venue.get("notify_channel") or "telegram", venue.get("zalo_account_ref"))
        g = groups.setdefault(key, {"venue": venue, "items": []})
        g["items"].append((cfg["venue_name"], cfg.get("slug", ""), ranges))

    # ĐỌC LỖI CẢ 3 cơ sở → báo CHỦ qua Telegram (đừng "chết âm thầm").
    if n_venues > 0 and n_err == n_venues and chat is not None:
        try:
            await ctx.bot.send_message(
                chat, f"⚠️ Canh sân ({when}): không đọc được lịch của {n_err}/{n_venues} cơ sở lúc này. "
                      f"Hệ thống sẽ tự thử lại lần báo sau. Nếu lặp lại nhiều lần, báo Claude kiểm tra giúp.",
                parse_mode=ParseMode.HTML)
        except Exception:  # noqa: BLE001
            pass

    for _, g in groups.items():
        msg = alobo_monitor.compose_combined_digest(g["items"], target, when)
        if not msg:
            continue  # tất cả cơ sở của đích này đều kín → không báo
        await _deliver_slot_message(ctx, chat, g["venue"], msg)


async def _deliver_slot_message(ctx, chat, venue: dict, msg: str):
    """Gửi tin sân trống đúng kênh: Telegram, hoặc nhóm Zalo (fallback Telegram)."""
    from ..zalo import transport as zalo_transport
    channel = venue.get("notify_channel") or "telegram"
    if channel == "zalo" and venue.get("zalo_account_ref"):
        z = store.get_zalo(int(venue["zalo_account_ref"]))
        group_ids = [g.strip() for g in (z or {}).get("group_ids", "").split(",") if g.strip()]
        try:
            for gid in group_ids:
                await asyncio.to_thread(zalo_transport.send_group, z, gid, msg)
            return
        except Exception as e:  # noqa: BLE001  (ZaloNotReady/ZaloBotError...) → fallback Telegram
            await ctx.bot.send_message(
                chat, f"🔔 <i>(Chưa gửi được vào nhóm Zalo: {e} — tạm báo qua Telegram)</i>\n\n" + msg,
                parse_mode=ParseMode.HTML)
            return
    await ctx.bot.send_message(chat, msg, parse_mode=ParseMode.HTML)


async def job_zalo_poll(ctx: ContextTypes.DEFAULT_TYPE):
    """Trợ lý cầu lông trên Zalo: đọc tin mới, ai tag hỏi thì tự trả lời.

    Chỉ chạy cho tài khoản Zalo Bot chính thức đã bật 'tự trả lời' và có token.
    """
    for z in store.list_zalo(only_enabled=True):
        if z.get("method") != "official_bot" or not z.get("auto_reply") or not z.get("bot_token"):
            continue
        token = z["bot_token"]
        bot_id = token.split(":")[0]  # phần trước dấu ':' là id của bot
        offset_key = f"zalo_offset_{z['id']}"
        try:
            off = store.get_setting(offset_key)
            offset = int(off) if off else None
            updates = await asyncio.to_thread(zalo_botapi.get_updates, token, offset, 0)
        except Exception:  # noqa: BLE001
            continue
        max_id = None
        for u in updates:
            max_id = max(max_id or 0, int(u.get("update_id", 0)))
            msg = u.get("message") or {}
            chat = msg.get("chat") or {}
            text = msg.get("text") or ""
            chat_id = chat.get("id")
            sender_id = str((msg.get("from") or {}).get("id", ""))
            ctype = (chat.get("chat_type") or chat.get("type") or "").upper()
            if not text or chat_id is None or sender_id == bot_id:
                continue  # bỏ tin rỗng / tin do chính bot gửi (tránh lặp)
            is_group = "GROUP" in ctype
            # Nhóm: chỉ trả lời khi được tag. Chat 1-1: trả lời mọi câu hỏi.
            if is_group and not zalo_responder.is_tagged(text):
                continue
            try:
                answer = await asyncio.to_thread(zalo_responder.reply, text)
                await asyncio.to_thread(zalo_botapi.send_message, token, str(chat_id), answer)
            except Exception:  # noqa: BLE001
                continue
        if max_id is not None:
            store.set_setting(offset_key, str(max_id + 1))


async def job_token_health(ctx: ContextTypes.DEFAULT_TYPE):
    chat = _owner()
    if chat is None:
        return
    problems = []
    for p in store.list_pages(only_enabled=True):
        if p.get("fb_page_token"):
            ok, _ = fb_client.check_token(p["fb_page_token"])
            if not ok:
                problems.append(f"• [{p['name']}] kết nối đăng bài có vấn đề.")
        if p.get("fb_ads_token"):
            ok, _ = fb_client.check_token(p["fb_ads_token"])
            if not ok:
                problems.append(f"• [{p['name']}] kết nối quảng cáo có vấn đề.")
    if problems:
        await ctx.bot.send_message(
            chat, "🔑 <b>Cảnh báo kết nối Facebook</b>\n" + "\n".join(problems) +
            "\n\nVào trang quản trị cập nhật lại token nhé.", parse_mode=ParseMode.HTML)
