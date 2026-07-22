"""Trang quản trị chạy trên máy (localhost) để chủ sân tự nhập/sửa chìa khoá
và quản lý nhiều Trang Facebook — không cần đụng file kỹ thuật.

Chạy: python run_admin.py  → mở http://127.0.0.1:8760
Chỉ nghe ở 127.0.0.1 (máy của bạn), không mở ra internet.
"""
from __future__ import annotations

from flask import Flask, redirect, render_template_string, request, url_for

from .. import db, store
from ..config import config
from ..facebook import client as fb_client
from . import supervisor
from . import zalo_supervisor

app = Flask(__name__)

BASE = """
<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trợ lý tự động — Quản trị</title>
<style>
 :root{--b:#2563eb;--bg:#f5f7fb;--card:#fff;--line:#e5e9f2;--ok:#16a34a;--bad:#dc2626;}
 *{box-sizing:border-box} body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:var(--bg);color:#1f2937}
 header{background:var(--b);color:#fff;padding:16px 22px;font-size:20px;font-weight:700}
 .wrap{max-width:820px;margin:22px auto;padding:0 16px}
 .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:18px}
 h2{margin:.2em 0 .6em;font-size:18px} h3{font-size:16px;margin:.4em 0}
 label{display:block;font-weight:600;margin:12px 0 4px;font-size:14px}
 .hint{font-weight:400;color:#6b7280;font-size:12px;margin-top:2px}
 input,textarea,select{width:100%;padding:10px;border:1px solid var(--line);border-radius:9px;font-size:14px;font-family:inherit}
 textarea{min-height:64px} .row{display:flex;gap:12px;flex-wrap:wrap} .row>div{flex:1;min-width:220px}
 button,.btn{background:var(--b);color:#fff;border:0;border-radius:9px;padding:10px 16px;font-size:14px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block}
 .btn.grey{background:#6b7280}.btn.red{background:var(--bad)}.btn.small{padding:6px 12px;font-size:13px}
 table{width:100%;border-collapse:collapse;margin-top:8px} td,th{padding:9px;border-bottom:1px solid var(--line);text-align:left;font-size:14px}
 .badge{font-size:12px;padding:2px 8px;border-radius:20px} .b-ok{background:#dcfce7;color:var(--ok)} .b-no{background:#fee2e2;color:var(--bad)}
 .flash{background:#ecfeff;border:1px solid #a5f3fc;color:#0e7490;padding:10px 14px;border-radius:9px;margin-bottom:14px}
 .muted{color:#6b7280;font-size:13px}
</style></head><body>
<header>🛠️ Trợ lý tự động — Trang quản trị</header>
<div class="wrap">
{% if flash %}<div class="flash">{{ flash }}</div>{% endif %}
{{ body|safe }}
</div></body></html>
"""

