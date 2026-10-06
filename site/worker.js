// The visualizer's Python parser in a Web Worker, so the page stays responsive.
//
// Messages in:  init {id, sources: {filename: text}, version}; export {id, bytes}.
// Messages out: ready {id, python}; result {id, json}; error {id, message}. A result's json is
// spoiler.Read's: {"status": "ok", "seed": <seed format>}, or a refusal.
//
// A classic worker, so the single-file build can start it from a Blob URL on a page opened
// from disk (Chrome refuses module workers there). Pyodide 0.28.3 still supports classic
// workers, and is the version ZORA's beta uses.
//
// Type-checked with JSDoc (tsc --noEmit -p site/jsconfig.worker.json, run by scripts/check_site.mjs).
// @ts-check

// The parts of Pyodide's API used here.
/**
 * @typedef {object} Pyodide
 * @property {{mkdirTree(path: string): void, writeFile(path: string, data: string): void}} FS
 * @property {(code: string) => any} runPython
 * @property {{get(name: string): any, set(name: string, value: unknown): void}} globals
 * @typedef {(options: {indexURL: string}) => Promise<Pyodide>} LoadPyodide
 */
const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";
const PYTHON_DIR = "/home/pyodide/visualizer";
/** @type {Pyodide | null} */
let pyodide = null;
/** @type {((bytes: Uint8Array) => string) | null} */
let exportRom = null;

/**
 * Loads Pyodide and the parser.
 * @param {Record<string, string>} sources  The parser's files, by name.
 * @param {string} version  The page's version, written as the seed's producer version.
 * @returns {Promise<string>} Python's version.
 */
async function init(sources, version) {
  importScripts(`${PYODIDE_URL}pyodide.js`);
  // pyodide.js defines loadPyodide as a global.
  const loadPyodide = /** @type {LoadPyodide} */ (/** @type {any} */ (self).loadPyodide);
  pyodide = await loadPyodide({ indexURL: PYODIDE_URL });
  pyodide.FS.mkdirTree(PYTHON_DIR);
  for (const [name, text] of Object.entries(sources)) {
    pyodide.FS.writeFile(`${PYTHON_DIR}/${name}`, text);
  }
  pyodide.globals.set("PRODUCER_VERSION", version);
  pyodide.runPython(`
import json, sys
sys.path.insert(0, "${PYTHON_DIR}")
import spoiler

def export_rom(data):
    return json.dumps(spoiler.Read(bytes(data.to_py()), PRODUCER_VERSION))
`);
  exportRom = pyodide.globals.get("export_rom");
  return pyodide.runPython("sys.version.split()[0]");
}

self.onmessage = async (/** @type {MessageEvent} */ event) => {
  const { type, id } = event.data;
  try {
    if (type === "init") {
      const python = await init(event.data.sources, event.data.version);
      self.postMessage({ type: "ready", id, python });
    } else if (type === "export") {
      const json = /** @type {(bytes: Uint8Array) => string} */ (exportRom)(event.data.bytes);
      self.postMessage({ type: "result", id, json });
    }
  } catch (err) {
    const message = String((err && /** @type {{message?: string}} */ (err).message) || err);
    self.postMessage({ type: "error", id, message });
  }
};
