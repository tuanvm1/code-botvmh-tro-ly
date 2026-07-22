// Dịch vụ Zalo (zca-js) cho trợ lý tự động — tài khoản cá nhân (phụ).
//
// Chạy nền, làm 3 việc:
//  1) Đăng nhập bằng QR (chủ quét 1 lần), lưu phiên để lần sau khỏi quét lại.
//  2) Nghe tin trong nhóm/1-1; ai tag hỏi thì hỏi phía Python (bộ não cầu lông) rồi trả lời.
//  3) Mở API nội bộ (localhost) để phía Python gửi thông báo sân trống vào nhóm.
//
// VAN AN TOÀN (né bị Zalo khóa): các tin CHỦ ĐỘNG gửi (thông báo) được xếp hàng,
// giãn cách tối thiểu + ngẫu nhiên, giới hạn số tin mỗi giờ/ngày, chỉ gửi trong khung giờ cho phép.
// Tin TRẢ LỜI (phản hồi khi có người hỏi) chỉ delay nhẹ cho giống người.

import { Zalo, ThreadType } from "zca-js";
import express from "express";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, "..", "data");
const SESSION_FILE = path.join(DATA_DIR, "zalo_session.json");
const QR_FILE = path.join(DATA_DIR, "zalo_qr.png");
fs.mkdirSync(DATA_DIR, { recursive: true });

const PY_URL = process.env.PYTHON_URL || "http://127.0.0.1:8760";
const PORT = parseInt(process.env.ZALO_PORT || "8791", 10);

// ---- Van an toàn (đọc từ biến môi trường, có mặc định thận trọng) ----
const SAFE = {
  minGapSec: parseInt(process.env.ZALO_MIN_GAP_SEC || "45", 10),
  jitterSec: parseInt(process.env.ZALO_JITTER_SEC || "60", 10),
  maxPerHour: parseInt(process.env.ZALO_MAX_PER_HOUR || "15", 10),
  maxPerDay: parseInt(process.env.ZALO_MAX_PER_DAY || "100", 10),
  allowedFrom: parseInt((process.env.ZALO_ALLOWED_HOURS || "7-22").split("-")[0], 10),
  allowedTo: parseInt((process.env.ZALO_ALLOWED_HOURS || "7-22").split("-")[1], 10),
};

let api = null;
let state = "starting"; // starting | awaiting_qr | logged_in | error
let selfName = "";
let lastError = "";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const rnd = (n) => Math.floor(Math.random() * (n + 1));
const log = (...a) =>
  console.log(`[zalo ${new Date().toLocaleTimeString("vi-VN", { hour12: false })}]`, ...a);

// ---------- Đăng nhập ----------
function saveSession(creds) {
  try { fs.writeFileSync(SESSION_FILE, JSON.stringify(creds)); } catch {}
}
function loadSession() {
  try { return JSON.parse(fs.readFileSync(SESSION_FILE, "utf8")); } catch { return null; }
}

// Mỗi lần đăng nhập/nối lại tăng "đời" (gen) lên 1; các handler của phiên nghe cũ
// so sánh gen của mình với gen hiện tại, khác thì tự bỏ qua (không nối lại nhầm).
let gen = 0;
// Chờ tăng dần khi nối lại nhiều lần liên tiếp (né đăng nhập dồn dập → dễ bị Zalo khóa).
let backoffMs = 30_000;
const MIN_BACKOFF = 30_000;
const MAX_BACKOFF = 10 * 60_000;
let reconnectTimer = null;

