"""Kho sản phẩm: ĐỌC file Excel (xuất từ Sapo) → hiểu sản phẩm → cho bot tư vấn & CHỐT ĐƠN.

Luồng: chủ tải file .xlsx ở trang quản trị → import_from_xlsx() bóc tách từng phiên bản
(gom về sản phẩm cha, suy ra nhãn hiệu/nhóm hàng, dò cột tồn nếu có) → lưu vào bảng products.
Agent Zalo dùng:
  - catalog_summary(): 1 khối NGẮN "shop đang bán gì" (luôn nhét vào ngữ cảnh để bot chủ động mời).
  - search_for_agent(query): CÔNG CỤ tra đúng hàng ĐANG CÓ theo nhu cầu khách (tên/giá/lựa chọn/tồn).

Lưu ý số tồn: file Sapo "xuất sản phẩm" thường KHÔNG có cột tồn → coi mọi hàng trong file là CÒN BÁN.
Nếu file có cột "Tồn kho"/"Số lượng" → tự đọc số tồn để tư vấn chính xác ("còn N cái").
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime

from . import store

LOW_STOCK = 5  # tồn <= ngần này coi là "sắp hết" → tạo khan hiếm THẬT khi tư vấn


# ---------- Tiện ích ----------

def _no_accent(s: str) -> str:
    """Bỏ dấu tiếng Việt để so khớp khi khách gõ không dấu ('vot' ~ 'vợt')."""
    s = (s or "").replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


def money(v) -> str:
    """Định dạng tiền dễ đọc: 195000→'195k', 2950000→'2,95tr'."""
    if v is None:
        return "?"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "?"
    if v >= 1_000_000:
        s = f"{v / 1_000_000:.2f}".rstrip("0").rstrip(".")
        return s.replace(".", ",") + "tr"
    if v >= 1000:
        return f"{int(round(v / 1000))}k"
    return f"{int(v)}đ"


# Nhóm hàng suy từ tên (thứ tự ưu tiên — khớp cái đầu tiên trúng).
_CATEGORIES = [
    ("Vợt", ["vot"]),
    ("Giày", ["giay"]),
    ("Dây cước", ["cuoc", "day cuoc", " day "]),
    ("Cầu", ["cau "]),
    ("Tất/Vớ", ["tat ", "vo "]),
    ("Quấn cán", ["quan can", "cuon can", "grip", "overgrip"]),
    ("Túi/Bao/Balo", ["tui", "bao ", "balo", "ba lo"]),
    ("Quần áo", ["ao ", "quan ", "vay ", "juri", "set "]),
    ("Nước/Phụ khác", ["nuoc ", "tang luc", "bu khoang", "khan ", "bang keo", "phu kien"]),
]

# Nhãn hiệu suy từ tên + từ đồng nghĩa (để tra cứu khớp cả khi khách gõ khác).
_BRANDS = [
    ("Yonex", ["yonex", "ynx"]),
    ("Lining", ["lining", " ln ", "ln "]),
    ("Victor", ["victor", "vic "]),
    ("Mizuno", ["mizuno"]),
    ("Kawasaki", ["kawasaki", "kason"]),
    ("Lefus", ["lefus"]),
    ("Baloli", ["baloli"]),
    ("Yasu", ["yasu"]),
    ("Apacs", ["apacs"]),
    ("Kumpoo", ["kumpoo"]),
]


def categorize(name: str) -> str:
    n = " " + _no_accent(name) + " "
    for label, keys in _CATEGORIES:
        if any(k in n for k in keys):
            return label
    return "Khác"


def brand_of(name: str) -> str:
    n = " " + _no_accent(name) + " "
    for label, keys in _BRANDS:
        if any(k in n for k in keys):
            return label
    return ""


def _brand_synonyms(brand: str) -> str:
    for label, keys in _BRANDS:
        if label == brand:
            return " ".join([label] + keys)
    return brand or ""


# ---------- Đọc file Excel Sapo ----------

def _cell(v) -> str:
    return "" if v is None else str(v).strip()


def _find_col(headers: list[str], *needles: str, exclude: str = "") -> int:
    """Tìm cột theo tên tiêu đề (không dấu, chứa 'needle'). -1 nếu không có."""
    for i, h in enumerate(headers):
        hl = _no_accent(h)
        if exclude and exclude in hl:
            continue
        if any(_no_accent(nd) in hl for nd in needles):
            return i
    return -1


def _find_stock_col(headers: list[str]) -> int:
    """Tìm cột TỒN KHO — khớp TRỌN TỪ 'ton' (để 'Tổng số lượng' → 'tong' KHÔNG bị nhận nhầm)."""
    for i, h in enumerate(headers):
        toks = re.findall(r"\w+", _no_accent(h), re.UNICODE)
        if "ton" in toks:                                   # 'Tồn kho', 'Số lượng tồn', 'Tồn cuối'
            return i
    return -1


def _to_price(v) -> float | None:
    s = _cell(v).replace(",", "").replace(" ", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_xlsx(path) -> list[dict]:
    """Bóc tách file .xlsx của Sapo thành danh sách PHIÊN BẢN (đã gom tên cha, suy nhãn/nhóm).

    Bền với việc đổi thứ tự cột: tìm cột theo TÊN tiêu đề, không dựa vị trí cứng.
    """
    import openpyxl  # nạp trễ: chỉ cần khi thật sự đọc file
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header = [_cell(c) for c in next(rows_iter)]
    except StopIteration:
        return []

    name_col = _find_col(header, "ten san pham", exclude="phien ban")
    if name_col < 0:
        name_col = _find_col(header, "ten san pham")
    variant_col = _find_col(header, "ten phien ban")
    sku_col = _find_col(header, "sku", "ma san pham")
    price_col = _find_col(header, "gia ban")
    if price_col < 0:
        price_col = len(header) - 1  # dự phòng: cột cuối thường là giá bán lẻ
    image_col = _find_col(header, "anh")
    unit_col = _find_col(header, "don vi")
    stock_col = _find_stock_col(header)

    # Các cặp thuộc tính (tên ↔ giá trị): 'Thuộc tính N' & 'Giá trị thuộc tính N'
    attr_pairs = []
    for n in range(1, 6):
        nc = _find_col(header, f"thuoc tinh {n}", exclude="gia tri")
        vc = _find_col(header, f"gia tri thuoc tinh {n}")
        if nc >= 0 and vc >= 0:
            attr_pairs.append((nc, vc))

    out: list[dict] = []
    cur_name = ""
    cur_attr_names: list[str] = ["" for _ in attr_pairs]
    for raw in rows_iter:
        row = list(raw)

        def g(i):
            return _cell(row[i]) if 0 <= i < len(row) else ""

        name_here = g(name_col)
        if name_here:                       # bắt đầu 1 SẢN PHẨM mới → nạp lại tên thuộc tính từ dòng này
            cur_name = name_here
            cur_attr_names = [g(nc) for nc, _ in attr_pairs]
        if not cur_name:                    # dòng rác trước sản phẩm đầu tiên
            continue

        # Ghép chuỗi thuộc tính "Màu sắc: Tím, Size: 42" (bỏ 'Mặc định' vô nghĩa)
        parts = []
        for idx, (_, vc) in enumerate(attr_pairs):
            aname = cur_attr_names[idx] if idx < len(cur_attr_names) else ""
            aval = g(vc)
            if aval and _no_accent(aval) not in ("mac dinh", "default"):
                parts.append(f"{aname}: {aval}" if aname else aval)
        attrs = ", ".join(parts)

        stock_qty = None
        in_stock = 1
        if stock_col >= 0:
            sraw = g(stock_col)
            if sraw:
                try:
                    stock_qty = int(float(sraw.replace(",", "")))
                    in_stock = 1 if stock_qty > 0 else 0
                except ValueError:
                    stock_qty = None

        variant = g(variant_col) or cur_name
        # Bỏ dòng hoàn toàn rỗng (không có tên phiên bản lẫn SKU) cho chắc
        if not (variant or g(sku_col)):
            continue

        out.append({
            "product_name": cur_name,
            "variant_name": variant,
            "sku": g(sku_col),
            "brand": brand_of(cur_name),
            "category": categorize(cur_name),
            "attrs": attrs,
            "price": _to_price(row[price_col] if 0 <= price_col < len(row) else None),
            "unit": g(unit_col),
            "image_url": g(image_col),
            "in_stock": in_stock,
            "stock_qty": stock_qty,
        })
    return out


def import_from_xlsx(path, source: str = "") -> dict:
    """Đọc file → THAY MỚI toàn bộ kho. Trả về {'products', 'variants'} sau khi nạp.

    AN TOÀN: nếu file đọc ra 0 sản phẩm (sai định dạng / thiếu cột tên / xuất nhầm file) thì
    KHÔNG động vào kho cũ — giữ nguyên hàng đang bán, chỉ báo 'không thấy sản phẩm'.
    """
    rows = parse_xlsx(path)
    if not rows:
        return {"products": 0, "variants": 0, "khong_thay": True}
    return store.replace_products(rows, source=source)


# ---------- Cho agent dùng ----------

def catalog_summary(max_cats: int = 10) -> str:
    """Khối NGẮN 'shop đang bán gì' — luôn nhét vào ngữ cảnh để bot chủ động mời & chốt."""
    rows = store.instock_product_rows()
    if not rows:
        return ""
    by_cat: dict[str, dict] = {}
    for r in rows:
        c = r.get("category") or "Khác"
        d = by_cat.setdefault(c, {"names": set(), "min": None, "max": None})
        d["names"].add(r.get("product_name") or "")
        p = r.get("price")
        if p is not None:
            d["min"] = p if d["min"] is None else min(d["min"], p)
            d["max"] = p if d["max"] is None else max(d["max"], p)
    total = len({r.get("product_name") for r in rows})
    meta = store.products_meta()
    when = ""
    if meta.get("updated_at"):
        try:
            when = " (cập nhật " + datetime.fromisoformat(meta["updated_at"]).strftime("%d/%m") + ")"
        except ValueError:
            pass
    cats = sorted(by_cat.items(), key=lambda kv: -len(kv[1]["names"]))[:max_cats]
    chunks = []
    for name, d in cats:
        rng = ""
        if d["min"] is not None:
            rng = f" {money(d['min'])}" if d["min"] == d["max"] else f" {money(d['min'])}–{money(d['max'])}"
        chunks.append(f"{name} {len(d['names'])} mẫu{rng}")
    return (f"KHO HÀNG SHOP ĐANG CÓ{when} — tổng {total} sản phẩm còn bán. "
            f"Nhóm hàng: " + "; ".join(chunks) + ".")


_STOP = {"co", "khong", "cho", "hoi", "mua", "can", "nao", "tam", "khoang", "gia", "bao",
         "nhieu", "cai", "chiec", "doi", "cua", "voi", "va", "em", "anh", "chi", "shop",
         "oi", "minh", "ban", "the", "la", "cot", "loai", "muon", "xem", "tu", "van", "gi"}


def _tokens(query: str) -> list[str]:
    toks = re.findall(r"\w+", _no_accent(query), re.UNICODE)
    return [t for t in toks if len(t) >= 2 and t not in _STOP]


def search_for_agent(query: str, max_products: int = 8) -> str:
    """CÔNG CỤ cho agent: tra đúng hàng ĐANG CÓ theo nhu cầu khách. Trả JSON gọn."""
    rows = store.instock_product_rows()
    if not rows:
        return json.dumps({"ket_qua": [], "ghi_chu": "Kho sản phẩm đang trống — chưa tải danh sách."},
                          ensure_ascii=False)
    toks = _tokens(query)

    # Gom theo sản phẩm cha
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r.get("product_name") or "", []).append(r)

    scored = []
    for name, variants in groups.items():
        text = " ".join([
            name, variants[0].get("brand") or "", variants[0].get("category") or "",
            _brand_synonyms(variants[0].get("brand") or ""),
            " ".join(v.get("attrs") or "" for v in variants),
        ])
        # Khớp TRỌN TỪ (không khớp một phần) để 'uong' không dính 'xuong/vuong'.
        hay_words = set(re.findall(r"\w+", _no_accent(text), re.UNICODE))
        score = sum(1 for t in toks if t in hay_words) if toks else 0
        scored.append((score, name, variants))

    matched = [s for s in scored if s[0] > 0]
    matched.sort(key=lambda s: (-s[0], s[1]))
    total_matched = len(matched)
    use = matched[:max_products]
    if not use:  # không trúng từ khoá nào → mời agent hỏi rõ nhu cầu
        return json.dumps({"ket_qua": [], "ghi_chu": "Chưa khớp mẫu nào với từ khoá; hãy hỏi rõ nhu cầu "
                           "(môn/loại đồ, ngân sách, trình độ) rồi tra lại."}, ensure_ascii=False)

    items = []
    for _, name, variants in use:
        prices = [v["price"] for v in variants if v.get("price") is not None]
        pmin, pmax = (min(prices), max(prices)) if prices else (None, None)
        gia = "?" if pmin is None else (money(pmin) if pmin == pmax else f"{money(pmin)}–{money(pmax)}")
        lua_chon = []
        for v in variants:
            a = (v.get("attrs") or "").strip()
            if a and a not in lua_chon:
                lua_chon.append(a)
        qtys = [v["stock_qty"] for v in variants if v.get("stock_qty") is not None]
        item = {"ten": name, "nhom": variants[0].get("category") or "", "gia": gia,
                "so_phien_ban": len(variants)}
        if lua_chon:
            item["lua_chon"] = lua_chon[:12]
        if qtys:  # có số tồn thật → nêu để tạo khan hiếm chính xác
            tong = sum(qtys)
            item["ton_kho"] = tong
            if min(qtys) <= LOW_STOCK:
                item["sap_het"] = True
        items.append(item)

    out = {"ket_qua": items}
    if total_matched > len(items):
        out["con_them"] = total_matched - len(items)
    return json.dumps(out, ensure_ascii=False)
