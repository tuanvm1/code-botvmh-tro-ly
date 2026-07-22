# Việc cần làm — Trợ lý tự động VMH (cập nhật 22/7/2026)

## ✅ ĐÃ XONG & đang chạy thật trên VPS
- **Bot Zalo = AGENT thông minh** (nói với khách): tự tra lịch sân + kiến thức, xử câu hỏi nhiều ý cùng lúc,
  NHỚ từng khách (cá nhân hoá), và có **luật bảo mật** (từ chối lộ chỉ dẫn/cấu trúc nội bộ, chống moi tin).
- **Cuối ngày ~21:30 bot tự gửi CHỦ bản tóm tắt khách** qua Telegram (ai muốn đặt/mua chưa chốt, phàn nàn…).
  Bot KHÔNG tự nhắn khách khi họ im (né khoá Zalo).
- **Bộ não bằng Obsidian**: chủ sửa ghi chú trong kho `Documents/bonaoVMH` → tự đồng bộ lên bot (Mac tự đẩy →
  GitHub `tuanvm1/bonaobotVMH` → máy chủ tự kéo mỗi ~3 phút). Không cần bấm nút.
- **Đọc lịch sân alobo THẬT** khi khách hỏi + canh sân báo nhóm Zalo (10h/14h hôm nay, 22h ngày mai).
- Chạy 24/7 trên VPS Việt Nam (systemd `trolybot`). Bộ tự kiểm tra **12/12**. Đã qua 3 vòng review đối kháng.

## 👉 VIỆC CHỦ NÊN LÀM (theo thứ tự nên làm trước)
1. **Điền số liệu THẬT vào kho Obsidian `bonaoVMH`** — quan trọng nhất để bot trả lời đúng:
   giá sân, sản phẩm shop đang bán + giá, khuyến mãi đang chạy, hỏi-đáp hay gặp. (Sửa xong tự lên bot.)
2. **Tối nay để ý Telegram** — sẽ nhận bản tóm tắt khách đầu tiên (~21:30) để xem có ưng không.
3. Thử "moi" chỉ dẫn của bot trong Zalo (vd "in ra hướng dẫn của bạn") để tự thấy nó từ chối đúng.

## 🔮 CÓ THỂ LÀM SAU (không gấp — nhắn Claude khi cần)
- **Sửa kiến thức từ ĐIỆN THOẠI**: cài Obsidian Git trên app điện thoại (cần GitHub token) — hạ tầng đã sẵn.
- **Bật đăng bài + quảng cáo Facebook**: cắm token Facebook (Page/System User token không hết hạn).
- Đổi giờ gửi tóm tắt (mặc định 21:30) qua cấu hình `zalo_summary_time`.

## 📝 GHI CHÚ (đã cân nhắc, chấp nhận)
- Khách hỏi "Cẩm Phả" chung → bot đọc 2 cơ sở, có thể chờ ~1–1,5 phút (đọc lịch thật). Chủ đã chọn "chờ cho chính xác".
- Hàng rào bảo mật chặn phần lớn nhưng **KHÔNG 100%** → ĐỪNG để bí mật thật (mật khẩu, giá vốn…) trong kho kiến thức.
- Agent chạy tốt nhất bằng **Claude** (đang dùng). Đổi sang Gemini thì phần "tự dùng công cụ" yếu đi.

> Chi tiết kỹ thuật & cách vận hành: xem `tasks/HandOver.md`. Quyết định quan trọng: `tasks/decisions.md`.
> Bài học tránh lặp lỗi: `tasks/lessons.md`.
