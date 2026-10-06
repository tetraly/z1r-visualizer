// Screenshots of each design direction's mockup, in headless Chrome:
//   <direction>-desktop-light.jpg  Level 5 with a staircase room pinned (pin, pair, tooltip)
//   <direction>-desktop-dark.jpg   the Item Summary
//   <direction>-phone-dark.jpg     Level 5 at 390 px wide
//   <direction>-phone-light.jpg    the empty state at 390 px wide
//
//   python3 docs/design/build_mockups.py
//   node docs/design/screenshots.mjs
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const DESIGN = dirname(fileURLToPath(import.meta.url));
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PORT = 9334;
const DIRECTIONS = ["atlas", "quest-log", "tracker"];
const SHOTS = [
  { name: "desktop-light", width: 1280, height: 860, mobile: false, query: "theme=light", view: "Level 5", pin: true },
  { name: "desktop-dark", width: 1280, height: 860, mobile: false, query: "theme=dark", view: "Item Summary" },
  { name: "phone-dark", width: 390, height: 844, mobile: true, query: "theme=dark", view: "Level 5", pin: true },
  { name: "phone-light", width: 390, height: 844, mobile: true, query: "theme=light&empty" },
];

const sleep = (ms) => new Promise((done) => setTimeout(done, ms));
const profile = mkdtempSync(join(tmpdir(), "z1r-shots-"));
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
                              "--hide-scrollbars", "about:blank"], { stdio: "ignore" });
try {
  let targets = null;
  for (let i = 0; i < 50 && !targets; i++) {
    targets = await fetch(`http://127.0.0.1:${PORT}/json`).then((r) => r.json()).catch(() => sleep(200).then(() => null));
  }
  const ws = new WebSocket(targets.find((target) => target.type === "page").webSocketDebuggerUrl);
  await new Promise((done) => ws.addEventListener("open", done));
  let nextId = 0;
  const waiting = new Map();
  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (waiting.has(message.id)) {
      waiting.get(message.id)(message);
      waiting.delete(message.id);
    }
  });
  const send = (method, params = {}) => new Promise((done) => {
    waiting.set(++nextId, done);
    ws.send(JSON.stringify({ id: nextId, method, params }));
  });
  const evaluate = async (expression) => (await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true })).result.result.value;

  for (const direction of DIRECTIONS) {
    for (const shot of SHOTS) {
      await send("Emulation.setDeviceMetricsOverride", { width: shot.width, height: shot.height, deviceScaleFactor: 1, mobile: shot.mobile });
      await send("Page.navigate", { url: `file://${join(DESIGN, `mockup-${direction}.html`)}?${shot.query}` });
      await sleep(600);
      if (shot.view) {
        await evaluate(`(async () => {
          for (let i = 0; i < 50 && document.body.dataset.state !== "loaded"; i++) await new Promise((r) => setTimeout(r, 100));
          document.querySelector('[data-view="${shot.view}"]').click();
          window.scrollTo(0, 0);
          if (${!!shot.pin}) {
            const room = [...document.querySelectorAll("rect.room")].find((node) => /Stair #1/.test(node.getAttribute("aria-label")));
            room.scrollIntoView({ block: "center", inline: "center" });
            room.dispatchEvent(new MouseEvent("click", { bubbles: true }));
          }
        })()`);
        await sleep(300);
      }
      const { result } = await send("Page.captureScreenshot", { format: "jpeg", quality: 84 });
      const file = join(DESIGN, `${direction}-${shot.name}.jpg`);
      writeFileSync(file, Buffer.from(result.data, "base64"));
      console.log(file.split("/").pop());
    }
  }
  ws.close();
} finally {
  chrome.kill();
  await sleep(300);
  rmSync(profile, { recursive: true, force: true });
}
