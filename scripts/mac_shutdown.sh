#!/usr/bin/env bash
# scripts/mac_shutdown.sh -- Special -> Shut Down in the Mac OS 8.1 Finder,
# driven from the host and checked against a screenshot before the press and
# before the release. This is the one Mac OS shutdown walker;
# scripts/guest/shutdown_finder.sh and scripts/guest/shutdown.sh run it.
#
# WHY THIS EXISTS. Reloading the core while Mac OS is running is a hard
# power-cut on a mounted HFS volume. Doing it repeatedly on 2026-08-30 corrupted
# the Quad Squad image badly enough that it hung mid-boot at a repeatable offset
# -- which then got misdiagnosed as an RTL fault more than once. Always shut the
# guest down first; only load a new core once the screen says it is safe.
#
# HOW IT AIMS (recalibrated 2026-09-16). mrext sends only RELATIVE motion, so
# there is no absolute position to command or read back. On 2026-09-16 both
# walkers failed on the 8.1 Finder: this one stepped 70 motion events right
# (~105 px, View) and slid along the bar with the button HELD, chasing a scale
# it re-derived from whichever title was open; shutdown_finder.sh aimed at
# x=229 -- Special on A/UX's Finder, Help on 8.1's -- and looked for the lit
# row at x 295..335, past the right edge of 8.1's Special panel (149..264), so
# it never saw one. An Opus operator then shut the Finder down by hand with the
# closed loop below, and this script is that loop:
#
#   1. Pin the pointer: 60 x mouse:-12,-12 drives it into the top-left corner,
#      the one position the screen edge makes certain. Grab that frame.
#   2. Read the frame before pressing anything (scripts/finder_probe.py
#      screen): not already halted, a Mac OS menu bar, no menu pulled down,
#      and the glyphs of "Special" centred at SPECIAL_X -- which also shows the
#      Finder is in front and no modal dialog has dimmed its menus.
#   3. With the button UP, move onto the title: down onto the bar first, then
#      across (a press on the top rows of the bar does not always land on the
#      title). Measured 2026-09-16 at 0.02 s pacing: 1.47-1.51 px per motion
#      event in both axes; 6 x mouse:0,1 then 123 x mouse:1,0 put the pointer
#      at (183,7). Find the pointer by difference against the pinned frame
#      (scripts/guest/probe_cursor.py) and correct with the scale that move
#      actually achieved, until the pointer is on the title.
#   4. Press only then. Check that the menu pulled down is the one under the
#      pointer and find the bottom border of its panel (finder_probe.py panel).
#   5. Walk down to the middle of the last row, which sits directly on that
#      border (60 x mouse:0,1 from the title reached it by hand). Re-probe and
#      correct -- from the lit row, or, when no row is lit, from the pointer
#      found against the post-press frame -- and release IN PLACE only when
#      the lit row is the last one. Restart is the row directly above Shut
#      Down, and a Quadra's Special menu has no Sleep item.
#   6. Wait for the "It is now safe to switch off your Macintosh" screen.
#
# Pacing: 0.008 s between motion events outruns the ~90 Hz ADB poll and moves
# are silently lost (2026-09-08); 0.02 s is what the scale was measured at.
# The button payloads are mousebtn:left_down / left_up -- mouseBtn:1 and :0 are
# logged by mrext and do nothing.
#
# THE BUTTON. A held button wedges the Finder in a menu track and looks exactly
# like a hung CPU (CLAUDE.md rule 4). Every exit -- success, refusal, failure,
# Ctrl-C, SIGTERM, SIGHUP -- sends mousebtn:left_up, and an exit with the button
# down first slides straight up onto the menu title so the release selects
# nothing. SIGKILL, or a Windows process-tree kill when a tool times out, cannot
# be trapped: after one, run --release. A run takes one to three minutes; give
# it a timeout of five or more.
#
# KEYBOARD, for chores around a shutdown (closing windows, answering a dialog):
# Command is PS/2 Left Alt in this core's ADB map (rtl/adb.sv:530, PS/2 0x11 ->
# ADB $37), Linux keycode 56 to scripts/mister_ws.py; Right Alt (100) is Command
# too. Keycode 125 (Left Meta) is Option ($3A, rtl/adb.sv:800), not Command:
# "cmd-W" sent with it types into the Finder's type-select. cmd-W is
#     python scripts/mister_ws.py --host "$MISTER_HOST" down:56 raw:17 up:56
#
# SCOPE. The Mac OS 8.1 Finder at 640x480 (Quad Squad, the retail CD, the fresh
# MacOS8-MiSTer disk). A/UX's Finder is refused on purpose: its Special title
# sits at x~231 behind a Label menu, its menus highlight by black inversion and
# its Special menu ends in Logout -- "release on the last row" would log out.
# Shut A/UX down with `shutdown -h now` in a CommandShell
# (scripts/guest/type.sh -r 'shutdown -h now'). The System 7.1 Finder on the
# A/UX disk's MacPartition, which the old shutdown_finder.sh was tuned for, has
# the same title layout and highlight and is refused as well.
#
# Usage:
#   bash scripts/mac_shutdown.sh              # shut down, with verification shots
#   bash scripts/mac_shutdown.sh --dry-run    # print the plan, send nothing
#   bash scripts/mac_shutdown.sh --release    # free a held button: slide up, left_up
# Exit: 0  the halt screen is showing (it already was, or Shut Down reached it)
#       3  refused or failed with nothing selected -- read the log and the shots
#       4  Shut Down selected but no halt screen within HALT_WAIT s: look before
#          loading any core (a save dialog? still closing?)
# Env:  SPECIAL_X (181)  PX_PER_EVENT_X100 (149)  MENU_DELAY (0.02)  HALT_WAIT (120)
# Shots land in scratch/shutdown/.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1
[ -r scripts/local.env ] && . scripts/local.env
: "${MISTER_HOST:?set MISTER_HOST in scripts/local.env}"

