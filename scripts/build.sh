#!/bin/sh
# Builds the static visualizer: build/site/ (to serve) and build/z1r-visualizer.html (one file
# that opens from disk). Run from anywhere:
#
#   sh scripts/build.sh
set -e
cd "$(dirname "$0")/.."
python3 scripts/build_site.py --single-file
