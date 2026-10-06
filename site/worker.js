// The visualizer's Python parser in a Web Worker, so the page stays responsive.
//
// Messages in:  init {id, sources: {filename: text}}; export {id, bytes}.
// Messages out: ready {id, python}; result {id, json}; error {id, message}.
//
// A classic worker, so the single-file build can start it from a Blob URL on a page opened
// from disk (Chrome refuses module workers there). Pyodide 0.28.3 still supports classic
// workers, and is the version ZORA's beta uses.
const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";
const PYTHON_DIR = "/home/pyodide/visualizer";
let pyodide = null;
let exportRom = null;

async function init(sources) {
  importScripts(`${PYODIDE_URL}pyodide.js`);
  pyodide = await loadPyodide({ indexURL: PYODIDE_URL });
  pyodide.FS.mkdirTree(PYTHON_DIR);
  for (const [name, text] of Object.entries(sources)) {
    pyodide.FS.writeFile(`${PYTHON_DIR}/${name}`, text);
  }
  pyodide.runPython(`
import json, sys
sys.path.insert(0, "${PYTHON_DIR}")
import spoiler

def export_rom(data):
    return json.dumps(spoiler.Export(bytes(data.to_py())))
`);
  exportRom = pyodide.globals.get("export_rom");
  return pyodide.runPython("sys.version.split()[0]");
}

self.onmessage = async (event) => {
  const { type, id } = event.data;
  try {
    if (type === "init") {
      const python = await init(event.data.sources);
      self.postMessage({ type: "ready", id, python });
    } else if (type === "export") {
      const json = exportRom(event.data.bytes);
      self.postMessage({ type: "result", id, json });
    }
  } catch (err) {
    self.postMessage({ type: "error", id, message: String((err && err.message) || err) });
  }
};
