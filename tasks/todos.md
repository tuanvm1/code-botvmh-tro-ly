# Việc cần làm — Trợ lý tự động VMH (cập nhật 22/7/2026)

## ✅ ĐÃ XONG & đang chạy thật trên VPS
- **Bot Zalo = AGENT thông minh** (nói với khách): tự tra lịch sân + kiến thức, xử câu hỏi nhiều ý cùng lúc,
  NHỚ từng khách (cá nhân hoá), và có **luật bảo mật** (từ chối lộ chỉ dẫn/cấu trúc nội bộ, chống moi tin).
- **Cuối ngày ~21:30 bot tự gửi CHỦ bản tóm tắt khách** qua Telegram (ai muốn đặt/mua chưa chốt, phàn nàn…).
  Bot KHÔNG tự nhắn khách khi họ im (né khoá Zalo).
- **Bộ não bằng Obsidian**: chủ sửa ghi chú trong kho `Documents/bonaoVMH` → tự đồng bộ lên bot (Mac tự đẩy →
  GitHub `tuanvm1/bonaobotVMH` → máy chủ tự kéo mỗi ~3 phút). Không cần bấm nút.
- **Đọc lịch sân alobo THẬT** khi khách hỏi + canh sân báo nhóm Zalo (10h/14h hôm nay, 22h ngày mai).
- **Chịu tải nhiều người cùng lúc**: web server đa-luồng (waitress) + HÀNG ĐỢI AI (8 lời gọi/lượt, dư thì xếp
  hàng xử lý lần lượt, không nghẽn). Đã test 30 câu đồng thời → 30/30 OK.
- **Chạy trong MỌI nhóm bot tham gia** (không cần khai báo): trả lời khi được @tag. Báo sân tự động gửi các nhóm
  trong `group_ids` (hiện: "vmh bot test" + "Nhóm thuê sân VMH - Giao lưu cầu lông"). Tin gửi chung xưng "anh/chị";
  bot gọi đúng anh/chị khi biết tên/giới tính.
- Chạy 24/7 trên VPS Việt Nam (systemd `trolybot`). Bộ tự kiểm tra **13/13**. Đã qua nhiều vòng review đối kháng.
- **🛒 KHO SẢN PHẨM (bán hàng)**: chủ tải file Excel (xuất từ Sapo) ở trang quản trị → bot TỰ đọc, hiểu sản phẩm/giá
  → dùng công cụ `tra_cuu_san_pham` tư vấn ĐÚNG hàng ĐANG CÓ + giá thật để CHỐT ĐƠN. Đã nạp sẵn file 22/7
  (161 SP / 454 phiên bản). Luật bán hàng: (1) tạo KHAN HIẾM, (2) tư vấn 2-3 lượt → ép ĐƯA SỐ 0339.288.166,
  (3) trả lời NGẮN. Tải file mới = thay MỚI toàn bộ kho (có/không còn trong file = còn/ngừng bán). Nếu file Sapo
  sau này có cột "Tồn kho" → bot tự đọc số tồn để tư vấn "còn N cái".

## 👉 VIỆC CHỦ NÊN LÀM (theo thứ tự nên làm trước)
0. **Vài ngày/lần: tải file Excel sản phẩm mới** ở trang quản trị (ô "🛒 Kho sản phẩm") để cập nhật kho.
   Có thể đổi Số điện thoại tư vấn ở ngay ô đó.
1. **Điền số liệu THẬT vào kho Obsidian `bonaoVMH`** — quan trọng nhất để bot trả lời đúng:
   giá sân, khuyến mãi đang chạy, hỏi-đáp hay gặp. (Sản phẩm/giá đã có KHO SẢN PHẨM lo; kho Obsidian
   dùng cho phần còn lại. Sửa xong tự lên bot.)
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
