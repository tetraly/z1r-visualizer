"""Builds the design-direction mockups: docs/design/mockup-<direction>.html.

    python3 docs/design/build_mockups.py

Each mockup is one self-contained page: the direction's shell (<direction>/shell.html) and
stylesheet (<direction>/style.css), the real renderer (site/validate.js, site/app.js) with its
Python preloading turned off, the seed format's schema, a sample seed (sample-seed.json, from
`cli.py --seed` on ZORA magical-sword seed 1), and the glue (mockup.js, and for Quest Log
modes.js). Mockups open seed files, not ROMs.

Quest Log (iteration 2) used to patch the renderer here (rooms that fit their longest label,
classes on door markers, walls and labels, a fuller details card). Stage 2 put those changes in
site/app.js itself, so the mockups now use the renderer as it is. The committed Atlas and Tracker
mockups were built against the stage-1 renderer: rebuilt today, their door colours (matched by
the old marker size) would no longer apply.

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
    "atlas": {"glue": ["mockup.js"]},
    "quest-log": {"glue": ["mockup.js", "modes.js"]},
    "tracker": {"glue": ["mockup.js"]},
}
PRELOAD = '''if (!window.opener) {
  ensurePython().catch((err) => {'''



def inline(text: str, what: str) -> str:
    if "</script" in text.lower() or "</style" in text.lower():
        raise SystemExit("%s contains an end tag that would end its element early" % what)
    return text


def json_script(element_id: str, text: str) -> str:
    return '<script type="application/json" id="%s">%s</script>' % (
        element_id, json.dumps(json.loads(text)).replace("</", "<\\/"))


def renderer() -> str:
    """site/app.js without its Python preload (mockups have no Python)."""
    app = (SITE / "app.js").read_text()
    start = app.index(PRELOAD)
    end = app.index("\n}\n", start) + 3
    return app[:start] + "// (mockup: no Python preload)\n" + app[end:]


def build(direction: str, config: dict, version: str) -> Path:
    shell = (DESIGN / direction / "shell.html").read_text()
    style = inline((DESIGN / direction / "style.css").read_text(), "style.css")
    scripts = "\n".join([
        json_script("seed-schema", (ROOT / "docs" / "seed-format.schema.json").read_text()),
        json_script("mockup-seed", (DESIGN / "sample-seed.json").read_text()),
        "<script>\n%s</script>" % inline((SITE / "validate.js").read_text(), "validate.js"),
        "<script>\n%s</script>" % inline(renderer(), "app.js"),
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
