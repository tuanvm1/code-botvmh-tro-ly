# Bàn giao — Trợ lý tự động (cập nhật 22/7/2026)

## HAI KHO GITHUB (ĐỪNG NHẦM — vai trò KHÁC HẲN)
- `tuanvm1/bonaobotVMH` = KHO KIẾN THỨC bot đọc (LIVE): chủ sửa Obsidian `Documents/bonaoVMH` → auto-push →
  VPS kéo mỗi 3 phút vào data/bot-kb → bot đọc để trả lời khách. BẮT BUỘC GIỮ + DÙNG (xoá = bot mất kiến thức sửa-được).
- `tuanvm1/code-botvmh-tro-ly` = SAO LƯU MÃ NGUỒN (private), tag `v1.0.0` (22/7). Chỉ để backup/khôi phục code, KHÔNG
  chạy runtime. Push từ Mac qua SSH key `github_bo_nao`. .gitignore loại .env/data/session/log/node_modules
  (đã soi kỹ không lọt bí mật; suýt lọt data/zalo_session.json do .gitignore ghi chú cùng dòng — đã sửa).
  KHÔNG gộp 2 kho (nhét code vào bonaobotVMH → VPS kéo về, bot đọc nhầm tasks/*.md làm kiến thức + lộ IP nội bộ).


## (22/7) BOT ZALO → AGENT THÔNG MINH (dùng công cụ) + BẢO MẬT — ✅ XONG, chạy thật VPS
File mới `app/ai/zalo_agent.py` (Claude tool-use) THAY badminton.answer làm bộ não bot khách (server.py
/internal/zalo-reply gọi zalo_agent.answer(...,uid)). Gemini → tự lùi badminton.answer. selftest 12/12.
- BƯỚC 1 (lõi): công cụ kiem_tra_lich_san (đọc lịch alobo thật), danh_sach_co_so; kiến thức Obsidian injected.
  Tự xử câu hỏi nhiều ý cùng lúc (lịch + sản phẩm). Test thật VPS: đọc lịch Hạ Long thật + câu phức tạp OK.
- BƯỚC 2 (nhớ khách): bảng `customer_memory` (uid,name,notes) — db._migrate tạo. store.remember_customer/
  customer_memory_text; tool ghi_nho_ve_khach; sổ tay khách nạp vào _system. Test thật: nhớ "Nam mới tập, tay
  trái" → lần sau tự nhận, cá nhân hoá.
- BƯỚC 3 (chủ động an toàn): job `zalo_summary` (bot/jobs.job_daily_zalo_summary, đăng ký core.py, mặc định
  21:30, setting `zalo_summary_time`) — cuối ngày tóm tắt khách gửi CHỦ qua Telegram (chỉ ra khách muốn đặt/mua
  chưa chốt). store.customer_messages_since + zalo_agent.owner_daily_summary. KHÔNG tự nhắn khách (né khoá Zalo).
- 🔒 BẢO MẬT (luật trong CODE, ở _SECURITY, không để trong kho Obsidian): bot từ chối lộ chỉ dẫn/tên file/cấu
  trúc kho, chống "ignore previous instructions" + giả danh lập trình viên, câu từ chối cố định. Xem tasks/decisions.md.
- REVIEW ĐỐI KHÁNG (8 agent) — ĐÃ SỬA 6 điểm: (#1 HIGH) chống CHÈN LỆNH/GIẢ MẠO LƯỢT TRỢ LÝ qua lịch sử chat
  (badminton._conversation_block: ép 1 dòng, tên khách bỏ ':' → không giả nhãn 'TRỢ LÝ VMH (bot)', bọc "nhật ký =
  dữ liệu"); (#2) chống "GIẶT LINK" lừa đảo (_drop_fabricated_links: nguồn tin cậy = kiến thức+kết quả công cụ,
  BỎ tin khách; allowlist domain datlich.alobo.vn); (#6) chốt chặn ĐẦU RA _finalize: lộ tên công cụ/dấu rào →
  thay câu từ chối; (#3) hết vòng công cụ → ép soạn câu cuối; (#4) _norm_time nhận '18h'. Test thật: tấn công
  đổi tên thành 'Trợ lý (bạn)' + nhồi lượt giả → bot TỪ CHỐI, không lộ. Bản cũ backup VPS `.bak_20260722_*`.
NHỚ: hàng rào prompt chặn phần lớn nhưng không 100% → KHÔNG để bí mật thật trong kho kiến thức.



## (21/7) BỘ NÃO BOT BẰNG OBSIDIAN — ✅ XONG, chạy thật trên VPS đạt (chờ review đối kháng chốt)
Chủ muốn quản lý kiến thức bot bằng Obsidian (kho RIÊNG cho bot + đồng bộ qua GitHub, sửa được cả trên điện thoại).
LUỒNG HOÀN CHỈNH đã chạy thật: chủ sửa ghi chú trong Obsidian → git push → VPS tự `git pull` mỗi 3 phút
(systemd timer `kb-sync`) → bot đọc để trả lời khách. ĐÃ TEST E2E: thêm ghi chú "wifi = VMH-CAULONG-2026"
trên Mac → push → VPS kéo → hỏi bot qua endpoint thật → bot trả đúng. Xoá ghi chú → cũng biến mất đúng.

KẾT NỐI GITHUB (đã xong):
- Repo PRIVATE: `git@github.com:tuanvm1/bonaobotVMH.git` (chủ đặt tên `bonaobotVMH`).
- Mac push: khoá `~/.ssh/github_bo_nao` (đã thêm vào SSH keys tài khoản GitHub `tuanvm1`); `~/.ssh/config` đã trỏ.
- VPS pull: khoá CHỈ-ĐỌC `~/.ssh/bonaobot_deploy` (đã thêm vào **Deploy keys** của repo, KHÔNG write). Clone ở
  `/root/tro-ly-tu-dong/data/bot-kb` (= mặc định `bot_kb_dir`, KHÔNG cần đặt setting).
- Tự kéo: `/root/tro-ly-tu-dong/kb_sync.py` + systemd `kb-sync.timer` (mỗi 180s) + `kb-sync.service`. Có flock
  chống chạy chồng, cảnh báo Telegram nếu pull lỗi >1h (throttle). LƯU Ý: nếu chạy kb_sync.py BẰNG TAY đúng lúc
  timer chạy có thể đụng git → đã thêm flock; 21/7 lúc test có thể chủ nhận 1-2 tin cảnh báo nhầm (đã dặn bỏ qua).

KHO MAC (21/7 chủ đổi chỗ): `/Users/bocuatho/Documents/bonaoVMH` (Obsidian vault; kho cũ `bo-nao-bot` đã xoá,
lịch sử git + remote đã chuyển sang; `.obsidian` được gitignore). Chủ nên điền số liệu THẬT (giá, sản phẩm, KM) vào ghi chú seed.
REVIEW ĐỐI KHÁNG (14 agent) đã sửa: knowledge_text CẮT bớt ghi chú quá dài thay vì bỏ sạch; chống SYMLINK/file lớn
(lộ .env/OOM); kb_sync đổi sang `git fetch`+`reset --hard origin/main` (mirror không kẹt) + bắt timeout/exception +
env BatchMode fail nhanh; prompt: kiến thức là "DỮ LIỆU THAM KHẢO", QUY TẮC cứng luôn thắng. THÊM hàng rào
`_drop_fabricated_links`: bỏ URL bot bịa (không có trong dữ liệu) — link Maps/alobo THẬT của chủ (trong DB "Link
đặt sân" + kho) vẫn qua. selftest 11/11 (Mac+VPS). Test thật VPS: hỏi địa chỉ → trả đủ Maps+alobo thật.
CÒN LÀM (không gấp): cài Obsidian Git trên app ĐIỆN THOẠI trỏ cùng repo (cần Personal Access Token, hướng dẫn sau).

--- (chi tiết kỹ thuật phần lõi, đã xong) ---
CODE (đã test + đã lên VPS, an toàn — kho thiếu thì bot tự về kiến thức cũ):
- `app/ai/kb_folder.py` (MỚI): bot đọc kiến thức từ THƯ MỤC ghi chú .md. Đường dẫn = setting `bot_kb_dir`
  (mặc định `<project>/data/bot-kb`). Chọn phần liên quan như `store.knowledge_text`; lọc cú pháp Obsidian;
  BỎ QUA file/thư mục bắt đầu bằng `.` hoặc `_`. Cache theo mtime.
- `badminton.answer` giờ dùng `kb_folder.combined_knowledge(question)` = kho Obsidian (ƯU TIÊN) + trang
  "Kiến thức" cũ (dự phòng). Khi CHƯA có kho trên VPS → tự về đúng hành vi cũ (an toàn, không đổi gì).
- selftest 11/11 (thêm `t_kb_folder`). Test AI thật: bỏ giá "95k" vào ghi chú → bot trả đúng 95k; không lộ file `_`.
- Đã deploy `kb_folder.py`+`badminton.py`+`selftest.py` lên VPS, restart, 11/11, service active.
- Kho Obsidian đã tạo ở MÁC: `/Users/bocuatho/bo-nao-bot` (9 ghi chú seed: cơ sở+link, giá, vợt, KM, câu chốt,
  FAQ, +file `_Nháp` demo). Đã `git init`+commit. Link Hạ Long đã sửa đúng đuôi `_cn3`.
- Khoá SSH GitHub tạo ở Mac: `~/.ssh/github_bo_nao` (+ đã cấu hình `~/.ssh/config` cho github.com).
  KHOÁ CÔNG KHAI: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAID5gqXg8ZseUQSNk/Q8UHG0oeddervHmBRIARNjZi+4O bo-nao-bot`

CÒN LẠI (cần CHỦ làm 2 bước trên GitHub, rồi mình nối nốt):
1) Chủ dán khoá công khai trên vào GitHub (Settings → SSH and GPG keys → New SSH key).
2) Chủ tạo repo RỖNG tên `bo-nao-bot`, để PRIVATE (github.com/new).
Sau đó MÌNH làm: thêm remote `git@github.com:tuanvm1/bo-nao-bot.git` + push; trên VPS copy khoá riêng
`github_bo_nao` sang + clone vào `/root/tro-ly-tu-dong/data/bot-kb` + systemd timer `git pull` mỗi ~3 phút +
đặt setting `bot_kb_dir` = đường dẫn đó + cảnh báo Telegram nếu pull lỗi. Rồi test thật + review đối kháng.
Điện thoại sửa được: sau khi xong Mac↔bot, cài Obsidian Git trên app điện thoại trỏ cùng repo (cần token, chỉ sau).
Tài khoản GitHub chủ: `tuanvm1` (git config global đã đặt sẵn tên+email noreply).


## (20/7 khuya-2) Bot "THÔNG MINH" khi khách hỏi sân trống — ĐÃ LÊN VPS + test thật đạt
Chủ phản ánh: hỏi "18:00 xem có lịch trống ở Cẩm Phả không" → bot chỉ quăng link, không báo lịch.
NGUYÊN NHÂN: `badminton._live_schedule_context` cũ chỉ đọc lịch khi câu chứa cụm từ khoá cứng
(`_AVAIL_KEYS`); "có LỊCH TRỐNG" không khớp → bỏ qua. ĐÃ SỬA (tất cả trong `app/ai/badminton.py`):
- **Bộ "hiểu ý" AI** `_detect_intent` (gọi Haiku, trả JSON {sched,venue,day,time}) thay danh sách từ khoá.
  Từ khoá cũ (`_AVAIL_KEYS`, `_fallback_venue_code`) GIỮ làm LƯỚI AN TOÀN khi AI lỗi/lệch.
- **Trả lời ĐÚNG GIỜ hỏi** `_time_status`: 18h còn/hết; hết → gợi khung gần nhất; giờ đã qua → nói "đã QUA".
  Khi có giờ vẫn kèm TOÀN BỘ khung trống (khách hỏi thêm giờ/đánh 2 tiếng vẫn đủ dữ liệu).
- **Prompt `_system` thêm khối CHĂM SÓC & CHỐT SÂN** (ưu tiên số 1) + GIỚI HẠN: KHÔNG hứa đặt/giữ sân hộ,
  KHÔNG hứa tự nhắn lại khi khách im (chỉ bám TRONG mạch chat — chủ đã chốt cách này).
- Sửa sau review 27-agent: đối chiếu NGÀY (chữ "hôm nay/mai" của khách THẮNG AI); chat xem HẾT sân (không
  lọc theo cfg['courts'] của canh tự động); định danh cơ sở theo SLUG cn1/cn2/cn3 (không vỡ khi đổi tên);
  ép true/false chắc; dặn AI đừng nhầm số giờ↔số cơ sở ("2h chiều"≠CS2); lọc link markdown.
- KIỂM CHỨNG: selftest 10/10 (Mac & VPS); hiểu-ý AI thật 13/13 kiểu nói; test thật trên VPS đúng câu chủ hỏi
  → bot đọc lịch thật CS1+CS2, báo 18h đã qua + gợi khung 23:30-24:00 + rủ chốt. Không hứa đặt hộ.
- Đã LÊN VPS: `systemctl restart trolybot` (active, Zalo vẫn logged_in). Bản cũ backup ở VPS
  `/root/tro-ly-tu-dong/.bak_20260720_2255/`. Muốn quay lại: copy 3 file từ thư mục đó về rồi restart.
- Ghi chú độ trễ: hỏi "Cẩm Phả" chung → đọc 2 cơ sở ~80s (khách chờ; chủ đã chọn chờ). Mỗi tin 2 lần gọi AI.


## (20/7 khuya) QC đa-agent + SỬA loạt lỗi — đã triển khai VPS + selftest 9/9
Đội review đối kháng (24 agent) soi code mới, đã sửa các lỗi THẬT (đều test lại):
- badminton.py: bỏ nhận diện "ngày mai" bằng chuỗi " mai" (dương tính giả với tên "Mai") → chỉ nhận cụm rõ
  ("ngày mai/sáng mai/tối mai..."), và "hôm nay" luôn thắng. Bỏ "số 1/số 2" khỏi dò cơ sở (nhầm "sân số 2" = CS2).
  Làm mềm câu (nhắc khách chốt nhanh, không hứa cứng vì lịch có thể đổi).
- server.py: AI trả RỖNG (không lỗi, vd Gemini bị lọc) cũng nhắn câu xin lỗi thay vì im lặng.
- source.py: (1) timeout đọc lịch → diệt LUÔN Chrome con (start_new_session + killpg) tránh Chrome mồ côi rò RAM;
  (2) kiểm-chứng-lưới: nếu header trục giờ không phải xanh nhạt (lưới chưa mở/alobo đổi giao diện) → BÁO LỖI
  thay vì đọc bừa ra "toàn sân kín"; (3) nhớ tạm 5 phút + kiểm lại cache SAU khi giành khoá (khỏi đọc trùng).
- llm.py: _is_retryable đọc MÃ trạng thái (429/5xx/529) thay vì khớp chuỗi ("rate" nằm trong "generate" → hết nhầm).
- monitor.py: free_ranges chỉ nối khung LIỀN NHAU (không nối qua khoảng hở).
- jobs.py: đọc lỗi CẢ 3 cơ sở → báo chủ qua Telegram (không "chết âm thầm").
- Hạ tầng VPS: thêm SWAP 2GB (vm.swappiness=10) → không lo tràn RAM khi đọc lịch.
Còn lại (chấp nhận/ghi chú): chat có thể chờ tới ~2-3 phút NẾU đúng lúc job canh sân 10/14/22h đang giữ khoá đọc
(hiếm); nhớ tạm theo TIẾN TRÌNH (admin/bot không chung cache); cả hai không nguy hiểm.

## (20/7 tối) 2 nâng cấp bot AI — ĐÃ triển khai VPS
- **Chống "im lặng" khi AI quá tải**: Claude/Gemini đôi lúc trả lỗi 529 (overloaded) → trước đây bot
  im. Giờ `ai/llm.py::chat` TỰ THỬ LẠI 3 lần (backoff 1.5s/3s); nếu vẫn lỗi, endpoint trả câu xin lỗi
  nhẹ thay vì im (`app/admin/server.py`).
- **Trợ lý đọc LỊCH SÂN THẬT khi khách hỏi**: `ai/badminton.py::_live_schedule_context` — khi khách hỏi
  "sân trống / đặt sân / trống giờ nào...", bot tự đọc lịch alobo THẬT của cơ sở khách nhắc (Hạ Long/CS1/CS2)
  rồi trả lời bằng số liệu thật + link đặt + mời chốt. Chưa rõ cơ sở → bot HỎI lại (nhanh). Có "mai" → đọc ngày mai.
  `source.fetch_schedule(use_cache=True)` nhớ tạm 10 phút cho nhanh; khoá file `/tmp/alobo_reader.lock`
  đảm bảo CHỈ 1 Chrome đọc lịch cùng lúc (tránh tràn RAM VPS 2GB). Mỗi lần đọc mới ~35-40s.
  Đã test thật trên VPS: hỏi "sân Hạ Long trống tối nay" → trả đúng 22:00-24:00 + link.

## ĐÃ LÊN VPS VIỆT NAM & CHẠY 24/7 (20/7/2026) — HỆ THỐNG SỐNG Ở ĐÂY GIỜ
- VPS: TDCloud, **IP 165.101.47.151**, Ubuntu 24.04, 2 CPU / 2GB RAM, **giờ Asia/Ho_Chi_Minh**.
  Thông tin đăng nhập + cách quản lý: `~/Downloads/vps-vietnam-info.txt` (trên máy Mac).
  Khoá SSH: `~/.ssh/tdcloud_vps` (đăng nhập không cần mật khẩu). Mật khẩu root đã đổi (cũ đã lộ).
- Đã cài: Node 22 (BẮT BUỘC ≥22 cho reader.mjs), Google Chrome, Python venv + deps (có Pillow), zca-js.
- Chạy 24/7 qua **systemd `trolybot`** (enable + Restart on-failure): admin + Telegram bot + Zalo + canh sân.
- Kiểm thử trên VPS ĐẠT: selftest 9/9; đọc lịch CS1 = 2 sân; **Zalo đăng nhập (quét QR 20/7)**;
  Telegram polling 200 OK; **đã gửi thử 1 tin digest vào nhóm từ VPS thành công**.
- **MÁC ĐÃ TẮT BOT** — hệ thống giờ chạy trên VPS. ⚠️ KHÔNG bật lại run_admin.py trên Mac (xung đột
  Telegram 409 + Zalo). Muốn quay lại Mac: `ssh ... 'systemctl stop trolybot'` trước rồi mới chạy Mac.
- Quản lý VPS: `systemctl {status|restart|stop|start} trolybot`; log: `journalctl -u trolybot -f`.
- Zalo bị đăng xuất → quét QR lại: mở tunnel `ssh -i ~/.ssh/tdcloud_vps -N -L 8760:127.0.0.1:8760
  root@165.101.47.151` rồi vào http://127.0.0.1:8760/zalo-service quét QR. (Session lưu ở VPS →
  restart KHÔNG cần quét lại.)
- Cập nhật code lên VPS sau: sửa ở Mac → `tar ... | ssh ... tar x` (loại .venv/node_modules/data) →
  `systemctl restart trolybot`. Reader dùng ALOBO_LOAD_MS=40000 trên VPS (chậm hơn Mac).

## MỚI (19/7 – phần bổ sung): tin gộp 3 cơ sở + sửa Hạ Long + ĐƯA LÊN VPS

### Tin báo sân trống — chỉnh theo yêu cầu chủ (đã chạy thật)
- Mỗi lần báo GỘP CẢ 3 CƠ SỞ vào 1 tin (đỡ spam): `monitor.compose_combined_digest`,
  job `_alobo_report` gom theo nhóm nhận rồi gửi 1 tin. Đã gửi thử vào nhóm "vmh bot test" → nhận được.
- Đổi tên "C.Lông N" → "SÂN N" (source.py).
- Mỗi cơ sở kèm LINK đặt sân: `https://datlich.alobo.vn/san/<slug>`.
- BỎ câu chốt "anh em chốt sân gọi..." ở cuối tin (theo yêu cầu).
- SỬA LỖI Hạ Long: hộp thoại chọn loại sân có 3 HAY 4 mục (Hạ Long có thêm "Thuê Sân Tháng"),
  làm nút "TIẾP TỤC" lệch → bấm trượt → đọc sai (ra 16 sân). Đã sửa toạ độ bấm (y=855, radio y=660)
  trúng cả 3 lẫn 4 mục. Giờ Hạ Long đọc ĐÚNG 4 sân.

### ĐƯA LÊN VPS (Google Cloud, IP 35.222.104.120) — ĐÃ CÀI + KIỂM THỬ ĐẠT, CHƯA BẬT LIVE
- VPS: Ubuntu 24.04, đã cài Node 22 (cần ≥22 vì reader.mjs dùng WebSocket toàn cục), Google Chrome 150,
  Python venv + thư viện (đã thêm Pillow vào requirements.txt). Key SSH: ~/Downloads/vps-test-handoff/vps-test-key.
- Đã copy code + DB (data/trolydb.sqlite3). Chạy `selftest.py` trên VPS → 9/9. Đọc thử lịch CS1 trên VPS
  bằng Chrome ẩn → ĐÚNG 2 sân. (Máy VPS chậm hơn → đặt ALOBO_LOAD_MS=38000, mặc định code là 35000.)
- Đã tạo systemd service `trolybot` (chạy run_admin.py, có Restart) NHƯNG **CHƯA bật** (disabled).
- ⚠️ CHƯA cho chạy LIVE trên VPS vì 2 RỦI RO cần chủ quyết:
  1) **Telegram 409**: chỉ 1 nơi được polling. Bật VPS PHẢI tắt bản trên Mac (không hai nơi cùng chạy bot).
  2) **Zalo khoá do đổi IP**: tài khoản Zalo VN đăng nhập từ IP MỸ (datacenter) → RẤT DỄ bị khoá.
     KHUYẾN NGHỊ: giữ phần Zalo cá nhân chạy ở Mac/VN; hoặc dùng VPS đặt tại VN; hoặc chấp nhận rủi ro nick phụ.
  3) Nếu chạy Zalo trên VPS: phải `cd ~/tro-ly-tu-dong/zalo_service && npm install` (chưa cài zca-js trên VPS)
     và quét lại QR (không copy zalo_session.json sang VPS).
- CÁCH BẬT LIVE trên VPS (khi chủ đồng ý): tắt Mac trước → SSH vào VPS →
  `sudo systemctl enable --now trolybot` → xem `journalctl -u trolybot -f`. Tắt: `sudo systemctl stop trolybot`.
- HIỆN TẠI: hệ thống vẫn chạy TRÊN MÁC như cũ (3/3, Zalo logged_in). VPS chỉ mới ở trạng thái "sẵn sàng".

## MỚI (19/7): nâng cấp Bot AI Zalo + thêm Gemini + hoàn thiện CANH SÂN

### 1) Bot AI Zalo — trả lời chất hơn (đã chạy thật, đạt)
Vấn đề cũ: hỏi thông số vợt (vd Yonex 88D Pro) trả lời vòng vo; không nhớ hội thoại; không đọc dữ liệu nhóm.
Đã sửa:
- `app/ai/badminton.py`: prompt mới → trả lời ĐÚNG TRỌNG TÂM, nói thẳng thông số mẫu vợt cụ thể,
  hướng GIỮ CHÂN & CHỐT SALE. Thêm kho `PRODUCT_SPECS` (thông số các mẫu phổ biến) trong `app/ai/knowledge.py`.
- NHỚ HỘI THOẠI nhiều lượt + dùng DỮ LIỆU NHÓM: lưu MỌI tin nhóm vào bảng `zalo_messages`
  (store.add_message/recent_messages/search_messages/prune). Khi trả lời, ghép bối cảnh hội thoại
  gần đây + tin cũ liên quan trong nhóm. Node giờ forward MỌI tin nhóm về Python để LƯU (kèm thread_id + uid),
  nhưng vẫn CHỈ TRẢ LỜI khi được @nhắc (nhóm) / tin 1-1 (quy tắc cũ giữ nguyên).
- Đã test thật: hỏi 88D Pro → ra thông số gọn đúng; hỏi dồn "đôi/đứng sau/2-3 triệu" rồi @nhắc → bot nhớ
  ngữ cảnh, gợi ý 88D Pro + chốt (ghé shop/hotline). Tin không-@nhắc được LƯU đúng, không trả lời.

### 2) Chọn "bộ não" AI: Claude HOẶC Gemini (mới)
- `app/ai/llm.py::chat()` — một cửa gọi AI, tự chọn theo cài đặt `ai_provider` (claude|gemini).
  Claude qua SDK anthropic; Gemini gọi REST (không cần cài thêm thư viện).
- Trang quản trị (Cấu hình chung) có mục "🧠 Bộ não AI đang dùng": chọn Claude/Gemini + ô Khoá Gemini +
  Model Gemini + nút "🔎 Kiểm tra AI". Bấm Lưu là đổi ngay.
- HIỆN đang dùng CLAUDE (mặc định). MUỐN DÙNG GEMINI: vào quản trị điền Khoá Gemini API
  (aistudio.google.com), chọn Gemini, Lưu, bấm Kiểm tra. Model mặc định `gemini-2.5-flash` (sửa được).
- Lưu ý: phần chọn AI áp dụng cho BOT ZALO. Phần viết bài Facebook + trợ lý Telegram (có công cụ) vẫn chạy Claude.

### 3) CANH SÂN alobo → báo nhóm Zalo (mới, đã chạy thật, đạt)
Cách báo (theo yêu cầu chủ): KHÔNG canh liên tục, mà BÁO CỐ ĐỊNH theo giờ:
- 10:00 & 14:00 → báo TOÀN BỘ lịch trống HÔM NAY (chỉ khung từ giờ hiện tại trở đi).
- 22:00 → báo TOÀN BỘ lịch trống NGÀY MAI.
Giờ báo sửa được ở `settings`: `alobo_report_today` (10:00,14:00), `alobo_report_tomorrow` (22:00).
Cách đọc lịch THẬT (alobo là Flutter, dữ liệu mã hoá): `app/alobo/reader.mjs` mở Chrome ẩn, vào "Đặt lịch"
→ chọn loại sân → chọn ngày → chụp lưới; `app/alobo/source.py::fetch_schedule` đọc MÀU từng ô (Pillow)
→ trắng=trống/đỏ=đặt/xám=khoá. Hình học lưới canh chỉnh trong `tasks/ALOBO-API.md`.
- 3 cơ sở đã tạo sẵn (bảng alobo_venues, báo qua nhóm Zalo "vmh bot test"):
  CS1 `sport_vmh_badminton_cn1`, CS2 `_cn2`, Hạ Long `_cn3` (loại "Truyền Thống").
- Trang quản trị mục "🏸 Sân alobo": form có Mã sân (slug) + Loại sân; nút "👁 Xem trước" đọc thử lịch NGAY
  (không gửi). Đã test: xem trước CS1 ra đúng khung trống; gửi thử digest vào nhóm → nhận được ✔.
- 3 job đăng ký: alobo_today_0 (10h), alobo_today_1 (14h), alobo_tomorrow_0 (22h).
- Đã mở khung giờ an toàn Zalo 6-23h (để tin 22h gửi được; vẫn không gửi đêm khuya).

## Đã có sẵn từ trước (nền tảng)
- Telegram + AI (viết bài/báo cáo/quản lý quảng cáo, xác nhận 2 bước, trần ngân sách).
- Đa-Trang Facebook, đa tài khoản Zalo, trang quản trị localhost (127.0.0.1:8760).
- Zalo cá nhân (zca-js) qua Node `zalo_service/`: tự nối lại khi rớt (retryOnClose + backoff),
  van an toàn né khóa (giãn tin, giới hạn/giờ/ngày, khung giờ, đổi câu). Nhóm chỉ trả lời khi @nhắc.

## Bật/tắt & kiểm tra
- Bật tất cả: `cd ~/tro-ly-tu-dong && ./.venv/bin/python run_admin.py &` (tự trông coi bot + Node).
- Quản trị: http://127.0.0.1:8760 (có nút Bật/Tắt/Khởi động lại). Sửa cấu hình xong bấm Khởi động lại.
- Tự kiểm tra: `./.venv/bin/python selftest.py` → kỳ vọng 9/9 (test alobo đôi khi flaky, chạy lại là đạt).

## CÒN LÀM / lưu ý cho phiên sau
- Bot AI: model Zalo đang là `claude-haiku-4-5` (nhanh, rẻ). Muốn trả lời "sâu" hơn có thể đổi model
  (Sonnet/Opus) hoặc dùng Gemini — ở Cấu hình chung.
- PRODUCT_SPECS mới có vài mẫu vợt chính; chủ nên bổ sung thông số/giá THẬT của shop qua mục "Kiến thức"
  (đó là kiến thức riêng, bot ưu tiên dùng). Bot có thể vẫn hơi "sáng tạo" vài chi tiết nếu không có trong kho.
- Canh sân: đọc lịch ~20s/cơ sở, cần MÁY BẬT + có Chrome. Lên VPS phải cài Chromium (reader.mjs tự dò).
  Đọc lưới bằng màu — nếu alobo đổi giao diện phải canh lại (xem ALOBO-API.md). Nguyên tắc: không chắc → coi là "đã đặt".
- "Ngày mai" (mốc 22h) đọc qua lịch chọn ngày (đã code + tính ô ngày); nên theo dõi lần chạy 22h đầu tiên.
- Kế hoạch canh sân đã duyệt: ~/.claude/plans/effervescent-wandering-lemon.md
