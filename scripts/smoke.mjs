// Headless smoke test for one sample.
// Usage: node scripts/smoke.mjs samples/<name>
// Serves <sample>/dist, opens it in headless Chrome and passes only if
// window.view.ready becomes true with no console error, no page error,
// no failed request and no request carrying a token.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import puppeteer from "puppeteer";

const sampleDir = process.argv[2];
if (!sampleDir) {
  console.error("usage: node scripts/smoke.mjs samples/<name>");
  process.exit(2);
}
const distDir = path.resolve(sampleDir, "dist");
if (!fs.existsSync(path.join(distDir, "index.html"))) {
  console.error(`no ${distDir}/index.html - run npm run build first`);
  process.exit(2);
}

const TIMEOUT_MS = 60_000;
const MIME = {
  ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript",
  ".css": "text/css", ".json": "application/json", ".wasm": "application/wasm",
  ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
  ".woff": "font/woff", ".woff2": "font/woff2", ".ttf": "font/ttf",
};

const server = http.createServer((req, res) => {
  const urlPath = decodeURIComponent(new URL(req.url, "http://x").pathname);
  let file = path.join(distDir, urlPath);
  if (!file.startsWith(distDir)) { res.writeHead(403).end(); return; }
  if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, "index.html");
  // Chrome asks for /favicon.ico on its own; a sample without one is not an error.
  if (!fs.existsSync(file) && urlPath === "/favicon.ico") { res.writeHead(204).end(); return; }
  if (!fs.existsSync(file)) { res.writeHead(404).end(); return; }
  const type = MIME[path.extname(file)] ?? "application/octet-stream";
  const size = fs.statSync(file).size;
  // Parquet readers fetch byte ranges, so answer Range requests the way a static host does.
  const range = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range ?? "");
  if (range) {
    const start = range[1] ? Number(range[1]) : size - Number(range[2]);
    const end = range[1] && range[2] ? Math.min(Number(range[2]), size - 1) : size - 1;
    res.writeHead(206, { "Content-Type": type, "Content-Length": end - start + 1, "Content-Range": `bytes ${start}-${end}/${size}`, "Accept-Ranges": "bytes" });
    fs.createReadStream(file, { start, end }).pipe(res);
    return;
  }
  res.writeHead(200, { "Content-Type": type, "Content-Length": size, "Accept-Ranges": "bytes" });
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const url = `http://127.0.0.1:${server.address().port}/`;

const problems = [];
let requests = 0;
const browser = await puppeteer.launch({
  headless: true,
  // Software WebGL so the map can draw on CI runners with no GPU.
  args: ["--no-sandbox", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 720 });
  page.on("console", (m) => { if (m.type() === "error") problems.push(`console error: ${m.text()}`); });
  page.on("pageerror", (e) => problems.push(`page error: ${e.message}`));
  page.on("request", (r) => {
    requests++;
    if (/[?&]token=/i.test(r.url())) problems.push(`token in request: ${r.url().split("?")[0]}`);
  });
  page.on("requestfailed", (r) => {
    // A Parquet reader cancels its own stream once it has the bytes it needs: not a failure.
    if (r.failure()?.errorText === "net::ERR_ABORTED" && /\.parquet$/i.test(new URL(r.url()).pathname)) return;
    problems.push(`request failed: ${r.url()} (${r.failure()?.errorText})`);
  });
  page.on("response", (r) => { if (r.status() >= 400) problems.push(`HTTP ${r.status()}: ${r.url()}`); });

  await page.goto(url, { waitUntil: "load", timeout: TIMEOUT_MS });
  await page.waitForFunction(() => window.view?.ready === true, { timeout: TIMEOUT_MS });
  // Let the first basemap tiles arrive so their errors, if any, are caught.
  await page.waitForFunction(() => window.view?.updating === false, { timeout: TIMEOUT_MS });
} catch (e) {
  problems.push(`smoke: ${e.message}`);
} finally {
  await browser.close();
  server.close();
}

if (problems.length) {
  console.error(`FAIL ${sampleDir}`);
  for (const p of problems) console.error(`  - ${p}`);
  process.exit(1);
}
console.log(`PASS ${sampleDir}: view ready, 0 console errors, 0 token requests, ${requests} requests`);