HOME = """
<div class="card" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px">
 <div>🤖 <b>Bot:</b>
   {% if bot_running %}<span class="badge b-ok">đang chạy</span>{% else %}<span class="badge b-no">đang tắt</span>{% endif %}
   <div class="hint">Đổi chìa khoá/tài khoản xong, bấm "Khởi động lại" để áp dụng ngay.</div>
 </div>
 <div>
   <a class="btn small" href="{{ url_for('bot_ctl', action='restart') }}">🔄 Khởi động lại</a>
   {% if bot_running %}<a class="btn small red" href="{{ url_for('bot_ctl', action='stop') }}">⏹ Tắt</a>
   {% else %}<a class="btn small" href="{{ url_for('bot_ctl', action='start') }}">▶️ Bật</a>{% endif %}
 </div>
</div>

<div class="card">
 <h2>⚙️ Cấu hình chung</h2>
 <form method="post" action="{{ url_for('save_settings') }}">
  <label>Mã bot Telegram <span class="hint">(từ @BotFather)</span></label>
  <input name="telegram_bot_token" value="{{ s.telegram_bot_token }}" placeholder="1234567:ABC...">
  <label>Telegram của bạn (chat id) <span class="hint">(chỉ mình bạn điều khiển bot)</span></label>
  <input name="telegram_owner_chat_id" value="{{ s.telegram_owner_chat_id }}" placeholder="vd: 823666685">
  <div style="border:1px solid #e3e3e3;border-radius:8px;padding:10px;margin:6px 0;background:#fafafa">
   <label>🧠 Bộ não AI đang dùng
     <span class="hint">(chọn Claude hoặc Gemini — bấm Lưu là đổi ngay)</span></label>
   <div class="row">
    <label style="font-weight:400"><input type="radio" name="ai_provider" value="claude"
       {{ 'checked' if (s.ai_provider or 'claude') == 'claude' else '' }}> Claude (Anthropic)</label>
    <label style="font-weight:400"><input type="radio" name="ai_provider" value="gemini"
       {{ 'checked' if s.ai_provider == 'gemini' else '' }}> Gemini (Google)</label>
    <a class="btn small grey" href="{{ url_for('check_ai') }}">🔎 Kiểm tra AI đang chọn</a>
   </div>
   <label>Khoá Claude API <span class="hint">(console.anthropic.com → API Keys)</span></label>
   <input name="anthropic_api_key" value="{{ s.anthropic_api_key }}" placeholder="sk-ant-...">
   <div class="row">
    <div><label>Model Claude</label><input name="anthropic_model" value="{{ s.anthropic_model }}"></div>
    <div><label>Model Gemini</label><input name="gemini_model" value="{{ s.gemini_model }}" placeholder="gemini-2.5-flash"></div>
   </div>
   <label>Khoá Gemini API <span class="hint">(aistudio.google.com → API Keys)</span></label>
   <input name="gemini_api_key" value="{{ s.gemini_api_key }}" placeholder="AIza...">
  </div>
  <div class="row">
   <div><label>Phiên bản Graph API</label><input name="fb_api_version" value="{{ s.fb_api_version }}"></div>
  </div>
  <div class="row">
   <div><label>Trần ngân sách/ngày (VND) <span class="hint">bot không được vượt</span></label>
    <input name="ads_max_daily_budget_vnd" value="{{ s.ads_max_daily_budget_vnd }}"></div>
   <div><label>Giờ báo cáo quảng cáo</label><input name="daily_ads_report_hour" value="{{ s.daily_ads_report_hour }}"></div>
   <div><label>Giờ gửi bản nháp</label><input name="daily_post_draft_hour" value="{{ s.daily_post_draft_hour }}"></div>
  </div>
  <div style="margin-top:16px"><button type="submit">💾 Lưu cấu hình chung</button></div>
 </form>
</div>

<div class="card">
 <h2>🏷 Các Trang Facebook ({{ pages|length }})</h2>
 <p class="muted">Thêm nhiều Trang tuỳ ý. Mỗi Trang có chìa khoá và giọng điệu riêng.</p>
 <table>
  <tr><th>Tên</th><th>Đăng bài</th><th>Quảng cáo</th><th>Bật</th><th></th></tr>
  {% for p in pages %}
  <tr>
   <td>{{ p.name }}</td>
   <td>{% if p.fb_page_id and p.fb_page_token %}<span class="badge b-ok">sẵn sàng</span>{% else %}<span class="badge b-no">thiếu</span>{% endif %}</td>
   <td>{% if p.fb_ad_account_id and p.fb_ads_token %}<span class="badge b-ok">sẵn sàng</span>{% else %}<span class="badge b-no">thiếu</span>{% endif %}</td>
   <td>{{ '✅' if p.enabled else '⏸' }}</td>
   <td>
     <a class="btn small" href="{{ url_for('page_form', page_id=p.id) }}">Sửa</a>
     <a class="btn small grey" href="{{ url_for('page_test', page_id=p.id) }}">Kiểm tra</a>
   </td>
  </tr>
  {% endfor %}
 </table>
 <div style="margin-top:14px"><a class="btn" href="{{ url_for('page_form', page_id=0) }}">➕ Thêm Trang mới</a></div>
</div>

<div class="card">
 <h2>🏸 Sân alobo ({{ venues|length }}) — báo lịch trống vào nhóm Zalo</h2>
 <p class="muted">Mỗi sân một dòng (mã sân alobo riêng). Bot tự đọc lịch trống và báo nhóm Zalo
  vào các giờ cố định (mặc định 10h & 14h cho hôm nay, 22h cho ngày mai — sửa ở cấu hình chung).
  Bấm <b>Xem trước</b> để đọc thử lịch ngay (không gửi nhóm).</p>
 <table>
  <tr><th>Tên sân</th><th>Mã sân</th><th>Loại</th><th>Báo qua</th><th>Bật</th><th></th></tr>
  {% for v in venues %}
  <tr>
   <td>{{ v.name }}</td>
   <td>{% if v.slug %}<span class="badge b-ok">{{ v.slug }}</span>{% else %}<span class="badge b-no">thiếu</span>{% endif %}</td>
   <td>{{ ['Truyền Thống','Điều Hoà','Ngày Lễ'][v.court_index or 0] }}</td>
   <td>{{ v.notify_channel }}</td>
   <td>{{ '✅' if v.enabled else '⏸' }}</td>
   <td><a class="btn small grey" href="{{ url_for('venue_preview', vid=v.id) }}">👁 Xem trước</a>
       <a class="btn small" href="{{ url_for('venue_form', vid=v.id) }}">Sửa</a></td>
  </tr>
  {% endfor %}
 </table>
 <div style="margin-top:14px"><a class="btn" href="{{ url_for('venue_form', vid=0) }}">➕ Thêm sân</a></div>
</div>

<div class="card">
 <h2>💬 Tài khoản Zalo ({{ zalos|length }})</h2>
 <p class="muted">Gửi thông báo vào nhóm Zalo + trợ lý cầu lông tự trả lời khi bị tag. Nên dùng
  tài khoản phụ + SIM riêng. Thêm nhiều tài khoản tuỳ ý; đổi tài khoản chỉ cần sửa ở đây.</p>
 <table>
  <tr><th>Tên</th><th>Cách nối</th><th>Nhóm</th><th>Tự trả lời</th><th>Bật</th><th></th></tr>
  {% for z in zalos %}
  <tr>
   <td>{{ z.name }}</td><td>{{ 'Bot chính thức' if z.method=='official_bot' else 'Tài khoản cá nhân' }}</td>
   <td>{{ z.group_ids or '—' }}</td><td>{{ '✅' if z.auto_reply else '—' }}</td>
   <td>{{ '✅' if z.enabled else '⏸' }}</td>
   <td>
     <a class="btn small" href="{{ url_for('zalo_form', zid=z.id) }}">Sửa</a>
     <a class="btn small grey" href="{{ url_for('zalo_test', zid=z.id) }}">Kiểm tra / Lấy mã nhóm</a>
   </td>
  </tr>
  {% endfor %}
 </table>
 <div style="margin-top:14px"><a class="btn" href="{{ url_for('zalo_form', zid=0) }}">➕ Thêm tài khoản Zalo</a></div>
</div>

<div class="card">
 <h2>🔗 Kết nối Zalo cá nhân (quét QR) — để đăng vào nhóm thường</h2>
 <p class="muted">Dùng cho tài khoản Zalo kiểu "cá nhân". Đăng nhập bằng quét QR, có VAN AN TOÀN
  né khóa (giãn tin, giới hạn/giờ/ngày, khung giờ).</p>
 <a class="btn" href="{{ url_for('zalo_service') }}">Mở trang kết nối &amp; an toàn Zalo →</a>
</div>

<div class="card">
 <h2>🧠 Bộ não — kiến thức riêng ({{ knowledge|length }})</h2>
 <p class="muted">Bạn nhập kiến thức mới (bí quyết, thông tin sản phẩm, bảng giá, câu hỏi hay gặp...),
  bot sẽ TỰ DÙNG khi trả lời (cả trợ lý Telegram lẫn bot Zalo). Thêm/sửa lúc nào cũng được.</p>
 <table>
  <tr><th>Tiêu đề</th><th>Nội dung (rút gọn)</th><th>Bật</th><th></th></tr>
  {% for k in knowledge %}
  <tr>
   <td>{{ k.title or '(không tiêu đề)' }}</td>
   <td>{{ (k.content or '')[:60] }}{% if (k.content or '')|length > 60 %}…{% endif %}</td>
   <td>{{ '✅' if k.enabled else '⏸' }}</td>
   <td><a class="btn small" href="{{ url_for('knowledge_form', kid=k.id) }}">Sửa</a></td>
  </tr>
  {% endfor %}
 </table>
 <div style="margin-top:14px"><a class="btn" href="{{ url_for('knowledge_form', kid=0) }}">➕ Thêm kiến thức</a></div>
 <p class="hint">Mẹo: bạn cũng có thể nhắn nhanh cho bot Telegram: <code>/ghinho &lt;nội dung&gt;</code></p>
</div>
"""

