"""Dùng Claude viết nội dung bài đăng Facebook đúng giọng điệu từng Trang."""
from __future__ import annotations

from typing import Optional

from ..config import config


class AIError(Exception):
    pass


def _client():
    if not config.anthropic_api_key:
        raise AIError("Chưa có khoá Claude API. Vào trang quản trị điền giúp.")
    try:
        import anthropic
    except ImportError:
        raise AIError("Chưa cài thư viện anthropic. Chạy: pip install anthropic")
    return anthropic.Anthropic(api_key=config.anthropic_api_key)


def generate_post(page: dict, topic: Optional[str] = None, extra: str = "") -> str:
    """Viết một bài đăng Facebook cho một Trang cụ thể (theo giọng điệu của Trang)."""
    client = _client()
    name = page.get("business_name") or page.get("name") or "Doanh nghiệp"
    desc = page.get("business_desc") or ""
    tone = page.get("brand_tone") or "Thân thiện, gần gũi."
    topic_line = f"Chủ đề hôm nay: {topic}." if topic else "Tự chọn một chủ đề phù hợp, hấp dẫn."
    prompt = f"""Bạn là người viết nội dung mạng xã hội cho doanh nghiệp Việt Nam.

Thông tin doanh nghiệp:
- Tên: {name}
- Mô tả: {desc}
- Giọng điệu thương hiệu: {tone}

Nhiệm vụ: viết MỘT bài đăng Facebook tiếng Việt để đăng lên Trang.
{topic_line}
{extra}

Yêu cầu:
- Ngắn gọn, tự nhiên, dễ đọc trên điện thoại (khoảng 3–6 dòng).
- Có một câu kêu gọi hành động (đặt sân/inbox/gọi...).
- Thêm 3–6 hashtag liên quan ở cuối.
- Dùng emoji vừa phải cho sinh động.
- CHỈ trả về nội dung bài đăng, không giải thích gì thêm."""
    msg = client.messages.create(
        model=config.anthropic_model,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in msg.content if block.type == "text").strip()
