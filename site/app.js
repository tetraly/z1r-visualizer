// The Z1R Visualizer page: reads a ROM in the browser, has the Python parser (spoiler.py, run in
// worker.js) turn it into JSON, and draws the views the Streamlit app (app.py) shows. Nothing is
// uploaded: the ROM's bytes go only to the worker.
//
// Served as a site, the page fetches worker.js and the parser from py/. The single-file build
// (scripts/build_site.py --single-file) inlines both, in the script elements read below.
"use strict";

const PYTHON_FILES = ["constants.py", "rom_reader.py", "data_extractor.py", "spoiler.py"];
const SVG_NS = "http://www.w3.org/2000/svg";
const VIEWS = [1, 2, 3, 4, 5, 6, 7, 8, 9].map((level) => `Level ${level}`)
  .concat(["Overworld", "Recorder Info", "Item Summary", "Hint Texts"]);
const NO_ROM_TEXT = "Please upload a Legend of Zelda ROM using the file widget above. Supported ROM " +
  "types are vanilla Legend of Zelda ROMs and randomized ROMs created by Zelda Randomizer without " +
  "the ‘Race ROM’ flag checked or by ZORA without ‘Encode level data’.";

const $ = (id) => document.getElementById(id);

function element(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  node.append(...children);
  return node;
}

function svgElement(tag, attrs = {}) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [name, value] of Object.entries(attrs)) node.setAttribute(name, value);
  return node;
}

// ---------------------------------------------------------------------------------------------
// The worker

function startWorker() {
  const inline = $("worker-source");
  if (inline) {
    return new Worker(URL.createObjectURL(new Blob([inline.textContent], { type: "text/javascript" })));
  }
  return new Worker("worker.js");
}

async function pythonSources() {
  const inline = $("python-sources");
  if (inline) return JSON.parse(inline.textContent);
  const sources = {};
  for (const name of PYTHON_FILES) {
    const response = await fetch(`py/${name}`);
    if (!response.ok) throw new Error(`could not load py/${name} (${response.status})`);
    sources[name] = await response.text();
  }
  return sources;
}

const worker = startWorker();
const pending = new Map();
let nextId = 1;

worker.onmessage = (event) => {
  const { id, type } = event.data;
  const request = pending.get(id);
  if (!request) return;
  pending.delete(id);
  if (type === "error") request.reject(new Error(event.data.message));
  else request.resolve(event.data);
};

function ask(type, payload = {}) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    worker.postMessage({ type, id, ...payload });
  });
}

// The parser's data for a ROM's bytes, as the JSON text Python wrote. The headless checks compare
// it byte for byte with `cli.py --json`.
async function exportRomJson(bytes) {
  const { json } = await ask("export", { bytes });
  return json;
}

async function exportRom(bytes) {
  return JSON.parse(await exportRomJson(bytes));
}

// ---------------------------------------------------------------------------------------------
// Messages, tables and tooltips

function infoBox(text) {
  return element("div", { className: "box info", textContent: text });
}

function errorBox(text) {
  return element("div", { className: "box error", textContent: text });
}

// A table like pandas' DataFrame.to_html(index=False), as the Streamlit app shows them.
function table(rows) {
  const columns = Object.keys(rows[0]);
  const head = element("tr", {}, columns.map((name) => element("th", { textContent: name })));
  const body = rows.map((row) => element("tr", {}, columns.map((name) => element("td", {
    textContent: String(row[name]),
  }))));
  return element("table", { className: "data" }, [element("thead", {}, [head]), element("tbody", {}, body)]);
}

