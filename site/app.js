// The Z1R Visualizer page: reads a ROM in the browser, has the Python parser (spoiler.py, run in
// worker.js) turn it into JSON, and draws the views the Streamlit app (app.py) shows. Nothing is
// uploaded: the ROM's bytes go only to the worker.
//
// Served as a site, the page fetches worker.js and the parser from py/. The single-file build
// (scripts/build_site.py --single-file) inlines both, in the script elements read below.
//
// Type-checked with JSDoc (tsc --noEmit -p site/jsconfig.json, run by scripts/check_site.mjs).
// @ts-check
"use strict";

// The parser's data (spoiler.Export in spoiler.py), as the page reads it.
/**
 * @typedef {{num: number, col: number, row: number, x_coord: number, y_coord: number,
 *   room_num: string, room_type: string, enemy_info: string, item_info: string, stair_info: string,
 *   stair_tooltip: string, enemy_type_tooltip: string, enemy_num_tooltip: string,
 *   [key: string]: string | number}} Room
 *   Besides these, "<direction>.x"/".y" (a door marker), ".color", ".wall.x"/".wall.y" (a solid
 *   wall) and ".wall_type", for each direction that has one.
 * @typedef {{palette: string[], rooms: Room[]}} Level
 * @typedef {{screen_num: string, col: number, row: number, x_coord: number, y_coord: number,
 *   cave: string, block_type: string, cave_name?: string, cave_name_short?: string}} OverworldScreen
 * @typedef {Record<string, string | number>} Row  A table row: column name to cell.
 * @typedef {{levels: Record<string, Row[]>, caves: Row[], shops: Row[], overworld: Row[]}} ItemSummary
 * @typedef {{text: string, data: number[], patch: number[], filename: string}} RecorderTune
 * @typedef {Partial<RecorderTune>} Recorder  Empty without a custom recorder tune.
 * @typedef {{status: "ok", message: string, recorder: Recorder, progressiveItems: boolean,
 *   levels: Record<string, Level>, overworld: OverworldScreen[], itemSummary: ItemSummary, texts: string[],
 *   recorderText: string}} ParsedRom
 * @typedef {{status: "encoded" | "unsupported", message: string, recorder: Recorder}} RefusedRom
 * @typedef {ParsedRom | RefusedRom} RomData
 * @typedef {Array<[string, string | number | undefined]>} TooltipFields
 * @typedef {"north" | "south" | "east" | "west"} Direction
 */

const PYTHON_FILES = ["constants.py", "rom_reader.py", "data_extractor.py", "spoiler.py"];
const SVG_NS = "http://www.w3.org/2000/svg";
const VIEWS = [1, 2, 3, 4, 5, 6, 7, 8, 9].map((level) => `Level ${level}`)
  .concat(["Overworld", "Recorder Info", "Item Summary", "Hint Texts"]);
const NO_ROM_TEXT = "Please upload a Legend of Zelda ROM using the file widget above. Supported ROM " +
  "types are vanilla Legend of Zelda ROMs and randomized ROMs created by Zelda Randomizer without " +
  "the ‘Race ROM’ flag checked or by ZORA without ‘Encode level data’.";

// The page's fixed elements (index.html; this script runs after them).
const romInput = /** @type {HTMLInputElement} */ (document.getElementById("rom"));
const viewSelect = /** @type {HTMLSelectElement} */ (document.getElementById("view"));
const statusLine = /** @type {HTMLElement} */ (document.getElementById("status"));
const messageArea = /** @type {HTMLElement} */ (document.getElementById("messages"));
const picker = /** @type {HTMLElement} */ (document.getElementById("picker"));
const output = /** @type {HTMLElement} */ (document.getElementById("output"));
const tooltip = /** @type {HTMLElement} */ (document.getElementById("tooltip"));

/**
 * @template {keyof HTMLElementTagNameMap} K
 * @param {K} tag
 * @param {Record<string, unknown>} [props]  Properties set on the element, e.g. textContent.
 * @param {Array<Node | string>} [children]
 * @returns {HTMLElementTagNameMap[K]}
 */
function element(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  node.append(...children);
  return node;
}

