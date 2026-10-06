"""Checks each design direction's colours against WCAG 2.2 AA, in light and dark.

    python3 docs/design/contrast.py

Reads the light-dark() tokens in docs/design/<direction>/style.css. Text needs 4.5:1; focus
rings, map outlines and markers need 3:1 (non-text contrast). Map labels are checked against
every one of the 64 NES colours as a room fill (a dungeon can have any of them), blended at the
direction's --room-opacity over the map background: the worst case, before the labels' halo.
"""
import re
import sys
from pathlib import Path

DESIGN = Path(__file__).resolve().parent
sys.path.insert(0, str(DESIGN.parent.parent))
from constants import PALETTE_COLORS  # noqa: E402

DIRECTIONS = ["atlas", "quest-log", "tracker"]
TEXT = 4.5
GRAPHIC = 3.0
CHECKS = [
    # (foreground, background, minimum, what)
    ("text", "bg", TEXT, "body text on the page"),
    ("text", "surface", TEXT, "body text on cards"),
    ("muted", "bg", TEXT, "secondary text on the page"),
    ("muted", "surface", TEXT, "secondary text on cards"),
    ("muted", "surface-2", TEXT, "secondary text on raised areas"),
    ("link", "surface", TEXT, "links and room numbers"),
    ("link", "bg", TEXT, "links on the page"),
    ("on-accent", "accent", TEXT, "text on the accent (buttons, current tab)"),
    ("info-text", "info-bg", TEXT, "info messages"),
    ("error-text", "error-bg", TEXT, "error messages"),
    ("focus", "bg", GRAPHIC, "focus ring on the page"),
    ("focus", "surface", GRAPHIC, "focus ring on cards"),
    ("map-text", "map-bg", TEXT, "map labels (on their halo)"),
    ("focus", "map-bg", GRAPHIC, "hovered or focused room outline"),
    ("pin", "map-bg", GRAPHIC, "pinned room outline"),
    ("stair", "map-bg", GRAPHIC, "staircase pair outline and line"),
    ("door-outline", "map-bg", GRAPHIC, "door marker outline"),
    ("wall", "map-bg", GRAPHIC, "solid wall"),
    ("major", "map-bg", GRAPHIC, "major-item outline (Quest Log)"),
    ("door-open", "map-bg", GRAPHIC, "open door marker"),
    ("door-bomb", "map-bg", GRAPHIC, "bombable wall marker"),
    ("door-key", "map-bg", GRAPHIC, "key-locked door marker"),
    ("door-walk", "map-bg", GRAPHIC, "walk-through wall marker"),
    ("door-shutter", "map-bg", GRAPHIC, "shutter door marker"),
]


def rgb(colour):
    colour = colour.strip().lstrip("#")
    if len(colour) == 3:
        colour = "".join(c * 2 for c in colour)
    return tuple(int(colour[i:i + 2], 16) for i in (0, 2, 4))


def luminance(colour):
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in colour)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def blend(top, alpha, bottom):
    return tuple(round(t * alpha + b * (1 - alpha)) for t, b in zip(top, bottom))


def tokens(css):
    """{name: (light, dark)} for the light-dark() tokens, and --room-opacity."""
    found = {}
    for name, light, dark in re.findall(r"--([\w-]+):\s*light-dark\(\s*(#[0-9a-fA-F]{3,6})\s*,\s*(#[0-9a-fA-F]{3,6})\s*\)", css):
        found[name] = (rgb(light), rgb(dark))
    opacity = float(re.search(r"--room-opacity:\s*([\d.]+)", css).group(1))
    return found, opacity


def main():
    failures = 0
    nes = [rgb(colour) for colour in PALETTE_COLORS]
    for direction in DIRECTIONS:
        values, opacity = tokens((DESIGN / direction / "style.css").read_text())
        print("== %s" % direction)
        for theme, index in (("light", 0), ("dark", 1)):
            worst = []
            for fg, bg, minimum, what in CHECKS:
                if fg not in values:
                    continue  # a token only some directions have
                ratio = contrast(values[fg][index], values[bg][index])
                worst.append((ratio / minimum, ratio, minimum, what))
                if ratio < minimum:
                    failures += 1
                    print("  FAIL %-5s %-45s %.2f < %.1f" % (theme, what, ratio, minimum))
            # Map labels on every NES room colour, without their halo.
            label = values["map-text"][index]
            room_ratios = [contrast(label, blend(colour, opacity, values["map-bg"][index])) for colour in nes]
            low = min(room_ratios)
            if low < TEXT:
                failures += 1
                print("  FAIL %-5s map labels on the worst of 64 NES room colours: %.2f" % (theme, low))
            tightest = min(worst)
            print("  %-5s all %d pairs pass; tightest: %s %.2f (needs %.1f); labels on any room colour: >= %.2f"
                  % (theme, len(CHECKS), tightest[3], tightest[1], tightest[2], low))
    print("all pass" if not failures else "%d failures" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
