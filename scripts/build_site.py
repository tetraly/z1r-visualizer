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
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BUILD = ROOT / "build"
PAGE_FILES = ["index.html", "style.css", "validate.js", "app.js", "worker.js"]
# The seed format's schema, which the page checks seeds against.
SCHEMA = ROOT / "docs" / "seed-format.schema.json"
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


def light_dark_arguments(text: str, start: int):
    """The two arguments of the light-dark( call whose "(" is at text[start], and the index after
    its ")"; commas inside rgba() and the like are kept."""
    depth, args, current = 0, [], start + 1
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                args.append(text[current:i].strip())
                return args, i + 1
        elif text[i] == "," and depth == 1:
            args.append(text[current:i].strip())
            current = i + 1
    raise SystemExit("style.css: an unclosed light-dark(")


def with_light_fallback(css: str) -> str:
    """style.css plus a light-only fallback for browsers without light-dark() (Chrome < 123,
    Firefox < 120, Safari < 17.5): an @supports block giving each colour token its light value."""
    tokens = []
    for match in re.finditer(r"(--[\w-]+):\s*light-dark(?=\()", css):
        args, _ = light_dark_arguments(css, match.end())
        if len(args) != 2:
            raise SystemExit("style.css: %s's light-dark() needs two colours" % match.group(1))
        tokens.append("    %s: %s;" % (match.group(1), args[0]))
    if not tokens:
        return css
    return css + ("\n/* Added by scripts/build_site.py: light colours where light-dark() is not supported. */\n"
                  "@supports not (color: light-dark(#000, #fff)) {\n  :root {\n%s\n  }\n}\n" % "\n".join(tokens))


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
    (out / "style.css").write_text(with_light_fallback((SITE / "style.css").read_text()))
    (out / "index.html").write_text(stamped_page(version))
    for name in PYTHON_FILES:
        shutil.copy(ROOT / name, out / "py" / name)
    shutil.copy(SCHEMA, out / SCHEMA.name)
    return out


def inline(text: str, end_tag: str, what: str) -> str:
    if end_tag in text.lower():
        raise SystemExit("%s contains %r, which would end its element early" % (what, end_tag))
    return text


def build_single_file(version: str) -> Path:
    page = stamped_page(version)
    style = inline(with_light_fallback((SITE / "style.css").read_text()), "</style", "style.css")
    validator = inline((SITE / "validate.js").read_text(), "</script", "validate.js")
    script = inline((SITE / "app.js").read_text(), "</script", "app.js")
    worker = inline((SITE / "worker.js").read_text(), "</script", "worker.js")
    sources = {name: (ROOT / name).read_text() for name in PYTHON_FILES}
    # JSON can carry "</script" inside a string; escaping "</" keeps the element intact.
    sources_json = json.dumps(sources).replace("</", "<\\/")
    schema_json = json.dumps(json.loads(SCHEMA.read_text())).replace("</", "<\\/")

    stylesheet_tag = '<link rel="stylesheet" href="style.css">'
    validator_tag = '<script src="validate.js"></script>'
    script_tag = '<script src="app.js"></script>'
    assert all(tag in page for tag in (stylesheet_tag, validator_tag, script_tag)), \
        "index.html lost its stylesheet or script tags"
    page = page.replace(stylesheet_tag, "<style>\n%s</style>" % style)
    page = page.replace(validator_tag, "<script>\n%s</script>" % validator)
    page = page.replace(script_tag, "\n".join([
        '<script type="text/plain" id="worker-source">\n%s</script>' % worker,
        '<script type="application/json" id="python-sources">%s</script>' % sources_json,
        '<script type="application/json" id="seed-schema">%s</script>' % schema_json,
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
