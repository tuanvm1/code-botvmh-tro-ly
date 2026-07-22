# Alobo — cách đọc lịch sân (phát hiện 19/7/2026)

## 3 cơ sở VMH (slug trên datlich.alobo.vn)
- CS1 Cẩm Phả: `sport_vmh_badminton_cn1` → tên hiển thị "VMH CS1 CẨM PHẢ", 2 sân (C.Lông 1, 2), mở 05:00–24:00.
- CS2 Cẩm Phả: `sport_vmh_badminton_cn2`
- Hạ Long:     `sport_vmh_badminton_cn3`

## Bản chất: KHÓ đọc bằng lệnh gọi thường
- Trang là app **Flutter** (canvas), HTML chỉ là vỏ rỗng → không đọc HTML trực tiếp được.
- API thật ở host `https://user-global.alobo.vn/v2/user/branch/...` (và `user-api-new.alobo.vn`).
- MỌI lời gọi phải kèm header ký:
  - `x-platform: web`, `x-name-app: alobo-user`, `x-version-app: 2.9.7`, `x-custom-lang: vi`
  - `x-user-app: <64 hex>` — CHỮ KÝ. Gọi thiếu → **401 Unauthorized**.
- Response bị **MÃ HOÁ AES**: `{"data":"<base64>","enc":true,"iv":"<base64>"}`. Giải mã ở phía Flutter.
  → Muốn giải bằng code phải moi thuật toán + khoá AES trong main.dart.js (mong manh, họ đổi là hỏng).

## Endpoint đã thấy (initial load)
- `GET /v2/user/branch/branch_info/{slug}` — thông tin sân.
- `GET /v2/user/branch/list_reviews/{slug}` — đánh giá.
- `POST /v2/user/branch/branches_first` (body `{"enc":true,"data":"..."}`) — danh sách sân.
- `GET user-api-new.alobo.vn/api/v1/public/sport-type` — loại môn.
- Trong JS còn: `get_lock_yards/`, `get_booking/`, `booking/pass-yard/` (lịch/khoá sân — chưa dò response).

## CÁCH CHẮC ĂN đã CHỨNG MINH được: dùng TRÌNH DUYỆT ẨN (headless Chrome + CDP)
Để trình duyệt tự giải mã & vẽ lịch, rồi ta ĐỌC màn hình (chụp ảnh / OCR / đọc cây accessibility).
Quy trình đã chạy thật (script trong scratchpad: shot.mjs / steps.mjs, điều khiển Chrome qua WebSocket CDP):
1. Mở `datlich.alobo.vn/san/{slug}` → chờ ~18–20s Flutter render.
2. Bấm nút **"Đặt lịch"** (góc phải).
3. Chọn loại sân (radio: Truyền Thống / Điều Hoà Mùa Hè / Ngày Lễ) → **TIẾP TỤC**.
4. Hiện LƯỚI LỊCH: hàng = từng sân (C.Lông 1, 2...), cột = khung 30' (5:00→24:00),
   ô **Trắng = Trống**, **Đỏ = Đã đặt**, **Xám = Khoá**. Có ô chọn NGÀY (mặc định hôm nay).
5. Chụp ảnh lưới → đọc ô trống/đặt theo sân + giờ. (Đã đọc được CS1 ngày 19/07/2026.)

## Gợi ý khi làm tính năng canh sân THẬT
- Nguồn dữ liệu (app/alobo/source.py::fetch_schedule) nên chạy headless Chrome theo quy trình trên,
  đọc lưới → chuẩn hoá về [{"court","date","start","end","free"}] (đúng định dạng monitor.py đang chờ).
- Đọc ô màu ổn định hơn OCR: cắt vùng lưới, lấy màu từng ô theo lưới thời gian đã biết (5:00 + n*30').
- Cần Chrome trên máy chạy (đã có). Trên VPS phải cài Chromium headless.
- KHÔNG cần đăng nhập chủ sân để XEM lịch (trang công khai cho khách). Đăng nhập chỉ cần nếu muốn ĐẶT.
- Chân thành: cách này chậm (mỗi lần ~20s/sân) nhưng chắc; hợp với chu kỳ canh mỗi vài phút.

## Bổ sung 19/7/2026 (quan trọng)
- **Hộp thoại chọn loại sân có 3 HAY 4 mục** (Hạ Long có thêm "Thuê Sân Tháng 2-3 buổi/tuần").
  Hộp thoại CENTER nên nhiều mục → nút "TIẾP TỤC" tụt xuống. Bấm cố định y=843 (cũ) TRƯỢT với 4 mục
  → lưới không mở → is_row đọc nền = ra 16 sân sai. SỬA: bấm radio y=660, "TIẾP TỤC" y=855
  (vùng chồng nhau của cả 3 lẫn 4 mục). Reader viewport 2000x1400.
- **Máy yếu (VPS) render Flutter chậm** → tăng chờ: ALOBO_LOAD_MS (mặc định 35000ms), + chờ sau mỗi bấm.
  Dấu hiệu bấm trượt = đọc ra rất nhiều sân "kín" (nền bị nhận nhầm là hàng). Nếu gặp → tăng ALOBO_LOAD_MS.
- **reader.mjs cần Node ≥ 22** (dùng WebSocket toàn cục cho CDP). Node 20 báo "WebSocket is not defined".
- Tên sân xuất ra: "Sân N" (N = thứ tự hàng trong lưới).
