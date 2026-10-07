// The Z1R Visualizer page. It draws every view from a seed in the seed format
// (docs/seed-format.md), which arrives one of three ways:
// - from a ROM the player chooses: the Python parser (spoiler.py, run in worker.js with Pyodide)
//   reads it; the ROM's bytes go only to the worker, and nothing is uploaded;
// - from a seed file (.json) the player chooses;
// - from the tab that opened this one, by window messaging ("View in Visualizer" in ZORA;
//   docs/seed-format.md section 5).
// Seeds from a file or another tab need no Pyodide. Every seed is checked against the format's
// schema (validate.js) before it is drawn.
//
// Served as a site, the page fetches worker.js, the schema and the parser (py/). The single-file
// build (scripts/build_site.py --single-file) inlines them, in the script elements read below.
//
// Type-checked with JSDoc (tsc --noEmit -p site/jsconfig.json, run by scripts/check_site.mjs).
// @ts-check
"use strict";

// The seed format, as the page reads it (docs/seed-format.schema.json has the full definition).
/**
 * @typedef {"north" | "east" | "south" | "west"} Direction
 * @typedef {"open" | "solid" | "bombable" | "locked" | "walk-through" | "shutter"} Door
 * @typedef {{kind: "item", item: string | null} | {kind: "transport", number: number, to: number}} Staircase
 * @typedef {{number: number, column: number, row: number, type: string,
 *   enemies: {name: string, count?: number} | null, item: {name: string, drop: boolean} | null,
 *   staircase: Staircase | null, doors: Record<Direction, Door>}} SeedRoom
 * @typedef {{number: number, color: string, rooms: SeedRoom[]}} SeedLevel
 * @typedef {{number: number, column: number, row: number, cave: {name: string, shortName: string}}} SeedScreen
 * @typedef {{item: string, price?: number, sellsOnce?: boolean}} Ware
 * @typedef {{name: string, kind: "item" | "take-any" | "shop" | "potion-shop", wares: Ware[]}} Cave
 * @typedef {{text: string, notes: number[]}} RecorderTune
 * @typedef {{format: "z1r-seed", formatVersion: string, producer: {name: string, version: string},
 *   seed?: {number?: string, flags?: string, zoraFlags?: string, code?: string[]},
 *   progressiveItems?: boolean, levels: SeedLevel[],
 *   overworld: {screens: SeedScreen[], armos: string | null, coast: string | null},
 *   caves: Cave[], hints: Array<{text: string, speaker?: string}>, recorder?: RecorderTune,
 *   requirements?: {whiteSwordHearts?: number, magicalSwordHearts?: number, level9Triforces?: number,
 *     doorRepairCost?: number},
 *   settings?: Array<{id?: string, name: string, chosen: string, resolved: string}>}} Seed
 *
 * What the page shows: a seed, or a ROM it refused (which still has its recorder tune).
 * @typedef {{seed: Seed, source: string} | {seed: null, status: "encoded" | "unsupported", message: string,
 *   recorder: RecorderTune | null}} Shown
 *
 * @typedef {Record<string, string | number>} Row  A table row: column name to cell.
 * @typedef {Array<[string, string | number | undefined]>} TooltipFields
 * @typedef {{node: SVGElement, key: string, label: string, fields: TooltipFields, stair: string,
 *   x: number, y: number}} MapSpot
 *   A room or overworld screen on a map. key: its room or screen number; label: what a screen
 *   reader announces for it; stair: its transport staircase ("Stair #2"), or ""; x, y: its centre
 *   in the SVG's pixels.
 */

const PYTHON_FILES = ["constants.py", "rom_reader.py", "data_extractor.py", "spoiler.py"];
const SCHEMA_FILE = "seed-format.schema.json";
const FORMAT_MAJOR = 1;  // the seed format's major version this page reads
const HANDOFF_PROTOCOL = 1;
const MAX_SEED_JSON = 4 * 1024 * 1024;  // characters
const SVG_NS = "http://www.w3.org/2000/svg";
const VIEWS = [1, 2, 3, 4, 5, 6, 7, 8, 9].map((level) => `Level ${level}`)
  .concat(["Overworld", "Recorder Info", "Item Summary", "Hint Texts", "Seed Info"]);
const NO_ROM_TEXT = "Please upload a Legend of Zelda ROM using the file widget above. Supported ROM " +
  "types are vanilla Legend of Zelda ROMs and randomized ROMs created by Zelda Randomizer without " +
  "the ‘Race ROM’ flag checked or by ZORA without ‘Encode level data’. A seed file (.json) in the " +
  "seed format works too.";

// The page's fixed elements (index.html; this script runs after them).
const romInput = /** @type {HTMLInputElement} */ (document.getElementById("rom"));
const viewSelect = /** @type {HTMLSelectElement} */ (document.getElementById("view"));
const statusLine = /** @type {HTMLElement} */ (document.getElementById("status"));
const messageArea = /** @type {HTMLElement} */ (document.getElementById("messages"));
const picker = /** @type {HTMLElement} */ (document.getElementById("picker"));
const output = /** @type {HTMLElement} */ (document.getElementById("output"));
const tooltip = /** @type {HTMLElement} */ (document.getElementById("tooltip"));
const pageVersion = /** @type {string} */ (/** @type {HTMLElement} */ (document.getElementById("version")).textContent);

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

/** @param {unknown} err */
const errorMessage = (err) => (err instanceof Error ? err.message : String(err));

// ---------------------------------------------------------------------------------------------
// The Python worker, started on first need: at once for a normal visit, but only when a ROM is
// chosen if another tab opened this one to hand it a seed.

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

/** @type {Worker | null} */
let worker = null;
/** @type {Map<number, {resolve: (reply: any) => void, reject: (err: Error) => void}>} */
const pending = new Map();
let nextId = 1;
/** @type {Promise<void> | null} */
let pythonReady = null;

