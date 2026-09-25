#!/usr/bin/env python3
"""Report which Mac OS menu-bar title is currently pulled down.

The open title is drawn as a filled dark box in the menu bar while every other
title is dark text on a light bar, so the highlighted one is the widest run of
columns that are dark through the WHOLE bar height.

  python3 scripts/menubar_probe.py <shot.png>
  -> "OPEN 154 208"   (left and right column of the open title)   or   "NONE"

Exists because the event-to-pixel scale of mrext motion is not stable -- it
depends on how many moves get coalesced into one ADB report -- so a script that
walks a fixed number of steps to a menu will sometimes land one menu over.
Callers should step and re-probe rather than trust a step count.

A pointer resting on the open title breaks the dark run, so the span can come
back as only the part left or right of the pointer (149..182 or 180..212 for
Special, whose full span is 149..212): test whether a target x falls inside
it, do not take the left edge as the title's.
"""
import sys

import numpy as np
from PIL import Image

# Sample only just inside the top and bottom of the bar, above and below the
# glyph bodies: a highlighted title is dark there, an unhighlighted one is not.
ROWS = [2, 3, 16, 17]
DARK = 100


def open_title(gray):
    """(left, right) columns of the pulled-down title in a greyscale frame
    (a 2-D int array), or None.  Also used by scripts/finder_probe.py."""
    col_dark = (gray[ROWS, :] < DARK).mean(axis=0) > 0.9
    best_len = 0
    best = None
    run = None
    for x, v in enumerate(list(col_dark) + [False]):
        if v and run is None:
            run = x
        elif not v and run is not None:
            if x - run > best_len:
                best_len, best = x - run, (run, x - 1)
            run = None
    if best is None or best_len < 8:
        return None
    return best


if __name__ == "__main__":
    t = open_title(np.array(Image.open(sys.argv[1]).convert("L")).astype(int))
    if t is None:
        print("NONE")
    else:
        # measured on a 640x480 Mac OS 8.1 Finder: apple 9 | View 105 |
        # Special 149..212 | Help 208
        print("OPEN %d %d" % t)
