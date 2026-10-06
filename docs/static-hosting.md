# A static visualizer on GitHub Pages

Status (2026-10-06): **built** as recommended (approach C), on `main`. GitHub Pages is **not**
enabled; publishing is the owner's step (below). The Streamlit app is unchanged and still
deploys from the `streamlit` branch. Sections 1-5 are the design record.

## Built: what there is

| File | What |
|---|---|
| `spoiler.py` | `Export(rom_bytes)`: every view's data as plain JSON, from the shared parser. Encoded or unsupported ROMs give only a status, the app's message and the recorder info |
| `cli.py --json` | the same data from the command line; the CLI stays Python |
| `site/` | the page: `index.html`, `style.css`, `app.js` (views drawn in SVG and HTML), `worker.js` (Pyodide 0.28.3 from jsDelivr, a classic worker) |
| `scripts/build_site.py` | `build/site/` (the page plus the parser in `py/`) and, with `--single-file`, `build/z1r-visualizer.html` (about 70 KB) |
| `scripts/check_site.mjs` | type-checks `site/`'s JavaScript (`tsc --noEmit`), then opens the single file from `file://` in headless Chrome, chooses each ROM through the file input, compares the page's data with `cli.py --json` byte for byte, checks every view renders and encoded ROMs are refused |
| `.github/workflows/pages.yml` | builds `build/site/` and deploys it to Pages; manual trigger only |

```bash
python3 scripts/build_site.py --single-file
```

```bash
python3 -m http.server 8000 --bind 127.0.0.1 --directory build/site
```

```bash
node scripts/check_site.mjs testdata/*.nes
```

The ROM is read with `File.arrayBuffer()` and posted only to the worker. The page fetches nothing
but Pyodide's files; the single file fetches nothing else at all.

### Checked (2026-10-06)