KNOWLEDGE_FORM = """
<div class="card">
 <h2>{{ '➕ Thêm kiến thức' if not k.id else '✏️ Sửa kiến thức' }}</h2>
 <form method="post" action="{{ url_for('knowledge_save') }}">
  <input type="hidden" name="id" value="{{ k.id or 0 }}">
  <label>Tiêu đề <span class="hint">(ngắn gọn, giúp bot & bạn dễ tìm)</span></label>
  <input name="title" value="{{ k.title or '' }}" placeholder="VD: Bảng giá thuê sân VMH Hạ Long">
  <label>Nội dung *</label>
  <textarea name="content" style="min-height:140px" required placeholder="VD: Sân VMH Hạ Long: giờ thường 80k/giờ, giờ cao điểm (18h-21h) 100k/giờ. Đặt sân gọi 0339.288.166.">{{ k.content or '' }}</textarea>
  <label>Từ khoá liên quan <span class="hint">cách nhau dấu phẩy, giúp bot tìm đúng lúc</span></label>
  <input name="tags" value="{{ k.tags or '' }}" placeholder="giá sân, thuê sân, hạ long">
  <label><input type="checkbox" name="enabled" {{ 'checked' if (k.enabled if k.id else 1) }} style="width:auto"> Đang dùng</label>
  <div style="margin-top:16px">
   <button type="submit">💾 Lưu kiến thức</button>
   <a class="btn grey" href="{{ url_for('home') }}">Quay lại</a>
   {% if k.id %}<a class="btn red" href="{{ url_for('knowledge_delete', kid=k.id) }}" onclick="return confirm('Xoá kiến thức này?')" style="float:right">🗑 Xoá</a>{% endif %}
  </div>
 </form>
</div>
"""