async function startLogin() {
  const zalo = new Zalo();
  // 1) Thử phiên đã lưu (khỏi quét QR)
  const creds = loadSession();
  if (creds) {
    try {
      api = await zalo.login(creds);
      await onLoggedIn();
      return;
    } catch (e) { log(`đăng nhập bằng phiên đã lưu lỗi: ${e?.message ?? e} → cần quét QR`); }
  }
  // 2) Quét QR
  state = "awaiting_qr";
  try {
    api = await zalo.loginQR({ qrPath: QR_FILE }, (ev) => {
      if (ev.type === 0 /* QRCodeGenerated */) {
        try { ev.actions.saveToFile(QR_FILE); } catch {}
        state = "awaiting_qr";
      } else if (ev.type === 1 /* QRCodeExpired */) {
        try { ev.actions.retry(); } catch {}  // tự tạo mã QR mới khi hết hạn
      } else if (ev.type === 2 /* QRCodeScanned */) {
        state = "scanned"; // đã quét, đang xác nhận
      } else if (ev.type === 4 /* GotLoginInfo */) {
        saveSession({ cookie: ev.data.cookie, imei: ev.data.imei, userAgent: ev.data.userAgent });
      }
    });
    await onLoggedIn();
  } catch (e) {
    state = "error";
    lastError = String(e && e.message ? e.message : e);
  }
}

let ownId = "";

async function onLoggedIn() {
  const myGen = ++gen;
  state = "logged_in";
  try { if (fs.existsSync(QR_FILE)) fs.unlinkSync(QR_FILE); } catch {}
  try {
    const info = await api.fetchAccountInfo();
    selfName = info?.profile?.displayName || info?.name || "";
    ownId = String(info?.profile?.userId || info?.userId || "");
  } catch {}
  if (!ownId) { try { ownId = String(api.getOwnId?.() || ""); } catch {} }
  console.log(`[zalo] đăng nhập: ${selfName} (uid=${ownId})`);
  startListener(myGen);
}

// Nối lại bằng PHIÊN ĐÃ LƯU (không đăng nhập QR lại) sau khoảng chờ waitMs.
// Chỉ đây mới được nối lại — có gen mới, các handler cũ tự vô hiệu.
function scheduleReconnect(reason, waitMs) {
  if (reconnectTimer) return;               // đã hẹn nối lại rồi, khỏi chồng
  state = "reconnecting";
  log(`nghe tin dừng (${reason}) — thử nối lại sau ${Math.round(waitMs / 1000)}s`);
  reconnectTimer = setTimeout(async () => {
    reconnectTimer = null;
    const creds = loadSession();
    if (!creds) { log("không có phiên đã lưu — chuyển sang chờ quét QR"); startLogin(); return; }
    try {
      const zalo = new Zalo();
      api = await zalo.login(creds);
      await onLoggedIn();                    // ++gen, nghe lại; backoff reset khi 'connected'
    } catch (e) {
      backoffMs = Math.min(backoffMs * 2, MAX_BACKOFF);
      scheduleReconnect(`nối lại thất bại: ${e?.message ?? e}`, backoffMs);
    }
  }, waitMs);
}

