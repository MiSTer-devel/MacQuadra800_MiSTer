#!/usr/bin/env python3
"""Read a Mac OS 8.1 Finder screenshot for scripts/mac_shutdown.sh.

  python scripts/finder_probe.py screen <shot.png> <special_x>
      Before anything is pressed, with the pointer parked in the top-left
      corner. One of:
        HALT                    the "It is now safe to switch off" screen
        NOBAR                   no Mac OS menu bar (MiSTer menu, console, blank)
        MENUOPEN <l> <r>        a title is already pulled down
        SPECIAL <x> <iou>       the Special title is centred at x (an integer),
                                within SPECIAL_TOL of special_x
        ELSEWHERE <x> <iou>     a Special title, but not at special_x (x~231
                                is A/UX's Finder)
        NOSPECIAL <iou>         no Special title: another application is in
                                front, or a modal dialog has dimmed the menus
  python scripts/finder_probe.py panel <shot.png> <special_x>
      With the button held. One of:
        CLOSED                  no title is pulled down
        OTHER <l> <r>           the pulled-down title is not over special_x
        NOPANEL <l> <r>         no platinum panel under it (System 7 / A/UX)
        NOROW <frame>           panel open, bottom border at y=frame, no row lit
        ROW <frame> <y0> <y1> <last>
                                row y0..y1 is lit; last=1 when it sits directly
                                on the bottom border, i.e. it is the last item
  python scripts/finder_probe.py halt <shot.png>
        HALT | NOHALT

Every line may carry a trailing "# ..." comment for the log; callers read the
leading fields.

Why the panel is measured from its bottom BORDER. scripts/menuitem_probe.py
finds the panel bottom by following platinum grey down from the title, which
runs straight on into a grey Finder window sitting behind the menu (it read
219 against a panel that ends at 112 in the failed 2026-09-16 run). The border
is the menu's own 1 px black frame line, drawn over whatever is behind it, and
nothing inside a platinum panel is black across the columns sampled here.

Geometry of the 8.1 Finder's Special menu on this core (640x480, no Sleep item
on a Quadra): title 149..212, panel columns 149..264, rows Empty Trash 20..37,
Eject 42..57, Erase Disk 58..73, Restart 80..95, Shut Down 96..111, border
y=112, shadow y=113. Highlight rgb (84,84,179) with a (0,0,165) bottom row,
white item text on it. A/UX's Finder is different in every respect that
matters: Special at x~231 behind a Label menu, a white panel, black inverted
highlight, and Logout (not Shut Down) as the last item -- so `panel` reports
NOPANEL there and the walker never releases.
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from menubar_probe import open_title  # noqa: E402

# "Special" as the 8.1 Finder draws it (Charcoal), dark pixels (grey < 100) of
# the unhighlighted title, cut from scratch/p1_shutdown/01_initial.png. Its
# top-left pixel is at (159, 5), so the title's centre is x = 180.5.
SPECIAL = """
.####.........................##..........##
##........................................##
##.....##.##....####....####..##...####...##
###....###.##..##..##..##..#..##......##..##
.###...##..##..##..##..##.....##...#####..##
..###..##..##..######..##.....##..##..##..##
...##..##..##..##......##.....##..##..##..##
...##..##..##..##......##.....##..##.###..##
####...#####....#####...####..##...##.##..##
.......##...................................
.......##...................................
"""
TEMPLATE = np.array([[c == "#" for c in row] for row in SPECIAL.split()])
TEMPLATE_Y = 5
# Over the 1,151 saved frames with a menu bar (scratch/, 2026-08..09): 331
# 8.1 Finder frames matched at x=180.5 with IoU 0.79-1.00 (the low end with
# the pointer resting on the title), 100 A/UX Finder frames at x=231.5 with
# 0.92 (Chicago, not Charcoal), and nothing else scored above 0.57
# ("Controls" in Script Editor).
MATCH_IOU = 0.75
SPECIAL_TOL = 8          # px between the matched centre and special_x

# The panel is sampled in columns special_x +- HALF: inside the Special panel
# (149..264) and wide enough that the pointer (11 px at its widest) and a
# row's white text cannot hide a lit row.
HALF = 30
ROW_BLUE = 0.3           # lit rows measured 0.54-1.0 blue here, unlit rows 0
BORDER_BLACK = 0.7       # the border measured 0.95-1.0, pointer on it included
PLATINUM = 0.4           # 8.1 panels measured 0.65-0.82 grey, A/UX's 0.00


def load(path):
    """(rgb, luma) int arrays. Luma, not the channel mean, is what "dark"
    means to menubar_probe.py and the template: the 8.1 highlight blue is
    94.8 in luma but 115.7 as a mean."""
    im = Image.open(path)
    return (np.asarray(im.convert("RGB")).astype(int),
            np.asarray(im.convert("L")).astype(int))


def is_halt(rgb):
    """The shutdown screen is pure black with one white dialog and nothing
    else: Mac OS's "It is now safe to switch off" and A/UX's "You may now
    switch off" measured 83-90 % black, 10-17 % white and not one other pixel
    over 71 saved frames. The nearest other screens were the 50/50 grey boot
    dither and near-black frames with no dialog (93 % black, < 1 % white)."""
    black = (rgb.max(axis=2) <= 24).mean()
    white = (rgb.min(axis=2) >= 232).mean()
    return black >= 0.75 and 0.05 <= white <= 0.25 and black + white >= 0.99


def has_menubar(gray):
    """A 20 px bar: a black rule on row 19 and mostly light rows above it."""
    rule = (gray[19, :] < 60).mean() >= 0.9
    light = (gray[1:18, 40:520] > 170).mean() >= 0.6
    return rule and light


def find_special(gray):
    """(centre_x, iou) of the best match for the Special title."""
    th, tw = TEMPLATE.shape
    dark = gray[TEMPLATE_Y - 1:TEMPLATE_Y + th + 1, :] < 100
    win = np.lib.stride_tricks.sliding_window_view(dark, (th, tw))
    inter = (win & TEMPLATE).sum(axis=(2, 3))
    union = (win | TEMPLATE).sum(axis=(2, 3))
    iou = np.where(union > 0, inter / np.maximum(union, 1), 0.0)
    dy, x = np.unravel_index(int(iou.argmax()), iou.shape)
    return x + (tw - 1) / 2.0, float(iou[dy, x])


def screen(path, special_x):
    rgb, gray = load(path)
    if is_halt(rgb):
        return "HALT"
    if not has_menubar(gray):
        return "NOBAR"
    t = open_title(gray)
    if t is not None:
        return "MENUOPEN %d %d" % t
    cx, iou = find_special(gray)
    if iou < MATCH_IOU:
        return "NOSPECIAL %.2f  # best match x=%.1f" % (iou, cx)
    if abs(cx - special_x) <= SPECIAL_TOL:
        return "SPECIAL %d %.2f  # centre x=%.1f" % (int(cx + 0.5), iou, cx)
    return "ELSEWHERE %d %.2f  # centre x=%.1f" % (int(cx + 0.5), iou, cx)


def panel(path, special_x):
    rgb, gray = load(path)
    t = open_title(gray)
    if t is None:
        return "CLOSED"
    if not (t[0] - 10 <= special_x <= t[1] + 10):
        return "OTHER %d %d" % t
    a = rgb[:, max(0, special_x - HALF):special_x + HALF + 1]
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    black = (a.max(axis=2) <= 40).mean(axis=1)
    frame = next((y for y in range(21, a.shape[0]) if black[y] >= BORDER_BLACK), None)
    if frame is None or frame < 30:
        return "NOPANEL %d %d  # no bottom border" % t
    grey = ((abs(r - g) < 10) & (abs(g - b) < 10) & (r >= 200) & (r <= 245)).mean(axis=1)
    if grey[22:frame - 1].mean() < PLATINUM:
        return "NOPANEL %d %d  # not a platinum panel (System 7 / A/UX?)" % t
    blue = ((b - r > 50) & (b > 120)).mean(axis=1)
    lit = [y for y in range(21, frame) if blue[y] >= ROW_BLUE]
    if not lit:
        return "NOROW %d  # title %d..%d, border y=%d" % (frame, t[0], t[1], frame)
    # one row can be lit; keep the longest contiguous run
    runs, cur = [], [lit[0]]
    for y in lit[1:]:
        if y == cur[-1] + 1:
            cur.append(y)
        else:
            runs.append(cur)
            cur = [y]
    runs.append(cur)
    run = max(runs, key=len)
    y0, y1 = run[0], run[-1]
    last = int(12 <= len(run) <= 20 and frame - 2 <= y1 <= frame - 1)
    return "ROW %d %d %d %d  # title %d..%d, row %d..%d, border y=%d%s" % (
        frame, y0, y1, last, t[0], t[1], y0, y1, frame, ", LAST row" if last else "")


def main(argv):
    if len(argv) >= 3 and argv[0] == "screen":
        print(screen(argv[1], int(float(argv[2]))))
    elif len(argv) >= 3 and argv[0] == "panel":
        print(panel(argv[1], int(float(argv[2]))))
    elif len(argv) >= 2 and argv[0] == "halt":
        print("HALT" if is_halt(load(argv[1])[0]) else "NOHALT")
    else:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
