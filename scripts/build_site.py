"""Builds the static visualizer from site/ and the Python parser at the repo root.

    python3 scripts/build_site.py                 # the site: build/site/
    python3 scripts/build_site.py --single-file   # also one page: build/z1r-visualizer.html

The site is what GitHub Pages would serve (.github/workflows/pages.yml). It needs an HTTP
server, not file://, because it fetches worker.js and py/*.py:

    python3 -m http.server 8000 --directory build/site

The single file inlines the stylesheet, the page script, the worker and the parser, and opens
from disk. Both fetch Pyodide from jsDelivr on first use; nothing else is fetched, and no ROM is
ever sent anywhere.
"""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BUILD = ROOT / "build"
PAGE_FILES = ["index.html", "style.css", "app.js", "worker.js"]
# The parser, shared with app.py and cli.py. Keep in step with PYTHON_FILES in site/app.js.
PYTHON_FILES = ["constants.py", "rom_reader.py", "data_extractor.py", "spoiler.py"]


def version_label() -> str:
    """The commit the page was built from, e.g. "2026-10-06 5bb35e0", plus "modified" if the
    page or parser differ from it."""
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    try:
        label = git("log", "-1", "--format=%cs %h")
        if git("status", "--porcelain", "--", "site", *PYTHON_FILES):
            label += " modified"
        return label
    except (OSError, subprocess.CalledProcessError):
        return "unknown version"


def stamped_page(version: str) -> str:
    page = (SITE / "index.html").read_text()
    marker = '<span class="version" id="version">dev</span>'
    assert marker in page, "index.html lost its version marker"
    return page.replace(marker, '<span class="version" id="version">%s</span>' % version)


def build_site(version: str) -> Path:
    out = BUILD / "site"
    if out.exists():
        shutil.rmtree(out)
    (out / "py").mkdir(parents=True)
    for name in PAGE_FILES[1:]:
        shutil.copy(SITE / name, out / name)
    (out / "index.html").write_text(stamped_page(version))
    for name in PYTHON_FILES:
        shutil.copy(ROOT / name, out / "py" / name)
    return out


def inline(text: str, end_tag: str, what: str) -> str:
    if end_tag in text.lower():
        raise SystemExit("%s contains %r, which would end its element early" % (what, end_tag))
    return text


def build_single_file(version: str) -> Path:
    page = stamped_page(version)
    style = inline((SITE / "style.css").read_text(), "</style", "style.css")
    script = inline((SITE / "app.js").read_text(), "</script", "app.js")
    worker = inline((SITE / "worker.js").read_text(), "</script", "worker.js")
    sources = {name: (ROOT / name).read_text() for name in PYTHON_FILES}
    # JSON can carry "</script" inside a string; escaping "</" keeps the element intact.
    sources_json = json.dumps(sources).replace("</", "<\\/")

    stylesheet_tag = '<link rel="stylesheet" href="style.css">'
    script_tag = '<script src="app.js"></script>'
    assert stylesheet_tag in page and script_tag in page, "index.html lost its stylesheet or script tag"
    page = page.replace(stylesheet_tag, "<style>\n%s</style>" % style)
    page = page.replace(script_tag, "\n".join([
        '<script type="text/plain" id="worker-source">\n%s</script>' % worker,
        '<script type="application/json" id="python-sources">%s</script>' % sources_json,
        "<script>\n%s</script>" % script,
    ]))
    out = BUILD / "z1r-visualizer.html"
    out.write_text(page)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--single-file", action="store_true", help="also write build/z1r-visualizer.html")
    args = parser.parse_args()
    version = version_label()
    print("site: %s" % build_site(version).relative_to(ROOT))
    if args.single_file:
        out = build_single_file(version)
        print("single file: %s (%d KB)" % (out.relative_to(ROOT), out.stat().st_size // 1024))
    print("version: %s" % version)


if __name__ == "__main__":
    main()