MODE=run
case "${1:-}" in
    "")        ;;
    --dry-run) MODE=dry ;;
    --release) MODE=release ;;
    *) echo "usage: bash scripts/mac_shutdown.sh [--dry-run | --release]" >&2; exit 2 ;;
esac

SPECIAL_X=${SPECIAL_X:-181}      # centre of the Special title on the 8.1 Finder; Help is ~230
S=${PX_PER_EVENT_X100:-149}      # px per motion event x100; re-measured from every long move
MENU_DELAY=${MENU_DELAY:-0.02}
HALT_WAIT=${HALT_WAIT:-120}
BAR_Y=9                          # aim at the middle of the 20 px menu bar ...
Y_MIN=3; Y_MAX=15                # ... and accept these rows
X_TOL=10                         # px from the title centre; the title spans 149..212
POS_TRIES=6
WALK_TRIES=8

WS="python scripts/mister_ws.py --host $MISTER_HOST --delay $MENU_DELAY"
P=scratch/shutdown

log()    { echo "[$(date +%H:%M:%S)] $*"; }
ws()     { $WS "$@" >/dev/null 2>&1; }
# N motion events of (dx,dy), as mister_ws.py arguments
steps()  { local n=$1 dx=$2 dy=$3 out=""; while [ "$n" -gt 0 ]; do out="$out mouse:$dx,$dy"; n=$((n-1)); done; echo "$out"; }
# signed motion events for a signed pixel distance $1 at scale $2, rounded
events() { local a=${1#-} n; n=$(( (a * 100 + $2 / 2) / $2 )); [ "$1" -lt 0 ] && n=$(( -n )); echo "$n"; }
clamp()  { local v=$1; [ "$v" -lt 50 ] && v=50; [ "$v" -gt 800 ] && v=800; echo "$v"; }
# move <x events> <y events>, both signed; y first
move() {
    local nx=$1 ny=$2 args=""
    [ "$ny" -gt 0 ] && args="$(steps "$ny" 0 1)"
    [ "$ny" -lt 0 ] && args="$(steps $(( -ny )) 0 -1)"
    [ "$nx" -gt 0 ] && args="$args $(steps "$nx" 1 0)"
    [ "$nx" -lt 0 ] && args="$args $(steps $(( -nx )) -1 0)"
    [ -z "$args" ] || ws $args
}
# a fresh screenshot, or failure -- never a stale file left by an earlier run
shot()   { rm -f "$1"; bash scripts/grab_fresh.sh "$1" >/dev/null 2>&1 && [ -s "$1" ]; }

if [ "$MODE" = dry ]; then
    nx=$(events "$SPECIAL_X" "$S"); ny=$(events "$BAR_Y" "$S")
    echo "host $MISTER_HOST, $MENU_DELAY s per event, shots in $P/. Would:"
    echo "  1. pin the pointer (60 x mouse:-12,-12) and grab the background frame"
    echo "  2. refuse unless it shows a menu bar with nothing pulled down and Special centred at x=$SPECIAL_X"
    echo "  3. button up: $ny x mouse:0,1 then $nx x mouse:1,0 toward ($SPECIAL_X,$BAR_Y) at $S/100 px per event;"
    echo "     probe the pointer and correct (up to $POS_TRIES looks) until it is within $X_TOL px of the"
    echo "     title centre on rows $Y_MIN..$Y_MAX"
    echo "  4. mousebtn:left_down; check Special is the menu open and find its bottom border"
    echo "  5. walk down to the last row's middle; release in place only when the last row is lit"
    echo "     (up to $WALK_TRIES looks), otherwise slide up onto the title and release on nothing"
    echo "  6. wait up to ${HALT_WAIT}s for the safe-to-switch-off screen"
    exit 0
fi

if [ "$MODE" = release ]; then
    log "sliding the pointer straight up onto the menu bar, then mousebtn:left_up"
    if ws $(steps 30 0 -12) mousebtn:left_up; then log "released"; exit 0; fi
    log "mister_ws.py failed -- is the remote at $MISTER_HOST:${MISTER_HTTP_PORT:-8182} up?"
    exit 3
fi

BUTTON=up          # "down" from the moment a left_down may have reached the guest
# release [cancel] -- cancel slides straight up onto the menu title first, so
# the release selects nothing; plain releases where the pointer is
release() {
    if [ "${1:-}" = cancel ]; then ws $(steps 30 0 -12) mousebtn:left_up; else ws mousebtn:left_up; fi
    BUTTON=up
}
finish() {
    local rc=$?
    trap '' INT TERM HUP          # let the release go out
    if [ "$BUTTON" = down ]; then
        log "leaving with the button down: sliding up onto the menu title and releasing (nothing selected)"
        release cancel
    else
        ws mousebtn:left_up       # the explicit release on every exit; harmless when up
    fi
    exit "$rc"
}
trap finish EXIT
trap 'log "interrupted (SIGINT)"; exit 130' INT
trap 'log "terminated (SIGTERM)"; exit 143' TERM
trap 'log "hung up (SIGHUP)"; exit 129' HUP
fail() { log "$*"; exit 3; }

mkdir -p "$P"

# ---- 1-2: pin, look, refuse anything that is not the 8.1 Finder at rest ----
log "pinning the pointer into the top-left corner"
ws $(steps 60 -12 -12) || fail "mister_ws.py failed -- is the remote at $MISTER_HOST:${MISTER_HTTP_PORT:-8182} up?"
shot "$P/00_pinned.png" || fail "no fresh screenshot -- is video capture alive? (scripts/grab_fresh.sh)"
line=$(python scripts/finder_probe.py screen "$P/00_pinned.png" "$SPECIAL_X")
read -r st a b _ <<<"$line"
case "$st" in
    SPECIAL)   AIM_X=$a; log "Finder menu bar at rest: $line" ;;
    HALT)      log "already at the safe-to-switch-off screen, nothing to do"; exit 0 ;;
    NOBAR)     fail "no Mac OS menu bar on screen (the MiSTer menu? a console? a full-screen dialog?) -- refusing" ;;
    MENUOPEN)  fail "a menu is already pulled down (title x=$a..$b), perhaps a sticky one from an interrupted run: close it (Escape, or a click on the desktop) and retry" ;;
    ELSEWHERE) fail "the Special title is at x=$a, not SPECIAL_X=$SPECIAL_X -- x~231 is A/UX's Finder, which is refused (see the header); otherwise rerun with SPECIAL_X=$a" ;;
    NOSPECIAL) fail "no Special title on the menu bar ($line): another application is in front, or a dialog has dimmed the Finder's menus -- bring the Finder forward and retry" ;;
    *)         fail "finder_probe.py failed: '$line'" ;;
