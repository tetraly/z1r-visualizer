// Mockup glue for the design directions in docs/design (not part of the real page yet). Each
// mockup is the real renderer (site/app.js, site/validate.js) inside a direction's own shell and
// stylesheet; this script adds what the shells share:
// - the theme: follows the system, with a toggle (system, light, dark) remembered per browser;
// - navigation: buttons with data-view drive the renderer's view select, and show which is current;
// - the drop area: elements with data-drop take a dropped file as if it were chosen;
// - a docked tooltip, where the shell has a [data-tooltip-dock] panel;
// - the sample seed, shown unless the URL has ?empty (the empty state).
// Mockups have no Python, so they open seed files (.json), not ROMs.
"use strict";
(() => {
  const root = document.documentElement;
  const select = /** @type {HTMLSelectElement} */ (document.getElementById("view"));
  const input = /** @type {HTMLInputElement} */ (document.getElementById("rom"));
  const picker = /** @type {HTMLElement} */ (document.getElementById("picker"));
  const output = /** @type {HTMLElement} */ (document.getElementById("output"));
  const params = new URLSearchParams(location.search);

  // Theme: "system" removes data-theme, so the stylesheet's light-dark() follows the system.
  const THEMES = ["system", "light", "dark"];
  const THEME_LABELS = { system: "Theme: system", light: "Theme: light", dark: "Theme: dark" };
  let theme = "system";
  try {
    theme = localStorage.getItem("z1r-theme") || "system";
  } catch (err) {
    // storage blocked: follow the system
  }
  if (params.get("theme")) theme = params.get("theme");
  const applyTheme = () => {
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    for (const button of document.querySelectorAll("[data-theme-toggle]")) {
      button.setAttribute("aria-label", `${THEME_LABELS[theme]}. Change theme`);
      button.dataset.mode = theme;
      const label = button.querySelector("[data-theme-label]");
      if (label) label.textContent = theme[0].toUpperCase() + theme.slice(1);
    }
  };
  for (const button of document.querySelectorAll("[data-theme-toggle]")) {
    button.addEventListener("click", () => {
      theme = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
      try {
        localStorage.setItem("z1r-theme", theme);
      } catch (err) {
        // not remembered
      }
      applyTheme();
    });
  }
  applyTheme();

  // Navigation: the renderer switches views through its select; the buttons drive it, and follow
  // it when the renderer switches by itself (an Item Summary room link opens a level).
  const syncNav = () => {
    for (const button of document.querySelectorAll("[data-view]")) {
      const current = button.getAttribute("data-view") === select.value;
      if (current) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    }
    document.body.dataset.view = select.value.startsWith("Level") ? "level" : select.value.toLowerCase().replace(/ /g, "-");
    const title = document.querySelector("[data-view-title]");
    if (title) title.textContent = select.value;
  };
  for (const button of document.querySelectorAll("[data-view]")) {
    button.addEventListener("click", () => {
      select.value = /** @type {string} */ (button.getAttribute("data-view"));
      select.dispatchEvent(new Event("change"));
      syncNav();
    });
  }
  new MutationObserver(syncNav).observe(output, { childList: true });

  // The page's state, for the shells' CSS: "empty" until a seed is shown.
  const syncState = () => {
    document.body.dataset.state = picker.hidden ? "empty" : "loaded";
    const name = document.querySelector("[data-file-name]");
    const shown = window.z1rVisualizer && window.z1rVisualizer.current();
    if (name) name.textContent = shown && shown.seed ? shown.source : "";
    // Level buttons carry their dungeon's colour, for shells that show it.
    for (const button of document.querySelectorAll('[data-view^="Level "]')) {
      const number = Number(button.getAttribute("data-view").split(" ")[1]);
      const level = shown && shown.seed ? shown.seed.levels.find((candidate) => candidate.number === number) : null;
      if (level) button.style.setProperty("--level-color", level.color);
      else button.style.removeProperty("--level-color");
    }
  };
  new MutationObserver(syncState).observe(picker, { attributes: true, attributeFilter: ["hidden"] });

  // The drop area.
  for (const zone of document.querySelectorAll("[data-drop]")) {
    zone.addEventListener("dragover", (event) => {
      event.preventDefault();
      zone.classList.add("dragging");
    });
    zone.addEventListener("dragleave", () => zone.classList.remove("dragging"));
    zone.addEventListener("drop", (event) => {
      event.preventDefault();
      zone.classList.remove("dragging");
      if (!event.dataTransfer || !event.dataTransfer.files.length) return;
      input.files = event.dataTransfer.files;
      input.dispatchEvent(new Event("change"));
    });
  }
  for (const button of document.querySelectorAll("[data-open-file]")) {
    button.addEventListener("click", () => input.click());
  }

  // A docked tooltip: the renderer keeps updating the same element wherever it is.
  const dock = document.querySelector("[data-tooltip-dock]");
  if (dock) dock.append(/** @type {HTMLElement} */ (document.getElementById("tooltip")));

  syncState();
  syncNav();
  const sample = document.getElementById("mockup-seed");
  if (sample && !params.has("empty")) {
    window.z1rVisualizer.showSeedJson(sample.textContent, "zora-sword-seed1.json").then(() => {
      select.value = params.get("view") || "Level 4";
      select.dispatchEvent(new Event("change"));
      syncState();
      syncNav();
    });
  }
})();
