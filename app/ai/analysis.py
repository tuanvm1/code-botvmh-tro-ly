"""Dùng Claude phân tích số liệu quảng cáo và gợi ý tối ưu.

Chốt an toàn: chỉ gợi ý dứt khoát (tắt/giảm) khi ĐỦ dữ liệu
(chi tiêu ≥ ngưỡng và đã chạy đủ số ngày). Gợi ý chỉ là ý kiến tư vấn,
mọi quyết định thực thi vẫn cần chủ sân bấm nút xác nhận.
"""
from __future__ import annotations

from ..config import config
from .content import AIError, _client
from .knowledge import ADS_PLAYBOOK


def analyze_campaigns(rows: list[dict], page_name: str = "") -> str:
    """Nhận danh sách số liệu chiến dịch, trả về phân tích + gợi ý (tiếng Việt)."""
    if not rows:
        return "Chưa có dữ liệu quảng cáo hôm nay để phân tích."
    client = _client()
    who = f" của Trang «{page_name}»" if page_name else ""

    lines = []
    for r in rows:
        lines.append(
            f"- {r.get('campaign_name','(không tên)')}: chi {r.get('spend',0):,.0f}đ, "
            f"hiển thị {r.get('impressions',0):,}, click {r.get('clicks',0):,}, "
            f"CTR {r.get('ctr',0):.2f}%, CPC {r.get('cpc',0):,.0f}đ, "
            f"tần suất {r.get('frequency',0):.2f}, "
            f"kết quả {r.get('results',0)} {r.get('result_type','')}"
        )
    data_block = "\n".join(lines)

    prompt = f"""Bạn là CHUYÊN GIA quảng cáo Facebook, đang tư vấn cho một chủ doanh nghiệp
Việt Nam KHÔNG rành kỹ thuật. Hãy giải thích thật đời thường, ngắn gọn.

{ADS_PLAYBOOK}

Số liệu quảng cáo hôm nay{who} (theo từng chiến dịch):
{data_block}

Ngưỡng an toàn khi khuyên: chỉ khuyên TẮT/GIẢM một chiến dịch khi nó đã chi
ít nhất {config.ads_min_spend_for_advice_vnd:,}đ và chạy đủ dữ liệu; nếu chưa đủ
dữ liệu thì nói "cần theo dõi thêm", đừng vội kết luận.

Hãy trả về:
1. Nhận xét tổng quan 1–2 câu (hôm nay tốt/xấu chỗ nào).
2. Với mỗi chiến dịch: một dòng ngắn "nên làm gì" (giữ nguyên / theo dõi thêm /
   nên xem lại / nên tắt), kèm lý do dựa trên con số.
3. ĐỊNH HƯỚNG rõ nhất cho hôm nay/ngày tới (ví dụ: đổi nội dung, chỉnh vị trí/tệp,
   tạo tệp nhắm lại, tăng/giảm ngân sách bao nhiêu) — bám số liệu, cụ thể.

Viết gọn, không thuật ngữ trống rỗng. Dùng emoji nhẹ. Không quá 14 dòng."""

    msg = client.messages.create(
        model=config.anthropic_model,
        max_tokens=900,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if b.type == "text").strip()
