"""Khởi động TOÀN BỘ hệ thống: trang quản trị + bot (được trông coi tự động).

Chạy DUY NHẤT lệnh này:  python run_admin.py
- Trang quản trị: http://127.0.0.1:8760  (nhập/sửa chìa khoá, thêm Trang/Zalo/sân, nút Khởi động lại)
- Bot Telegram tự chạy nền và tự bật lại nếu chết.
"""
from app.admin.server import run

if __name__ == "__main__":
    print("🛠️  Trang quản trị: http://127.0.0.1:8760")
    print("🤖 Bot Telegram tự chạy nền (có nút Khởi động lại trên trang quản trị).")
    print("   Nhấn Ctrl+C để dừng tất cả.")
    run()