// ---------- Nghe tin & tự trả lời ----------
function startListener(myGen) {
  const cur = () => myGen === gen;           // handler này còn thuộc phiên hiện tại?
  api.listener.on("connected", () => {
    if (!cur()) return;
    backoffMs = MIN_BACKOFF;                  // nối tốt → reset nhịp chờ
    log("nghe tin: đã kết nối, sẵn sàng nhận tin");
  });
  api.listener.on("closed", (code, reason) => {
    if (!cur()) return;                       // phiên cũ bị đóng (vd sau relogin) → mặc kệ
    if (code === 1000) return;                // 1000 = mình chủ động đóng, không nối lại
    // 3000/3003 = tài khoản đang mở ở nơi khác / bị đá → KHÔNG tranh giành liên tục,
    // chờ lâu (5 phút) rồi mới thử lại để chủ dùng Zalo Web bình thường.
    if (code === 3000 || code === 3003) {
      scheduleReconnect(`tài khoản đang được dùng ở nơi khác (mã ${code})`, 5 * 60_000);
    } else {
      const wait = backoffMs;
      backoffMs = Math.min(backoffMs * 2, MAX_BACKOFF);
      scheduleReconnect(`mất kết nối (mã ${code ?? "?"} ${reason ?? ""})`, wait);
    }
  });
  // 'error' của zca-js thường là LỖI GIẢI MÃ 1 TIN LẺ, đường nghe VẪN SỐNG →
  // chỉ ghi log, TUYỆT ĐỐI không ngắt/khởi động lại (tránh đăng nhập dồn dập).
  api.listener.on("error", (err) => {
    if (!cur()) return;
    log(`nghe tin gặp lỗi lẻ (bỏ qua, không ngắt): ${err?.message ?? err?.type ?? "?"}`);
  });
  api.listener.on("message", async (message) => {
    if (!cur()) return;
    try {
      const isPlainText = typeof message?.data?.content === "string";
      if (message.isSelf) return;
      const isGroup = message.type === ThreadType.Group;
      const asker = message.data?.dName || "";
      if (!isPlainText) { log(`tin đến (${isGroup ? "nhóm" : "1-1"}) từ "${asker}": không phải chữ, bỏ qua`); return; }
      const text = message.data.content;

      // @nhắc ĐÍCH DANH bot? (uid trùng chính mình — chỉ chắc khi biết ownId).
      const mentions = Array.isArray(message.data.mentions) ? message.data.mentions : [];
      const mentioned = !!ownId && mentions.some((m) => String(m.uid) === ownId);
      log(`tin đến (${isGroup ? "nhóm" : "1-1"}) từ "${asker}"${mentioned ? " [được @nhắc]" : ""}: ${text.slice(0, 100)}`);

      // Bỏ TẤT CẢ "@tên" (kể cả @bot) khỏi câu cho sạch. Cắt từ CUỐI về ĐẦU để pos không lệch.
      let question = text;
      const spans = mentions.filter((m) => typeof m.pos === "number" && typeof m.len === "number")
                            .sort((a, b) => b.pos - a.pos);
      for (const m of spans) {
        question = question.slice(0, m.pos) + question.slice(m.pos + m.len);
      }
      question = question.trim() || text;

      // Gửi MỌI tin sang Python để LƯU (bot học nội dung nhóm + nhớ hội thoại).
      // Python quyết định có trả lời không (nhóm: chỉ khi @nhắc). Trả rỗng = không gửi.
      const threadId = String(message.threadId || "");
      const uid = String(message.data?.uidFrom || "");
      const reply = await askPython(question, isGroup, asker, mentioned, threadId, uid);
      if (!reply) { log(`→ không trả lời (${isGroup && !mentioned ? "tin nhóm không @nhắc — chỉ lưu" : "bộ não rỗng"})`); return; }
      await sleep(2000 + rnd(6000)); // delay giống người 2–8s
      await api.sendMessage({ msg: reply, quote: message.data }, message.threadId, message.type);
      log(`→ đã trả lời "${asker}": ${reply.slice(0, 80)}`);
    } catch (e) { log(`xử lý 1 tin bị lỗi (bỏ qua tin đó): ${e?.message ?? e}`); }
  });
  // retryOnClose: zca-js tự nối lại đường nghe khi rớt mạng (không đăng nhập lại),
  // chỉ khi nó bó tay mới phát 'closed' cho ta xử lý.
  api.listener.start({ retryOnClose: true });
}

