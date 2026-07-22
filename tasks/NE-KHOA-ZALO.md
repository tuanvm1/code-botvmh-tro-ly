# Né khóa tài khoản Zalo (zca-js) — cơ chế rủi ro & cách phòng

Nguồn: tra cứu 18/7/2026 (help.zalo.me, tdung.gitbook.io/zca-js, cộng đồng Zalo Marketing VN).
Bối cảnh của ta: dùng tài khoản PHỤ đăng vào NHÓM của chính khách quen + tự trả lời khi được hỏi
→ đây là kịch bản RỦI RO THẤP hơn nhiều so với spam người lạ. Rủi ro lớn nhất còn lại là "dấu vết bot".

## Cơ chế Zalo hay dùng để khóa (cao → thấp)
1. **Dùng tool bên thứ 3 (zca-js) — cờ đỏ nền, luôn tồn tại.** → dùng nick PHỤ, coi như có thể mất.
2. **Gửi nội dung GIỐNG HỆT nhau hàng loạt.** → hệ thống tự ĐỔI NHẸ câu chữ mỗi tin (đã làm).
3. **Tốc độ gửi dồn dập / đều như máy.** → giãn ngẫu nhiên + giới hạn giờ/ngày (đã làm).
4. **Bị "Báo xấu" nhiều.** → chỉ đăng vào nhóm khách quen; xin phép trưởng nhóm trước.
5. **Kết bạn / mời nhóm ồ ạt.** → hệ thống KHÔNG tự kết bạn/mời nhóm; chỉ đăng vào nhóm đã tham gia.
6. **Hành vi giống bot (24/7, không tương tác người thật).** → chỉ chạy khung giờ ngày; chủ nên thỉnh
   thoảng vẫn dùng nick như người thật (thả tim, xem tin).
7. **Nhiều nick / đổi thiết bị / đổi IP bất thường.** → giữ đăng nhập ổn định một chỗ.
8. **SIM không chính chủ / số bị thu hồi.** → dùng SIM chính chủ, số sạch.
9. **Nick mới thao tác mạnh ngay.** → "làm ấm" nick 7–14 ngày trước khi chạy.
10. **Gửi link lạ / nội dung nhạy cảm.** → dễ khóa VĨNH VIỄN; tuyệt đối tránh.

## Van an toàn đã cài (sửa được ở trang quản trị → Kết nối Zalo)
- Giãn tối thiểu giữa 2 tin + cộng NGẪU NHIÊN (mặc định 45s + tới 60s) → không đều như máy.
- Tối đa tin/giờ (15) và /ngày (100).
- Chỉ gửi trong khung giờ 7–22h (không chạy đêm).
- Tự ĐỔI NHẸ câu mở/đóng mỗi tin thông báo (spin content).
- Tin TRẢ LỜI là phản ứng theo ngữ cảnh (ít bị report) + delay giống người 2–8s.
- Chỉ đăng vào nhóm tài khoản ĐÃ tham gia; không kết bạn/mời nhóm tự động.

## Dấu hiệu SẮP bị khóa — thấy là DỪNG tự động vài ngày
- Tin gửi đi không có "đã gửi", hoặc hiện "hiện tại tôi không muốn nhận tin nhắn".
- Đột nhiên không kết bạn / không gửi ảnh được (phạt nhẹ 24–48h).
- Có thông báo "tài khoản tạm vô hiệu hóa" đòi xác thực chính chủ, hoặc cảnh báo ghim về SĐT.

## Phục hồi
- Tạm khóa (24–48h, có khi 7 ngày): NGỪNG hành vi gây ra, để nhịp về bình thường thường tự gỡ;
  xác thực CCCD chính chủ khi được yêu cầu.
- Khóa vĩnh viễn (tái phạm/nội dung nặng): gần như không gỡ được → lập nick mới (dùng lại số cũ sau 48h).

## Việc chủ nên tự làm để an toàn
- Dùng SIM chính chủ + nick PHỤ, xác thực CCCD; "làm ấm" 7–14 ngày.
- Báo trước với trưởng nhóm/nhóm rằng sẽ có tin thông báo lịch trống tự động (tránh bị báo xấu).
- Thỉnh thoảng vẫn vào nick phụ dùng như người thật.
- Chấp nhận nick phụ có thể bị khóa; có sẵn phương án lưới an toàn (báo qua Telegram).
