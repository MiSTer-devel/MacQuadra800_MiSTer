#!/usr/bin/env python3
"""Where is the highlighted row in an open Mac OS pull-down menu?

  python3 scripts/menuitem_probe.py <shot.png> <title_left_x>
  -> "ITEM band=[98,111] panel_bottom=113 gap=2"  (gap 0-4 means the LAST item)
  -> "NOITEM panel_bottom=113"                    (menu open, nothing under the pointer)
  -> "NOPANEL"

`title_left_x` is the second field from scripts/menubar_probe.py: a Mac OS menu
panel is left-aligned with its title.

Detection is by colour, not brightness. The panel is neutral grey (R=G=B, light),
the highlighted row is the appearance blue (measured: rgb ~ (84,84,179), so
B - R is large), and the desktop below the panel is teal (G,B > R). Brightness
alone cannot separate a blue highlight from the dark desktop, which is what an
earlier greyscale version of this got wrong.

Used by scripts/guest/menu.sh. scripts/mac_shutdown.sh used it until
2026-09-16 and now reads the panel with scripts/finder_probe.py instead:
panel_bottom here follows grey, so it runs on into a grey Finder window behind
the menu (219 against a panel ending at 112), and "gap" goes wrong with it.
The band itself stays reliable.
"""
import sys

import numpy as np
from PIL import Image

rgb = np.array(Image.open(sys.argv[1]).convert("RGB")).astype(int)
x0 = int(sys.argv[2])


def inverted_band(y_lo, y_hi):
    """System 7 (A/UX 3.1) inverts the highlighted row to BLACK, and its panel
    top is not the platinum grey the blue logic expects.  Return the longest
    run (>= 8 rows) of dark rows in the panel column between y_lo and y_hi
    that has a light row directly above and below it -- a highlighted row sits
    inside the light panel, whereas a dark desktop below the panel does not.
    (2026-09-07 gate run: menu.sh wandered under A/UX without this.)"""
    win = rgb[y_lo:y_hi, x0:x0 + 150].mean(axis=2)
    # BLACK rows only (< 40): the Mac OS 8 teal desktop between a panel's bottom
    # and the next window reads 60-90 and was taken for a highlight at < 100
    # (2026-09-08 gate run)
    dark = (win < 40).mean(axis=1) > 0.5
    light = (win > 150).mean(axis=1) > 0.5
    best = run = None
    for y, v in enumerate(list(dark) + [False]):
        if v and run is None:
            run = y
        elif not v and run is not None:
            if (y - run) >= 8 and run > 0 and y < len(light) and light[run - 1] and light[y]:
                if best is None or (y - run) > (best[1] - best[0] + 1):
                    best = (run, y - 1)
            run = None
    return None if best is None else (best[0] + y_lo, best[1] + y_lo)

# start a little left of the title: the panel is left-aligned with it, but the
# title's detected left edge can be a few px off when its glyphs are wide.
win = rgb[20:220, max(0, x0 - 2):x0 + 70]
r, g, b = win[:, :, 0], win[:, :, 1], win[:, :, 2]

grey = ((abs(r - g) < 10) & (abs(g - b) < 10) & (r > 120)).mean(axis=1)
blue = ((b - r > 50) & (b > 120)).mean(axis=1)

# Separator rules and item underlines are neither, so allow a few such rows
# inside the panel before calling it the bottom edge.
bottom, miss = None, 0
for y in range(win.shape[0]):
    if grey[y] > 0.5 or blue[y] > 0.5:
        bottom, miss = y, 0
    else:
        miss += 1
        if miss > 4:
            break

if bottom is None:
    inv = inverted_band(20, 240)
    if inv:
        print("ITEM band=[%d,%d] panel_bottom=%d gap=99 inverted" % (inv[0], inv[1], inv[1]))
        sys.exit(0)
    print("NOPANEL")
    sys.exit(0)

band = [y for y in range(bottom + 1) if blue[y] > 0.5]
if band:
    print("ITEM band=[%d,%d] panel_bottom=%d gap=%d"
          % (band[0] + 20, band[-1] + 20, bottom + 20, bottom - band[-1]))
else:
    # the grey-panel bottom found above stops at a black System 7 highlight,
    # so search the whole panel height, not just above that bottom
    inv = inverted_band(20, 240)
    if inv:
        print("ITEM band=[%d,%d] panel_bottom=%d gap=99 inverted" % (inv[0], inv[1], inv[1]))
        sys.exit(0)
    print("NOITEM panel_bottom=%d" % (bottom + 20))