VENUE_FORM = """
<div class="card">
 <h2>{{ '➕ Thêm sân' if not v.id else '✏️ Sửa sân' }}</h2>
 <form method="post" action="{{ url_for('venue_save') }}">
  <input type="hidden" name="id" value="{{ v.id or 0 }}">
  <label>Tên sân (hiển thị trong tin) *</label>
  <input name="name" value="{{ v.name or '' }}" placeholder="VMH CS1 Cẩm Phả" required>
  <label>Mã sân alobo (slug) *
    <span class="hint">phần cuối link đặt sân, vd datlich.alobo.vn/san/<b>sport_vmh_badminton_cn1</b></span></label>
  <input name="slug" value="{{ v.slug or '' }}" placeholder="sport_vmh_badminton_cn1" required>
  <div class="row">
   <div><label>Loại sân</label>
     <select name="court_index">
       <option value="0" {{ 'selected' if (v.court_index or 0)==0 }}>Truyền Thống</option>
       <option value="1" {{ 'selected' if v.court_index==1 }}>Điều Hoà Mùa Hè</option>
       <option value="2" {{ 'selected' if v.court_index==2 }}>Ngày Lễ</option>
     </select></div>
   <div><label>Sân cần canh <span class="hint">để trống = tất cả</span></label>
     <input name="courts" value="{{ v.courts or '' }}" placeholder="để trống"></div>
  </div>
  <div class="row">
   <div><label>Báo qua</label>
     <select name="notify_channel">
       <option value="telegram" {{ 'selected' if v.notify_channel=='telegram' }}>Telegram (an toàn)</option>
       <option value="zalo" {{ 'selected' if v.notify_channel=='zalo' }}>Nhóm Zalo</option>
     </select></div>
   <div><label>Nếu báo Zalo, dùng tài khoản Zalo</label>
     <select name="zalo_account_ref">
       <option value="">— chọn —</option>
       {% for z in zalos %}<option value="{{ z.id }}" {{ 'selected' if v.zalo_account_ref==z.id }}>{{ z.name }}</option>{% endfor %}
     </select></div>
  </div>
  <label><input type="checkbox" name="enabled" {{ 'checked' if (v.enabled if v.id else 1) }} style="width:auto"> Bật canh sân này</label>
  <div style="margin-top:16px">
   <button type="submit">💾 Lưu sân</button>
   <a class="btn grey" href="{{ url_for('home') }}">Quay lại</a>
   {% if v.id %}<a class="btn red" href="{{ url_for('venue_delete', vid=v.id) }}" onclick="return confirm('Xoá sân này?')" style="float:right">🗑 Xoá</a>{% endif %}
  </div>
 </form>
</div>
"""

ZALO_SERVICE = """
<div class="card">
 <h2>🔗 Kết nối Zalo cá nhân</h2>
 {% if not node_ok %}
  <p class="flash">⚠️ Không tìm thấy Node trên máy — dịch vụ Zalo cá nhân cần Node để chạy.</p>
 {% endif %}
 <p>Trạng thái: <b>{{ status_vi }}</b>{% if st.name %} · Tài khoản: <b>{{ st.name }}</b>{% endif %}
   {% if st.sentToday is defined %} · Đã gửi hôm nay: {{ st.sentToday }}{% endif %}</p>

 {% if st.state == 'awaiting_qr' %}
  <p><b>Quét mã QR bên dưới bằng app Zalo</b> (tài khoản phụ): mở Zalo → Cá nhân → biểu tượng quét mã.</p>
  <img src="{{ url_for('zalo_qr') }}?t={{ ts }}" alt="QR" style="max-width:260px;border:1px solid #e5e9f2;border-radius:10px">
  <p class="hint">Quét xong, bấm "Kiểm tra lại" sau vài giây.</p>
 {% elif st.state == 'logged_in' %}
  <p>✅ Đã đăng nhập. Bấm dưới để lấy danh sách nhóm và mã nhóm.</p>
 {% endif %}

 <div style="margin-top:12px">
  <a class="btn small" href="{{ url_for('zalo_service') }}">🔄 Kiểm tra lại</a>
  <a class="btn small" href="{{ url_for('zalo_relogin') }}">📷 Đăng nhập / Quét lại QR</a>
  <a class="btn small grey" href="{{ url_for('zalo_service', groups=1) }}">📋 Lấy danh sách nhóm</a>
 </div>

 {% if groups is not none %}
  <h3>Nhóm tài khoản đang tham gia</h3>
  {% if groups %}
   <table><tr><th>Tên nhóm</th><th>Mã nhóm (dán vào ô "ID các nhóm")</th></tr>
   {% for g in groups %}<tr><td>{{ g.name }}</td><td><code>{{ g.id }}</code></td></tr>{% endfor %}</table>
  {% else %}<p class="muted">Chưa thấy nhóm nào (hoặc chưa đăng nhập xong).</p>{% endif %}
 {% endif %}
</div>

<div class="card">
 <h2>🛡️ Van an toàn (né bị khóa)</h2>
 <p class="muted">Các giới hạn để tài khoản hành xử giống người thật. Sửa xong bấm Lưu (dịch vụ sẽ tự khởi động lại).</p>
 <form method="post" action="{{ url_for('zalo_save_safety') }}">
  <div class="row">
   <div><label>Giãn tối thiểu giữa 2 tin (giây)</label><input name="zalo_min_gap_sec" value="{{ s.zalo_min_gap_sec }}"></div>
   <div><label>Cộng ngẫu nhiên tới (giây)</label><input name="zalo_jitter_sec" value="{{ s.zalo_jitter_sec }}"></div>
  </div>
  <div class="row">
   <div><label>Tối đa tin/giờ</label><input name="zalo_max_per_hour" value="{{ s.zalo_max_per_hour }}"></div>
   <div><label>Tối đa tin/ngày</label><input name="zalo_max_per_day" value="{{ s.zalo_max_per_day }}"></div>
   <div><label>Khung giờ được gửi</label><input name="zalo_allowed_hours" value="{{ s.zalo_allowed_hours }}" placeholder="7-22"></div>
  </div>
  <div style="margin-top:14px"><button type="submit">💾 Lưu van an toàn</button>
   <a class="btn grey" href="{{ url_for('home') }}">Về trang chính</a></div>
 </form>
</div>
"""

