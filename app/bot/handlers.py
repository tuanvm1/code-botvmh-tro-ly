"""Xử lý lệnh & nút bấm của bot Telegram (đa-Trang).

Free-text → trợ lý AI (chuyên gia quảng cáo + cầu lông), theo Trang đang chọn.
Lệnh & nút → viết bài / báo cáo / quản lý chiến dịch cho Trang đang chọn.
"""
from __future__ import annotations

import asyncio

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ..config import config
from .. import db, store
from ..ai import agent as ai_agent
from ..ai import content as ai_content
from ..ai import analysis as ai_analysis
from ..ai.content import AIError
from ..facebook import ads as fb_ads
from ..facebook import posting as fb_posting
from ..facebook import page as fb_page
from ..facebook import client as fb_client
from ..reports import charts
from . import keyboards as kb

HISTORY_MAX = 12


# ---------- Quyền & tiện ích ----------

def is_owner(update: Update) -> bool:
    owner = config.owner_chat_id_int()
    if owner is None:
        return True
    chat = update.effective_chat
    return chat is not None and chat.id == owner


async def _guard(update: Update) -> bool:
    if not is_owner(update):
        if update.effective_message:
            await update.effective_message.reply_text("Xin lỗi, bạn không có quyền dùng trợ lý này.")
        return False
    return True


async def _reply(update: Update, text: str, **kw):
    if update.effective_message:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, **kw)


def get_active_page(ctx: ContextTypes.DEFAULT_TYPE) -> dict | None:
    """Trang đang chọn; nếu chỉ có đúng 1 Trang thì tự chọn."""
    pid = ctx.chat_data.get("active_page_id")
    if pid is not None:
        p = store.get_page(pid)
        if p:
            return p
    pages = store.list_pages(only_enabled=True)
    if len(pages) == 1:
        ctx.chat_data["active_page_id"] = pages[0]["id"]
        return pages[0]
    return None


async def _need_page(ctx, chat_id: int) -> dict | None:
    """Trả về Trang đang chọn, hoặc mời chọn Trang rồi trả None."""
    page = get_active_page(ctx)
    if page:
        return page
    pages = store.list_pages(only_enabled=True)
    if not pages:
        await ctx.bot.send_message(
            chat_id, "Chưa có Trang nào. Vào trang quản trị <code>http://127.0.0.1:8760</code> để thêm.",
            parse_mode=ParseMode.HTML)
        return None
    await ctx.bot.send_message(chat_id, "Bạn muốn thao tác với Trang nào?",
                               reply_markup=kb.pages_list(pages, ctx.chat_data.get("active_page_id")))
    return None


# ---------- Lệnh cơ bản ----------

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    if config.owner_chat_id_int() is None and update.effective_chat:
        await _reply(update,
                     f"🔑 Mã Telegram của bạn là: <code>{update.effective_chat.id}</code>\n"
                     "Gửi mã này cho Claude (hoặc điền ở trang quản trị) để khoá quyền về mình bạn.")
    await _reply(
        update,
        "👋 Chào bạn! Mình là trợ lý số kiêm chuyên gia <b>quảng cáo Facebook</b> và <b>cầu lông</b>.\n\n"
        "Bạn cứ <b>nhắn thẳng câu hỏi</b>, ví dụ:\n"
        "• <i>Hôm qua Trang A tốn bao nhiêu quảng cáo?</i>\n"
        "• <i>Vợt cho người mới nên chọn loại nào?</i>\n"
        "• <i>Nên target ai để ra khách rẻ hơn?</i>\n\n"
        "Hoặc bấm menu 👇",
        reply_markup=kb.main_menu(),
    )


async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    page = get_active_page(ctx)
    tag = f"\n\n🏷 Trang đang chọn: <b>{page['name']}</b>" if page else ""
    await _reply(update, "Chọn việc bạn muốn làm:" + tag, reply_markup=kb.main_menu())