/**
 * @param {string} tag
 * @param {Record<string, string | number>} [attrs]
 * @returns {SVGElement}
 */
function svgElement(tag, attrs = {}) {
  const node = /** @type {SVGElement} */ (document.createElementNS(SVG_NS, tag));
  for (const [name, value] of Object.entries(attrs)) node.setAttribute(name, String(value));
  return node;
}

// ---------------------------------------------------------------------------------------------
// The worker

/** @returns {Worker} */
function startWorker() {
  const inline = document.getElementById("worker-source");
  if (inline) {
    const source = /** @type {string} */ (inline.textContent);
    return new Worker(URL.createObjectURL(new Blob([source], { type: "text/javascript" })));
  }
  return new Worker("worker.js");
}

/** @returns {Promise<Record<string, string>>} The parser's files, by name. */
async function pythonSources() {
  const inline = document.getElementById("python-sources");
  if (inline) return JSON.parse(/** @type {string} */ (inline.textContent));
  /** @type {Record<string, string>} */
  const sources = {};
  for (const name of PYTHON_FILES) {
    const response = await fetch(`py/${name}`);
    if (!response.ok) throw new Error(`could not load py/${name} (${response.status})`);
    sources[name] = await response.text();
  }
  return sources;
}

const worker = startWorker();
/** @type {Map<number, {resolve: (reply: any) => void, reject: (err: Error) => void}>} */
const pending = new Map();
let nextId = 1;

worker.onmessage = (/** @type {MessageEvent} */ event) => {
  const { id, type } = event.data;
  const request = pending.get(id);
  if (!request) return;
  pending.delete(id);
  if (type === "error") request.reject(new Error(event.data.message));
  else request.resolve(event.data);
};

/**
 * Sends the worker a request (worker.js lists them) and resolves to its reply.
 * @param {string} type
 * @param {Record<string, unknown>} [payload]
 * @returns {Promise<any>}
 */
function ask(type, payload = {}) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    worker.postMessage({ type, id, ...payload });
  });
}

// The parser's data for a ROM's bytes, as the JSON text Python wrote. The headless checks compare
// it byte for byte with `cli.py --json`.
/**
 * @param {Uint8Array} bytes
 * @returns {Promise<string>}
 */
async function exportRomJson(bytes) {
  const { json } = await ask("export", { bytes });
  return json;
}

/**
 * @param {Uint8Array} bytes
 * @returns {Promise<RomData>}
 */
async function exportRom(bytes) {
  return JSON.parse(await exportRomJson(bytes));
}

// ---------------------------------------------------------------------------------------------
// Messages, tables and tooltips

/** @param {string} text */
function infoBox(text) {
  return element("div", { className: "box info", textContent: text });
}

/** @param {string} text */
function errorBox(text) {
  return element("div", { className: "box error", textContent: text });
}

// A table like pandas' DataFrame.to_html(index=False), as the Streamlit app shows them.
/** @param {Row[]} rows  At least one; the first one's keys are the columns. */
function table(rows) {
  const columns = Object.keys(rows[0]);
  const head = element("tr", {}, columns.map((name) => element("th", { textContent: name })));
  const body = rows.map((row) => element("tr", {}, columns.map((name) => element("td", {
    textContent: String(row[name]),
  }))));
  return element("table", { className: "data" }, [element("thead", {}, [head]), element("tbody", {}, body)]);
}

/**
 * @param {MouseEvent} event
 * @param {TooltipFields} fields
 */
function showTooltip(event, fields) {
  const tip = tooltip;
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
  tooltip.hidden = true;
}

/**
 * @param {SVGElement} node
 * @param {TooltipFields} fields
 * @returns {SVGElement}
 */
function withTooltip(node, fields) {
  node.addEventListener("mousemove", (event) => showTooltip(event, fields));
  node.addEventListener("mouseleave", hideTooltip);
  node.addEventListener("click", (event) => showTooltip(event, fields));
  return node;
}

// ---------------------------------------------------------------------------------------------
// The maps. Coordinates are the parser's: x grows right, y grows up from the bottom of the map,
// one unit per room or screen, as in the app's Bokeh figures.

