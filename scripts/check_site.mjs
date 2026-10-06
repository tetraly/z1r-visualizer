// Checks the page. First it type-checks site/'s JavaScript (tsc --noEmit, from its JSDoc types).
// Then it opens the single file build/z1r-visualizer.html from file:// in headless Chrome, chooses
// each ROM through the page's file input, and compares the data the page draws from with
// `python3 cli.py --json` for the same ROM, byte for byte. It also checks that every view renders,
// and that encoded ROMs are refused.
//
//   python3 scripts/build_site.py --single-file
//   node scripts/check_site.mjs testdata/*.nes
//
// Needs Node 22 or later (for its built-in WebSocket and npx) and Google Chrome. The first run
// downloads TypeScript (pinned below) through npx, and Pyodide from jsDelivr into a throwaway
// Chrome profile.
import { execFileSync, spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PORT = 9333;
const PAGE = resolve("build/z1r-visualizer.html");
const VIEWS = ["Level 1", "Overworld", "Recorder Info", "Item Summary", "Hint Texts"];
// TypeScript 6.0.3: the last release of the JavaScript compiler; 7 is the native port, whose
// JSDoc support differs. Each config checks one file: the page with the DOM's types, the worker
// with the WebWorker's.
const TYPESCRIPT = "typescript@6.0.3";
const TYPE_CONFIGS = ["site/jsconfig.json", "site/jsconfig.worker.json"];
const roms = process.argv.slice(2).map((path) => resolve(path));
if (!roms.length) {
  console.error("usage: node scripts/check_site.mjs ROM...");
  process.exit(2);
}

let typeErrors = 0;
for (const config of TYPE_CONFIGS) {
  try {
    execFileSync("npx", ["--yes", `--package=${TYPESCRIPT}`, "--", "tsc", "--noEmit", "-p", config],
                 { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
    console.log(`types: ${config} ok`);
  } catch (err) {
    typeErrors++;
    console.log(`types: ${config} FAILED\n${err.stdout || ""}${err.stderr || ""}`);
  }
}

const sleep = (ms) => new Promise((done) => setTimeout(done, ms));
const profile = mkdtempSync(join(tmpdir(), "z1r-check-"));
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
                              "about:blank"], { stdio: "ignore" });

let ws = null;
let failures = typeErrors;
try {
  let targets = null;
  for (let i = 0; i < 50 && !targets; i++) {
    try {
      targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
    } catch {
      await sleep(200);
    }
  }
  ws = new WebSocket(targets.find((target) => target.type === "page").webSocketDebuggerUrl);
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
  const evaluate = async (expression) => {
    const { result } = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception.description);
    return result.result.value;
  };
  const status = () => evaluate("document.getElementById('status').textContent");

  await send("Page.navigate", { url: `file://${PAGE}` });
  let text = "";
  for (let i = 0; i < 240 && !text.startsWith("Ready") && !text.startsWith("Could not"); i++) {
    await sleep(500);
    text = (await evaluate("document.getElementById('status') ? document.getElementById('status').textContent : ''")) || "";
  }
  console.log(`page: ${text}`);
  if (!text.startsWith("Ready")) throw new Error("the page did not get ready");
  await send("DOM.enable");

  for (const rom of roms) {
    const { result: { root } } = await send("DOM.getDocument");
    const { result: { nodeId } } = await send("DOM.querySelector", { nodeId: root.nodeId, selector: "#rom" });
    await send("DOM.setFileInputFiles", { nodeId, files: [rom] });
    for (let i = 0; i < 100 && !(await status()).startsWith("Showing"); i++) await sleep(100);

    const pageJson = await evaluate(
      "document.getElementById('rom').files[0].arrayBuffer()" +
      ".then((buffer) => window.z1rVisualizer.exportRomJson(new Uint8Array(buffer)))");
    const cli = JSON.parse(execFileSync("python3", ["cli.py", "--json", `--files=${rom}`], { encoding: "utf8" }));
    delete cli.file;  // added last by cli.py, so the rest keeps Python's order
    const cliJson = JSON.stringify(cli);
    // Python's json.dumps spacing differs from JSON.stringify's, so compare re-serialized forms.
    const same = JSON.stringify(JSON.parse(pageJson)) === cliJson;

    const views = await evaluate(`(() => {
      const select = document.getElementById("view");
      return ${JSON.stringify(VIEWS)}.map((view) => {
        select.value = view;
        select.dispatchEvent(new Event("change"));
        const out = document.getElementById("output");
        return out.querySelector("svg, table, a, p") ? "drawn" : out.innerText.trim();
      });
    })()`);
    const data = JSON.parse(pageJson);
    const expected = data.status === "ok" ? VIEWS.map((view) => (view === "Recorder Info" && !data.recorder.data
      ? "This ROM doesn't appear to have a custom recorder tune" : "drawn")) : null;
    const viewsOk = expected ? JSON.stringify(views) === JSON.stringify(expected)
      : views.slice(0, 2).every((view) => view === "Sorry, level maps aren't available for this ROM");
    const ok = same && viewsOk;
    failures += !ok;
    console.log(`${ok ? "ok  " : "FAIL"} ${rom.split("/").pop()}: ${data.status}` +
                `${same ? "" : ", data differs from cli.py --json"}${viewsOk ? "" : `, views: ${JSON.stringify(views)}`}`);
  }
} catch (err) {
  failures++;
  console.error(`error: ${err.message}`);
} finally {
  if (ws) ws.close();
  chrome.kill();
  await sleep(300);
  rmSync(profile, { recursive: true, force: true });
}
console.log(failures ? `${failures} failed` : `all ${roms.length} ROMs match`);
process.exit(failures ? 1 : 0);
