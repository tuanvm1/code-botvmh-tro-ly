// Đọc lưới lịch sân alobo bằng Chrome ẩn (tự quản), chụp ảnh cho Python đọc màu.
//   node reader.mjs <slug> <courtIndex> <dayOffset> <outPng>
// dayOffset: 0 = hôm nay, 1 = ngày mai. In "OK" nếu chụp xong, "ERR ..." nếu lỗi.
//
// Toạ độ canh chỉnh cho viewport 2000x1400 (xem tasks/ALOBO-API.md).
import { spawn, execSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const [SLUG, COURT_IDX_s, DAY_OFF_s, OUT] = process.argv.slice(2);
const COURT_IDX = parseInt(COURT_IDX_s || "0", 10);
const DAY_OFF = parseInt(DAY_OFF_s || "0", 10);
const URL = `https://datlich.alobo.vn/san/${SLUG}`;
const W = 2000, H = 1400;
// Thời gian chờ Flutter render (ms). Máy yếu (VPS) render chậm → cho chờ lâu hơn qua env ALOBO_LOAD_MS.
const LOAD_MS = parseInt(process.env.ALOBO_LOAD_MS || "35000", 10);

function findChrome() {
  const cands = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
  ];
  for (const c of cands) if (fs.existsSync(c)) return c;
  for (const b of ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]) {
    try { return execSync(`which ${b}`).toString().trim(); } catch {}
  }
  return null;
}

function fail(msg) { console.log("ERR " + msg); process.exit(1); }

const CHROME = findChrome();
if (!CHROME) fail("không tìm thấy Chrome/Chromium trên máy");
if (!SLUG || !OUT) fail("thiếu tham số slug/out");

const PORT = 9500 + (process.pid % 400);
const prof = fs.mkdtempSync(path.join(os.tmpdir(), "alr-"));
const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-sandbox",
  `--remote-debugging-port=${PORT}`, "--remote-allow-origins=*", "--hide-scrollbars",
  `--user-data-dir=${prof}`, "about:blank"], { stdio: "ignore" });

const sleep = (ms) => new Promise(r => setTimeout(r, ms));
function cleanup() { try { chrome.kill("SIGKILL"); } catch {} try { fs.rmSync(prof, { recursive: true, force: true }); } catch {} }

async function cdpTarget() {
  for (let i = 0; i < 40; i++) {
    try { const r = await fetch(`http://127.0.0.1:${PORT}/json/new?${encodeURIComponent(URL)}`, { method: "PUT" }); if (r.ok) return await r.json(); } catch {}
    await sleep(500);
  }
  throw new Error("Chrome CDP không lên");
}

// Ô ngày trong calendar (Monday-first). d: Date mục tiêu.
function dateCell(target) {
  const y = target.getFullYear(), m = target.getMonth();
  const first = new Date(y, m, 1);
  const firstCol = (first.getDay() + 6) % 7;      // T2=0 .. CN=6
  const idx = firstCol + (target.getDate() - 1);
  const col = idx % 7, row = Math.floor(idx / 7);
  return { x: 862 + col * 45, y: 624 + row * 43 };
}

try {
  const t = await cdpTarget();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res, { once: true }); ws.addEventListener("error", rej, { once: true }); });
  let id = 0; const pending = new Map();
  const send = (m, p = {}) => { const i = ++id; ws.send(JSON.stringify({ id: i, method: m, params: p })); return new Promise(r => pending.set(i, r)); };
  ws.addEventListener("message", (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); } });
  const click = async (x, y) => {
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
    await sleep(60);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
  };

  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  await sleep(LOAD_MS);                      // chờ Flutter render trang sân (máy yếu cần lâu hơn)

  await click(1943, 379);                   // nút "Đặt lịch"
  await sleep(6000);
  // Hộp thoại chọn loại sân CENTER theo viewport, cao/thấp tuỳ số mục (3 hay 4).
  // y=660 nằm trong hàng radio ĐẦU của cả 2 trường hợp; y=855 nằm trong nút "TIẾP TỤC"
  // của cả 3-mục lẫn 4-mục (vùng nút chồng nhau) → bấm trúng bất kể số mục.
  await click(788, 660 + COURT_IDX * 49);   // chọn loại sân (radio, mặc định mục đầu)
  await sleep(1500);
  await click(1000, 855);                   // "TIẾP TỤC"
  await sleep(9000);                        // chờ lưới ngày HÔM NAY

  if (DAY_OFF > 0) {
    const now = new Date();
    const target = new Date(now.getFullYear(), now.getMonth(), now.getDate() + DAY_OFF);
    await click(1900, 74);                  // mở ô chọn ngày
    await sleep(1500);
    if (target.getMonth() !== now.getMonth()) { await click(1135, 543); await sleep(800); } // sang tháng sau
    const cell = dateCell(target);
    await click(cell.x, cell.y);            // chọn ngày mục tiêu
    await sleep(600);
    await click(1102, 870);                 // "Xác nhận"
    await sleep(7000);                       // chờ lưới ngày mới
  }

  const shot = await send("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync(OUT, Buffer.from(shot.data, "base64"));
  ws.close();
  cleanup();
  console.log("OK");
  process.exit(0);
} catch (e) {
  cleanup();
  fail(String(e && e.message ? e.message : e));
}