/**
 * Sends the worker a request (worker.js lists them) and resolves to its reply.
 * @param {Worker} target
 * @param {string} type
 * @param {Record<string, unknown>} [payload]
 * @returns {Promise<any>}
 */
function ask(target, type, payload = {}) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    target.postMessage({ type, id, ...payload });
  });
}

/** Starts Pyodide and the parser once; later calls wait for the same start. */
function ensurePython() {
  if (!pythonReady) {
    const started = performance.now();
    const target = startWorker();
    worker = target;
    target.onmessage = (/** @type {MessageEvent} */ event) => {
      const { id, type } = event.data;
      const request = pending.get(id);
      if (!request) return;
      pending.delete(id);
      if (type === "error") request.reject(new Error(event.data.message));
      else request.resolve(event.data);
    };
    pythonReady = (async () => {
      const { python } = await ask(target, "init", { sources: await pythonSources(), version: pageVersion });
      if (!current) statusLine.textContent = `Ready (Python ${python}, ${Math.round(performance.now() - started)} ms).`;
    })();
  }
  return pythonReady;
}

// What the parser reads from a ROM, as the JSON text Python wrote (spoiler.Read). The headless
// checks compare it byte for byte with `cli.py --json`.
/**
 * @param {Uint8Array} bytes
 * @returns {Promise<string>}
 */
async function exportRomJson(bytes) {
  await ensurePython();
  const { json } = await ask(/** @type {Worker} */ (worker), "export", { bytes });
  return json;
}

// ---------------------------------------------------------------------------------------------
// Checking a seed: its format, its major version, then the schema.

/** @type {Promise<any> | null} */
let schemaLoaded = null;

function seedSchema() {
  if (!schemaLoaded) {
    const inline = document.getElementById("seed-schema");
    schemaLoaded = inline ? Promise.resolve(JSON.parse(/** @type {string} */ (inline.textContent)))
      : fetch(SCHEMA_FILE).then((response) => {
        if (!response.ok) throw new Error(`could not load ${SCHEMA_FILE} (${response.status})`);
        return response.json();
      });
  }
  return schemaLoaded;
}

/**
 * Checks a seed document, or explains why it can't be shown.
 * @param {unknown} value
 * @returns {Promise<{seed: Seed} | {error: string}>}
 */
async function checkSeed(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return { error: "This is not a seed document." };
  const fields = /** @type {Record<string, unknown>} */ (value);
  if (fields.format !== "z1r-seed") return { error: "This is not a seed document: its \"format\" is not \"z1r-seed\"." };
  const version = typeof fields.formatVersion === "string" ? /^(\d+)\.(\d+)$/.exec(fields.formatVersion) : null;
  if (!version) return { error: "This seed document has no valid \"formatVersion\"." };
  if (Number(version[1]) !== FORMAT_MAJOR) {
    return { error: `This seed uses seed format ${fields.formatVersion}, but this visualizer reads format ` +
                    `${FORMAT_MAJOR}.x. A newer or older visualizer is needed to show it.` };
  }
  const problems = validateJsonSchema(await seedSchema(), value);
  if (problems.length) {
    const more = problems.length > 3 ? ` (and ${problems.length - 3} more)` : "";
    return { error: `This seed document does not match seed format ${FORMAT_MAJOR}: ${problems.slice(0, 3).join("; ")}${more}.` };
  }
  return { seed: /** @type {Seed} */ (value) };
}

// ---------------------------------------------------------------------------------------------
// Names, as the views show them.

// With Progressive Items, these items give the next level of their line.
/** @type {Record<string, string>} */
const PROGRESSIVE_LINES = {
  "Wood Sword": "Sword Upgrade", "White Sword": "Sword Upgrade", "Magical Sword": "Sword Upgrade",
  "Blue Candle": "Candle Upgrade", "Red Candle": "Candle Upgrade",
  "Wooden Arrow": "Arrow Upgrade", "Silver Arrow": "Arrow Upgrade",
  "Blue Ring": "Ring Upgrade", "Red Ring": "Ring Upgrade",
  "Boomerang": "Boomerang Upgrade", "Magical Boomerang": "Boomerang Upgrade",
};

/**
 * @param {Seed} seed
 * @param {string} item
 */
const itemLabel = (seed, item) => (seed.progressiveItems && PROGRESSIVE_LINES[item]) || item;

/** @param {number} number */
const roomNumber = (number) => number.toString(16).toUpperCase();

/**
 * The room's four map lines: type, enemies, item, staircase.
 * @param {Seed} seed
 * @param {SeedRoom} room
 */