- 48 ROMs: vanilla PRG0 and PRG1, 14 Zelda Randomizer seeds (two unsupported, as in the app),
  ZORA plain and with each ZORA option (sword, letter, both, Shop Items in the Item Pool,
  Progressive Items, both of those), three encoded ROMs, the playtest ROMs. The page's data equals
  `cli.py --json` on all 48, served (in the desktop app's browser) and as the single file from
  `file://` (headless Chrome). A deliberately altered page fails the check.
- The rendered shop tables and hint texts equal `cli.py`'s CSV lines on all 43 ROMs that parse.
- Item summary: `spoiler.ItemSummary` gives exactly the app's tables (the app run headlessly) on
  all 48 ROMs.
- Level and overworld maps compared by eye with the app's Bokeh figures for the same ROM: same
  rooms, doors, walls, labels and colours.
- Phone width (375 px): no sideways page scroll; maps scroll inside their own box.
- Not checked: Safari, Firefox and Edge, Windows, and `file://` outside Chrome.

### Parity with the Streamlit app

Matched: every view (Level 1-9, Overworld, Recorder Info with the IPS download, Item Summary,
Hint Texts), the ZORA fixes, the messages and the encoded-ROM refusal.

Differences:

- **Tooltips** are the page's own (hover, or tap on a phone), with the app's fields and labels,
  including the overworld's "Cave2" and "Cave3". Bokeh's hover box looked different.
- **Upload**: a standard file input. Dropping a file on it works in most browsers, but there is no
  large drop zone as in Streamlit.
- **A ROM the parser can't even open** (not a Zelda ROM, a truncated file) shows the app's
  "doesn't seem to be supported" message. The app showed a Python error there.
- **Additions**: a version label (build commit), a status line, and the page follows the system's
  dark mode. The maps stay white, as the app forces.
- **Speed**: the first visit downloads Pyodide (about 5.5 MB), about 3-5 s to "Ready". Later
  visits use the browser cache. Each ROM then takes about 20 ms.

### Type checking

`site/app.js` and `site/worker.js` carry JSDoc types and `// @ts-check`. `site/jsconfig.json` (the
page, with the DOM's types) and `site/jsconfig.worker.json` (the worker, with the WebWorker's)
check them strictly; nothing is compiled, and the build does not change. `scripts/check_site.mjs`
runs `tsc --noEmit` on both before opening the page (TypeScript 6.0.3 through npx, no
`package.json`), and a type error fails the check.

### Interaction ideas from the Plotly prototype (`plotly_proto.py`; not built)

What the prototype does: the same room boxes, doors, walls and four labels; a hover tooltip with
the app's fields, carried by invisible square markers; a horizontal legend below. It switches
zoom, pan and the mode bar **off** (`fixedrange`, `dragmode=False`, `displayModeBar: False`), and
has no selection. Its legend entries are dummy traces, so clicking one would hide nothing on the
map.

Ideas for the SVG maps, roughly in order of value for a spoiler view:

| # | Idea | Where it comes from | Value | Effort |
|---|---|---|---|---|
| 1 | **Pin a room**: click (or tap) keeps its tooltip and outlines it until another click; Escape clears. Rooms focusable with Tab, tooltip on focus | Plotly's hover label, which stays put on the point; the page's tooltip follows the cursor | High: readable on phones and with a keyboard | Small |
| 2 | **Staircase pairs**: hovering or pinning a room with "Stair #n" outlines the room at the other end | not in the prototype; uses data the page has (`stair_info`) | High: transport stairs are the hardest thing to follow on the map | Small |
| 3 | **Item Summary to map**: each row's Screen links to its level map with that room pinned | Plotly's linked selection, done simply | High | Small to medium |
| 4 | **Legend as a filter**: clicking a door type dims the others (for example, show only bombable walls) | Plotly's legend toggling, which the prototype's dummy traces can't actually do | Medium | Small |
| 5 | **Item search**: a box that outlines every room whose item, drop or cellar matches (for example "Sword", "Heart Container") | Plotly's selection, aimed at what players look for | Medium | Small |
| 6 | **Zoom and pan** with a reset button: wheel or pinch on the SVG's viewBox | Plotly's default zoom, which the prototype disabled | Medium, mostly on phones, instead of the sideways scroll | Medium |
| 7 | **Download the map** as SVG (or PNG) | Plotly's mode-bar "download plot" | Low to medium (sharing a spoiler) | Small |
| 8 | Look only: the prototype's darker room outline (`#555`), door markers at 0.8 opacity with explicit colours (shutter `#8B4513`, bombable `#1E40FF`), 11 px labels | `plotly_proto.py` | Taste; changes parity with the Streamlit app | Trivial |

Not recommended: box or lasso selection (rooms are few and fixed, so a click does the job) and
free zoom without a reset (easy to get lost on an 8x8 map).

### Publishing (the owner's step; nothing is enabled)

1. Settings -> Pages -> Build and deployment -> Source: **GitHub Actions**.
2. Actions -> "Publish static visualizer" -> Run workflow (branch `main`).
3. The site appears at `https://tetraly.github.io/z1r-visualizer/`.

Until step 1 the deploy job fails and nothing is published. The single file is built locally and
shared by hand; the workflow does not upload it anywhere.

**Goal.** Serve the visualizer as a static page on GitHub Pages
(`tetraly.github.io/z1r-visualizer`), so the ROM is read in the player's
browser and never uploaded. Streamlit Cloud today receives every uploaded ROM.

**Requirements:**
- It works offline.
- There is a single-file option, like ZORA's beta.
- It keeps refusing encoded ROMs.
- It stays open to a later ZORA tie-in without assuming code is copied into
  ZORA (zora-integration.md, owner decision 3).

## 1. What has to be replaced

| Piece today | Lines | Depends on | In a static page |
|---|---|---|---|
| Parser: `data_extractor.py`, `rom_reader.py`, `constants.py` | about 1,200 (38 KB) | standard library only | runs unchanged in Pyodide, or is ported to JS |
| UI and drawing: `app.py` | 450 | Streamlit, streamlit-bokeh, Bokeh, pandas | rewritten, or run through Pyodide |
| `cli.py` | 120 | the parser | stays as it is (Python, local) |

`app.py` covers:
- the upload;
- the level maps: room boxes in the level palette, coloured door markers, red
  walls between rooms, four text lines per room, hover tooltips and a legend;
- the overworld map;
- the item summary tables;
- the hint texts;
- the recorder info, with an IPS download.

None of this needs a server: the IPS download becomes a `Blob` link.

GitHub Pages is free for this repo because it is public. The site would be a
`site/` folder (not `docs/`, which holds these design notes), published by a
small Actions workflow.

## 2. Approaches

Measured or quoted sizes:
- **Pyodide 0.28.3's core:** 5.5 MB on first load and about 1 KB once cached.
  ZORA measured a warm start of 0.8-2.1 s (zora-ng docs/packaging.md).
- **Bokeh and its dependencies in Pyodide 0.28.3:** 16.4 MB more. That is
  bokeh 6.4 MB, pandas 5.0 MB, numpy 2.9 MB, pillow 1.0 MB and eight smaller
  packages, measured from jsDelivr on 2026-10-06. Pyodide ships Bokeh 3.6.3;
  this repo pins 3.8.0.

### A. stlite: today's Streamlit app, run in the browser

stlite runs a Streamlit app on Pyodide. `app.py` could stay almost as it is.

- **Effort:** low if it works, about 1-2 days to try.
- **Risks:**
  - `streamlit-bokeh` is a custom component, and whether stlite runs it was
    **not checked**.
  - The download is Pyodide plus Streamlit's stack plus the 16.4 MB Bokeh
    stack, roughly 25 MB or more on first load. Startup takes many seconds.
- **Offline:** only from the browser's cache after a first online visit.
- **Single file:** no practical one.
- **Maintenance:** one codebase, but tied to stlite's support for Streamlit
  and to components.
- **ZORA fit:** none. Nobody would embed Streamlit in ZORA's page.

### B. Pyodide plus the existing Python, Bokeh kept, Streamlit dropped

A small HTML page replaces Streamlit's widgets. Python builds the same Bokeh
figures and hands them to BokehJS (`bokeh.embed.json_item`).

- **Effort:** about 3-4 days. Mostly the UI shell, plus checking the figures
  on Bokeh 3.6.3.
- **First load:** about 22 MB, plus BokehJS.
- **Offline and single file:** as A.
- **Maintenance:** one codebase. The Bokeh version is whatever Pyodide ships.
- **ZORA fit:** poor, for the same size reasons.

### C. Pyodide for the parser only, drawing in JavaScript (ZORA's beta pattern)

The stdlib-only parser runs in a Pyodide worker. It returns plain JSON: a new
`DataExtractor.to_json()` with the levels, rooms, doors, walls, stairs,
overworld caves, shop data, requirements, texts and recorder data. The page
draws the maps as SVG and the tables as HTML. Bokeh, pandas and Streamlit
leave the runtime entirely.

- **Effort:** about 5-7 days:
  - `to_json()` and its tests: about half a day;
  - the page, worker and file input: about 1 day;
  - the SVG level and overworld renderer with tooltips and the legend, plus
    the tables: about 3-4 days;
  - the Pages workflow and a browser check: about 1 day.
- **First load:** 5.5 MB (Pyodide core) plus about 40 KB of our own code.
  Warm start is about 1-2 s.
- **Offline:** after the first visit, from the browser cache. Self-hosting
  Pyodide on Pages removes the third-party CDN but not the first download.
- **Single file:** yes, exactly as ZORA's beta does it:
  - one HTML file with the Python, the JS and the CSS inlined;
  - a classic worker started from a Blob URL;
  - Pyodide fetched from jsDelivr on first open.

  This is "single file, online once", not "offline from the first open".
- **Maintenance:**
  - **One parser** (the Python that is already tested), used by the page, the
    CLI and the unit tests.
  - The drawing exists once, in JS. The Streamlit app retires once the page
    reaches parity.
- **ZORA fit:** good, and no code needs to move. ZORA's page already runs
  Pyodide, and the JSON is the natural contract for ZORA's facts (section 4).

### D. A full JavaScript port: parser and drawing

The parser is ported to JS (about 700-900 lines plus the tables) and draws as
in C.

- **Effort:** about 9-12 days. C's renderer, plus 3-4 days for the port and
  1-2 days for a parity harness. The harness runs the Python `to_json()` and
  the JS parser over a corpus (the Desktop Z1R ROMs, vanilla PRG0 and PRG1,
  and generated ZORA seeds) and diffs the JSON.
- **First load:** about 100-150 KB, with no runtime to download. Start is
  instant.
- **Offline:** fully, including from `file://` on the first open.
- **Single file:** yes, small and self-contained.
- **Maintenance:**
  - While `cli.py` stays in Python, there are **two parsers** kept in step,
    and the parity harness is what keeps them honest.
  - The visualizer's history of walk fixes ("phantom staircase", one-way
    stairs, shutters) shows the walk is where they would drift.
  - Porting the CLI to Node would make it one parser again.
