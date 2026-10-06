"""Builds the design-direction mockups: docs/design/mockup-<direction>.html.

    python3 docs/design/build_mockups.py

Each mockup is one self-contained page: the direction's shell (<direction>/shell.html) and
stylesheet (<direction>/style.css), the real renderer (site/validate.js, site/app.js) with its
Python preloading turned off, the seed format's schema, a sample seed (sample-seed.json, from
`cli.py --seed` on ZORA magical-sword seed 1), and the glue (mockup.js, and for Quest Log
modes.js). Mockups open seed files, not ROMs.

Quest Log (iteration 2) also patches the renderer, as stage 2 would change site/app.js: rooms
sized to fit their longest label (cells wider than tall), classes on door markers, walls and the
four kinds of label (so the mode toggles can hide them), and a fuller room-details card. Every
patch checks that its target is there, so a renderer change can't silently break a mockup.

It also estimates each direction's real single-file build: today's build/z1r-visualizer.html
with the page's stylesheet and shell swapped for the direction's, plus its glue.
"""
import json
import subprocess
from pathlib import Path

DESIGN = Path(__file__).resolve().parent
ROOT = DESIGN.parent.parent
SITE = ROOT / "site"
DIRECTIONS = {
    "atlas": {"glue": ["mockup.js"], "patch": False},
    "quest-log": {"glue": ["mockup.js", "modes.js"], "patch": True},
    "tracker": {"glue": ["mockup.js"], "patch": False},
}
PRELOAD = '''if (!window.opener) {
  ensurePython().catch((err) => {'''

LEVEL_FIELDS_OLD = """      fields: [
        ["Room Number", key], ["Col", room.column], ["Row", room.row],
        ["Stair", staircase ? (staircase.kind === "transport" ? `Stairway #${staircase.number}`
          : staircase.item ? itemLabel(seed, staircase.item) : "No Item") : "None"],
        ["Room Type", room.type], ["Enemy Type", enemies ? enemies.name : ""],
        ["Num Enemies", enemies ? enemies.count : undefined],
      ],"""
LEVEL_FIELDS_NEW = """      fields: [
        ["Room", `${key} · ${room.type}`],
        ["Enemies", enemies ? (enemies.count !== undefined ? `${enemies.count} ${enemies.name}` : enemies.name) : "None"],
        ["Item", room.item ? `${itemLabel(seed, room.item.name)} (${room.item.drop ? "dropped by the enemies" : "on the floor"})` : "None"],
        ["Stairs", staircase ? (staircase.kind === "transport"
          ? `Stairway #${staircase.number}, to room ${roomNumber(staircase.to)}`
          : `Item cellar: ${staircase.item ? itemLabel(seed, staircase.item) : "empty"}`) : "None"],
        ["Doors", ["north", "east", "south", "west"].map((side) => `${side[0].toUpperCase()} ${room.doors[side]}`).join(" · ")],
        ["Position", `column ${room.column}, row ${room.row}`],
      ],"""
DOOR_OLD = """        fill: colour, "fill-opacity": 0.6, stroke: colour, "pointer-events": "none",
      }));"""
DOOR_NEW = """        fill: colour, "fill-opacity": 0.6, stroke: colour, "pointer-events": "none", class: `door door-${door}`,
      }));"""
LABEL_OLD = """      const label = text(x - 0.86, y - 0.2 * (i + 1), line, "8pt");
      label.setAttribute("pointer-events", "none");"""
LABEL_NEW = """      const label = text(x - 0.925, y - 0.2 * (i + 1), line, "10px");
      label.setAttribute("pointer-events", "none");
      label.setAttribute("class", "label " + (i < 3 ? ["label-type", "label-enemies", "label-item"][i]
        : room.staircase && room.staircase.kind === "transport" ? "label-transport" : "label-cellar"));"""
SCREEN_FIELDS_OLD = """      fields: [["Screen Number", key], ["Col", screen.column], ["Row", screen.row], ["Cave", screen.cave.name],
               ["Map Label", screen.cave.shortName]],"""
SCREEN_FIELDS_NEW = """      fields: [["Screen", `${key} · ${screen.cave.name}`], ["Map label", screen.cave.shortName],
               ["Position", `column ${screen.column}, row ${screen.row}`]],"""

