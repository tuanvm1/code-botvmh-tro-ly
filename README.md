# Trợ lý tự động (Facebook + Zalo + Telegram + alobo)

Trợ lý số chạy 24/7, điều khiển qua Telegram, cho chủ sân thể thao. Hỗ trợ **nhiều Trang
Facebook** (5–10), có **trang quản trị localhost** để tự nhập chìa khoá.

## Tình trạng
- **Giai đoạn 1 (Facebook) — XONG bộ khung đa-Trang + quản trị, selftest 6/6.** Telegram + AI
  đã chạy thật; chờ token Facebook để chạy thật phần đăng bài/quảng cáo.
- Giai đoạn 2 (Zalo + alobo) — làm sau.

## Tính năng
1. **Trợ lý AI trò chuyện (Telegram)** — chuyên gia KÉP: quảng cáo Facebook + cầu lông (sản phẩm & kỹ thuật). Hỏi số liệu bất kỳ Trang, định hướng target/tối ưu.
2. **Tự viết bài + duyệt qua Telegram** rồi đăng lên Trang (theo giọng điệu từng Trang).
3. **Báo cáo quảng cáo theo chiến dịch** + gợi ý; tắt/bật/đổi ngân sách bằng nút (xác nhận 2 bước, trần an toàn, nhật ký).
4. **Báo cáo hiệu quả Trang** theo thời gian (tự lưu lịch sử mỗi ngày, theo từng Trang).
5. **Trang quản trị localhost** (127.0.0.1:8760) — nhập/sửa chìa khoá, thêm/xoá Trang, kiểm tra token.

## Cấu trúc
```
main.py               # khởi động bot + hẹn giờ
run_admin.py          # khởi động trang quản trị localhost
selftest.py           # tự kiểm tra (không cần token) — kỳ vọng 6/6
app/store.py          # kho cấu hình chung + danh sách Trang (SQLite)
app/config.py         # đọc cấu hình chung từ kho
app/db.py             # SQLite đa-Trang: số liệu (page_ref), nhật ký, bản nháp
app/facebook/         # client, posting, ads, page — nhận ngữ cảnh từng Trang
app/ai/               # content, analysis, agent (chuyên gia kép), knowledge, badminton
app/reports/charts.py # biểu đồ
app/bot/              # core, handlers, keyboards, jobs (đa-Trang)
app/admin/server.py   # trang quản trị Flask
tasks/                # context, todos, decisions, lessons, HandOver
```

## Chạy
```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python selftest.py       # tự kiểm tra (6/6)
./.venv/bin/python run_admin.py &     # trang quản trị → điền chìa khoá
./.venv/bin/python main.py            # chạy bot
```
Điền chìa khoá tại **http://127.0.0.1:8760** (xem HUONG-DAN.md).
