"""Builds the static visualizer: build/site/ (to serve) and build/z1r-visualizer.html (one file
that opens from disk). Run from anywhere:

    python3 scripts/build.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_site  # noqa: E402


def main() -> None:
    version = build_site.version_label()
    print("site: %s" % build_site.build_site(version).relative_to(build_site.ROOT))
    out = build_site.build_single_file(version)
    print("single file: %s (%d KB)" % (out.relative_to(build_site.ROOT), out.stat().st_size // 1024))
    print("version: %s" % version)


if __name__ == "__main__":
    main()