function roomLines(seed, room) {
  const { enemies, item, staircase } = room;
  return [
    room.type,
    enemies ? (enemies.count !== undefined ? `${enemies.count} ${enemies.name}` : enemies.name) : "",
    item ? `${item.drop ? "D " : ""}${itemLabel(seed, item.name)}` : "",
    staircase ? (staircase.kind === "transport" ? `Stair #${staircase.number}`
      : staircase.item ? itemLabel(seed, staircase.item) : "No Item") : "",
  ];
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
/**
 * @param {Row[]} rows  At least one; the first one's keys are the columns.
 * @param {(column: string, value: string | number) => Node | string} [cell]  A cell's content;
 *   its text by default.
 */
function table(rows, cell = (column, value) => String(value)) {
  const columns = Object.keys(rows[0]);
  const head = element("tr", {}, columns.map((name) => element("th", { textContent: name })));
  const body = rows.map((row) => element("tr", {}, columns.map((name) => element("td", {}, [
    cell(name, row[name]),
  ]))));
  return element("table", { className: "data" }, [element("thead", {}, [head]), element("tbody", {}, body)]);
}

// The tooltip follows the cursor over a room, or sits beside a focused or pinned room (its
// anchor), following it when the page or a map's scroller moves.
/** @type {SVGElement | null} */
let tooltipAnchor = null;

/** @param {TooltipFields} fields */
function fillTooltip(fields) {
  tooltip.replaceChildren(...fields.map(([label, value]) => element("div", {}, [
    element("span", { className: "tip-label", textContent: `${label}: ` }),
    element("span", { textContent: value === undefined || value === "" ? "???" : String(value) }),
  ])));
  tooltip.hidden = false;
}

/**
 * Puts the tooltip's top left corner at (x, y) in the viewport, kept inside it.
 * @param {number} x
 * @param {number} y
 */
function placeTooltip(x, y) {
  const left = Math.min(x, window.innerWidth - tooltip.offsetWidth - 8);
  const top = Math.min(y, window.innerHeight - tooltip.offsetHeight - 8);
  tooltip.style.left = `${Math.max(8, left)}px`;
  tooltip.style.top = `${Math.max(8, top)}px`;
}

/**
 * @param {MouseEvent} event
 * @param {TooltipFields} fields
 */
function showTooltip(event, fields) {
  tooltipAnchor = null;
  fillTooltip(fields);
  placeTooltip(event.clientX + 14, event.clientY + 14);
}

/**
 * @param {SVGElement} node
 * @param {TooltipFields} fields
 */
function showTooltipBeside(node, fields) {
  tooltipAnchor = node;
  fillTooltip(fields);
  placeBesideAnchor();
}

// Right of the anchor, or left of it where the right has no room; hidden while it is off screen.
function placeBesideAnchor() {
  if (!tooltipAnchor) return;
  const box = tooltipAnchor.getBoundingClientRect();
  const onScreen = box.bottom > 0 && box.top < window.innerHeight && box.right > 0 && box.left < window.innerWidth;
  tooltip.hidden = !onScreen;
  if (!onScreen) return;
  const right = box.right + 8;
  placeTooltip(right + tooltip.offsetWidth <= window.innerWidth - 8 ? right : box.left - tooltip.offsetWidth - 8,
               box.top);
}

function hideTooltip() {
  tooltipAnchor = null;
  tooltip.hidden = true;
}

window.addEventListener("scroll", placeBesideAnchor, true);  // capturing, to hear the maps' scrollers
window.addEventListener("resize", placeBesideAnchor);

// ---------------------------------------------------------------------------------------------
// Pinning: a click or tap on a room, or Enter or Space on a focused one, keeps its tooltip beside
// it and outlines it. Clicking it again, clicking the map beside the rooms, or Escape unpins.
//
// Staircase pairs: while a room at one end of a transport staircase is hovered, focused or
// pinned, the room at the other end has a dashed outline and a dashed line joins the two.

/**
 * The pinned room and the view it is on. It stays while other views are shown, and is dropped
 * when a new seed is shown.
 * @type {{view: string, key: string} | null}
 */
let pinned = null;

/**
 * The map on screen, if any.
 * @type {{showPin: () => void, unpin: () => void, spot: (key: string) => MapSpot | null} | null}
 */
let currentMap = null;

const MAP_HINT = "Hover over a room for its details. Click or tap it, or press Enter on it, to pin them; " +
                 "Escape unpins. Tab moves between rooms.";

/**
 * Makes a map's spots hoverable, focusable and pinnable, and makes it the current map.
 * @param {string} view  The view showing the map, e.g. "Level 4".
 * @param {SVGElement} svg
 * @param {MapSpot[]} spots  In tab order.
 */
function makeInteractive(view, svg, spots) {
  /** @param {string} key */
  const spot = (key) => spots.find((candidate) => candidate.key === key) || null;
  const pinnedSpot = () => (pinned && pinned.view === view ? spot(pinned.key) : null);

  // The staircase lines go under the labels, so the labels stay readable.
  const links = svgElement("g", { class: "stair-links", "aria-hidden": "true" });
  svg.insertBefore(links, svg.querySelector("text"));
  /** @type {MapSpot | null} */
  let paired = null;
  /** @param {MapSpot | null} active  The hovered, focused or pinned spot. */
  const showStairPair = (active) => {
    if (active === paired) return;
    paired = active;
    links.replaceChildren();
    for (const candidate of spots) {
      const isPair = !!active && !!active.stair && candidate !== active && candidate.stair === active.stair;
      candidate.node.classList.toggle("stair-pair", isPair);
      if (isPair && active) {
        links.append(svgElement("line", { x1: active.x, y1: active.y, x2: candidate.x, y2: candidate.y,
                                          class: "stair-link" }));
      }
    }
  };

  // Marks the pinned spot and shows its tooltip and staircase pair, or neither.
  const showPin = () => {
    const current = pinnedSpot();
    showStairPair(current);
    for (const candidate of spots) {
      candidate.node.classList.toggle("pinned", candidate === current);
      candidate.node.setAttribute("aria-pressed", String(candidate === current));
    }
    if (current) showTooltipBeside(current.node, current.fields);
    else hideTooltip();
  };
  const unpin = () => {
    if (pinnedSpot()) pinned = null;
    showPin();
  };
  /** @param {MapSpot} target */
  const togglePin = (target) => {
    pinned = pinnedSpot() === target ? null : { view, key: target.key };
    showPin();
  };

  for (const target of spots) {
    const { node } = target;
    node.setAttribute("tabindex", "0");
    node.setAttribute("role", "button");
    node.setAttribute("aria-label", target.label);
    node.setAttribute("aria-pressed", "false");
    node.addEventListener("mousemove", (event) => {
      showStairPair(target);
      showTooltip(event, target.fields);
    });
    node.addEventListener("mouseleave", showPin);
    node.addEventListener("focus", () => {
      showStairPair(target);
      showTooltipBeside(node, target.fields);
    });
    node.addEventListener("blur", showPin);
    node.addEventListener("click", (event) => {
      event.stopPropagation();
      togglePin(target);
    });
    node.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      togglePin(target);
    });
  }
  svg.addEventListener("click", unpin);  // reached only beside the rooms: theirs stop here
  currentMap = { showPin, unpin, spot };
}