ZALO_FORM = """
<div class="card">
 <h2>{{ '➕ Thêm tài khoản Zalo' if not z.id else '✏️ Sửa tài khoản Zalo' }}</h2>
 <form method="post" action="{{ url_for('zalo_save') }}">
  <input type="hidden" name="id" value="{{ z.id or 0 }}">
  <label>Tên gợi nhớ *</label>
  <input name="name" value="{{ z.name or '' }}" placeholder="Zalo phụ Sân VMH" required>
  <div class="row">
   <div><label>Cách nối</label>
     <select name="method">
       <option value="official_bot" {{ 'selected' if z.method=='official_bot' }}>Zalo Bot chính thức (khuyên dùng)</option>
       <option value="personal" {{ 'selected' if z.method=='personal' }}>Tài khoản cá nhân (zca-js)</option>
     </select></div>
   <div><label>SIM/số điện thoại (ghi nhớ)</label><input name="phone" value="{{ z.phone or '' }}"></div>
  </div>
  <label>Token Zalo Bot <span class="hint">(nếu dùng Bot chính thức)</span></label>
  <input name="bot_token" value="{{ z.bot_token or '' }}">
  <label>ID các nhóm Zalo cần đăng <span class="hint">cách nhau dấu phẩy</span></label>
  <input name="group_ids" value="{{ z.group_ids or '' }}">
  <label>🎭 Vai của trợ lý (khi tự trả lời trong nhóm) <span class="hint">để trống = HLV cầu lông thân thiện mặc định</span></label>
  <textarea name="persona" placeholder="VD: Bạn là 'Thầy Tuấn' — HLV cầu lông 10 năm kinh nghiệm, nói chuyện dí dỏm, hay động viên học viên...">{{ z.persona or '' }}</textarea>
  <div class="row">
   <div><label><input type="checkbox" name="auto_reply" {{ 'checked' if z.auto_reply }} style="width:auto"> Tự trả lời cầu lông khi bị tag</label></div>
   <div><label><input type="checkbox" name="enabled" {{ 'checked' if (z.enabled if z.id else 1) }} style="width:auto"> Bật tài khoản này</label></div>
  </div>
  <div style="margin-top:16px">
   <button type="submit">💾 Lưu tài khoản Zalo</button>
   <a class="btn grey" href="{{ url_for('home') }}">Quay lại</a>
   {% if z.id %}<a class="btn red" href="{{ url_for('zalo_delete', zid=z.id) }}" onclick="return confirm('Xoá tài khoản Zalo này?')" style="float:right">🗑 Xoá</a>{% endif %}
  </div>
 </form>
</div>
"""

PAGE_FORM = """
<div class="card">
 <h2>{{ '➕ Thêm Trang' if not p.id else '✏️ Sửa Trang' }}</h2>
 <form method="post" action="{{ url_for('page_save') }}">
  <input type="hidden" name="id" value="{{ p.id or 0 }}">
  <label>Tên gợi nhớ (bạn tự đặt) *</label>
  <input name="name" value="{{ p.name or '' }}" placeholder="vd: Sân VMH — Trang chính" required>

  <h3>📣 Đăng bài & báo cáo Trang</h3>
  <label>ID Trang Facebook</label>
  <input name="fb_page_id" value="{{ p.fb_page_id or '' }}" placeholder="vd: 1000123456789">
  <label>Token đăng bài của Trang (không hết hạn)</label>
  <input name="fb_page_token" value="{{ p.fb_page_token or '' }}" placeholder="EAAB...">

  <h3>🎯 Quảng cáo</h3>
  <label>ID tài khoản quảng cáo</label>
  <input name="fb_ad_account_id" value="{{ p.fb_ad_account_id or '' }}" placeholder="act_1234567890">
  <label>Token quảng cáo (System User, không hết hạn)</label>
  <input name="fb_ads_token" value="{{ p.fb_ads_token or '' }}" placeholder="EAAB...">

  <h3>✍️ Giọng điệu để AI viết bài</h3>
  <label>Tên doanh nghiệp/Trang (hiển thị trong bài)</label>
  <input name="business_name" value="{{ p.business_name or '' }}" placeholder="Sân cầu lông VMH">
  <label>Mô tả ngắn</label>
  <textarea name="business_desc" placeholder="Cho thuê sân theo giờ, có căng-tin, chỗ để xe...">{{ p.business_desc or '' }}</textarea>
  <label>Giọng điệu thương hiệu</label>
  <textarea name="brand_tone" placeholder="Thân thiện, gần gũi, khích lệ chơi thể thao...">{{ p.brand_tone or '' }}</textarea>

  <div class="row" style="margin-top:12px">
   <div><label><input type="checkbox" name="auto_post" {{ 'checked' if p.auto_post }} style="width:auto"> Tự gửi bản nháp mỗi sáng</label></div>
   <div><label><input type="checkbox" name="enabled" {{ 'checked' if (p.enabled if p.id else 1) }} style="width:auto"> Bật Trang này</label></div>
  </div>

  <div style="margin-top:16px">
   <button type="submit">💾 Lưu Trang</button>
   <a class="btn grey" href="{{ url_for('home') }}">Quay lại</a>
   {% if p.id %}
   <a class="btn red" href="{{ url_for('page_delete', page_id=p.id) }}"
      onclick="return confirm('Xoá Trang này?')" style="float:right">🗑 Xoá</a>
   {% endif %}
  </div>
 </form>
</div>
"""


