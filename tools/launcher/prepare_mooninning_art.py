"""Turn the MoonInning UI pack mockups into launcher backdrops.

The pack (user-supplied original art, not game content) has two flat 1672x941 mockups with
example text and states baked in. The launcher draws those parts live, so this erases them by
interpolating each region from the pixels around it:
  main.png      the yellow "selected" sparks beside JUGAR and the info box text;
  settings.png  the tab strip, the option rows and the help text.
Buttons, logo, hints and the close button stay. Layout rectangles used here are the ones
launcher.cpp uses (image pixels).

usage: prepare_mooninning_art.py <pack>/assets <out dir>
"""
import sys
from pathlib import Path

from PIL import Image


def average(px, xs, ys):
    pts = [px[x, y] for x in xs for y in ys]
    return tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))


# Boundary colours are averaged over a 9-pixel window along the edge and 3 pixels outward, so the
# halftone dots and JPEG-like noise of the art do not turn into streaks across the fill.
def fill_rows(px, x0, x1, y0, y1):
    """Each row of [x0, x1) x [y0, y1) becomes a blend of the pixels just left and right of it."""
    for y in range(y0, y1):
        ys = range(max(y0, y - 4), min(y1, y + 5))
        a = average(px, range(x0 - 3, x0), ys)
        b = average(px, range(x1, x1 + 3), ys)
        for x in range(x0, x1):
            t = (x - x0 + 1) / (x1 - x0 + 1)
            px[x, y] = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def fill_cols(px, x0, x1, y0, y1):
    """Each column of [x0, x1) x [y0, y1) becomes a blend of the pixels just above and below."""
    for x in range(x0, x1):
        xs = range(max(x0, x - 4), min(x1, x + 5))
        a = average(px, xs, range(y0 - 3, y0))
        b = average(px, xs, range(y1, y1 + 3))
        for y in range(y0, y1):
            t = (y - y0 + 1) / (y1 - y0 + 1)
            px[x, y] = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def inpaint_where(px, x0, x1, y0, y1, select, grow=3, iterations=400):
    """Erases the pixels of [x0, x1) x [y0, y1) that `select` picks (plus `grow` pixels around them)
    by repeatedly averaging their neighbours, so the background flows in from every side."""
    hit = {(x, y) for y in range(y0, y1) for x in range(x0, x1) if select(px[x, y])}
    mask = {(x + dx, y + dy) for x, y in hit for dx in range(-grow, grow + 1) for dy in range(-grow, grow + 1)
            if x0 <= x + dx < x1 and y0 <= y + dy < y1}
    value = {p: px[p] for p in mask}
    for _ in range(iterations):
        nxt = {}
        for (x, y) in mask:
            around = [value.get(q, px[q]) for q in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))]
            nxt[(x, y)] = tuple(sum(c[i] for c in around) / 4 for i in range(3))
        value = nxt
    for p, c in value.items():
        px[p] = tuple(round(v) for v in c)


def is_spark(c):
    r, g, b = c
    return r > 200 and g > 170 and b < 140  # the yellow strokes; their white rim is covered by `grow`


def main(assets: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)

    main_menu = Image.open(assets / "mooninning_main_menu.png").convert("RGB")
    assert main_menu.size == (1672, 941), main_menu.size
    px = main_menu.load()
    inpaint_where(px, 20, 92, 296, 392, is_spark)  # sparks left of JUGAR (drawn by the launcher instead)
    inpaint_where(px, 86, 98, 298, 326, lambda c: sum(c) > 560)  # tip of the top spark, above the glow
    fill_cols(px, 86, 1592, 774, 853)    # info box text
    main_menu.save(out / "main.png", optimize=True)

    # Setup window: same backdrop with blank buttons (icon and label erased, arrow kept) so the Setup
    # can write its own actions on them. Each button's fill is a vertical gradient, so a row-wise
    # blend across the icon and label leaves a clean pill.
    for centre in (378, 476, 573, 672):  # JUGAR, AJUSTES, MODS, SALIR
        fill_rows(px, 120, 560, centre - 30, centre + 31)
    # Leftovers of the JUGAR baseball outline above and below the blended rows.
    inpaint_where(px, 120, 212, 345, 412, lambda c: c[0] < 215 or c[2] > 120, grow=1)
    inpaint_where(px, 130, 200, 338, 352, lambda c: c[0] < 200, grow=2)
    main_menu.save(out / "setup.png", optimize=True)

    settings = Image.open(assets / "mooninning_settings_menu.png").convert("RGB")
    assert settings.size == (1672, 941), settings.size
    px = settings.load()
    fill_rows(px, 112, 949, 116, 208)    # tabs
    fill_rows(px, 121, 834, 231, 686)    # option rows
    fill_rows(px, 880, 1546, 250, 430)   # help text
    settings.save(out / "settings.png", optimize=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