async def cmd_trangthai(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    await _reply(update, config.status_report())


async def cmd_ghinho(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Thêm nhanh một mẩu kiến thức vào 'bộ não' của bot."""
    if not await _guard(update):
        return
    text = (update.effective_message.text or "")
    body = text.split(" ", 1)[1].strip() if " " in text else ""
    if not body:
        await _reply(update, "Cách dùng: <code>/ghinho nội dung cần bot nhớ</code>\n"
                             "VD: <code>/ghinho Sân VMH Cẩm Phả mở 6h-23h, giá 80k/giờ</code>")
        return
    title = body.split("\n", 1)[0][:50]
    store.create_knowledge({"title": title, "content": body, "enabled": 1})
    n = len(store.list_knowledge(only_enabled=True))
    await _reply(update, f"🧠 Đã ghi vào bộ não! (tổng {n} mẩu kiến thức)\n"
                         "Bot sẽ tự dùng khi trả lời. Xem/sửa tại trang quản trị.")


async def cmd_kienthuc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    items = store.list_knowledge()
    if not items:
        await _reply(update, "Bộ não chưa có kiến thức nào. Thêm bằng <code>/ghinho ...</code> "
                             "hoặc ở trang quản trị.")
        return
    lines = [f"🧠 <b>Bộ não có {len(items)} mẩu:</b>", ""]
    for k in items[:20]:
        mark = "" if k.get("enabled") else "⏸ "
        lines.append(f"• {mark}{k.get('title') or (k.get('content') or '')[:40]}")
    await _reply(update, "\n".join(lines))


async def cmd_chontrang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    pages = store.list_pages(only_enabled=True)
    await _reply(update, "Chọn Trang:", reply_markup=kb.pages_list(pages, ctx.chat_data.get("active_page_id")))


# ---------- Trò chuyện tự do → trợ lý AI ----------

async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return

    pending = ctx.chat_data.get("awaiting_budget")
    if pending:
        await _handle_budget_input(update, ctx, pending)
        return

    if config.missing_for("ai"):
        await _reply(update, "🔧 Trợ lý AI chưa bật (thiếu khoá Claude). Bấm /trangthai để xem.")
        return

    question = update.effective_message.text
    await ctx.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    active = get_active_page(ctx)
    history = ctx.chat_data.get("history", [])
    try:
        answer = await asyncio.to_thread(ai_agent.ask_agent, question, active, history)
    except AIError as e:
        await _reply(update, f"🔧 {e}")
        return
    except Exception as e:  # noqa: BLE001
        await _reply(update, f"⚠️ Có lỗi khi hỏi trợ lý: {e}")
        return

    history = history + [{"role": "user", "content": question},
                         {"role": "assistant", "content": answer}]
    ctx.chat_data["history"] = history[-HISTORY_MAX:]
    await _reply(update, answer)


# ---------- Viết bài ----------

async def _make_and_send_draft(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, page: dict):
    if config.missing_for("ai"):
        await ctx.bot.send_message(chat_id, "🔧 Chưa bật AI (thiếu khoá Claude). Bấm /trangthai.")
        return
    await ctx.bot.send_chat_action(chat_id=chat_id, action="typing")
    try:
        text = await asyncio.to_thread(ai_content.generate_post, page)
    except AIError as e:
        await ctx.bot.send_message(chat_id, f"🔧 {e}")
        return
    draft_id = db.create_draft(page["id"], text)
    await ctx.bot.send_message(
        chat_id,
        f"✍️ <b>Bản nháp cho Trang «{page['name']}»:</b>\n\n{text}",
        parse_mode=ParseMode.HTML,
        reply_markup=kb.draft_actions(draft_id),
    )


async def cmd_vietbai(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    page = await _need_page(ctx, update.effective_chat.id)
    if page:
        await _make_and_send_draft(ctx, update.effective_chat.id, page)


# ---------- Báo cáo quảng cáo ----------

async def cmd_baocao(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    page = await _need_page(ctx, update.effective_chat.id)
    if page:
        await send_ads_report(ctx, update.effective_chat.id, page)


async def send_ads_report(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, page: dict, date_preset: str = "yesterday"):
    await ctx.bot.send_chat_action(chat_id=chat_id, action="typing")
    try:
        rows = await asyncio.to_thread(fb_ads.fetch_campaign_insights, page, date_preset)
    except fb_client.FacebookError as e:
        await ctx.bot.send_message(chat_id, f"[{page['name']}] {e.friendly}")
        return

    if date_preset in ("yesterday", "today"):
        from datetime import date
        try:
            db.save_ads_rows(page["id"], date.today().isoformat(), rows)
        except Exception:  # noqa: BLE001
            pass

    if not rows:
        await ctx.bot.send_message(chat_id, f"📊 [{page['name']}] Chưa có số liệu quảng cáo cho kỳ này.")
        return

    total_spend = sum(r["spend"] for r in rows)
    total_results = sum(r["results"] for r in rows)
    lines = [f"📊 <b>Báo cáo quảng cáo — {page['name']} ({date_preset})</b>",
             f"Tổng chi: <b>{total_spend:,.0f}đ</b> · Tổng kết quả: <b>{total_results}</b>", ""]
    for r in rows:
        lines.append(
            f"• <b>{r['campaign_name']}</b>\n"
            f"   chi {r['spend']:,.0f}đ · {r['results']} {r['result_type'] or 'kết quả'} · "
            f"CTR {r['ctr']:.2f}% · tần suất {r['frequency']:.1f}")
    await ctx.bot.send_message(chat_id, "\n".join(lines), parse_mode=ParseMode.HTML)

    chart = await asyncio.to_thread(
        charts.bars_chart, [r["campaign_name"] for r in rows], [r["spend"] for r in rows],
        f"Chi tiêu theo chiến dịch — {page['name']} (đ)", f"ads_{page['id']}.png")
    if chart:
        with open(chart, "rb") as fh:
            await ctx.bot.send_photo(chat_id, fh)

    try:
        advice = await asyncio.to_thread(ai_analysis.analyze_campaigns, rows, page["name"])
        await ctx.bot.send_message(chat_id, f"🧠 <b>Nhận định & định hướng</b>\n\n{advice}",
                                   parse_mode=ParseMode.HTML)
    except AIError:
        pass


# ---------- Quản lý chiến dịch ----------

async def cmd_quangcao(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    page = await _need_page(ctx, update.effective_chat.id)
    if page:
        await send_campaign_manager(ctx, update.effective_chat.id, page)


async def send_campaign_manager(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, page: dict):
    try:
        campaigns = await asyncio.to_thread(fb_ads.list_campaigns, page)
    except fb_client.FacebookError as e:
        await ctx.bot.send_message(chat_id, f"[{page['name']}] {e.friendly}")
        return
    if not campaigns:
        await ctx.bot.send_message(chat_id, f"[{page['name']}] Chưa có chiến dịch nào.")
        return
    from telegram import InlineKeyboardMarkup
    await ctx.bot.send_message(chat_id, f"🎯 <b>Chiến dịch của Trang «{page['name']}»</b>",
                               parse_mode=ParseMode.HTML)
    for c in campaigns:
        status = "🟢 đang chạy" if c.get("status") == "ACTIVE" else "⚪️ đã tắt"
        budget = f"{c['daily_budget']:,}đ/ngày" if c.get("daily_budget") else "—"
        await ctx.bot.send_message(
            chat_id, f"<b>{c['name']}</b>\n{status} · Ngân sách: {budget}",
            parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([kb.campaign_row(c)]))


# ---------- Báo cáo Trang ----------

async def cmd_trang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    page = await _need_page(ctx, update.effective_chat.id)
    if page:
        await send_page_report(ctx, update.effective_chat.id, page)


async def send_page_report(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, page: dict):
    await ctx.bot.send_chat_action(chat_id=chat_id, action="typing")
    try:
        snap = await asyncio.to_thread(fb_page.fetch_page_snapshot, page)
    except fb_client.FacebookError as e:
        await ctx.bot.send_message(chat_id, f"[{page['name']}] {e.friendly}")
        return
    if not snap:
        await ctx.bot.send_message(chat_id, f"[{page['name']}] Chưa lấy được số liệu Trang.")
        return
    lines = [f"📈 <b>Số liệu Trang «{page['name']}» hôm nay</b>", ""]
    for k, v in snap.items():
        lines.append(f"• {fb_page.metric_label(k)}: <b>{v:,.0f}</b>")
    lines.append("\n<i>Xu hướng theo tuần sẽ dày dữ liệu hơn sau vài ngày hệ thống tự lưu.</i>")
    await ctx.bot.send_message(chat_id, "\n".join(lines), parse_mode=ParseMode.HTML)

    series = db.page_metric_series(page["id"], "followers_count", limit_days=14)
    chart = await asyncio.to_thread(charts.line_chart, series,
                                    f"Người theo dõi — {page['name']}", f"follows_{page['id']}.png")
    if chart:
        with open(chart, "rb") as fh:
            await ctx.bot.send_photo(chat_id, fh)


# ---------- Ngân sách ----------

async def _handle_budget_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE, pending: dict):
    raw = (update.effective_message.text or "").replace(".", "").replace(",", "").replace("đ", "").strip()
    ctx.chat_data.pop("awaiting_budget", None)
    if not raw.isdigit():
        await _reply(update, "Mình chưa hiểu số tiền. Bạn gõ lại một con số, ví dụ 200000.")
        return
    amount = int(raw)
    if amount > config.ads_max_daily_budget_vnd:
        await _reply(update, f"⛔ {amount:,}đ vượt trần an toàn {config.ads_max_daily_budget_vnd:,}đ/ngày.")
        return
    await _reply(update, f"Xác nhận đặt ngân sách <b>{amount:,}đ/ngày</b> cho chiến dịch này?",
                 reply_markup=kb.confirm(f"setbudget_{amount}", pending["campaign"]))


# ---------- Bộ định tuyến nút bấm ----------

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    q = update.callback_query
    await q.answer()
    parts = (q.data or "").split(":")
    domain = parts[0]
    chat_id = q.message.chat_id

    if domain == "menu":
        await _route_menu(parts[1], ctx, chat_id)
    elif domain == "page":
        await _route_page(parts[1], parts[2], ctx, chat_id)
    elif domain == "post":
        await _route_post(parts[1], int(parts[2]), ctx, q)
    elif domain == "ads":
        await _route_ads(parts[1], parts[2], ctx, q)
    elif domain == "confirm":
        await _route_confirm(parts[1], parts[2], ctx, q)


async def _route_menu(action: str, ctx, chat_id: int):
    if action == "chontrang":
        pages = store.list_pages(only_enabled=True)
        await ctx.bot.send_message(chat_id, "Chọn Trang:",
                                   reply_markup=kb.pages_list(pages, ctx.chat_data.get("active_page_id")))
        return
    if action == "trangthai":
        await ctx.bot.send_message(chat_id, config.status_report(), parse_mode=ParseMode.HTML)
        return
    page = await _need_page(ctx, chat_id)
    if not page:
        return
    if action == "vietbai":
        await _make_and_send_draft(ctx, chat_id, page)
    elif action == "baocao":
        await send_ads_report(ctx, chat_id, page)
    elif action == "quangcao":
        await send_campaign_manager(ctx, chat_id, page)
    elif action == "trang":
        await send_page_report(ctx, chat_id, page)


async def _route_page(action: str, target: str, ctx, chat_id: int):
    if action == "select":
        page = store.get_page(int(target))
        if page:
            ctx.chat_data["active_page_id"] = page["id"]
            await ctx.bot.send_message(chat_id, f"🏷 Đã chọn Trang: <b>{page['name']}</b>",
                                       parse_mode=ParseMode.HTML, reply_markup=kb.main_menu())


async def _route_post(action: str, draft_id: int, ctx, q):
    chat_id = q.message.chat_id
    draft = db.get_draft(draft_id)
    if not draft:
        await ctx.bot.send_message(chat_id, "Bản nháp này không còn nữa.")
        return
    page = store.get_page(draft.get("page_ref")) if draft.get("page_ref") else None
    if action == "cancel":
        db.update_draft(draft_id, status="rejected")
        await q.edit_message_reply_markup(reply_markup=None)
        await ctx.bot.send_message(chat_id, "🗑 Đã bỏ bản nháp.")
    elif action == "regen":
        await q.edit_message_reply_markup(reply_markup=None)
        if page:
            await _make_and_send_draft(ctx, chat_id, page)
    elif action == "approve":
        if not page:
            await ctx.bot.send_message(chat_id, "Không rõ Trang của bản nháp này.")
            return
        try:
            post_id = await asyncio.to_thread(fb_posting.publish_draft, page, draft["text"], draft.get("image_path"))
            db.update_draft(draft_id, status="posted", fb_post_id=post_id)
            db.log_action("owner", "publish_post", post_id, "Đăng bài từ bản nháp", page_ref=page["id"])
            link = await asyncio.to_thread(fb_posting.post_permalink, page, post_id)
            await q.edit_message_reply_markup(reply_markup=None)
            msg = f"✅ Đã đăng lên Trang «{page['name']}»!"
            if link:
                msg += f"\n{link}"
            await ctx.bot.send_message(chat_id, msg)
        except fb_client.FacebookError as e:
            await ctx.bot.send_message(chat_id, e.friendly)


async def _route_ads(action: str, campaign_id: str, ctx, q):
    chat_id = q.message.chat_id
    if action == "pause":
        await ctx.bot.send_message(chat_id, "Bạn chắc chắn muốn <b>TẮT</b> chiến dịch này?",
                                   parse_mode=ParseMode.HTML, reply_markup=kb.confirm("pause", campaign_id))
    elif action == "enable":
        await ctx.bot.send_message(chat_id, "Bạn chắc chắn muốn <b>BẬT</b> chiến dịch này?",
                                   parse_mode=ParseMode.HTML, reply_markup=kb.confirm("enable", campaign_id))
    elif action == "budget":
        ctx.chat_data["awaiting_budget"] = {"campaign": campaign_id}
        await ctx.bot.send_message(
            chat_id, f"💰 Gõ số tiền/ngày (VND), tối đa {config.ads_max_daily_budget_vnd:,}đ. Ví dụ: 200000")


async def _route_confirm(action: str, target: str, ctx, q):
    chat_id = q.message.chat_id
    await q.edit_message_reply_markup(reply_markup=None)
    if action == "cancel":
        await ctx.bot.send_message(chat_id, "Đã huỷ.")
        return
    page = get_active_page(ctx)
    if not page:
        await ctx.bot.send_message(chat_id, "Chưa chọn Trang nên chưa thực hiện được. Bấm 🏷 Chọn Trang.")
        return
    try:
        if action == "pause":
            await asyncio.to_thread(fb_ads.set_campaign_status, page, target, False)
            await ctx.bot.send_message(chat_id, "⏸ Đã tắt chiến dịch. (Đã ghi nhật ký.)")
        elif action == "enable":
            await asyncio.to_thread(fb_ads.set_campaign_status, page, target, True)
            await ctx.bot.send_message(chat_id, "▶️ Đã bật chiến dịch. (Đã ghi nhật ký.)")
        elif action.startswith("setbudget_"):
            amount = int(action.split("_", 1)[1])
            await asyncio.to_thread(fb_ads.set_campaign_daily_budget, page, target, amount)
            await ctx.bot.send_message(chat_id, f"💰 Đã đặt ngân sách {amount:,}đ/ngày. (Đã ghi nhật ký.)")
    except fb_client.FacebookError as e:
        await ctx.bot.send_message(chat_id, e.friendly)
