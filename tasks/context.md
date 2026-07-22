# Bối cảnh dự án — Trợ lý tự động (Facebook + Zalo + Telegram + alobo)

## Chủ dự án
Chủ sân thể thao (cầu lông — thư mục "VMH BADMINTON" trên máy), tự chạy quảng cáo Facebook.
Không đọc được code, không tự sửa kỹ thuật. Mọi phần kỹ thuật do Claude lo.

## Mục tiêu hệ thống
Một trợ lý số chạy 24/7, điều khiển hoàn toàn qua Telegram, làm 4 việc:
1. Tự viết nội dung + đăng bài Facebook Page (có bước duyệt tay qua Telegram).
2. Báo cáo quảng cáo theo chiến dịch + gợi ý tối ưu + cho phép tắt/bật/chỉnh ngân sách từ Telegram.
3. Báo cáo hiệu quả Trang Facebook theo tuần/tháng.
4. (GĐ2) Gửi tin Zalo soạn sẵn + tự đọc lịch sân alobo và báo nhóm Zalo khi có giờ trống.

## Quyết định đã chốt (xem decisions.md)
- Nơi chạy: thuê VPS nhỏ 24/7 (phát triển ở máy Mac trước).
- Đăng FB: duyệt trước qua Telegram rồi mới đăng.
- Lộ trình: Giai đoạn 1 = Facebook (chắc chắn); Giai đoạn 2 = Zalo + alobo.
- Quảng cáo: tài khoản của chính chủ → đọc + điều khiển được.
- Zalo: dùng tài khoản phụ + SIM riêng.
- alobo: chủ sân → đăng nhập tài khoản chủ sân đọc lịch của chính mình.

## Nền công nghệ
- Python 3.9.6 (có sẵn máy). Node ở ~/.local/node/bin (cho Zalo zca-js ở GĐ2).
- Bot Telegram: python-telegram-bot (long polling).
- Hẹn giờ: APScheduler. Kho dữ liệu: SQLite. Biểu đồ: matplotlib.
- AI: Claude API (Haiku 4.5) — viết nội dung + phân tích quảng cáo.
- Bí mật: file .env (không commit).

## Trạng thái
Kế hoạch đã được duyệt (16/7/2026). Đang dựng khung code Giai đoạn 1.
Kế hoạch gốc: ~/.claude/plans/luminous-conjuring-ullman.md

## 20/7/2026 — Bot "chưa thông minh" khi hỏi sân trống (✅ ĐÃ XONG, lên VPS, test thật đạt — xem HandOver)
Chủ phản ánh: hỏi "18:00 xem có lịch trống ở Cẩm Phả không" → bot CHỈ đưa link đặt sân,
KHÔNG báo lịch thật. Yêu cầu: chăm sóc khách đặt lên hàng đầu, bám đuổi tới khi đặt xong sân.

NGUYÊN NHÂN (đã soi code): `app/ai/badminton.py::_live_schedule_context` chỉ đọc lịch thật khi
câu khách chứa 1 trong các cụm cứng `_AVAIL_KEYS` ("sân trống", "đặt sân"...). Câu "có LỊCH TRỐNG"
KHÔNG khớp cụm nào ("lịch sân"/"sân trống" đều không trúng) → bot không đọc lịch → rơi về câu chung
"muốn đặt thì đây là link" (đúng luật prompt: khách muốn đặt → luôn đưa link alobo). Thêm nữa: kể cả
khi khớp, bot đổ CẢ NGÀY chứ không trả lời ĐÚNG GIỜ khách hỏi (18:00).

HƯỚNG SỬA (chờ chủ chốt cách "bám đuổi"):
1. Thay bộ "từ khoá cứng" bằng bộ "hiểu ý" dùng AI (gọi Haiku nhanh/rẻ): mỗi tin tự rút ra
   {có hỏi sân/đặt sân?, cơ sở nào, hôm nay/mai, mấy giờ}. Bỏ luôn `_match_venues`/dò ngày cứng.
2. Trả lời ĐÚNG GIỜ hỏi: 18:00 CS1 còn/không, CS2 còn/không; nếu kín → gợi khung gần nhất + cơ sở khác.
3. Prompt: ưu tiên số 1 = CHỐT SÂN — xác nhận giờ + đưa đúng link + hướng dẫn ngắn + hỏi lại
   "anh đặt được chưa, cần chỉ từng bước không". Bám trong mạch chat (KHÔNG tự spam ngoài → né khoá số).