// After a map is drawn and on the page: shows its pinned spot, if it has one.
function showMapPin() {
  if (currentMap) currentMap.showPin();
}

/**
 * Tab order for a map: the top row first, each row left to right.
 * @template {{column: number, row: number}} T
 * @param {T[]} items
 * @returns {T[]}
 */
const inMapOrder = (items) => [...items].sort((a, b) => a.row - b.row || a.column - b.column);

// ---------------------------------------------------------------------------------------------
// The maps. Map units: x grows right from the map's left edge, y grows up from its bottom edge,
// one unit per room or screen, as in the Streamlit app's Bokeh figures. The seed format counts
// columns from 1 at the left and rows from 1 at the top.

/**
 * An empty map: `rect` and `text` place shapes in map units.
 * @param {number} widthUnits
 * @param {number} heightUnits
 * @param {number} unit  Pixels per map unit, across.
 * @param {string} title
 * @param {number} [unitY]  Pixels per map unit, down; cells can be wider than tall.
 */
function plot(widthUnits, heightUnits, unit, title, unitY = unit) {
  const svg = svgElement("svg", {
    viewBox: `0 0 ${widthUnits * unit} ${heightUnits * unitY}`,
    width: widthUnits * unit, height: heightUnits * unitY, class: "map", role: "group", "aria-label": title,
  });
  /** @param {number} x */
  const toX = (x) => x * unit;
  /** @param {number} y */
  const toY = (y) => (heightUnits - y) * unitY;
  /**
   * A rectangle centred on (cx, cy).
   * @param {number} cx
   * @param {number} cy
   * @param {number} w
   * @param {number} h
   * @param {Record<string, string | number>} attrs
   */
  const rect = (cx, cy, w, h, attrs) => svgElement("rect", {
    x: toX(cx - w / 2), y: toY(cy + h / 2), width: w * unit, height: h * unitY, ...attrs,
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
  return { svg, rect, text, toX, toY };
}

/** @type {Direction[]} */
const DIRECTIONS = ["north", "south", "east", "west"];
// Door markers' colours, as in the Streamlit app (an open door's 'black' drawn dark grey).
/** @type {Record<Door, string>} */
const DOOR_COLOURS = {
  open: "#333333", bombable: "blue", locked: "orange", "walk-through": "purple", shutter: "brown", solid: "red",
};
// Level maps: cells wider than tall, so the longest label ("D Boomerang Upgrade", 112 px at 10 px)
// fits its room; rooms fill most of their cell. The overworld's cells fit "Take Any" at 13 px.
const LEVEL_CELL = { width: 132, height: 96, room: [0.92, 0.84], label: "10px", labelInset: 0.925 };
const OVERWORLD_CELL = { width: 66, height: 44, room: 0.95, label: "13px", labelInset: 0.95 };
// Relative to a room's top right corner, in map units: where a direction's door marker sits (east
// and west ones in the gap between rooms, clear of the labels) and its size; where its solid
// wall's bar is centred; and the bar's size.
/** @type {Record<Direction, [number, number]>} */
const DOOR_OFFSET = { north: [-0.5, -0.05], south: [-0.5, -0.95], east: [-0.04, -0.5], west: [-0.96, -0.5] };
/** @type {Record<Direction, [number, number]>} */
const DOOR_SIZE = { north: [0.1, 0.1], south: [0.1, 0.1], east: [0.05, 0.13], west: [0.05, 0.13] };
// The order the details card lists a room's doors in.
/** @type {Direction[]} */
const CLOCKWISE = ["north", "east", "south", "west"];
// A class for each of a room's four label lines, so the page can show or hide each kind.
const LABEL_CLASSES = ["label label-type", "label label-enemies", "label label-item"];
/** @type {Record<Direction, [number, number]>} */
const WALL_OFFSET = { north: [-0.5, 0], south: [-0.5, -1], east: [0, -0.5], west: [-1, -0.5] };
/** @type {Record<Direction, [number, number]>} */
const WALL_SIZE = { north: [1, 0.05], south: [1, 0.05], east: [0.05, 1], west: [0.05, 1] };
// Which neighbour (column, row change) a side faces; rows count down from the top.
/** @type {Record<Direction, [number, number]>} */
const NEIGHBOUR = { north: [0, -1], south: [0, 1], east: [1, 0], west: [-1, 0] };
// The legend: each entry's label and the kind of door (or the wall) its swatch shows.
/** @type {Array<[string, Door]>} */
const LEGEND = [["Open Door", "open"], ["Shutter Door", "shutter"], ["Key-Locked Door", "locked"],
                ["Bombable Wall", "bombable"], ["Walk-Through Wall", "walk-through"], ["Solid Wall", "solid"]];

/**
 * @param {Seed} seed
 * @param {SeedLevel} level
 */
function drawLevel(seed, level) {
  const { svg, rect, text, toX, toY } = plot(8, 8, LEVEL_CELL.width, `Level ${level.number} map`, LEVEL_CELL.height);
  const roomColour = level.color;
  // A room's top right corner in map units: x = column, y = rows above the bottom edge.
  const corner = (/** @type {SeedRoom} */ room) => [room.column, 9 - room.row];
  const occupied = new Set(level.rooms.map((room) => `${room.column},${room.row}`));

  /** @type {MapSpot[]} */
  const spots = [];
  for (const room of inMapOrder(level.rooms)) {
    const [x, y] = corner(room);
    const node = rect(x - 0.5, y - 0.5, LEVEL_CELL.room[0], LEVEL_CELL.room[1], {
      fill: roomColour, "fill-opacity": 0.6, stroke: roomColour, class: "room",
    });
    svg.append(node);
    const { staircase, enemies } = room;
    const key = roomNumber(room.number);
    spots.push({
      node,
      key,
      label: [`Room ${key}`, ...roomLines(seed, room)].filter(Boolean).join(", "),
      fields: [
        ["Room", `${key} · ${room.type}`],
        ["Enemies", enemies ? (enemies.count !== undefined ? `${enemies.count} ${enemies.name}` : enemies.name) : "None"],
        ["Item", room.item
          ? `${itemLabel(seed, room.item.name)} (${room.item.drop ? "dropped by the enemies" : "on the floor"})` : "None"],
        ["Stairs", staircase ? (staircase.kind === "transport"
          ? `Stairway #${staircase.number}, to room ${roomNumber(staircase.to)}`
          : `Item cellar: ${staircase.item ? itemLabel(seed, staircase.item) : "empty"}`) : "None"],
        ["Doors", CLOCKWISE.map((side) => `${side[0].toUpperCase()} ${room.doors[side]}`).join(" · ")],
        ["Position", `column ${room.column}, row ${room.row}`],
      ],
      stair: staircase && staircase.kind === "transport" ? `Stair #${staircase.number}` : "",
      x: toX(x - 0.5),
      y: toY(y - 0.5),
    });
  }
  for (const room of level.rooms) {
    const [x, y] = corner(room);
    for (const direction of DIRECTIONS) {
      const door = room.doors[direction];
      if (door === "solid") continue;
      const [dx, dy] = DOOR_OFFSET[direction];
      const [w, h] = DOOR_SIZE[direction];
      const colour = DOOR_COLOURS[door];
      svg.append(rect(x + dx, y + dy, w, h, {
        fill: colour, "fill-opacity": 0.6, stroke: colour, "pointer-events": "none", class: `door door-${door}`,
      }));
    }
  }
  // A solid wall is drawn only between two rooms of the level; each such wall is on both rooms'
  // sides, so it is drawn once.
  /** @type {Map<string, [number, number, number, number]>} */
  const walls = new Map();
  for (const room of level.rooms) {
    const [x, y] = corner(room);
    for (const direction of DIRECTIONS) {
      if (room.doors[direction] !== "solid") continue;
      const [nc, nr] = NEIGHBOUR[direction];
      if (!occupied.has(`${room.column + nc},${room.row + nr}`)) continue;
      const [dx, dy] = WALL_OFFSET[direction];
      const [w, h] = WALL_SIZE[direction];
      walls.set(`${(x + dx).toFixed(3)},${(y + dy).toFixed(3)},${w},${h}`, [x + dx, y + dy, w, h]);
    }
  }
  for (const [x, y, w, h] of walls.values()) {
    svg.append(rect(x, y, w, h, { fill: "red", stroke: "red", "pointer-events": "none", class: "wall" }));
  }
  for (const room of level.rooms) {
    const [x, y] = corner(room);
    roomLines(seed, room).forEach((line, i) => {
      if (!line) return;
      const label = text(x - LEVEL_CELL.labelInset, y - 0.2 * (i + 1), line, LEVEL_CELL.label);
      label.setAttribute("pointer-events", "none");
      label.setAttribute("class", i < 3 ? LABEL_CLASSES[i]
        : room.staircase && room.staircase.kind === "transport" ? "label label-transport" : "label label-cellar");
      svg.append(label);
    });
  }

  const legend = element("div", { className: "legend" }, [
    element("span", { className: "legend-title", textContent: "The Legend of Door & Wall Types" }),
    ...LEGEND.map(([label, kind]) => element("span", { className: "legend-item" }, [
      element("span", { className: `swatch swatch-${kind}` }), label,
    ])),
  ]);
  makeInteractive(`Level ${level.number}`, svg, spots);
  return element("figure", { className: "plot level" }, [
    element("figcaption", { textContent: `Level ${level.number}` }), element("div", { className: "scroll" }, [svg]), legend,
    element("p", { className: "map-hint", textContent: MAP_HINT }),
  ]);
}

/** @param {SeedScreen[]} screens */
function drawOverworld(screens) {
  const { svg, rect, text, toX, toY } = plot(16, 8, OVERWORLD_CELL.width, "Overworld map", OVERWORLD_CELL.height);
  /** @type {MapSpot[]} */
  const spots = [];
  for (const screen of inMapOrder(screens)) {
    const x = screen.column - 0.5;
    const y = 8.5 - screen.row;
    const node = rect(x, y, OVERWORLD_CELL.room, OVERWORLD_CELL.room, {
      fill: "#4CAF50", "fill-opacity": 0.6, stroke: "#4CAF50", class: "room",
    });
    svg.append(node);
    const key = screen.number.toString(16);
    spots.push({
      node,
      key,
      label: `Screen ${key}, ${screen.cave.name}`,
      fields: [["Screen", `${key} · ${screen.cave.name}`], ["Map label", screen.cave.shortName],
               ["Position", `column ${screen.column}, row ${screen.row}`]],
      stair: "",
      x: toX(x),
      y: toY(y),
    });
  }
  for (const screen of screens) {
    const label = text(screen.column - OVERWORLD_CELL.labelInset, 8.5 - screen.row, screen.cave.shortName,
                       OVERWORLD_CELL.label);
    label.setAttribute("pointer-events", "none");
    label.setAttribute("class", "label label-cave");
    svg.append(label);
  }
  makeInteractive("Overworld", svg, spots);
  return element("figure", { className: "plot overworld" }, [
    element("figcaption", { textContent: "Overworld" }), element("div", { className: "scroll" }, [svg]),
    element("p", { className: "map-hint", textContent: MAP_HINT }),
  ]);
}

// ---------------------------------------------------------------------------------------------
// The other views

const hex = (/** @type {number[]} */ values) => values.map((value) => value.toString(16).padStart(2, "0")).join(" ") + " ";

/**
 * The IPS patch that adds a custom recorder tune to a ROM, as the Streamlit app builds it
 * (data_extractor.py, GetRecorderPatchData).
 * @param {number[]} notes
 */
function recorderPatch(notes) {
  return [
    0x50, 0x41, 0x54, 0x43, 0x48,  // PATCH
    0x00, 0x1A, 0xFE, 0x00, 0x03, 0x20, 0x00, 0xA0,
    0x00, 0x1B, 0x12, 0x00, 0x03, 0x20, 0x10, 0xA0,
    0x00, 0x1B, 0x3D, 0x00, 0x03, 0x20, 0x10, 0xA0,
    0x00, 0x20, 0x10, 0x00, 0x0E,
    0xAD, 0x07, 0x06, 0xC9, 0x10, 0xD0, 0x03, 0xA9, 0x00, 0x60, 0xB9, 0x54, 0x9A, 0x60,
    0x00, 0x20, 0x20, 0x00, 0x0F,
    0xAD, 0x07, 0x06, 0xC9, 0x10, 0xD0, 0x04, 0xB9, 0x20, 0xA0, 0x60, 0xB9, 0x55, 0x9A, 0x60,
    0x00, 0x20, 0x30, 0x00, notes.length, ...notes,
    0x45, 0x4F, 0x46,  // EOF
  ];
}

/**
 * @param {RecorderTune | null | undefined} tune
 * @returns {HTMLElement[]}
 */
function recorderInfo(tune) {
  if (!tune) return [infoBox("This ROM doesn't appear to have a custom recorder tune")];
  const patch = recorderPatch(tune.notes);
  const filename = `${tune.text.replace(/ /g, "_")}.ips`;
  const url = URL.createObjectURL(new Blob([new Uint8Array(patch)], { type: "application/octet-stream" }));
  return [
    element("p", { textContent: `Recorder Text: ${tune.text}` }),
    element("p", { className: "mono", textContent: `Recorder Data: ${hex(tune.notes)}` }),
    element("p", { className: "mono", textContent: `Recorder Patch Data: ${hex(patch)}` }),
    element("a", { className: "button", href: url, download: filename,
                   textContent: `Download recorder tune IPS patch (${filename})` }),
  ];
}

// The item summary, with the Streamlit app's rules (spoiler.ItemSummary has them in Python).
const EXCLUDED_ITEMS = ["Rupee", "5 Rupees", "Bombs", "Key", "Map", "Compass", "Triforce", "No Item", "Nothing"];

/**
 * @param {Seed} seed
 * @returns {{levels: Record<string, Row[]>, caves: Row[], shops: Row[], overworld: Row[]}}
 */
function itemSummaryTables(seed) {
  const named = (/** @type {string} */ item) => !item.startsWith("Unknown Item ");
  /** @type {Record<string, Row[]>} */
  const levels = {};
  for (let number = 1; number <= 9; number++) {
    /** @type {Row[]} */
    const rows = [];
    const level = seed.levels.find((candidate) => candidate.number === number);
    for (const room of level ? level.rooms : []) {
      if (room.item) {
        const item = itemLabel(seed, room.item.name);
        if (!EXCLUDED_ITEMS.includes(item)) {
          rows.push({ Item: item, Screen: roomNumber(room.number), Location: room.item.drop ? "Drop" : "Floor" });
        }
      }
      if (room.staircase && room.staircase.kind === "item") {
        const item = room.staircase.item ? itemLabel(seed, room.staircase.item) : "No Item";
        if (!EXCLUDED_ITEMS.includes(item)) rows.push({ Item: item, Screen: roomNumber(room.number), Location: "Item Stairway" });
      }
    }
    levels[String(number)] = rows;
  }
  const caves = seed.caves.filter((cave) => cave.kind === "item").flatMap((cave) => cave.wares
    .filter((ware) => named(ware.item)).map((ware) => ({ Cave: cave.name, Item: itemLabel(seed, ware.item) })));
  const shops = seed.caves.filter((cave) => cave.kind === "shop" || cave.kind === "potion-shop").flatMap((cave) => cave.wares
    .filter((ware) => named(ware.item)).map((ware) => {
      /** @type {Row} */
      const row = { Shop: cave.name, Item: itemLabel(seed, ware.item), Price: ware.price === undefined ? "" : ware.price };
      if (ware.sellsOnce) row.Once = "yes";
      return row;
    }));
  // A table's columns come from its first row: give every row the "Once" column if any has it.
  if (shops.some((row) => row.Once)) for (const row of shops) row.Once = row.Once || "";
  const overworld = [
    { Location: "Armos", Item: seed.overworld.armos ? itemLabel(seed, seed.overworld.armos) : "Nothing" },
    { Location: "Coast", Item: seed.overworld.coast ? itemLabel(seed, seed.overworld.coast) : "Nothing" },
  ];
  return { levels, caves, shops, overworld };
}

/**
 * Shows a level's map with one room pinned, scrolled into view and focused.
 * @param {number} level
 * @param {string} key  The room number.
 */
function showRoomOnMap(level, key) {
  const view = `Level ${level}`;
  pinned = { view, key };
  viewSelect.value = view;
  renderView();
  const target = currentMap ? currentMap.spot(key) : null;
  if (!target) return;
  target.node.scrollIntoView({ block: "center", inline: "center" });
  target.node.focus({ preventScroll: true });
}

/**
 * An Item Summary room number that opens its level's map with the room pinned.
 * @param {number} level
 * @param {string} key
 */
function roomLink(level, key) {
  const button = element("button", { type: "button", className: "link", textContent: key });
  button.setAttribute("aria-label", `Show room ${key} on the Level ${level} map`);
  button.title = `Show on the Level ${level} map`;
  button.addEventListener("click", () => showRoomOnMap(level, key));
  return button;
}

/**
 * @param {Seed} seed
 * @returns {HTMLElement[]}
 */
function itemSummary(seed) {
  const summary = itemSummaryTables(seed);
  /** @type {HTMLElement[]} */
  const out = [];
  if (seed.progressiveItems) {
    out.push(infoBox("This ROM uses ZORA's Progressive Items: each sword, candle, arrow, ring and " +
                     "boomerang found or bought gives the next level the player lacks, so they are " +
                     "listed by their upgrade line."));
  }
  out.push(element("h2", { textContent: "Dungeon Items" }));
  const levels = element("div", { className: "grid three" });
  for (let level = 1; level <= 9; level++) {
    const items = summary.levels[String(level)];
    levels.append(element("div", {}, items.length
      ? [element("p", {}, [element("strong", { textContent: `Level ${level}:` })]),
         table(items, (column, value) => (column === "Screen" ? roomLink(level, String(value)) : String(value)))]
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
 * @param {Seed} seed
 * @returns {HTMLElement[]}
 */
function hintTexts(seed) {
  const speakers = seed.hints.some((hint) => hint.speaker !== undefined);
  /** @type {Row[]} */
  const rows = seed.hints.map((hint, num) => /** @type {Row} */ (speakers
    ? { "Text #": num, Text: hint.text, "Said By": hint.speaker || "" } : { "Text #": num, Text: hint.text }));
  if (seed.recorder && seed.recorder.text) {
    rows.push(speakers ? { "Text #": "Recorder", Text: seed.recorder.text, "Said By": "" }
      : { "Text #": "Recorder", Text: seed.recorder.text });
  }
  return [
    element("p", { textContent: `This seed has ${seed.hints.length} texts.${speakers ? ""
      : " Which character says each one isn't stored in the ROM."}` }),
    ...(rows.length ? [table(rows)] : []),
  ];
}

/**
 * The seed's source and producer, how it was made, and what it needs.
 * @param {Seed} seed
 * @param {string} source
 * @returns {HTMLElement[]}
 */
function seedInfo(seed, source) {
  /** @type {Row[]} */
  const about = [
    { Field: "Shown from", Value: source },
    { Field: "Producer", Value: `${seed.producer.name} ${seed.producer.version}`.trim() },
    { Field: "Seed format", Value: seed.formatVersion },
  ];
  const made = seed.seed || {};
  if (made.number) about.push({ Field: "Seed", Value: made.number });
  if (made.flags) about.push({ Field: "Flags", Value: made.flags });
  if (made.zoraFlags) about.push({ Field: "ZORA flags", Value: made.zoraFlags });
  if (made.code && made.code.length) about.push({ Field: "Seed code", Value: made.code.join(" · ") });
  about.push({ Field: "Progressive Items", Value: seed.progressiveItems ? "on" : "off" });
  const out = [element("h2", { textContent: "Seed" }), table(about)];

  const needs = seed.requirements || {};
  /** @type {Array<[string, number | undefined]>} */
  const needed = [["White sword cave (hearts)", needs.whiteSwordHearts],
                  ["Magical sword cave (hearts)", needs.magicalSwordHearts],
                  ["Level 9 (triforce pieces)", needs.level9Triforces], ["Door repair (rupees)", needs.doorRepairCost]];
  const knownNeeds = needed.filter(([, value]) => value !== undefined);
  if (knownNeeds.length) {
    out.push(element("h2", { textContent: "Requirements" }),
             table(knownNeeds.map(([what, value]) => ({ Requirement: what, Value: /** @type {number} */ (value) }))));
  }
  if (seed.settings && seed.settings.length) {
    out.push(element("h2", { textContent: "Settings" }), table(seed.settings.map((setting) => ({
      Setting: setting.id ? `${setting.id} ${setting.name}` : setting.name, Chosen: setting.chosen, Resolved: setting.resolved,
    }))));
  }
  const url = URL.createObjectURL(new Blob([JSON.stringify(seed, null, 2)], { type: "application/json" }));
  out.push(element("p", {}, [element("a", { className: "button", href: url, download: "seed.json",
                                            textContent: "Download this seed as a seed file (.json)" })]));
  return out;
}

// ---------------------------------------------------------------------------------------------
// The page

/** @type {Shown | null} */
let current = null;

function renderView() {
  hideTooltip();
  currentMap = null;
  const shown = current;
  if (!shown) return;  // nothing chosen: the view picker is hidden
  const view = viewSelect.value;
  const seed = shown.seed;
  /** @type {HTMLElement[]} */
  let content;
  if (view.startsWith("Level ")) {
    const number = Number(view.split(" ")[1]);
    const level = seed ? seed.levels.find((candidate) => candidate.number === number) : undefined;
    content = !seed ? [infoBox("Sorry, level maps aren't available for this ROM")]
      : level ? [drawLevel(seed, level)] : [infoBox(`This seed has no Level ${number}.`)];
  } else if (view === "Overworld") {
    content = seed ? [drawOverworld(seed.overworld.screens)] : [infoBox("Sorry, level maps aren't available for this ROM")];
  } else if (view === "Recorder Info") {
    content = recorderInfo(shown.seed ? shown.seed.recorder : shown.recorder);
  } else if (view === "Item Summary") {
    content = seed ? itemSummary(seed) : [infoBox("Sorry, item summary isn't available for this ROM")];
  } else if (view === "Hint Texts") {
    content = seed ? hintTexts(seed) : [infoBox("Sorry, hint texts aren't available for this ROM")];
  } else {
    content = shown.seed ? seedInfo(shown.seed, shown.source) : [infoBox("Sorry, seed info isn't available for this ROM")];
  }
  output.replaceChildren(...content);
  showMapPin();
}

/** @param {Shown} shown */
function show(shown) {
  current = shown;
  pinned = null;
  messageArea.replaceChildren(...(shown.seed ? []
    : [shown.status === "encoded" ? errorBox(shown.message) : infoBox(shown.message)]));
  picker.hidden = false;
  renderView();
}

/** @param {string} [message]  Why nothing is shown, as an error. */
function showNothing(message) {
  current = null;
  pinned = null;
  messageArea.replaceChildren(message ? errorBox(message) : infoBox(NO_ROM_TEXT));
  picker.hidden = true;
  output.replaceChildren();
}

/**
 * Checks a seed document's JSON text and shows it, or shows why not.
 * @param {string} json
 * @param {string} source  Where it came from, e.g. "seed.json".
 * @returns {Promise<string | null>} null when shown, else the reason it was refused.
 */
async function showSeedJson(json, source) {
  /** @type {unknown} */
  let value;
  try {
    value = JSON.parse(json);
  } catch (err) {
    const reason = `This is not a seed document: it is not valid JSON (${errorMessage(err)}).`;
    showNothing(reason);
    return reason;
  }
  const checked = await checkSeed(value);
  if ("error" in checked) {
    showNothing(checked.error);
    return checked.error;
  }
  show({ seed: checked.seed, source });
  const { name, version } = checked.seed.producer;
  statusLine.textContent = `Showing ${source}: a seed from ${name}${version ? ` ${version}` : ""} ` +
                           `(seed format ${checked.seed.formatVersion}).`;
  return null;
}

/** @param {File} file */
async function isSeedFile(file) {
  if (/\.json$/i.test(file.name)) return true;
  const start = new TextDecoder().decode(await file.slice(0, 64).arrayBuffer());
  return start.trimStart().startsWith("{");
}

async function onFileChosen() {
  const file = romInput.files?.[0];
  if (!file) {
    showNothing();
    return;
  }
  try {
    if (await isSeedFile(file)) {
      if (file.size > MAX_SEED_JSON) throw new Error("the file is too large to be a seed document");
      await showSeedJson(await file.text(), file.name);
      return;
    }
    statusLine.textContent = pythonReady ? `Reading ${file.name}…` : `Loading Python to read ${file.name}…`;
    /** @type {{status: "ok", seed: unknown} | {status: "encoded" | "unsupported", message: string, recorder: RecorderTune | null}} */
    const result = JSON.parse(await exportRomJson(new Uint8Array(await file.arrayBuffer())));
    if (result.status !== "ok") {
      show({ seed: null, status: result.status, message: result.message, recorder: result.recorder });
      statusLine.textContent = `Showing ${file.name}.`;
      return;
    }
    const checked = await checkSeed(result.seed);
    if ("error" in checked) throw new Error(checked.error);
    show({ seed: checked.seed, source: file.name });
    statusLine.textContent = `Showing ${file.name}.`;
  } catch (err) {
    showNothing();
    statusLine.textContent = `Could not read ${file.name}: ${errorMessage(err)}`;
  }
}

viewSelect.append(...VIEWS.map((view) => element("option", { value: view, textContent: view })));
viewSelect.addEventListener("change", renderView);
romInput.addEventListener("change", onFileChosen);
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (currentMap) currentMap.unpin();
  else hideTooltip();
});
showNothing();

// ---------------------------------------------------------------------------------------------
// The hand-off (docs/seed-format.md section 5): tell the opener this page is ready, and show the
// seed it posts back. Only the opener is listened to; any origin may be the opener.

/**
 * @param {MessageEventSource} target
 * @param {string} origin  The origin the message came from; "null" for a page opened from disk.
 * @param {string | null} error
 */
function replyToOpener(target, origin, error) {
  const reply = error ? { type: "z1r-seed-received", protocol: HANDOFF_PROTOCOL, ok: false, error }
    : { type: "z1r-seed-received", protocol: HANDOFF_PROTOCOL, ok: true };
  /** @type {Window} */ (target).postMessage(reply, origin === "null" ? "*" : origin);
}

function listenToOpener() {
  const opener = window.opener;
  if (!opener) return;
  let received = false;
  let tries = 0;
  const sayReady = () => opener.postMessage({ type: "z1r-seed-ready", protocol: HANDOFF_PROTOCOL }, "*");
  sayReady();
  const timer = window.setInterval(() => {
    if (received || ++tries >= 30) window.clearInterval(timer);
    else sayReady();
  }, 1000);
  statusLine.textContent = "Waiting for a seed from the page that opened this one…";

  window.addEventListener("message", async (event) => {
    if (event.source !== window.opener || !event.source) return;
    const data = event.data;
    if (!data || typeof data !== "object" || data.type !== "z1r-seed") return;
    received = true;
    /** @type {string | null} */
    let error = null;
    if (data.protocol !== HANDOFF_PROTOCOL) error = `unknown hand-off protocol ${JSON.stringify(data.protocol)}`;
    else if (typeof data.json !== "string") error = "the message has no seed JSON text";
    else if (data.json.length > MAX_SEED_JSON) error = "the seed JSON text is too large";
    if (error) showNothing(`The page that opened this one sent a seed that can't be shown: ${error}.`);
    else error = await showSeedJson(data.json, "the seed from the page that opened this one");
    replyToOpener(event.source, event.origin, error);
  });
}

Object.assign(window, {
  z1rVisualizer: {
    exportRomJson, current: () => current, showSeedJson,
    itemSummary: () => (current && current.seed ? itemSummaryTables(current.seed) : null),
    recorderPatch,
  },
});

listenToOpener();
if (!window.opener) {
  ensurePython().catch((err) => {
    statusLine.textContent = `Could not load Python: ${errorMessage(err)}. The first visit needs an internet ` +
                             "connection to download Pyodide. Seed files (.json) still open.";
  });
}
