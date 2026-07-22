"""Điểm khởi động hệ thống trợ lý tự động.

Chạy: python main.py
Bot sẽ lắng nghe Telegram và tự chạy các việc theo giờ.
"""
import logging

from app.bot.core import build_application

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    app = build_application()
    print("✅ Trợ lý đang chạy. Nhấn Ctrl+C để dừng.")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
