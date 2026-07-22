"""Vẽ biểu đồ báo cáo bằng matplotlib (dùng backend Agg — không cần màn hình)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from ..config import DATA_DIR

TMP = DATA_DIR / "tmp"
TMP.mkdir(exist_ok=True)


def line_chart(series: list[tuple[str, float]], title: str,
               fname: str = "chart.png") -> Optional[str]:
    """Vẽ biểu đồ đường từ chuỗi (ngày, giá trị). Trả về đường dẫn ảnh, hoặc None nếu ít dữ liệu."""
    if not series or len(series) < 2:
        return None
    days = [d[5:] for d, _ in series]   # bỏ năm cho gọn (MM-DD)
    values = [v for _, v in series]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(days, values, marker="o", linewidth=2, color="#2563eb")
    ax.fill_between(range(len(values)), values, alpha=0.1, color="#2563eb")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if len(days) > 10:
        step = max(1, len(days) // 10)
        ax.set_xticks(range(0, len(days), step))
        ax.set_xticklabels([days[i] for i in range(0, len(days), step)], rotation=45)
    else:
        plt.xticks(rotation=45)
    fig.tight_layout()

    out = TMP / fname
    fig.savefig(out, dpi=110)
    plt.close(fig)
    return str(out)


def bars_chart(labels: list[str], values: list[float], title: str,
               fname: str = "bars.png") -> Optional[str]:
    """Biểu đồ cột, ví dụ so sánh chi tiêu giữa các chiến dịch."""
    if not labels or not values:
        return None
    fig, ax = plt.subplots(figsize=(8, 4))
    short = [l[:18] + "…" if len(l) > 18 else l for l in labels]
    ax.barh(short, values, color="#2563eb")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.grid(True, axis="x", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()

    out = TMP / fname
    fig.savefig(out, dpi=110)
    plt.close(fig)
    return str(out)
