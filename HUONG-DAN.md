# Hướng dẫn dùng hệ thống (dành cho chủ sân — không cần biết kỹ thuật)

Toàn bộ phần kỹ thuật đã dựng xong và chạy thử đạt. Bạn chỉ cần **điền vài "chìa khoá"**
vào **trang quản trị** (một web đơn giản chạy trên máy bạn), không phải đụng file kỹ thuật.

## Trang quản trị ở đâu?
Mở trình duyệt, vào: **http://127.0.0.1:8760**

Ở đó bạn thấy:
- Thanh trên cùng: **Bật / Tắt / 🔄 Khởi động lại** bot. Mỗi khi sửa chìa khoá/tài khoản xong,
  bấm **🔄 Khởi động lại** là hệ thống nạp cái mới và chạy tiếp — **không cần Claude, không cần code lại**.
- **Cấu hình chung**: chìa khoá Telegram, Claude...
- **Các Trang Facebook**: thêm/sửa/xoá bao nhiêu Trang cũng được.
- **Sân alobo**: thêm/sửa/xoá nhiều sân (mỗi sân tài khoản + khung giờ riêng).
- **Tài khoản Zalo**: thêm/sửa/xoá nhiều tài khoản (đổi tài khoản chỉ cần sửa ở đây).

> Nếu mở không lên nghĩa là hệ thống chưa bật — nhắn Claude "bật hệ thống" là được.
> (Chỉ cần chạy một lệnh `run_admin.py` là có cả trang quản trị lẫn bot.)

---

## Đã xong (Claude làm sẵn)
- ✅ Bot Telegram **@vmhfbbot** đã nối, khoá riêng cho bạn.
- ✅ Khoá AI (Claude) đã cắm — trợ lý trò chuyện + viết bài + phân tích được.
- ✅ Đã tạo sẵn 1 Trang "Sân VMH — Trang chính" (điền sẵn giọng điệu, chỉ thiếu chìa khoá Facebook).

## Việc cần bạn làm (khi rảnh) — lấy chìa khoá Facebook

Đây là phần duy nhất cần bạn, vì Claude không tự đăng nhập Facebook giùm được.
Claude sẽ **chỉ bạn từng bước** khi bạn sẵn sàng. Tóm tắt cần lấy:

**Cho mỗi Trang muốn dùng:**
1. **ID Trang** + **Token đăng bài** (loại không hết hạn) → để đăng bài & xem số liệu Trang.
2. **ID tài khoản quảng cáo** (act_...) + **Token quảng cáo** (System User, không hết hạn) → để báo cáo & điều khiển quảng cáo.

Lấy xong, bạn **dán vào ô tương ứng của Trang đó trong trang quản trị**, bấm Lưu, rồi bấm
**"Kiểm tra"** — nếu hiện "OK ✔" là chuẩn. Muốn thêm Trang thứ 2, 3... bấm **"➕ Thêm Trang mới"**.

---

## Dùng trợ lý (Telegram) như thế nào
- **Nhắn thẳng câu hỏi**, ví dụ:
  - *"Vợt cho người mới nên chọn loại nào?"* (chuyên gia cầu lông)
  - *"Hôm qua Trang X tốn bao nhiêu quảng cáo?"* (số liệu)
  - *"Nên target ai để ra khách rẻ hơn?"* (định hướng quảng cáo)
- Gõ **/menu** để thấy nút: 🏷 Chọn Trang · ✍️ Viết bài · 📊 Báo cáo quảng cáo · 🎯 Quản lý chiến dịch · 📈 Báo cáo Trang · ⚙️ Trạng thái.
- Có nhiều Trang thì bấm **🏷 Chọn Trang** trước, rồi mọi thao tác sẽ áp cho Trang đó.
- Mỗi sáng tự nhận: báo cáo quảng cáo + (nếu bật) bản nháp bài để bấm Đăng/Viết lại.

## An toàn
- Chỉ mình bạn (đúng Telegram của bạn) điều khiển được bot.
- Lệnh tắt/chỉnh quảng cáo luôn phải **bấm xác nhận lần 2**, và có **trần ngân sách** bot không được vượt.
- Mọi thay đổi đều ghi **nhật ký**.