def _render(tpl, **kw):
    flash = request.args.get("msg", "")
    body = render_template_string(tpl, **kw)
    return render_template_string(BASE, body=body, flash=flash)


@app.route("/")
def home():
    return _render(HOME, s=store.all_settings(), pages=store.list_pages(),
                   venues=store.list_venues(), zalos=store.list_zalo(),
                   knowledge=store.list_knowledge(),
                   bot_running=supervisor.is_running(), url_for=url_for)


@app.route("/bot/<action>")
def bot_ctl(action: str):
    if action == "restart":
        supervisor.restart(); msg = "Đã khởi động lại bot ✔ (nạp cấu hình mới)"
    elif action == "stop":
        supervisor.stop(); msg = "Đã tắt bot ✔"
    elif action == "start":
        supervisor.start(); msg = "Đã bật bot ✔"
    else:
        msg = "Lệnh không hợp lệ."
    return redirect(url_for("home", msg=msg))


@app.route("/settings", methods=["POST"])
def save_settings():
    for key in ["telegram_bot_token", "telegram_owner_chat_id", "anthropic_api_key",
                "anthropic_model", "ai_provider", "gemini_api_key", "gemini_model",
                "fb_api_version", "ads_max_daily_budget_vnd",
                "daily_ads_report_hour", "daily_post_draft_hour"]:
        if key in request.form:
            store.set_setting(key, request.form.get(key, "").strip())
    return redirect(url_for("home", msg="Đã lưu cấu hình chung ✔"))


@app.route("/check-ai")
def check_ai():
    from ..ai import llm
    ok, msg = llm.check_provider()
    return redirect(url_for("home", msg=("AI OK ✔ — " + msg) if ok else ("AI LỖI ✖ — " + msg)))


_STATUS_VI = {"starting": "đang khởi động", "awaiting_qr": "chờ quét QR",
              "scanned": "đã quét, đang xác nhận", "logged_in": "đã đăng nhập",
              "error": "lỗi", "off": "chưa chạy"}


@app.route("/zalo-service")
def zalo_service():
    from ..zalo import transport
    st = transport.node_status()
    status_vi = _STATUS_VI.get(st.get("state"), st.get("state", "?"))
    if st.get("state") == "error" and st.get("error"):
        status_vi += f" ({st['error']})"
    groups = None
    if request.args.get("groups"):
        g = transport.node_groups()
        groups = g.get("groups", []) if "error" not in g else []
    return _render(ZALO_SERVICE, st=st, status_vi=status_vi, s=store.all_settings(),
                   groups=groups, node_ok=zalo_supervisor.node_available(),
                   ts=st.get("sentToday", 0), url_for=url_for)


@app.route("/zalo-service/qr.png")
def zalo_qr():
    from flask import send_file
    qr = db.DATA_DIR / "zalo_qr.png"
    if qr.exists():
        return send_file(str(qr), mimetype="image/png")
    return ("Chưa có QR", 404)


@app.route("/zalo-service/relogin")
def zalo_relogin():
    import requests as _rq
    zalo_supervisor.start()
    try:
        _rq.post((store.get_setting("zalo_service_url") or "http://127.0.0.1:8765") + "/relogin", timeout=5)
    except Exception:  # noqa: BLE001
        pass
    return redirect(url_for("zalo_service", msg="Đang tạo mã QR mới, chờ vài giây rồi Kiểm tra lại."))


@app.route("/zalo-service/save-safety", methods=["POST"])
def zalo_save_safety():
    for k in ["zalo_min_gap_sec", "zalo_jitter_sec", "zalo_max_per_hour",
              "zalo_max_per_day", "zalo_allowed_hours"]:
        if k in request.form:
            store.set_setting(k, request.form.get(k, "").strip())
    zalo_supervisor.restart()
    return redirect(url_for("zalo_service", msg="Đã lưu van an toàn ✔"))


@app.route("/knowledge/<int:kid>")
def knowledge_form(kid: int):
    k = store.get_knowledge(kid) if kid else {}
    return _render(KNOWLEDGE_FORM, k=k or {}, url_for=url_for)


