#!/usr/bin/env bash
# click.sh <x> <y> [move] — put the pointer on an absolute screen pixel, click it.
#
# There is no absolute pointer position to command: mrext sends relative motion
# and Mac OS accelerates it, so the event-to-pixel scale drifts between roughly
# 1.3 and 4 px per event depending on how many events get coalesced into one
# ADB report. So this does not trust any conversion. It pins the pointer into
# the top-left corner -- the one position the screen edge makes certain -- and
# then walks toward the target, MEASURING the achieved px-per-event from a
# screenshot after every move and re-estimating from that. Steps are damped to
# half the estimate so a bad scale converges instead of oscillating.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)" || exit 1
. scripts/local.env
WS="python scripts/mister_ws.py --host $MISTER_HOST --delay 0.02"
P=scratch/guest

# A timed-out observer may leave this walker alive. Never let another walker
# fight it for the pointer; children inherit the lock until they also exit.
mkdir -p "$P"
exec 9>"$P/click.lock"
if ! flock -n 9; then
    echo "Another mouse navigation is still running; wait for its process to finish." >&2
    exit 4
fi
release_mouse() {
    local click_status=$?
    trap - EXIT
    $WS mousebtn:left_up >/dev/null 2>&1 || true
    exit "$click_status"
}
trap release_mouse EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

TX=${1:?target x}; TY=${2:?target y}; MODE=${3:-click}
TOL=3

steps() { local n=$1 dx=$2 dy=$3 out=""; while [ "$n" -gt 0 ]; do out="$out mouse:$dx,$dy"; n=$((n-1)); done; echo "$out"; }
log()   { echo "[$(date +%H:%M:%S)] $*"; }

$WS $(steps 60 -12 -12) >/dev/null 2>&1                       # pin to (0,0)
bash scripts/grab_fresh.sh "$P/_bg.png" >/dev/null 2>&1       # diff background

sx=200; sy=200        # hundredths of a px per event
cx=0;  cy=0
for attempt in $(seq 1 16); do
    dx=$(( TX - cx )); dy=$(( TY - cy ))
    adx=${dx#-}; ady=${dy#-}
    if [ "$adx" -le "$TOL" ] && [ "$ady" -le "$TOL" ]; then
        log "on target ($cx,$cy)"
        case "$MODE" in
            click)  $WS mousebtn:left_down sleep:0.15 mousebtn:left_up >/dev/null 2>&1; log "clicked" ;;
            dclick) # both presses must land inside the double-click time AND
                    # without the pointer moving, or the Finder reads two singles
                    $WS mousebtn:left_down sleep:0.08 mousebtn:left_up sleep:0.12 \
                        mousebtn:left_down sleep:0.08 mousebtn:left_up >/dev/null 2>&1
                    log "double-clicked" ;;
            move)   log "moved only" ;;
        esac
        exit 0
    fi

    ex=$(( (dx * 100) / sx / 2 )); ey=$(( (dy * 100) / sy / 2 ))   # damped
    [ "$ex" -eq 0 ] && [ "$adx" -gt "$TOL" ] && ex=$(( dx > 0 ? 1 : -1 ))
    [ "$ey" -eq 0 ] && [ "$ady" -gt "$TOL" ] && ey=$(( dy > 0 ? 1 : -1 ))
    sent_x=$ex; sent_y=$ey

    if [ "$ex" -ne 0 ]; then
        d=1; n=$ex; [ "$n" -lt 0 ] && { d=-1; n=$(( -n )); }
        [ "$n" -gt 300 ] && n=300
        $WS $(steps "$n" "$d" 0) >/dev/null 2>&1
    fi
    if [ "$ey" -ne 0 ]; then
        d=1; n=$ey; [ "$n" -lt 0 ] && { d=-1; n=$(( -n )); }
        [ "$n" -gt 300 ] && n=300
        $WS $(steps "$n" 0 "$d") >/dev/null 2>&1
    fi

    bash scripts/grab_fresh.sh "$P/_cur.png" >/dev/null 2>&1
    probe=$(python scripts/guest/probe_cursor.py "$P/_bg.png" "$P/_cur.png")
    case "$probe" in
        CURSOR*)
            nx=${probe#*x=}; nx=${nx%% *}
            ny=${probe##*y=}
            mx=$(( nx - cx )); my=$(( ny - cy ))
            # re-estimate scale from what actually happened
            amx=${mx#-}; asx=${sent_x#-}
            [ "$asx" -gt 2 ] && [ "$amx" -gt 0 ] && sx=$(( (amx * 100) / asx ))
            amy=${my#-}; asy=${sent_y#-}
            [ "$asy" -gt 2 ] && [ "$amy" -gt 0 ] && sy=$(( (amy * 100) / asy ))
            [ "$sx" -lt 50 ] && sx=50; [ "$sx" -gt 800 ] && sx=800
            [ "$sy" -lt 50 ] && sy=50; [ "$sy" -gt 800 ] && sy=800
            log "at ($nx,$ny) target ($TX,$TY) scale ${sx}/${sy} per 100 events"
            cx=$nx; cy=$ny ;;
        *)
            log "cursor not found ($probe) — nudging"
            $WS mouse:3,3 >/dev/null 2>&1 ;;
    esac
done
log "failed to reach ($TX,$TY); last at ($cx,$cy)"
exit 3
