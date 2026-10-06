// Checks the page. First it type-checks site/'s JavaScript (tsc --noEmit, from its JSDoc types).
// Then, in headless Chrome, with the single file build/z1r-visualizer.html opened from file://:
// - the ROM path: each ROM is chosen through the page's file input; what the page read must equal
//   `python3 cli.py --json` byte for byte, its item summary must equal `cli.py --item-summary`,
//   every view must render, and encoded ROMs must be refused;
// - the recorder tune's IPS patch must equal the Python one;
// - a seed file: a ROM's `cli.py --seed` output, chosen as a .json file, must render every view
//   exactly as the ROM did;
// - the hand-off (docs/seed-format.md section 5): a harness page opens the visualizer as a popup,
//   answers its ready message with the seed, and every view must render exactly as from the ROM;
//   a wrong major version, a seed that breaks the schema, text that is not JSON, and a message
//   that is not from the opener must all be refused or ignored.
//
//   python3 scripts/build_site.py --single-file
//   node scripts/check_site.mjs testdata/*.nes
//
// Needs Node 22 or later (for its built-in WebSocket and npx) and Google Chrome. The first run
// downloads TypeScript (pinned below) through npx, and Pyodide from jsDelivr into a throwaway
// Chrome profile.
import { execFileSync, spawn } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PORT = 9333;
const PAGE = resolve("build/z1r-visualizer.html");
const PAGE_URL = `file://${PAGE}`;
const VIEWS = ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5", "Level 6", "Level 7", "Level 8", "Level 9",
               "Overworld", "Recorder Info", "Item Summary", "Hint Texts", "Seed Info"];
// TypeScript 6.0.3: the last release of the JavaScript compiler; 7 is the native port, whose
// JSDoc support differs. Each config checks the files of one context: the page with the DOM's
// types, the worker with the WebWorker's.
const TYPESCRIPT = "typescript@6.0.3";
const TYPE_CONFIGS = ["site/jsconfig.json", "site/jsconfig.worker.json"];

let failures = 0;
const fail = (message) => {
  failures++;
  console.log(`FAIL ${message}`);
};