function showTooltip(event, fields) {
  const tip = $("tooltip");
  tip.replaceChildren(...fields.map(([label, value]) => element("div", {}, [
    element("span", { className: "tip-label", textContent: `${label}: ` }),
    element("span", { textContent: value === undefined || value === "" ? "???" : String(value) }),
  ])));
  tip.hidden = false;
  const x = Math.min(event.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
  const y = Math.min(event.clientY + 14, window.innerHeight - tip.offsetHeight - 8);
  tip.style.left = `${Math.max(8, x)}px`;
  tip.style.top = `${Math.max(8, y)}px`;
}

function hideTooltip() {
  $("tooltip").hidden = true;
}

function withTooltip(node, fields) {
  node.addEventListener("mousemove", (event) => showTooltip(event, fields));
  node.addEventListener("mouseleave", hideTooltip);
  node.addEventListener("click", (event) => showTooltip(event, fields));
  return node;
}

// ---------------------------------------------------------------------------------------------
// The maps. Coordinates are the parser's: x grows right, y grows up from the bottom of the map,
// one unit per room or screen, as in the app's Bokeh figures.

function plot(widthUnits, heightUnits, unit, title) {
  const svg = svgElement("svg", {
    viewBox: `0 0 ${widthUnits * unit} ${heightUnits * unit}`,
    width: widthUnits * unit, height: heightUnits * unit, class: "map", role: "img", "aria-label": title,
  });
  const toX = (x) => x * unit;
  const toY = (y) => (heightUnits - y) * unit;
  const rect = (cx, cy, w, h, attrs) => svgElement("rect", {
    x: toX(cx - w / 2), y: toY(cy + h / 2), width: w * unit, height: h * unit, ...attrs,
  });
  const text = (x, y, value, size) => {
    const node = svgElement("text", { x: toX(x), y: toY(y), "font-size": size, "dominant-baseline": "middle" });
    node.textContent = value;
    return node;
  };
  return { svg, rect, text };
}

// Door markers: the app maps 'black' (an open door) to dark grey and keeps the other colours.
const DOOR_COLOUR = (colour) => (colour === "black" ? "#333333" : colour);
const DIRECTIONS = ["north", "south", "east", "west"];
// Solid walls are drawn as bars on the side of the room they belong to.
const WALL_SIZE = { north: [1, 0.05], south: [1, 0.05], east: [0.05, 1], west: [0.05, 1] };
const LEGEND = [["Open Door", "black"], ["Shutter Door", "brown"], ["Key-Locked Door", "orange"],
                ["Bombable Wall", "blue"], ["Walk-Through Wall", "purple"], ["Solid Wall", "red"]];

function drawLevel(levelNum, level) {
  const { svg, rect, text } = plot(8, 8, 100, `Level ${levelNum} map`);
  const roomColour = level.palette[2];
  for (const room of level.rooms) {
    svg.append(withTooltip(rect(room.x_coord, room.y_coord, 0.8, 0.8, {
      fill: roomColour, "fill-opacity": 0.6, stroke: roomColour, class: "room",
    }), [
      ["Room Number", room.room_num], ["Col", room.col], ["Row", room.row], ["Stair", room.stair_tooltip],
      ["Room Type", room.room_type], ["Enemy Type", room.enemy_type_tooltip],
      ["Num Enemies", room.enemy_num_tooltip],
    ]));
  }
  for (const room of level.rooms) {
    for (const direction of DIRECTIONS) {
      if (room[`${direction}.x`] === undefined) continue;
      const colour = DOOR_COLOUR(room[`${direction}.color`]);
      svg.append(rect(room[`${direction}.x`], room[`${direction}.y`], 0.1, 0.1, {
        fill: colour, "fill-opacity": 0.6, stroke: colour, "pointer-events": "none",
      }));
    }
  }
  // Each wall between two rooms is recorded on both rooms' sides: draw it once.
  const walls = new Map();
  for (const room of level.rooms) {
    for (const direction of DIRECTIONS) {
      if (room[`${direction}.color`] !== "red" || room[`${direction}.wall.x`] === undefined) continue;
      const [w, h] = WALL_SIZE[direction];
      const x = room[`${direction}.wall.x`];
      const y = room[`${direction}.wall.y`];
      walls.set(`${x.toFixed(3)},${y.toFixed(3)},${w},${h}`, [x, y, w, h]);
    }
  }
  for (const [x, y, w, h] of walls.values()) {
    svg.append(rect(x, y, w, h, { fill: "red", stroke: "red", "pointer-events": "none" }));
  }
  for (const room of level.rooms) {
    const lines = [room.room_type, room.enemy_info, room.item_info, room.stair_info];
    lines.forEach((line, i) => {
      if (!line) return;
      const label = text(room.col - 0.86, room.row - 0.2 * (i + 1), line, "8pt");
      label.setAttribute("pointer-events", "none");
      svg.append(label);
    });
  }

  const legend = element("div", { className: "legend" }, [
    element("span", { className: "legend-title", textContent: "The Legend of Door & Wall Types" }),
    ...LEGEND.map(([label, colour]) => element("span", { className: "legend-item" }, [
      element("span", { className: `swatch${colour === "red" ? " solid" : ""}`, style: `background:${colour}` }),
      label,
    ])),
  ]);
  return element("figure", { className: "plot level" }, [
    element("figcaption", { textContent: `Level ${levelNum}` }), element("div", { className: "scroll" }, [svg]), legend,
  ]);
}

function drawOverworld(screens) {
  const { svg, rect, text } = plot(16, 8, 50, "Overworld map");
  for (const screen of screens) {
    svg.append(withTooltip(rect(screen.x_coord, screen.y_coord, 0.95, 0.95, {
      fill: "#4CAF50", "fill-opacity": 0.6, stroke: "#4CAF50", class: "room",
    }), [
      ["Screen Number", screen.screen_num], ["Col", screen.col], ["Row", screen.row], ["Cave", screen.cave],
      ["Cave2", screen.cave_name], ["Cave3", screen.cave_name_short],
    ]));
  }
  for (const screen of screens) {
    if (!screen.cave_name_short) continue;
    const label = text(screen.col + 0.1, screen.y_coord, screen.cave_name_short, "14px");
    label.setAttribute("pointer-events", "none");
    svg.append(label);
  }
  return element("figure", { className: "plot overworld" }, [
    element("figcaption", { textContent: "Overworld" }), element("div", { className: "scroll" }, [svg]),
  ]);
}

// ---------------------------------------------------------------------------------------------
// The other views

const hex = (values) => values.map((value) => value.toString(16).padStart(2, "0")).join(" ") + " ";

function recorderInfo(recorder) {
  if (!recorder || !recorder.data) return [infoBox("This ROM doesn't appear to have a custom recorder tune")];
  const url = URL.createObjectURL(new Blob([new Uint8Array(recorder.patch)], { type: "application/octet-stream" }));
  return [
    element("p", { textContent: `Recorder Text: ${recorder.text}` }),
    element("p", { className: "mono", textContent: `Recorder Data: ${hex(recorder.data)}` }),
    element("p", { className: "mono", textContent: `Recorder Patch Data: ${hex(recorder.patch)}` }),
    element("a", { className: "button", href: url, download: recorder.filename,
                   textContent: `Download recorder tune IPS patch (${recorder.filename})` }),
  ];
}

function itemSummary(data) {
  const summary = data.itemSummary;
  const out = [];
  if (data.progressiveItems) {
    out.push(infoBox("This ROM uses ZORA's Progressive Items: each sword, candle, arrow, ring and " +
                     "boomerang found or bought gives the next level the player lacks, so they are " +
                     "listed by their upgrade line."));
  }
  out.push(element("h2", { textContent: "Dungeon Items" }));
  const levels = element("div", { className: "grid three" });
  for (let level = 1; level <= 9; level++) {
    const items = summary.levels[String(level)];
    levels.append(element("div", {}, items.length
      ? [element("p", {}, [element("strong", { textContent: `Level ${level}:` })]), table(items)]
      : [element("p", {}, [element("strong", { textContent: `Level ${level}:` }), " No major items"])]));
  }
  out.push(levels);
  out.push(element("h2", { textContent: "Caves, Shops, and Overworld Items" }));
  const columns = [["Major Caves:", summary.caves], ["Shops:", summary.shops], ["Overworld Items:", summary.overworld]];
  out.push(element("div", { className: "grid three" }, columns.map(([title, rows]) => element("div", {}, [
    element("p", {}, [element("strong", { textContent: title })]), ...(rows.length ? [table(rows)] : []),
  ]))));
  return out;
}

function hintTexts(data) {
  const rows = data.texts.map((text, num) => ({ "Text #": num, Text: text }));
  if (data.recorderText) rows.push({ "Text #": "Recorder", Text: data.recorderText });
  return [
    element("p", { textContent: `This ROM has ${data.texts.length} texts. Which character says each one ` +
                                "isn't stored in the ROM." }),
    table(rows),
  ];
}

// ---------------------------------------------------------------------------------------------
// The page

let current = null;  // the parser's data for the chosen ROM

function renderView() {
  hideTooltip();
  const view = $("view").value;
  const ok = current.status === "ok";
  let content;
  if (view.startsWith("Level ")) {
    const level = view.split(" ")[1];
    content = ok ? [drawLevel(level, current.levels[level])]
      : [infoBox("Sorry, level maps aren't available for this ROM")];
  } else if (view === "Overworld") {
    content = ok ? [drawOverworld(current.overworld)] : [infoBox("Sorry, level maps aren't available for this ROM")];
  } else if (view === "Recorder Info") {
    content = recorderInfo(current.recorder);
  } else if (view === "Item Summary") {
    content = ok ? itemSummary(current) : [infoBox("Sorry, item summary isn't available for this ROM")];
  } else {
    content = ok ? hintTexts(current) : [infoBox("Sorry, hint texts aren't available for this ROM")];
  }
  $("output").replaceChildren(...content);
}

function showRom(data) {
  current = data;
  $("messages").replaceChildren(...(data.status === "encoded" ? [errorBox(data.message)]
    : data.status === "unsupported" ? [infoBox(data.message)] : []));
  $("picker").hidden = false;
  renderView();
}

function showNoRom() {
  current = null;
  $("messages").replaceChildren(infoBox(NO_ROM_TEXT));
  $("picker").hidden = true;
  $("output").replaceChildren();
}

async function onRomChosen() {
  const file = $("rom").files[0];
  if (!file) {
    showNoRom();
    return;
  }
  $("status").textContent = `Reading ${file.name}…`;
  try {
    showRom(await exportRom(new Uint8Array(await file.arrayBuffer())));
    $("status").textContent = `Showing ${file.name}.`;
  } catch (err) {
    showNoRom();
    $("status").textContent = `Could not read ${file.name}: ${err.message}`;
  }
}

$("view").append(...VIEWS.map((view) => element("option", { value: view, textContent: view })));
$("view").addEventListener("change", renderView);
$("rom").addEventListener("change", onRomChosen);
document.addEventListener("keydown", (event) => { if (event.key === "Escape") hideTooltip(); });
showNoRom();

window.z1rVisualizer = { exportRom, exportRomJson, current: () => current };

(async () => {
  const started = performance.now();
  try {
    const { python } = await ask("init", { sources: await pythonSources() });
    $("rom").disabled = false;
    $("status").textContent = `Ready (Python ${python}, ${Math.round(performance.now() - started)} ms).`;
    if ($("rom").files[0]) onRomChosen();
  } catch (err) {
    $("status").textContent = `Could not load Python: ${err.message}. The first visit needs an internet ` +
                              "connection to download Pyodide.";
  }
})();