@app.route("/knowledge/save", methods=["POST"])
def knowledge_save():
    f = request.form
    data = {k: f.get(k, "").strip() for k in ["title", "content", "tags"]}
    data["enabled"] = 1 if f.get("enabled") else 0
    kid = int(f.get("id", 0) or 0)
    if not data["content"]:
        return redirect(url_for("home", msg="Kiến thức phải có nội dung."))
    store.update_knowledge(kid, data) if kid else store.create_knowledge(data)
    return redirect(url_for("home", msg="Đã lưu kiến thức ✔ (bot dùng ngay)"))


@app.route("/knowledge/<int:kid>/delete")
def knowledge_delete(kid: int):
    store.delete_knowledge(kid)
    return redirect(url_for("home", msg="Đã xoá kiến thức ✔"))


@app.route("/venue/<int:vid>")
def venue_form(vid: int):
    v = store.get_venue(vid) if vid else {}
    return _render(VENUE_FORM, v=v or {}, zalos=store.list_zalo(), url_for=url_for)


@app.route("/venue/save", methods=["POST"])
def venue_save():
    f = request.form
    data = {k: f.get(k, "").strip() for k in
            ["name", "slug", "court_index", "courts", "notify_channel", "zalo_account_ref"]}
    data["enabled"] = 1 if f.get("enabled") else 0
    vid = int(f.get("id", 0) or 0)
    store.update_venue(vid, data) if vid else store.create_venue(data)
    return redirect(url_for("home", msg="Đã lưu sân ✔ (bấm Khởi động lại để áp dụng lịch báo)"))


@app.route("/venue/<int:vid>/preview")
def venue_preview(vid: int):
    """Đọc thử lịch trống của MỘT sân NGAY (không gửi nhóm) để chủ xem trước."""
    from ..alobo import monitor as _m, source as _s
    v = store.get_venue(vid)
    if not v:
        return redirect(url_for("home", msg="Không tìm thấy sân."))
    cfg = _m.venue_config(v)
    if not cfg.get("slug"):
        return redirect(url_for("home", msg=f"[{v['name']}] chưa có Mã sân (slug)."))
    try:
        from datetime import datetime
        slots = _s.fetch_schedule(cfg, day_offset=0)
        ranges = _m.free_ranges(slots, cfg["courts"], from_time=datetime.now().strftime("%H:%M"))
        if not ranges:
            return redirect(url_for("home", msg=f"[{v['name']}] đọc OK ✔ — hiện các sân đã KÍN (từ giờ tới cuối ngày)."))
        txt = "; ".join(f"{c} {a}-{b}" for c, a, b in ranges)
        return redirect(url_for("home", msg=f"[{v['name']}] đọc OK ✔ — TRỐNG: {txt}"))
    except Exception as e:  # noqa: BLE001
        return redirect(url_for("home", msg=f"[{v['name']}] đọc LỖI ✖: {e}"))


@app.route("/venue/<int:vid>/delete")
def venue_delete(vid: int):
    store.delete_venue(vid)
    return redirect(url_for("home", msg="Đã xoá sân ✔"))


@app.route("/zalo/<int:zid>")
def zalo_form(zid: int):
    z = store.get_zalo(zid) if zid else {}
    return _render(ZALO_FORM, z=z or {}, url_for=url_for)


@app.route("/zalo/save", methods=["POST"])
def zalo_save():
    f = request.form
    data = {k: f.get(k, "").strip() for k in ["name", "method", "bot_token", "phone", "group_ids", "persona"]}
    data["auto_reply"] = 1 if f.get("auto_reply") else 0
    data["enabled"] = 1 if f.get("enabled") else 0
    zid = int(f.get("id", 0) or 0)
    store.update_zalo(zid, data) if zid else store.create_zalo(data)
    return redirect(url_for("home", msg="Đã lưu tài khoản Zalo ✔ (bấm Khởi động lại để áp dụng)"))


@app.route("/zalo/<int:zid>/delete")
def zalo_delete(zid: int):
    store.delete_zalo(zid)
    return redirect(url_for("home", msg="Đã xoá tài khoản Zalo ✔"))


@app.route("/zalo/<int:zid>/test")
def zalo_test(zid: int):
    from ..zalo import botapi
    z = store.get_zalo(zid)
    if not z:
        return redirect(url_for("home", msg="Không tìm thấy tài khoản Zalo."))
    if z.get("method") != "official_bot":
        return redirect(url_for("home", msg=f"[{z['name']}] Đang để kiểu 'cá nhân' — nút này chỉ dùng cho Zalo Bot chính thức."))
    if not z.get("bot_token"):
        return redirect(url_for("home", msg=f"[{z['name']}] Chưa có token bot — hãy điền token rồi Kiểm tra."))
    ok, info = botapi.check(z["bot_token"])
    if not ok:
        return redirect(url_for("home", msg=f"[{z['name']}] LỖI: {info}"))
    try:
        groups = botapi.find_group_chats(z["bot_token"])
    except Exception:  # noqa: BLE001
        groups = []
    if groups:
        glist = "; ".join(f"{g['title']} → mã {g['chat_id']}" for g in groups)
        extra = f" | Nhóm tìm thấy: {glist} (dán mã nhóm vào ô 'ID các nhóm')"
    else:
        extra = " | Chưa thấy nhóm nào. Hãy thêm bot vào nhóm rồi cho ai đó @nhắc bot một câu, sau đó bấm lại."
    return redirect(url_for("home", msg=f"[{z['name']}] {info}{extra}"))


