"""Trợ lý AI trò chuyện trên Telegram — chuyên gia KÉP + hiểu nhiều Trang.

Vai: (1) chuyên gia quảng cáo Facebook + trợ lý số biết đọc số liệu các Trang;
(2) chuyên gia cầu lông (sản phẩm + kỹ thuật). Chủ nhắn câu hỏi bất kỳ, agent tự
chọn công cụ lấy đúng dữ liệu rồi trả lời.

An toàn: agent CHỈ có công cụ ĐỌC. Thao tác thay đổi (tắt/chỉnh quảng cáo) không ở
đây — phải qua nút xác nhận riêng ở phần bot.
"""
from __future__ import annotations

import json

from ..config import config
from .. import db, store
from ..facebook import ads as fb_ads
from ..facebook import page as fb_page
from ..facebook import client as fb_client
from .content import AIError, _client
from .knowledge import ADS_PLAYBOOK, BADMINTON_EXPERTISE

MAX_TOOL_ROUNDS = 6

TOOLS = [
    {
        "name": "lay_danh_sach_trang",
        "description": "Liệt kê các Trang Facebook đang quản lý (tên + trạng thái sẵn sàng). "
                       "Dùng khi cần biết có những Trang nào hoặc chủ hỏi 'so sánh giữa các trang'.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "lay_so_lieu_quang_cao",
        "description": "Số liệu quảng cáo theo từng chiến dịch của MỘT Trang (chi tiêu, hiển thị, "
                       "click, CTR, CPC, tần suất, kết quả).",
        "input_schema": {
            "type": "object",
            "properties": {
                "ten_trang": {"type": "string", "description": "Tên Trang cần xem. Bỏ trống = Trang đang chọn."},
                "khoang_thoi_gian": {"type": "string",
                    "enum": ["today", "yesterday", "last_7d", "last_14d", "last_30d", "this_month"],
                    "description": "Mốc thời gian, mặc định 'yesterday'."},
            },
        },
    },
    {
        "name": "lay_danh_sach_chien_dich",
        "description": "Danh sách chiến dịch của một Trang kèm trạng thái và ngân sách/ngày.",
        "input_schema": {"type": "object", "properties": {
            "ten_trang": {"type": "string", "description": "Tên Trang. Bỏ trống = Trang đang chọn."}}},
    },
    {
        "name": "lay_so_lieu_trang_hom_nay",
        "description": "Số liệu Trang hiện tại: người theo dõi, lượt thích, hiển thị, tiếp cận, tương tác.",
        "input_schema": {"type": "object", "properties": {
            "ten_trang": {"type": "string", "description": "Tên Trang. Bỏ trống = Trang đang chọn."}}},
    },
    {
        "name": "lay_lich_su_trang",
        "description": "Chuỗi số liệu Trang theo thời gian (đã lưu) để so sánh xu hướng.",
        "input_schema": {"type": "object", "properties": {
            "ten_trang": {"type": "string"},
            "chi_so": {"type": "string",
                "enum": ["followers_count", "page_impressions_unique", "page_post_engagements"]},
            "so_ngay": {"type": "integer"}},
            "required": ["chi_so"]},
    },
    {
        "name": "lay_nhat_ky_thay_doi",
        "description": "Nhật ký thay đổi quảng cáo gần đây (ai tắt/chỉnh gì, khi nào).",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def _safe(fn):
    try:
        return fn()
    except fb_client.FacebookError as e:
        return {"loi": e.friendly}
    except Exception as e:  # noqa: BLE001
        return {"loi": f"Không lấy được dữ liệu: {e}"}


def _resolve_page(name: str | None, active_page: dict | None) -> dict | None:
    """Chọn Trang theo tên; nếu không có tên thì dùng Trang đang chọn."""
    if name:
        for p in store.list_pages():
            if p["name"].strip().lower() == name.strip().lower():
                return p
        # khớp gần đúng
        for p in store.list_pages():
            if name.strip().lower() in p["name"].strip().lower():
                return p
    return active_page


def _dispatch(name: str, args: dict, active_page: dict | None) -> str:
    if name == "lay_danh_sach_trang":
        pages = [{"ten": p["name"],
                  "co_quang_cao": bool(p.get("fb_ad_account_id") and p.get("fb_ads_token")),
                  "co_dang_bai": bool(p.get("fb_page_id") and p.get("fb_page_token"))}
                 for p in store.list_pages()]
        return json.dumps(pages, ensure_ascii=False)

    page = _resolve_page(args.get("ten_trang"), active_page)
    if page is None and name != "lay_nhat_ky_thay_doi":
        return json.dumps({"loi": "Chưa chọn Trang nào. Hãy nói rõ tên Trang, hoặc chọn Trang trong menu."},
                          ensure_ascii=False)

    if name == "lay_so_lieu_quang_cao":
        preset = args.get("khoang_thoi_gian", "yesterday")
        data = _safe(lambda: fb_ads.fetch_campaign_insights(page, preset))
        return json.dumps({"trang": page["name"], "khoang": preset, "chien_dich": data}, ensure_ascii=False)

    if name == "lay_danh_sach_chien_dich":
        return json.dumps({"trang": page["name"], "chien_dich": _safe(lambda: fb_ads.list_campaigns(page))},
                          ensure_ascii=False)

    if name == "lay_so_lieu_trang_hom_nay":
        data = _safe(lambda: fb_page.fetch_page_snapshot(page))
        if isinstance(data, dict) and "loi" not in data:
            data = {fb_page.metric_label(k): v for k, v in data.items()}
        return json.dumps({"trang": page["name"], "so_lieu": data}, ensure_ascii=False)

    if name == "lay_lich_su_trang":
        metric = args.get("chi_so", "followers_count")
        days = int(args.get("so_ngay", 14))
        series = db.page_metric_series(page["id"], metric, limit_days=days)
        return json.dumps({"trang": page["name"], "chi_so": fb_page.metric_label(metric),
                           "du_lieu": series}, ensure_ascii=False)

    if name == "lay_nhat_ky_thay_doi":
        return json.dumps(db.recent_actions(10), ensure_ascii=False)

    return json.dumps({"loi": f"Không có công cụ tên {name}"}, ensure_ascii=False)


def _system(active_page: dict | None, knowledge: str = "") -> str:
    active = f"Trang đang chọn hiện tại: «{active_page['name']}». " if active_page else \
             "Hiện chưa chọn Trang cụ thể nào. "
    kb = f"\n\nKIẾN THỨC RIÊNG CỦA VMH (dùng khi liên quan, coi là sự thật chính xác):\n{knowledge}" if knowledge else ""
    return f"""Bạn là trợ lý số kiêm CHUYÊN GIA cho một chủ doanh nghiệp sân cầu lông (KHÔNG rành
kỹ thuật), trò chuyện qua Telegram. Luôn trả lời tiếng Việt, ngắn gọn, đời thường, emoji nhẹ.

Bạn có BA vai, tuỳ câu hỏi mà dùng:
1) TRỢ LÝ SỐ LIỆU: khi hỏi về số liệu Facebook (tương tác, tiếp cận, người theo dõi, quảng cáo,
   chi phí, chiến dịch...), DÙNG CÔNG CỤ lấy số thật rồi trả lời — không bịa số. {active}
   Chủ quản lý NHIỀU Trang; nếu câu hỏi không nói rõ Trang nào thì dùng Trang đang chọn, hoặc
   hỏi lại/khi cần thì liệt kê các Trang. Có thể so sánh giữa các Trang.
2) CHUYÊN GIA QUẢNG CÁO FACEBOOK: đọc số liệu và ĐỊNH HƯỚNG chạy hiệu quả (nhắm tệp, phễu khách,
   giữ/tăng/giảm/tắt, đổi nội dung, nhắm lại). Bám số liệu thật, nêu con số cụ thể.
3) CHUYÊN GIA CẦU LÔNG: tư vấn sản phẩm (vợt, dây, giày, phụ kiện) và kỹ thuật/huấn luyện như một HLV.

Bạn CHỈ xem và tư vấn; muốn tắt/chỉnh chiến dịch thì hướng dẫn chủ bấm nút lệnh, KHÔNG tự làm.

{ADS_PLAYBOOK}

{BADMINTON_EXPERTISE}{kb}"""


def ask_agent(question: str, active_page: dict | None = None, history: list | None = None) -> str:
    client = _client()
    messages = list(history or [])
    messages.append({"role": "user", "content": question})
    kb = store.knowledge_text(question)

    for _ in range(MAX_TOOL_ROUNDS):
        resp = client.messages.create(
            model=config.anthropic_model,
            max_tokens=1300,
            system=_system(active_page, kb),
            tools=TOOLS,
            messages=messages,
        )
        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    out = _dispatch(block.name, block.input or {}, active_page)
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": out})
            messages.append({"role": "user", "content": results})
            continue
        return "".join(b.text for b in resp.content if b.type == "text").strip()

    return "Xin lỗi, câu này hơi phức tạp nên mình chưa tổng hợp được. Bạn hỏi cụ thể hơn giúp mình nhé."


# Giữ tương thích cho selftest cũ
def dispatch(name: str, args: dict) -> str:
    return _dispatch(name, args, None)