for (const config of TYPE_CONFIGS) {
  try {
    execFileSync("npx", ["--yes", `--package=${TYPESCRIPT}`, "--", "tsc", "--noEmit", "-p", config],
                 { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
    console.log(`types: ${config} ok`);
  } catch (err) {
    fail(`types: ${config}\n${err.stdout || ""}${err.stderr || ""}`);
  }
}

const roms = process.argv.slice(2).map((path) => resolve(path));
if (!roms.length) {
  console.error("usage: node scripts/check_site.mjs ROM...");
  process.exit(2);
}

const sleep = (ms) => new Promise((done) => setTimeout(done, ms));
const python = (...args) => execFileSync("python3", args, { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
const work = mkdtempSync(join(tmpdir(), "z1r-check-"));
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${join(work, "profile")}`,
                              "--disable-popup-blocking", "about:blank"], { stdio: "ignore" });

const targets = async () => (await fetch(`http://127.0.0.1:${PORT}/json`)).json();

// A DevTools connection to one tab.
async function connect(target) {
  const ws = new WebSocket(target.webSocketDebuggerUrl);
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
  const evaluate = async (expression, userGesture = false) => {
    const { result } = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true, userGesture });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception.description);
    return result.result.value;
  };
  const until = async (expression, what, tries = 240) => {
    for (let i = 0; i < tries; i++) {
      const value = await evaluate(expression).catch(() => null);
      if (value) return value;
      await sleep(250);
    }
    throw new Error(`timed out waiting for ${what}`);
  };
  const status = () => evaluate("document.getElementById('status') ? document.getElementById('status').textContent : ''");
  const chooseFile = async (path) => {
    await send("DOM.enable");
    const { result: { root } } = await send("DOM.getDocument");
    const { result: { nodeId } } = await send("DOM.querySelector", { nodeId: root.nodeId, selector: "#rom" });
    await evaluate("document.getElementById('status').textContent = ''");
    await send("DOM.setFileInputFiles", { nodeId, files: [path] });
    await until("/^(Showing|Could not)/.test(document.getElementById('status').textContent)", "the file to be read");
  };
  // Each view's rendered HTML, as a SHA-256: blob: URLs and the seed's source line left out.
  const viewHashes = () => evaluate(`(async () => {
    const select = document.getElementById("view");
    const hashes = {};
    for (const view of ${JSON.stringify(VIEWS)}) {
      select.value = view;
      select.dispatchEvent(new Event("change"));
      const html = document.getElementById("output").innerHTML
        .replace(/blob:[^"]+/g, "blob:")
        .replace(/(Shown from<\\/td><td>)[^<]*/, "$1");
      const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(html));
      hashes[view] = [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
    }
    return hashes;
  })()`);
  return { send, evaluate, until, status, chooseFile, viewHashes, close: () => ws.close() };
}

const sameJson = (a, b) => JSON.stringify(a) === JSON.stringify(b);

const tabs = [];
try {
  let list = null;
  for (let i = 0; i < 50 && !list; i++) list = await targets().catch(() => sleep(200).then(() => null));
  const main = await connect(list.find((target) => target.type === "page"));
  tabs.push(main);
  await main.send("Page.navigate", { url: PAGE_URL });
  const ready = await main.until("/^(Ready|Could not)/.test(document.getElementById('status').textContent) && " +
                                 "document.getElementById('status').textContent", "Python to load");
  console.log(`page: ${ready}`);
  if (!ready.startsWith("Ready")) throw new Error("the page did not get ready");
  const version = await main.evaluate("document.getElementById('version').textContent");

  // The ROM path.
  const fromRom = new Map();  // ROM -> {seedJson, hashes}
  for (const rom of roms) {
    const name = rom.split("/").pop();
    await main.chooseFile(rom);
    const pageJson = await main.evaluate(
      "document.getElementById('rom').files[0].arrayBuffer()" +
      ".then((buffer) => window.z1rVisualizer.exportRomJson(new Uint8Array(buffer)))");
    const cli = JSON.parse(python("cli.py", "--json", `--producer-version=${version}`, `--files=${rom}`));
    delete cli.file;  // added last by cli.py, so the rest keeps Python's order
    const problems = [];
    // Python's json.dumps spacing differs from JSON.stringify's, so compare re-serialized forms.
    if (JSON.stringify(JSON.parse(pageJson)) !== JSON.stringify(cli)) problems.push("read differs from cli.py --json");
    const data = JSON.parse(pageJson);
    const hashes = await main.viewHashes();
    if (data.status === "ok") {
      const summary = await main.evaluate("window.z1rVisualizer.itemSummary()");
      const expected = JSON.parse(python("cli.py", "--item-summary", `--files=${rom}`));
      delete expected.file;
      if (!sameJson(summary, expected)) problems.push("item summary differs from cli.py --item-summary");
      const drawn = await main.evaluate(`(() => {
        const select = document.getElementById("view");
        return ${JSON.stringify(VIEWS)}.filter((view) => {
          select.value = view;
          select.dispatchEvent(new Event("change"));
          const out = document.getElementById("output");
          return !out.querySelector("svg, table, a") && !/custom recorder tune|has no Level/.test(out.innerText);
        });
      })()`);
      if (drawn.length) problems.push(`views not drawn: ${drawn.join(", ")}`);
      fromRom.set(rom, { seedJson: JSON.stringify(data.seed), hashes });
    } else {
      const refused = await main.evaluate(`(() => {
        const select = document.getElementById("view");
        select.value = "Level 1";
        select.dispatchEvent(new Event("change"));
        return document.getElementById("output").innerText.trim();
      })()`);
      if (refused !== "Sorry, level maps aren't available for this ROM") problems.push(`Level 1 shows "${refused}"`);
    }
    if (problems.length) fail(`${name}: ${data.status}, ${problems.join("; ")}`);
    else console.log(`ok   ${name}: ${data.status}`);
  }

  // The recorder tune's IPS patch, against the Python builder.
  const notes = [0x10, 0x22, 0x30, 0x46, 0x00];
  const jsPatch = await main.evaluate(`window.z1rVisualizer.recorderPatch(${JSON.stringify(notes)})`);
  const pyPatch = JSON.parse(python("-c", "import io, json; from data_extractor import DataExtractor; " +
    "de = DataExtractor(io.BytesIO(bytes(0x20000))); " +
    `de.rom_reader.GetRecorderData = lambda: ${JSON.stringify(notes)}; print(json.dumps(de.GetRecorderPatchData()))`));
  if (sameJson(jsPatch, pyPatch)) console.log("ok   recorder patch matches the Python one");
  else fail("recorder patch differs from the Python one");

  const parsed = [...fromRom.keys()];
  if (!parsed.length) throw new Error("no ROM parsed, so the seed paths were not checked");

  // A seed file, chosen like a ROM.
  {
    const rom = parsed[0];
    const file = join(work, "seed.json");
    writeFileSync(file, python("cli.py", "--seed", `--producer-version=${version}`, `--files=${rom}`));
    await main.chooseFile(file);
    if (sameJson(await main.viewHashes(), fromRom.get(rom).hashes)) console.log(`ok   seed file of ${rom.split("/").pop()}`);
    else fail(`seed file of ${rom.split("/").pop()} renders differently from the ROM`);
  }

  // The hand-off: a harness page that opens the visualizer, as ZORA would.
  const harness = join(work, "harness.html");
  writeFileSync(harness, `<!doctype html><meta charset="utf-8"><title>harness</title><script>
    window.sendSeed = (json) => new Promise((done) => {
      const viz = window.open(${JSON.stringify(PAGE_URL)}, "visualizer");
      const timer = setTimeout(() => {
        window.removeEventListener("message", onMessage);
        done({ ok: false, error: "no reply from the visualizer within 30 s" });
      }, 30000);
      const onMessage = (event) => {
        if (event.source !== viz || !event.data) return;
        if (event.data.type === "z1r-seed-ready") viz.postMessage({ type: "z1r-seed", protocol: 1, json }, "*");
        if (event.data.type === "z1r-seed-received") {
          clearTimeout(timer);
          window.removeEventListener("message", onMessage);
          done(event.data);
        }
      };
      window.addEventListener("message", onMessage);
    });
  </script>`);
  const { result: { targetId } } = await main.send("Target.createTarget", { url: `file://${harness}` });
  const opener = await connect((await targets()).find((target) => target.id === targetId));
  tabs.push(opener);
  await opener.until("typeof window.sendSeed === 'function'", "the harness");
  let popup = null;
  const handOff = async (json) => {
    const reply = await opener.evaluate(`window.sendSeed(${JSON.stringify(json)})`, true);
    if (!popup) {
      const target = (await targets()).find((candidate) => candidate.type === "page" && candidate.url === PAGE_URL &&
                                                          candidate.id !== targetId && candidate.url !== "about:blank" &&
                                                          !tabs.some((tab) => tab.id === candidate.id));
      popup = await connect(target);
      popup.id = target.id;
      tabs.push(popup);
    }
    return reply;
  };
  main.id = (await targets()).find((target) => target.url === PAGE_URL)?.id;

  for (const rom of parsed) {
    const name = rom.split("/").pop();
    const reply = await handOff(fromRom.get(rom).seedJson);
    if (!reply.ok) {
      fail(`hand-off of ${name}: refused (${reply.error})`);
      continue;
    }
    await popup.until("/^Showing the seed from/.test(document.getElementById('status').textContent)", "the seed");
    const status = await popup.status();
    if (!reply.ok) fail(`hand-off of ${name}: refused (${reply.error})`);
    else if (!sameJson(await popup.viewHashes(), fromRom.get(rom).hashes)) fail(`hand-off of ${name}: renders differently`);
    else if (!/a seed from z1r-visualizer .+ \(seed format 1\.0\)/.test(status)) fail(`hand-off of ${name}: status "${status}"`);
    else console.log(`ok   hand-off of ${name}`);
  }
  const pythonLoaded = await popup.evaluate("performance.getEntriesByType('resource').some((e) => e.name.includes('pyodide'))");
  if (pythonLoaded) fail("the hand-off page loaded Pyodide");
  else console.log("ok   the hand-off page did not load Pyodide");

  // Refusals.
  const good = JSON.parse(fromRom.get(parsed[0]).seedJson);
  const broken = structuredClone(good);
  broken.levels[0].rooms[0].doors.north = "window";
  const refusals = [
    ["a newer major version", JSON.stringify({ ...good, formatVersion: "2.0" }), /seed format 2\.0.*reads format 1\.x/],
    ["a seed that breaks the schema", JSON.stringify(broken), /levels\[0\]\.rooms\[0\]\.doors\.north/],
    ["text that is not JSON", "{not json", /not valid JSON/],
  ];
  for (const [what, json, expected] of refusals) {
    const reply = await handOff(json);
    const shown = await popup.until("document.getElementById('messages').innerText", "the refusal");
    if (reply.ok || !expected.test(reply.error) || !expected.test(shown)) fail(`${what}: ${JSON.stringify(reply)} / "${shown}"`);
    else console.log(`ok   refuses ${what}: ${reply.error.slice(0, 90)}`);
  }
  // A seed message from anyone but the opener is ignored.
  await handOff(fromRom.get(parsed[0]).seedJson);
  const before = await popup.status();
  await popup.evaluate(`window.postMessage({ type: "z1r-seed", protocol: 1, json: ${JSON.stringify(JSON.stringify(broken))} }, "*")`);
  await sleep(500);
  if ((await popup.status()) === before && !(await popup.evaluate("document.getElementById('messages').innerText"))) {
    console.log("ok   ignores a seed message that is not from its opener");
  } else {
    fail("a seed message that is not from the opener was acted on");
  }
} catch (err) {
  fail(`error: ${err.message}`);
} finally {
  for (const tab of tabs) tab.close();
  chrome.kill();
  await sleep(300);
  rmSync(work, { recursive: true, force: true });
}
console.log(failures ? `${failures} failed` : `all ${roms.length} ROMs match, and the seed file and hand-off paths too`);
process.exit(failures ? 1 : 0);