@app.route("/page/<int:page_id>")
def page_form(page_id: int):
    p = store.get_page(page_id) if page_id else {}
    return _render(PAGE_FORM, p=p or {}, url_for=url_for)


@app.route("/page/save", methods=["POST"])
def page_save():
    f = request.form
    data = {
        "name": f.get("name", "").strip(),
        "fb_page_id": f.get("fb_page_id", "").strip(),
        "fb_page_token": f.get("fb_page_token", "").strip(),
        "fb_ad_account_id": f.get("fb_ad_account_id", "").strip(),
        "fb_ads_token": f.get("fb_ads_token", "").strip(),
        "business_name": f.get("business_name", "").strip(),
        "business_desc": f.get("business_desc", "").strip(),
        "brand_tone": f.get("brand_tone", "").strip(),
        "auto_post": 1 if f.get("auto_post") else 0,
        "enabled": 1 if f.get("enabled") else 0,
    }
    pid = int(f.get("id", 0) or 0)
    if pid:
        store.update_page(pid, data)
    else:
        store.create_page(data)
    return redirect(url_for("home", msg="Đã lưu Trang ✔"))


@app.route("/page/<int:page_id>/delete")
def page_delete(page_id: int):
    store.delete_page(page_id)
    return redirect(url_for("home", msg="Đã xoá Trang ✔"))


@app.route("/page/<int:page_id>/test")
def page_test(page_id: int):
    p = store.get_page(page_id)
    if not p:
        return redirect(url_for("home", msg="Không tìm thấy Trang."))
    parts = []
    if p.get("fb_page_token"):
        ok, msg = fb_client.check_token(p["fb_page_token"])
        parts.append(("Đăng bài: " + ("OK ✔ " + msg if ok else "LỖI ✖ " + msg)))
    else:
        parts.append("Đăng bài: chưa có token")
    if p.get("fb_ads_token"):
        ok, msg = fb_client.check_token(p["fb_ads_token"])
        parts.append(("Quảng cáo: " + ("OK ✔ " + msg if ok else "LỖI ✖ " + msg)))
    else:
        parts.append("Quảng cáo: chưa có token")
    return redirect(url_for("home", msg=f"[{p['name']}] " + " | ".join(parts)))


@app.route("/internal/zalo-reply", methods=["POST"])
def internal_zalo_reply():
    """Node zca-js gọi vào đây cho MỌI tin: lưu lại (làm kiến thức + trí nhớ) và trả lời nếu nên."""
    from ..ai import zalo_agent
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    asker = data.get("asker", "")
    uid = data.get("uid", "")
    thread_id = str(data.get("thread_id") or "")
    is_group = bool(data.get("is_group"))
    mentioned = bool(data.get("mentioned"))  # được @nhắc ĐÍCH DANH bot (Node đã so uid)

    # 1) LƯU tin của khách để bot học nội dung nhóm + nhớ hội thoại (kể cả tin không trả lời).
    if thread_id and text:
        try:
            store.add_message(thread_id, text, sender=asker, uid=uid,
                              is_group=is_group, is_self=False)
        except Exception:  # noqa: BLE001
            app.logger.exception("zalo-reply: lưu tin lỗi")

    acct = next((z for z in store.list_zalo()
                 if z.get("method") == "personal" and z.get("enabled") and z.get("auto_reply")), None)
    if not acct or not text:
        return {"reply": ""}
    # TRONG NHÓM: CHỈ trả lời khi được @nhắc đích danh. Chat 1-1: trả lời bình thường.
    if is_group and not mentioned:
        return {"reply": ""}
    reply = ""
    try:
        reply = zalo_agent.answer(text, asker, acct.get("persona", ""),
                                  thread_id=thread_id or None, is_group=is_group, uid=uid)
    except Exception:  # noqa: BLE001
        app.logger.exception("zalo-reply: bộ não trả lời lỗi")
    # Được gọi mà AI LỖI hoặc trả RỖNG (server AI quá tải / bị lọc) → nhắn nhẹ thay vì im lặng.
    if not (reply or "").strip():
        who = f"{asker} " if asker else ""
        return {"reply": f"{who}ơi, cho mình xin chút xíu nha, mình đang hơi nghẽn — "
                         f"anh/chị nhắn lại giúp mình sau ít phút nhé! 🙏"}
    # LƯU câu trả lời của bot vào lịch sử để lượt sau nhớ mạch.
    if thread_id:
        try:
            store.add_message(thread_id, reply, sender="Trợ lý", is_group=is_group, is_self=True)
            store.prune_messages(thread_id)
        except Exception:  # noqa: BLE001
            pass
    return {"reply": reply}


def run(host: str = "127.0.0.1", port: int = 8760, manage_bot: bool = True):
    db.init_db()
    store.bootstrap_from_env()
    if manage_bot:
        supervisor.start()        # bot Telegram
        zalo_supervisor.start()   # dịch vụ Zalo (nếu có tài khoản cá nhân bật)
    app.run(host=host, port=port, debug=False)