- **ZORA fit:** good. It is easy to embed anywhere, with no Pyodide needed,
  but that depends on the licence decision.

### Rejected

- Other Python-in-browser tools (PyScript is Pyodide underneath; Brython and
  Transcrypt are not drop-in for this code). They add no advantage over C.
- Keeping the server and promising not to store ROMs. That doesn't meet the
  goal.

### Comparison

| | A stlite | B Pyodide + Bokeh | C Pyodide parser + JS drawing | D JS port |
|---|---|---|---|---|
| Effort | 1-2 days (risky) | 3-4 days | 5-7 days | 9-12 days |
| First load | 25 MB or more | about 22 MB | about 5.5 MB | about 0.15 MB |
| Warm start | slow | several s | about 1-2 s | instant |
| Offline | after first visit | after first visit | after first visit | always |
| Single file | no | no | yes (online once) | yes (fully offline) |
| Parsers to maintain | 1 | 1 | 1 | 2 (unless the CLI moves to JS) |
| ZORA tie-in | no | no | yes, via JSON | yes, via JSON or code |

## 3. Recommendation

**Build C now, and keep D as a later step if fully offline matters.**

- C removes the upload, which is the actual goal. It keeps the single tested
  parser, and its single file matches ZORA's beta, which the owner has
  already accepted.