esac

# ---- 3: button up, onto the title, verified absolutely ----
nx=$(events "$AIM_X" "$S"); ny=$(events "$BAR_Y" "$S")
log "button up: $ny x mouse:0,1 onto the bar, $nx x mouse:1,0 across to Special"
move "$nx" "$ny"
cx=0; on=0
for try in $(seq 1 "$POS_TRIES"); do
    shot "$P/1${try}_aim.png" || fail "no fresh screenshot"
    probe=$(python scripts/guest/probe_cursor.py "$P/00_pinned.png" "$P/1${try}_aim.png")
    case "$probe" in
        CURSOR*) x=${probe#*x=}; x=${x%% *}; y=${probe##*y=} ;;
        *) fail "pointer not found ($probe): did it move at all? Remote input goes dead if the mrext service restarts under a running core (CLAUDE.md rule 3)" ;;
    esac
    # the scale the last move achieved -- only a long x move says much
    m=$(( x - cx ))
    [ "${nx#-}" -ge 8 ] && [ $(( m * nx )) -gt 0 ] && S=$(clamp $(( ${m#-} * 100 / ${nx#-} )))
    dx=$(( AIM_X - x ))
    if [ "${dx#-}" -le "$X_TOL" ] && [ "$y" -ge "$Y_MIN" ] && [ "$y" -le "$Y_MAX" ]; then on=1; break; fi
    nx=$(events "$dx" "$S"); ny=0
    if [ "$y" -lt "$Y_MIN" ] || [ "$y" -gt "$Y_MAX" ]; then ny=$(events $(( BAR_Y - y )) "$S"); fi
    log "pointer at ($x,$y), Special at ($AIM_X,$BAR_Y), $S/100 px per event: moving $nx,$ny"
    cx=$x
    move "$nx" "$ny"
done
[ "$on" = 1 ] || fail "could not put the pointer on Special (last seen at ($x,$y))"

# ---- 4: press, and check what opened ----
log "pointer on Special at ($x,$y), $S/100 px per event: pressing"
PRESS_Y=$y
BUTTON=down
ws mousebtn:left_down sleep:0.4
shot "$P/20_pressed.png" || fail "no fresh screenshot after the press"
line=$(python scripts/finder_probe.py panel "$P/20_pressed.png" "$AIM_X")
read -r st f _ <<<"$line"
case "$st" in
    NOROW|ROW) FRAME=$f ;;
    *) fail "pressed on Special, but its menu is not what opened: $line" ;;
esac
TARGET=$(( FRAME - 8 ))
log "Special is open ($line): the last row's middle is y=$TARGET"

# ---- 5: walk down to the last row; release only on it ----
py=$PRESS_Y
n=$(events $(( TARGET - py )) "$S")
log "button held: $n x mouse:0,1 down to y=$TARGET"
move 0 "$n"
lit=0
for try in $(seq 1 "$WALK_TRIES"); do
    shot "$P/3${try}_walk.png" || fail "no fresh screenshot"
    line=$(python scripts/finder_probe.py panel "$P/3${try}_walk.png" "$AIM_X")
    read -r st f y0 y1 last _ <<<"$line"
    case "$st" in
        ROW)
            [ "$last" = 1 ] && { lit=1; break; }
            ny=$(( (y0 + y1) / 2 )) ;;
        NOROW)
            # no row lit: between rows, on a disabled item, or off the panel.
            # The pointer is the only change since the press below its old spot.
            probe=$(python scripts/guest/probe_cursor.py "$P/20_pressed.png" "$P/3${try}_walk.png" --min-y $(( PRESS_Y + 18 )))
            case "$probe" in
                CURSOR*) ny=${probe##*y=} ;;
                *) fail "no row is lit and the pointer is not in sight ($probe)" ;;
            esac ;;
        CLOSED|OTHER|NOPANEL)
            # Only vertical moves since the press, so the menu cannot really
            # have changed. Read this as a misread frame, not a closed menu:
            # releasing in place would select the row under the pointer, while
            # the slide up onto the title (the exit path) selects nothing.
            fail "Special's menu no longer reads as open: $line" ;;
        *) fail "finder_probe.py failed: '$line'" ;;
    esac
    m=$(( ny - py ))
    [ "${n#-}" -ge 10 ] && [ $(( m * n )) -gt 0 ] && S=$(clamp $(( ${m#-} * 100 / ${n#-} )))
    py=$ny
    n=$(events $(( TARGET - py )) "$S"); [ "$n" -eq 0 ] && n=1
    log "$st, pointer near y=$py ($line): moving $n toward y=$TARGET"
    move 0 "$n"
done
[ "$lit" = 1 ] || fail "could not confirm Shut Down as the lit row"

log "the lit row $y0..$y1 sits on the panel border at y=$f, so it is Shut Down: releasing in place"
# Released in place. Do NOT nudge the pointer first: Restart is the row above.
release

# ---- 6: the guest parks itself ----
log "waiting up to ${HALT_WAIT}s for the safe-to-switch-off screen"
end=$(( SECONDS + HALT_WAIT ))
while [ "$SECONDS" -lt "$end" ]; do
    sleep 5
    shot "$P/40_after.png" || continue
    if [ "$(python scripts/finder_probe.py halt "$P/40_after.png")" = HALT ]; then
        log "HALTED: $P/40_after.png shows the safe-to-switch-off screen"
        exit 0
    fi
done
log "Shut Down was selected but no halt screen after ${HALT_WAIT}s: look at $P/40_after.png (a save dialog? still closing?) before loading any core"
exit 4