async function askPython(text, isGroup, asker, mentioned, threadId, uid) {
  try {
    const res = await fetch(`${PY_URL}/internal/zalo-reply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, is_group: isGroup, asker, mentioned, thread_id: threadId, uid }),
    });
    const data = await res.json();
    return (data && data.reply) || "";
  } catch (e) { log(`hỏi bộ não Python lỗi: ${e?.message ?? e}`); return ""; }
}

// ---------- Van an toàn cho tin CHỦ ĐỘNG ----------
const queue = [];
let sentTimes = []; // mốc thời gian các tin đã gửi (ms)
let lastSentAt = 0;

function withinAllowedHours() {
  const h = new Date().getHours();
  if (SAFE.allowedFrom <= SAFE.allowedTo) return h >= SAFE.allowedFrom && h < SAFE.allowedTo;
  return h >= SAFE.allowedFrom || h < SAFE.allowedTo; // khung qua đêm
}
function countLast(ms) {
  const now = Date.now();
  sentTimes = sentTimes.filter((t) => now - t < 24 * 3600 * 1000);
  return sentTimes.filter((t) => now - t < ms).length;
}

async function queueWorker() {
  for (;;) {
    if (queue.length === 0 || state !== "logged_in") { await sleep(2000); continue; }
    if (!withinAllowedHours()) { await sleep(60000); continue; }
    if (countLast(3600 * 1000) >= SAFE.maxPerHour) { await sleep(60000); continue; }
    if (countLast(24 * 3600 * 1000) >= SAFE.maxPerDay) { await sleep(300000); continue; }

    const gap = SAFE.minGapSec * 1000 + rnd(SAFE.jitterSec * 1000);
    const wait = lastSentAt + gap - Date.now();
    if (wait > 0) { await sleep(Math.min(wait, 15000)); continue; }

    const job = queue.shift();
    try {
      await api.sendMessage({ msg: job.message }, job.threadId, job.type ?? ThreadType.Group);
      lastSentAt = Date.now();
      sentTimes.push(lastSentAt);
      log(`đã gửi tin chủ động vào ${job.threadId}`);
    } catch (e) {
      // gửi lỗi → KHÔNG dồn lại vô hạn; ghi log để còn biết mà báo chủ.
      log(`gửi tin chủ động THẤT BẠI (bỏ tin này) tới ${job.threadId}: ${e?.message ?? e}`);
    }
  }
}
queueWorker();

// ---------- API nội bộ (chỉ localhost) ----------
const app = express();
app.use(express.json());

app.get("/status", (req, res) => {
  res.json({ state, name: selfName, error: lastError,
             qrAvailable: state === "awaiting_qr" && fs.existsSync(QR_FILE),
             queued: queue.length, sentToday: countLast(24 * 3600 * 1000) });
});

app.get("/qr.png", (req, res) => {
  if (fs.existsSync(QR_FILE)) res.sendFile(QR_FILE);
  else res.status(404).send("Chưa có mã QR (có thể đã đăng nhập rồi).");
});

app.post("/relogin", async (req, res) => {
  // Đóng phiên nghe cũ TRƯỚC (nếu không, khi đăng nhập mới Zalo sẽ đá phiên cũ →
  // phiên cũ phát 'closed' → nối lại loạn). Tăng gen để mọi handler cũ tự vô hiệu.
  gen++;
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
  try { api?.listener?.stop?.(); } catch {}
  try { fs.existsSync(SESSION_FILE) && fs.unlinkSync(SESSION_FILE); } catch {}
  api = null;
  state = "starting"; lastError = ""; backoffMs = MIN_BACKOFF;
  startLogin();
  res.json({ ok: true });
});

app.get("/groups", async (req, res) => {
  if (state !== "logged_in") return res.json({ error: "chưa đăng nhập" });
  try {
    const all = await api.getAllGroups();
    const ids = Object.keys(all.gridVerMap || {});
    if (ids.length === 0) return res.json({ groups: [] });
    const info = await api.getGroupInfo(ids);
    const m = info.gridInfoMap || {};
    res.json({ groups: ids.map((id) => ({ id, name: (m[id] && m[id].name) || "(nhóm)" })) });
  } catch (e) {
    res.json({ error: String(e && e.message ? e.message : e) });
  }
});

app.post("/send", (req, res) => {
  const { threadId, message, isGroup } = req.body || {};
  if (!threadId || !message) return res.status(400).json({ error: "thiếu threadId/message" });
  queue.push({ threadId, message, type: isGroup === false ? ThreadType.User : ThreadType.Group });
  res.json({ queued: true, position: queue.length });
});

const server = app.listen(PORT, "127.0.0.1", () => {
  console.log(`[zalo] dịch vụ Zalo chạy tại http://127.0.0.1:${PORT}`);
  startLogin();
});
// Nếu cổng đã bị một tiến trình Zalo cũ (mồ côi) chiếm: THOÁT êm, KHÔNG đăng nhập,
// tránh vòng lặp crash liên tục. Tiến trình cũ vẫn đang chạy tốt nên không cần bản mới.
server.on("error", (e) => {
  if (e && e.code === "EADDRINUSE") {
    console.log(`[zalo] cổng ${PORT} đang được một tiến trình Zalo khác dùng — thoát êm.`);
    process.exit(0);
  }
  console.log(`[zalo] lỗi mở cổng: ${e?.message ?? e}`);
  process.exit(1);
});
