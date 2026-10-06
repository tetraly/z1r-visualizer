# z1r-visualizer

Shows a Legend of Zelda ROM's dungeon maps, overworld caves, item placements, shops and texts: an
interactive spoiler log for vanilla ROMs, Zelda Randomizer seeds made without "Race ROM", and ZORA
seeds made without "Encode level data". Encoded ROMs are refused.

The static page draws everything from a seed in the **seed format** (docs/seed-format.md and its
JSON Schema), which it reads from a ROM, from a seed file (.json), or from ZORA's "View in
Visualizer" button by window messaging.

## Ways to run it

- **Static page** (`site/`): the Python parser runs in your browser through Pyodide, so the ROM is
  never uploaded.

  ```bash
  python3 scripts/build_site.py --single-file
  ```

  This writes `build/site/` (serve it with `python3 -m http.server --directory build/site`) and
  `build/z1r-visualizer.html`, a single page that opens from disk. docs/static-hosting.md has the
  details and the GitHub Pages steps.
- **Streamlit app** (`app.py`): `streamlit run app.py`. The hosted app deploys from the `streamlit`
  branch.
- **Command line** (`cli.py`): `python3 cli.py --files=rom.nes` prints CSV lines. `--seed` prints the
  seed in the seed format (a seed file), `--json` what the static page reads from the ROM, and
  `--item-summary` the item summary's tables.

## Tests

```bash
python3 -m pytest data_extractor_test.py spoiler_test.py
```

```bash
node scripts/check_site.mjs testdata/*.nes
```

The first checks every test ROM's seed against the seed format's schema (with `jsonschema`). The
second type-checks the page's JavaScript (`tsc --noEmit` from its JSDoc types), then, in headless
Chrome, compares the single-file page with `cli.py` on each ROM, and checks that the same seed sent
as a seed file or by ZORA's hand-off renders every view exactly as the ROM does.

The ROMs in `testdata/` are not in the repository. Most tests skip when their ROM is missing; the
three oldest (`DataExtractorTest`) fail instead.