# Quest Log's renderer changes: (what, old text, new text).
RENDERER_PATCHES = [
    ("a separate vertical unit for maps",
     "function plot(widthUnits, heightUnits, unit, title) {",
     "function plot(widthUnits, heightUnits, unit, title, unitY = unit) {"),
    ("...in the view box", "viewBox: `0 0 ${widthUnits * unit} ${heightUnits * unit}`,",
     "viewBox: `0 0 ${widthUnits * unit} ${heightUnits * unitY}`,"),
    ("...in the height", "width: widthUnits * unit, height: heightUnits * unit, class",
     "width: widthUnits * unit, height: heightUnits * unitY, class"),
    ("...in y", "const toY = (y) => (heightUnits - y) * unit;", "const toY = (y) => (heightUnits - y) * unitY;"),
    ("...in rectangles", "width: w * unit, height: h * unit, ...attrs,", "width: w * unit, height: h * unitY, ...attrs,"),
    ("level cells 132 x 96 px (the longest label, 'D Boomerang Upgrade', is 112 px at 10 px)",
     "plot(8, 8, 100, `Level ${level.number} map`)", "plot(8, 8, 132, `Level ${level.number} map`, 96)"),
    ("rooms fill more of their cell", "rect(x - 0.5, y - 0.5, 0.8, 0.8, {", "rect(x - 0.5, y - 0.5, 0.92, 0.84, {"),
    ("a fuller room-details card", LEVEL_FIELDS_OLD, LEVEL_FIELDS_NEW),
    ("door markers get classes", DOOR_OLD, DOOR_NEW),
    ("east and west door markers sit in the gap between rooms, clear of the labels",
     "const DOOR_OFFSET = { north: [-0.5, -0.05], south: [-0.5, -0.95], east: [-0.05, -0.5], west: [-0.95, -0.5] };",
     "const DOOR_OFFSET = { north: [-0.5, -0.05], south: [-0.5, -0.95], east: [-0.04, -0.5], west: [-0.96, -0.5] };"),
    ("...and are narrower and taller",
     "svg.append(rect(x + dx, y + dy, 0.1, 0.1, {",
     'svg.append(rect(x + dx, y + dy, direction === "east" || direction === "west" ? 0.05 : 0.1,\n'
     '        direction === "east" || direction === "west" ? 0.13 : 0.1, {'),
    ("walls get a class", '{ fill: "red", stroke: "red", "pointer-events": "none" }',
     '{ fill: "red", stroke: "red", "pointer-events": "none", class: "wall" }'),
    ("labels at 10 px, nearer the room's edge, with a class per kind", LABEL_OLD, LABEL_NEW),
    ("overworld cells 66 x 44 px", 'plot(16, 8, 50, "Overworld map")', 'plot(16, 8, 66, "Overworld map", 44)'),
    ("overworld details card", SCREEN_FIELDS_OLD, SCREEN_FIELDS_NEW),
    ("overworld labels at 13 px, with a class",
     'const label = text(screen.column - 0.9, 8.5 - screen.row, screen.cave.shortName, "14px");',
     'const label = text(screen.column - 0.95, 8.5 - screen.row, screen.cave.shortName, "13px");\n'
     '    label.setAttribute("class", "label label-cave");'),
]


def inline(text: str, what: str) -> str:
    if "</script" in text.lower() or "</style" in text.lower():
        raise SystemExit("%s contains an end tag that would end its element early" % what)
    return text


def json_script(element_id: str, text: str) -> str:
    return '<script type="application/json" id="%s">%s</script>' % (
        element_id, json.dumps(json.loads(text)).replace("</", "<\\/"))


def renderer(patch: bool) -> str:
    """site/app.js without its Python preload (mockups have no Python), and patched if asked."""
    app = (SITE / "app.js").read_text()
    start = app.index(PRELOAD)
    end = app.index("\n}\n", start) + 3
    app = app[:start] + "// (mockup: no Python preload)\n" + app[end:]
    if patch:
        for what, old, new in RENDERER_PATCHES:
            if app.count(old) != 1:
                raise SystemExit("renderer patch no longer applies: %s" % what)
            app = app.replace(old, new)
    return app


def build(direction: str, config: dict, version: str) -> Path:
    shell = (DESIGN / direction / "shell.html").read_text()
    style = inline((DESIGN / direction / "style.css").read_text(), "style.css")
    scripts = "\n".join([
        json_script("seed-schema", (ROOT / "docs" / "seed-format.schema.json").read_text()),
        json_script("mockup-seed", (DESIGN / "sample-seed.json").read_text()),
        "<script>\n%s</script>" % inline((SITE / "validate.js").read_text(), "validate.js"),
        "<script>\n%s</script>" % inline(renderer(config["patch"]), "app.js"),
    ] + ["<script>\n%s</script>" % inline((DESIGN / name).read_text(), name) for name in config["glue"]])
    for marker in ("<!-- STYLE -->", "<!-- SCRIPTS -->", "{{VERSION}}"):
        assert marker in shell, "%s/shell.html lacks %s" % (direction, marker)
    page = (shell.replace("<!-- STYLE -->", "<style>\n%s</style>" % style)
            .replace("<!-- SCRIPTS -->", scripts).replace("{{VERSION}}", version))
    out = DESIGN / ("mockup-%s.html" % direction)
    out.write_text(page)
    return out


def main() -> None:
    version = subprocess.run(["git", "log", "-1", "--format=%cs %h"], cwd=ROOT, capture_output=True, text=True,
                             check=True).stdout.strip() + " mockup"
    subprocess.run(["python3", "scripts/build_site.py", "--single-file"], cwd=ROOT, check=True, capture_output=True)
    today = (ROOT / "build" / "z1r-visualizer.html").stat().st_size
    base = (SITE / "style.css").stat().st_size + (SITE / "index.html").stat().st_size
    print("today's single file: %.0f KB" % (today / 1024))
    for direction, config in DIRECTIONS.items():
        out = build(direction, config, version)
        own = sum((DESIGN / direction / name).stat().st_size for name in ("style.css", "shell.html"))
        estimate = today - base + own + sum((DESIGN / name).stat().st_size for name in config["glue"])
        print("%-10s %s (%.0f KB with the sample seed); its single file: about %.0f KB"
              % (direction, out.name, out.stat().st_size / 1024, estimate / 1024))


if __name__ == "__main__":
    main()