/**
 * An empty map: `rect` and `text` place shapes in map units.
 * @param {number} widthUnits
 * @param {number} heightUnits
 * @param {number} unit  Pixels per map unit.
 * @param {string} title
 */
function plot(widthUnits, heightUnits, unit, title) {
  const svg = svgElement("svg", {
    viewBox: `0 0 ${widthUnits * unit} ${heightUnits * unit}`,
    width: widthUnits * unit, height: heightUnits * unit, class: "map", role: "img", "aria-label": title,
  });
  /** @param {number} x */
  const toX = (x) => x * unit;
  /** @param {number} y */
  const toY = (y) => (heightUnits - y) * unit;
  /**
   * A rectangle centred on (cx, cy).
   * @param {number} cx
   * @param {number} cy
   * @param {number} w
   * @param {number} h
   * @param {Record<string, string | number>} attrs
   */
  const rect = (cx, cy, w, h, attrs) => svgElement("rect", {
    x: toX(cx - w / 2), y: toY(cy + h / 2), width: w * unit, height: h * unit, ...attrs,
  });
  /**
   * Left-aligned text, vertically centred on y.
   * @param {number} x
   * @param {number} y
   * @param {string} value
   * @param {string} size  A CSS font size.
   */
  const text = (x, y, value, size) => {
    const node = svgElement("text", { x: toX(x), y: toY(y), "font-size": size, "dominant-baseline": "middle" });
    node.textContent = value;
    return node;
  };
  return { svg, rect, text };
}

// Door markers: the app maps 'black' (an open door) to dark grey and keeps the other colours.
const DOOR_COLOUR = (/** @type {string} */ colour) => (colour === "black" ? "#333333" : colour);
/** @type {Direction[]} */
const DIRECTIONS = ["north", "south", "east", "west"];
// Solid walls are drawn as bars on the side of the room they belong to.
/** @type {Record<Direction, [number, number]>} */
const WALL_SIZE = { north: [1, 0.05], south: [1, 0.05], east: [0.05, 1], west: [0.05, 1] };
/** @type {Array<[string, string]>} */
const LEGEND = [["Open Door", "black"], ["Shutter Door", "brown"], ["Key-Locked Door", "orange"],
                ["Bombable Wall", "blue"], ["Walk-Through Wall", "purple"], ["Solid Wall", "red"]];

/**
 * A room's number-valued field, such as "north.x"; the caller has checked it is there.
 * @param {Room} room
 * @param {string} key
 */
const coordinate = (room, key) => /** @type {number} */ (room[key]);

