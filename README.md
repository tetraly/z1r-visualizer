# z1r-visualizer

Shows a Legend of Zelda ROM's dungeon maps, overworld caves, item placements, shops and texts: an
interactive spoiler log for vanilla ROMs, Zelda Randomizer seeds made without "Race ROM", and ZORA
seeds made without "Encode level data". Encoded ROMs are refused.

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
- **Command line** (`cli.py`): `python3 cli.py --files=rom.nes` prints CSV lines; `--json` prints the
  static page's data.

## Tests

```bash
python3 -m pytest data_extractor_test.py spoiler_test.py
```

```bash
node scripts/check_site.mjs testdata/*.nes
```

The ROMs in `testdata/` are not in the repository. Most tests skip when their ROM is missing; the
three oldest (`DataExtractorTest`) fail instead.