- The JS renderer is the bulk of C and is exactly what D needs too. So
  nothing in C is thrown away if a port follows later: D then only swaps the
  worker for a JS parser and keeps the same JSON.
- A and B carry the whole data-science stack into the browser to draw a few
  hundred rectangles.

Suggested order:
1. `DataExtractor.to_json()`, with a schema documented in this folder and
   golden-JSON tests over `testdata/`.
2. A `site/` page:
   - a file input (the ROM is read with `File.arrayBuffer()`, never sent);
   - a Pyodide worker that loads the three parser files;
   - SVG level and overworld maps, the item summary, hint texts and recorder
     info with the IPS download.
3. A browser check on the generated ZORA ROMs, the Desktop Z1R ROMs and
   vanilla, compared view by view with the Streamlit app.
4. A Pages workflow (manual trigger at first) and a single-file build script,
   reusing ZORA's approach: inline everything, a classic worker from a Blob
   URL, Pyodide from jsDelivr.
5. Replace the Streamlit app with a notice that links to the Pages site.

**Privacy rules for the page:**
- No analytics and no web fonts.
- The only network fetch is Pyodide, from jsDelivr or self-hosted.
- The page says plainly that the ROM never leaves the browser.

**Encoded ROMs:** the refusal stays in the parser (the ZORA decoder marker
plus the room-walk heuristic), so C inherits it unchanged. D must port both,
with a parity test on the encoded samples.

## 4. How this keeps the ZORA tie-in open

Nothing here copies code into ZORA. Once the visualizer is a static page that
accepts JSON:

- **Same origin.** If ZORA is ever served from `tetraly.github.io` too, both
  pages share an origin, and an "Open in Visualizer" button becomes simple:
  `window.open` plus `postMessage`, or `BroadcastChannel`. From ZORA's
  `file://` beta, `postMessage` still works, because the static page receives
  it in JS, which Streamlit could not. The button is offered only when
  "Encode level data" is off (zora-integration.md, decision 1).
- **ZORA's facts as a second input.** The page accepts an optional "spoiler
  facts" JSON, handed over by message or loaded as a file. It carries what
  the ROM can't tell (decision 2):
  - how each "?" flag resolved;
  - progressive meaning;
  - one-time wares;
  - who says which hint;
  - the seed, flags and seed code.

  The visualizer overlays these on what it parsed. Defining that format is
  the one piece of joint design left. It is data, not code, so it needs no
  licence decision.
- **Later, if the licence allows.** ZORA could embed C's parser in its own
  Pyodide worker, or D's JS, without either repo changing shape.

## 5. Questions for the owner

1. Is "single file, online once" (C) good enough, or must the single file
   work offline from its first open (D)?
2. Retire the Streamlit app once the Pages site reaches parity, or keep both
   for a while?
3. Should the CLI stay Python? If D is ever chosen, this decides whether
   there are one or two parsers.
4. Self-host Pyodide on Pages (no third-party fetch, about 5.5 MB in the
   repo's Pages artifact), or use jsDelivr as ZORA does?