/**
 * @param {string} levelNum
 * @param {Level} level
 */
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
      const colour = DOOR_COLOUR(/** @type {string} */ (room[`${direction}.color`]));
      svg.append(rect(coordinate(room, `${direction}.x`), coordinate(room, `${direction}.y`), 0.1, 0.1, {
        fill: colour, "fill-opacity": 0.6, stroke: colour, "pointer-events": "none",
      }));
    }
  }
  // Each wall between two rooms is recorded on both rooms' sides: draw it once.
  /** @type {Map<string, [number, number, number, number]>} */
  const walls = new Map();
  for (const room of level.rooms) {
    for (const direction of DIRECTIONS) {
      if (room[`${direction}.color`] !== "red" || room[`${direction}.wall.x`] === undefined) continue;
      const [w, h] = WALL_SIZE[direction];
      const x = coordinate(room, `${direction}.wall.x`);
      const y = coordinate(room, `${direction}.wall.y`);
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

/** @param {OverworldScreen[]} screens */
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

const hex = (/** @type {number[]} */ values) => values.map((value) => value.toString(16).padStart(2, "0")).join(" ") + " ";

/**
 * @param {Recorder} recorder
 * @returns {HTMLElement[]}
 */
function recorderInfo(recorder) {
  if (!recorder || !recorder.data) return [infoBox("This ROM doesn't appear to have a custom recorder tune")];
  const tune = /** @type {RecorderTune} */ (recorder);
  const url = URL.createObjectURL(new Blob([new Uint8Array(tune.patch)], { type: "application/octet-stream" }));
  return [
    element("p", { textContent: `Recorder Text: ${tune.text}` }),
    element("p", { className: "mono", textContent: `Recorder Data: ${hex(tune.data)}` }),
    element("p", { className: "mono", textContent: `Recorder Patch Data: ${hex(tune.patch)}` }),
    element("a", { className: "button", href: url, download: tune.filename,
                   textContent: `Download recorder tune IPS patch (${tune.filename})` }),
  ];
}

/**
 * @param {ParsedRom} data
 * @returns {HTMLElement[]}
 */
function itemSummary(data) {
  const summary = data.itemSummary;
  /** @type {HTMLElement[]} */
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
  /** @type {Array<[string, Row[]]>} */
  const columns = [["Major Caves:", summary.caves], ["Shops:", summary.shops], ["Overworld Items:", summary.overworld]];
  out.push(element("div", { className: "grid three" }, columns.map(([title, rows]) => element("div", {}, [
    element("p", {}, [element("strong", { textContent: title })]), ...(rows.length ? [table(rows)] : []),
  ]))));
  return out;
}

/**
 * @param {ParsedRom} data
 * @returns {HTMLElement[]}
 */
function hintTexts(data) {
  /** @type {Row[]} */
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

/** @type {RomData | null} */
let current = null;  // the parser's data for the chosen ROM

/** @param {unknown} err */
const errorMessage = (err) => (err instanceof Error ? err.message : String(err));

function renderView() {
  hideTooltip();
  const data = current;
  if (!data) return;  // no ROM: the view picker is hidden
  const view = viewSelect.value;
  const ok = data.status === "ok";
  /** @type {HTMLElement[]} */
  let content;
  if (view.startsWith("Level ")) {
    const level = view.split(" ")[1];
    content = ok ? [drawLevel(level, data.levels[level])]
      : [infoBox("Sorry, level maps aren't available for this ROM")];
  } else if (view === "Overworld") {
    content = ok ? [drawOverworld(data.overworld)] : [infoBox("Sorry, level maps aren't available for this ROM")];
  } else if (view === "Recorder Info") {
    content = recorderInfo(data.recorder);
  } else if (view === "Item Summary") {
    content = ok ? itemSummary(data) : [infoBox("Sorry, item summary isn't available for this ROM")];
  } else {
    content = ok ? hintTexts(data) : [infoBox("Sorry, hint texts aren't available for this ROM")];
  }
  output.replaceChildren(...content);
}

/** @param {RomData} data */
function showRom(data) {
  current = data;
  messageArea.replaceChildren(...(data.status === "encoded" ? [errorBox(data.message)]
    : data.status === "unsupported" ? [infoBox(data.message)] : []));
  picker.hidden = false;
  renderView();
}

function showNoRom() {
  current = null;
  messageArea.replaceChildren(infoBox(NO_ROM_TEXT));
  picker.hidden = true;
  output.replaceChildren();
}

async function onRomChosen() {
  const file = romInput.files?.[0];
  if (!file) {
    showNoRom();
    return;
  }
  statusLine.textContent = `Reading ${file.name}…`;
  try {
    showRom(await exportRom(new Uint8Array(await file.arrayBuffer())));
    statusLine.textContent = `Showing ${file.name}.`;
  } catch (err) {
    showNoRom();
    statusLine.textContent = `Could not read ${file.name}: ${errorMessage(err)}`;
  }
}

viewSelect.append(...VIEWS.map((view) => element("option", { value: view, textContent: view })));
viewSelect.addEventListener("change", renderView);
romInput.addEventListener("change", onRomChosen);
document.addEventListener("keydown", (event) => { if (event.key === "Escape") hideTooltip(); });
showNoRom();

Object.assign(window, { z1rVisualizer: { exportRom, exportRomJson, current: () => current } });

(async () => {
  const started = performance.now();
  try {
    const { python } = await ask("init", { sources: await pythonSources() });
    romInput.disabled = false;
    statusLine.textContent = `Ready (Python ${python}, ${Math.round(performance.now() - started)} ms).`;
    if (romInput.files?.[0]) onRomChosen();
  } catch (err) {
    statusLine.textContent = `Could not load Python: ${errorMessage(err)}. The first visit needs an internet ` +
                              "connection to download Pyodide.";
  }
})();
