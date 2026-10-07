// The page's furniture around the renderer (app.js): the theme toggle, the navigation, the drop
// area, the map options (what the maps show, and whether room details are a popup or sit in the
// side panel), and labels that always fit their room. app.js draws the views and owns the data;
// this script only arranges and shows or hides what it drew. It runs after app.js and uses its
// page elements and its current seed.
//
// Type-checked with JSDoc (tsc --noEmit -p site/jsconfig.json, run by scripts/check_site.mjs).
// @ts-check
"use strict";

(() => {
  const body = document.body;
  const root = document.documentElement;

  /** @param {string} key */
  const load = (key) => {
    try {
      return localStorage.getItem(key);
    } catch (err) {
      return null;  // storage blocked: nothing remembered
    }
  };
  /**
   * @param {string} key
   * @param {string} value
   */
  const store = (key, value) => {
    try {
      localStorage.setItem(key, value);
    } catch (err) {
      // not remembered
    }
  };

  // -------------------------------------------------------------------------------------------
  // Theme: "system" follows the system (the stylesheet's light-dark() colours); "light" and
  // "dark" set data-theme on <html>.

  const THEMES = ["system", "light", "dark"];
  let theme = load("z1r-theme") || "system";
  if (!THEMES.includes(theme)) theme = "system";
  const applyTheme = () => {
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    for (const button of document.querySelectorAll("[data-theme-toggle]")) {
      button.setAttribute("aria-label", `Theme: ${theme}. Change theme`);
      const label = button.querySelector("[data-theme-label]");
      if (label) label.textContent = theme[0].toUpperCase() + theme.slice(1);
    }
  };
  for (const button of document.querySelectorAll("[data-theme-toggle]")) {
    button.addEventListener("click", () => {
      theme = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
      store("z1r-theme", theme);
      applyTheme();
    });
  }
  applyTheme();

  // -------------------------------------------------------------------------------------------
  // Navigation: the buttons drive the renderer's view select, and follow it when the renderer
  // switches by itself (an Item Summary room link opens a level).

  const syncNavigation = () => {
    for (const button of document.querySelectorAll("[data-view]")) {
      if (button.getAttribute("data-view") === viewSelect.value) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    }
    body.classList.toggle("map-view", /^(Level |Overworld)/.test(viewSelect.value));
    const title = document.querySelector("[data-view-title]");
    if (title) title.textContent = viewSelect.value;
  };
  for (const button of document.querySelectorAll("[data-view]")) {
    button.addEventListener("click", () => {
      viewSelect.value = /** @type {string} */ (button.getAttribute("data-view"));
      viewSelect.dispatchEvent(new Event("change"));
    });
  }

  // The page's state for the stylesheet ("empty" until something is shown), the file's name, and
  // each level button's dungeon colour.
  const syncState = () => {
    body.dataset.state = picker.hidden ? "empty" : "loaded";
    const shown = current;
    for (const name of document.querySelectorAll("[data-file-name]")) {
      name.textContent = shown && shown.seed ? shown.source : "";
    }
    for (const button of /** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll('[data-view^="Level "]'))) {
      const number = Number(/** @type {string} */ (button.getAttribute("data-view")).split(" ")[1]);
      const level = shown && shown.seed ? shown.seed.levels.find((candidate) => candidate.number === number) : undefined;
      if (level) button.style.setProperty("--level-color", level.color);
      else button.style.removeProperty("--level-color");
    }
  };
  new MutationObserver(syncState).observe(picker, { attributes: true, attributeFilter: ["hidden"] });

  // -------------------------------------------------------------------------------------------
  // Opening files: drop one anywhere on [data-drop], or use a button marked [data-open-file].

  for (const zone of /** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll("[data-drop]"))) {
    zone.addEventListener("dragover", (event) => {
      event.preventDefault();
      zone.classList.add("dragging");
    });
    zone.addEventListener("dragleave", () => zone.classList.remove("dragging"));
    zone.addEventListener("drop", (event) => {
      event.preventDefault();
      zone.classList.remove("dragging");
      if (!event.dataTransfer || !event.dataTransfer.files.length) return;
      romInput.files = event.dataTransfer.files;
      romInput.dispatchEvent(new Event("change"));
    });
  }
  for (const button of document.querySelectorAll("[data-open-file]")) {
    button.addEventListener("click", () => romInput.click());
  }

  // -------------------------------------------------------------------------------------------
  // Map options. Presets set the layers; changing a layer by hand shows "Custom". The details
  // choice moves the renderer's tooltip into the side panel or back onto the page.

  // Minor items: the ones the Item Summary leaves out.
  const MINOR = new Set(["Rupee", "5 Rupees", "Bombs", "Key", "Map", "Compass", "Triforce", "No Item"]);
  /** @type {Record<string, Record<string, boolean>>} */
  const PRESETS = {
    everything: { types: true, enemies: true, items: true, minor: true, stairs: true, doors: true, highlight: false, dim: false },
    route: { types: false, enemies: false, items: true, minor: false, stairs: true, doors: true, highlight: true, dim: false },
    items: { types: false, enemies: false, items: true, minor: false, stairs: false, doors: false, highlight: true, dim: true },
    layout: { types: true, enemies: false, items: false, minor: false, stairs: true, doors: true, highlight: false, dim: false },
  };
  // Layers drawn unless switched off (hide-<layer>), and extras shown when switched on (show-<layer>).
  const HIDEABLE = ["types", "enemies", "items", "minor", "stairs", "doors"];
  const EXTRAS = ["highlight", "dim", "advanced"];

  /** @type {{preset: string, layers: Record<string, boolean>, details: string}} */
  let options = { preset: "everything", layers: { ...PRESETS.everything, advanced: false }, details: "popup" };
  try {
    const saved = JSON.parse(load("z1r-view-options") || "null");
    if (saved && typeof saved === "object" && saved.layers && typeof saved.layers === "object") {
      options = {
        preset: typeof saved.preset === "string" ? saved.preset : options.preset,
        layers: { ...options.layers, ...saved.layers },
        details: saved.details === "panel" ? "panel" : "popup",
      };
    }
  } catch (err) {
    // unreadable: the defaults
  }
  const panel = document.querySelector("[data-details-panel]");

  const applyOptions = () => {
    for (const layer of HIDEABLE) body.classList.toggle(`hide-${layer}`, !options.layers[layer]);
    for (const layer of EXTRAS) body.classList.toggle(`show-${layer}`, !!options.layers[layer]);
    for (const box of /** @type {NodeListOf<HTMLInputElement>} */ (document.querySelectorAll("input[data-layer]"))) {
      box.checked = !!options.layers[/** @type {string} */ (box.getAttribute("data-layer"))];
    }
    for (const radio of /** @type {NodeListOf<HTMLInputElement>} */ (document.querySelectorAll('input[name="preset"]'))) {
      radio.checked = radio.value === options.preset;
    }
    for (const note of /** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll("[data-custom-note]"))) {
      note.hidden = options.preset !== "custom";
    }
    for (const radio of /** @type {NodeListOf<HTMLInputElement>} */ (document.querySelectorAll('input[name="details"]'))) {
      radio.checked = radio.value === options.details;
    }
    const docked = options.details === "panel" && panel !== null;
    body.classList.toggle("details-panel", docked);
    if (docked && panel && tooltip.parentElement !== panel) panel.append(tooltip);
    if (!docked && tooltip.parentElement !== body) body.append(tooltip);
    store("z1r-view-options", JSON.stringify(options));
  };

  for (const radio of /** @type {NodeListOf<HTMLInputElement>} */ (document.querySelectorAll('input[name="preset"]'))) {
    radio.addEventListener("change", () => {
      options.preset = radio.value;
      options.layers = { ...options.layers, ...PRESETS[radio.value] };
      applyOptions();
    });
  }
  for (const box of /** @type {NodeListOf<HTMLInputElement>} */ (document.querySelectorAll("input[data-layer]"))) {
    box.addEventListener("change", () => {
      const layer = /** @type {string} */ (box.getAttribute("data-layer"));
      options.layers[layer] = box.checked;
      if (layer !== "advanced") {
        const match = Object.entries(PRESETS).find(([, layers]) =>
          Object.entries(layers).every(([name, on]) => !!options.layers[name] === on));
        options.preset = match ? match[0] : "custom";
      }
      applyOptions();
    });
  }
  for (const radio of /** @type {NodeListOf<HTMLInputElement>} */ (document.querySelectorAll('input[name="details"]'))) {
    radio.addEventListener("change", () => {
      options.details = radio.value;
      applyOptions();
    });
  }
  // Escape closes the Customise panel (before the renderer's Escape unpins a room).
  for (const details of /** @type {NodeListOf<HTMLDetailsElement>} */ (document.querySelectorAll("details.customise"))) {
    details.addEventListener("keydown", (event) => {
      if (event.key !== "Escape" || !details.open) return;
      details.open = false;
      const summary = details.querySelector("summary");
      if (summary) summary.focus();
      event.stopPropagation();
    });
  }

  // -------------------------------------------------------------------------------------------
  // After each map is drawn: mark minor items and the rooms with a major item, and narrow any
  // label still too wide for its room, measured in its own font, so it never spills over.

  const measure = /** @type {CanvasRenderingContext2D} */ (document.createElement("canvas").getContext("2d"));

  const markMap = () => {
    const svg = output.querySelector("svg.map");
    if (!svg) return;
    const shown = current;
    const view = viewSelect.value;
    const level = view.startsWith("Level ") && shown && shown.seed
      ? shown.seed.levels.find((candidate) => candidate.number === Number(view.split(" ")[1])) : undefined;
    const rooms = [...svg.querySelectorAll("rect.room")];
    for (const room of rooms) {
      const key = /^Room ([0-9A-F]+),/.exec(room.getAttribute("aria-label") || "");
      const data = level && key ? level.rooms.find((candidate) => roomNumber(candidate.number) === key[1]) : undefined;
      const items = data ? [data.item ? data.item.name : null,
                            data.staircase && data.staircase.kind === "item" ? data.staircase.item : null] : [];
      room.classList.toggle("has-major", items.some((name) => !!name && !MINOR.has(name)));
    }
    const boxes = rooms.map((room) => {
      const x = Number(room.getAttribute("x"));
      const y = Number(room.getAttribute("y"));
      return { left: x, top: y, right: x + Number(room.getAttribute("width")), bottom: y + Number(room.getAttribute("height")) };
    });
    for (const label of /** @type {NodeListOf<SVGTextElement>} */ (svg.querySelectorAll("text.label"))) {
      const text = label.textContent || "";
      if (label.classList.contains("label-item") || label.classList.contains("label-cellar")) {
        label.classList.toggle("minor", MINOR.has(text.replace(/^D /, "")));
      }
      const x = Number(label.getAttribute("x"));
      const y = Number(label.getAttribute("y"));
      const box = boxes.find((b) => x >= b.left - 12 && x <= b.right && y >= b.top && y <= b.bottom);
      if (!box) continue;
      const style = getComputedStyle(label);
      measure.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
      const room = box.right - x - 3;
      if (measure.measureText(text).width > room) {
        label.setAttribute("textLength", String(room));
        label.setAttribute("lengthAdjust", "spacingAndGlyphs");
      }
    }
  };

  new MutationObserver(() => {
    syncState();
    syncNavigation();
    markMap();
  }).observe(output, { childList: true });

  applyOptions();
  syncState();
  syncNavigation();
})();
