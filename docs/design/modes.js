// Quest Log mockup glue, on top of mockup.js: the map modes, the popup / side-panel switch, and
// labels that always fit their room.
// - Modes: presets (Everything, Route, Items, Layout only) and the layers behind them (room types,
//   enemies, items, minor items, transport staircases, door markers, major-item outline, fading),
//   plus the advanced tabs. They set classes on <body>; the stylesheet hides or shows by them.
// - Room details: as a popup by the room, or docked in the side panel ("Room ledger").
// - Fit: a label wider than its room is narrowed to fit (SVG textLength), measured with the
//   label's own font, so it never spills into the next room.
// Choices are remembered per browser. Stage 2 would move this into the page's own script.
"use strict";
(() => {
  const body = document.body;
  const output = /** @type {HTMLElement} */ (document.getElementById("output"));
  const tooltip = /** @type {HTMLElement} */ (document.getElementById("tooltip"));
  const panel = document.querySelector("[data-details-panel]");
  const params = new URLSearchParams(location.search);

  // Minor items: the ones the Item Summary leaves out.
  const MINOR = new Set(["Rupee", "5 Rupees", "Bombs", "Key", "Map", "Compass", "Triforce", "No Item"]);
  const LAYERS = ["types", "enemies", "items", "minor", "stairs", "doors", "highlight", "dim", "advanced"];
  const PRESETS = {
    everything: { types: true, enemies: true, items: true, minor: true, stairs: true, doors: true, highlight: false, dim: false },
    route: { types: false, enemies: false, items: true, minor: false, stairs: true, doors: true, highlight: true, dim: false },
    items: { types: false, enemies: false, items: true, minor: false, stairs: false, doors: false, highlight: true, dim: true },
    layout: { types: true, enemies: false, items: false, minor: false, stairs: true, doors: true, highlight: false, dim: false },
  };

  /** @type {{preset: string, layers: Record<string, boolean>, details: string}} */
  let state = { preset: "everything", layers: { ...PRESETS.everything, advanced: false }, details: "popup" };
  try {
    const saved = JSON.parse(localStorage.getItem("z1r-quest-log") || "null");
    if (saved && saved.layers) state = { ...state, ...saved, layers: { ...state.layers, ...saved.layers } };
  } catch (err) {
    // storage blocked or unreadable: the defaults
  }
  if (params.get("preset") && PRESETS[params.get("preset")]) {
    state.preset = params.get("preset");
    state.layers = { ...state.layers, ...PRESETS[state.preset] };
  }
  if (params.get("details")) state.details = params.get("details") === "panel" ? "panel" : "popup";
  const save = () => {
    try {
      localStorage.setItem("z1r-quest-log", JSON.stringify(state));
    } catch (err) {
      // not remembered
    }
  };

  const apply = () => {
    for (const layer of LAYERS) {
      const on = !!state.layers[layer];
      if (layer === "highlight" || layer === "dim" || layer === "advanced") body.classList.toggle(`show-${layer}`, on);
      else body.classList.toggle(`hide-${layer}`, !on);
      const box = document.querySelector(`[data-layer="${layer}"]`);
      if (box) box.checked = on;
    }
    for (const radio of document.querySelectorAll('input[name="preset"]')) radio.checked = radio.value === state.preset;
    const note = document.querySelector("[data-custom-note]");
    if (note) note.hidden = state.preset !== "custom";
    for (const radio of document.querySelectorAll('input[name="details"]')) radio.checked = radio.value === state.details;
    // Room details: docked in the panel, or a popup on the page.
    const docked = state.details === "panel" && panel;
    body.classList.toggle("details-panel", !!docked);
    if (docked && tooltip.parentElement !== panel) panel.append(tooltip);
    if (!docked && tooltip.parentElement !== body) body.append(tooltip);
  };

  for (const radio of document.querySelectorAll('input[name="preset"]')) {
    radio.addEventListener("change", () => {
      state.preset = radio.value;
      state.layers = { ...state.layers, ...PRESETS[radio.value] };
      apply();
      save();
    });
  }
  for (const box of document.querySelectorAll("[data-layer]")) {
    box.addEventListener("change", () => {
      state.layers[box.getAttribute("data-layer")] = box.checked;
      if (box.getAttribute("data-layer") !== "advanced") {
        const match = Object.entries(PRESETS).find(([, layers]) =>
          Object.entries(layers).every(([layer, on]) => !!state.layers[layer] === on));
        state.preset = match ? match[0] : "custom";
      }
      apply();
      save();
    });
  }
  for (const radio of document.querySelectorAll('input[name="details"]')) {
    radio.addEventListener("change", () => {
      state.details = radio.value;
      apply();
      save();
    });
  }
  // Escape closes the Customise panel when focus is in it.
  for (const details of document.querySelectorAll("details.customise")) {
    details.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && details.open) {
        details.open = false;
        details.querySelector("summary").focus();
        event.stopPropagation();
      }
    });
  }

  // After each render: mark minor items and rooms with a major item, and fit the labels.
  const canvas = document.createElement("canvas").getContext("2d");
  const seedRoom = (level, key) => {
    const shown = window.z1rVisualizer.current();
    const levelData = shown && shown.seed ? shown.seed.levels.find((candidate) => candidate.number === level) : null;
    return levelData ? levelData.rooms.find((room) => room.number.toString(16).toUpperCase() === key) : null;
  };
  const tag = () => {
    const svg = output.querySelector("svg.map");
    if (!svg) return;
    const view = document.getElementById("view").value;
    const level = view.startsWith("Level ") ? Number(view.split(" ")[1]) : null;
    const rooms = [...svg.querySelectorAll("rect.room")];
    for (const room of rooms) {
      const key = /^(?:Room|Screen) ([0-9A-Fa-f]+)/.exec(room.getAttribute("aria-label") || "");
      const data = level && key ? seedRoom(level, key[1]) : null;
      const items = data ? [data.item && data.item.name, data.staircase && data.staircase.kind === "item" && data.staircase.item] : [];
      room.classList.toggle("has-major", items.some((name) => name && !MINOR.has(name)));
    }
    const boxes = rooms.map((room) => ({
      left: Number(room.getAttribute("x")), top: Number(room.getAttribute("y")),
      right: Number(room.getAttribute("x")) + Number(room.getAttribute("width")),
      bottom: Number(room.getAttribute("y")) + Number(room.getAttribute("height")),
    }));
    for (const label of svg.querySelectorAll("text.label")) {
      if (label.classList.contains("label-item") || label.classList.contains("label-cellar")) {
        label.classList.toggle("minor", MINOR.has(label.textContent.replace(/^D /, "")));
      }
      const x = Number(label.getAttribute("x"));
      const y = Number(label.getAttribute("y"));
      const box = boxes.find((b) => x >= b.left - 12 && x <= b.right && y >= b.top && y <= b.bottom);
      if (!box) continue;
      const style = getComputedStyle(label);
      canvas.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
      const available = box.right - x - 3;
      if (canvas.measureText(label.textContent).width > available) {
        label.setAttribute("textLength", String(available));
        label.setAttribute("lengthAdjust", "spacingAndGlyphs");
      }
    }
  };
  new MutationObserver(tag).observe(output, { childList: true });

  // The options bar matters on the maps only.
  const syncOptions = () => body.classList.toggle("map-view", /^(Level |Overworld)/.test(document.getElementById("view").value));
  new MutationObserver(syncOptions).observe(output, { childList: true });

  apply();
})();
