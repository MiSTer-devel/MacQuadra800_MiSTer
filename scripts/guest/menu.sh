#!/usr/bin/env bash
# menu.sh — drive a classic Mac OS pull-down menu by press-drag-release.
#
# Generalised from scripts/mac_shutdown.sh. Same hard-won rules apply:
#   * mrext sends RELATIVE motion and Mac OS accelerates it, so the
#     event-to-pixel scale is NOT stable. Never trust a step count -- step,
#     screenshot, re-probe, repeat.
#   * Move ONTO the bar (y) before moving across it (x).
#   * The button stays down across separate mister_ws.py invocations, which is
#     what lets each verb below be its own process.
#
# Verbs:
#   open  <title_center_x> <shot>     press and slide until that title is open
#   item  <title_left_x> <target_y> <shot>   walk down until the highlighted row
#                                            covers target_y
#   release                            release in place (selects the hovered row)
#   cancel                             slide back up to the title and release
#                                      (selects nothing)
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)" || exit 1
. scripts/local.env
# System 7 (A/UX) accelerates 0.02 s-spaced events into ~12 px jumps; 0.05 s
# gives ~1 px per event there.  MENU_DELAY=0.05 for System 7 guests.
WS="python scripts/mister_ws.py --host $MISTER_HOST --delay ${MENU_DELAY:-0.02}"

steps() { local n=$1 dx=$2 dy=$3 out=""; while [ "$n" -gt 0 ]; do out="$out mouse:$dx,$dy"; n=$((n-1)); done; echo "$out"; }
log()   { echo "[$(date +%H:%M:%S)] $*"; }

case "${1:?verb}" in

open)
    TARGET=${2:?title center x}; SHOT=${3:-scripts/guest/menu_open.png}
    TOL=18
    $WS $(steps 60 -12 -12) >/dev/null 2>&1          # pin to top-left
    $WS $(steps 4 0 1) >/dev/null 2>&1               # down onto the bar
    $WS $(steps 12 1 0) >/dev/null 2>&1              # a little right of apple
    $WS mousebtn:left_down sleep:0.4 >/dev/null 2>&1
    # The px-per-event scale is MEASURED from what each move actually did
    # (start pessimistic at 4 px/event): a fixed damping oscillated View <->
    # Help for minutes on 2026-09-07 because the scale was nowhere near 2.
    scale=400; prev=-1; sent=0
    for attempt in $(seq 1 20); do
        bash scripts/grab_fresh.sh "$SHOT" >/dev/null 2>&1
        read -r st a b <<<"$(python scripts/menubar_probe.py "$SHOT")"
        if [ "$st" != "OPEN" ]; then
            log "no menu open ($st) — stepping right 2"
            prev=-1; sent=0
            $WS $(steps 2 1 0) >/dev/null 2>&1
            continue
        fi
        # menubar_probe prints: OPEN <left> <right>  (the title's column span)
        L=$a; R=$b
        C=$(( (L + R) / 2 ))
        if [ "$prev" -ge 0 ] && [ "$sent" -gt 1 ]; then
            moved=$(( C - prev )); am=${moved#-}
            [ "$am" -gt 0 ] && scale=$(( am * 100 / sent ))
            [ "$scale" -lt 50 ] && scale=50; [ "$scale" -gt 900 ] && scale=900
        fi
        err=$(( TARGET - C ))
        aerr=${err#-}
        if [ "$aerr" -le "$TOL" ]; then
            log "open title center=$C left=$L (target $TARGET)"
            echo "TITLE_LEFT=$L"
            exit 0
        fi
        n=$(( aerr * 100 / scale / 2 )); [ "$n" -lt 1 ] && n=1; [ "$n" -gt 40 ] && n=40
        prev=$C; sent=$n
        if [ "$err" -gt 0 ]; then
            log "center=$C target=$TARGET scale=$scale — stepping right $n"; $WS $(steps "$n" 1 0) >/dev/null 2>&1
        else
            log "center=$C target=$TARGET scale=$scale — stepping left $n";  $WS $(steps "$n" -1 0) >/dev/null 2>&1
        fi
    done
    log "could not land on target — cancelling"
    $WS $(steps 40 0 -1) mousebtn:left_up >/dev/null 2>&1
    exit 3 ;;

item)
    TL=${2:?title left x}; TY=${3:?target y}; SHOT=${4:-scripts/guest/menu_item.png}
    $WS $(steps 12 0 1) >/dev/null 2>&1              # get inside the panel
    seen=0
    for attempt in $(seq 1 30); do
        bash scripts/grab_fresh.sh "$SHOT" >/dev/null 2>&1
        probe=$(python scripts/menuitem_probe.py "$SHOT" "$TL")
        case "$probe" in
            ITEM*)
                seen=1
                band=${probe#*band=[}; band=${band%%]*}
                y0=${band%%,*}; y1=${band##*,}
                mid=$(( (y0 + y1) / 2 ))
                if [ "$TY" -ge "$y0" ] && [ "$TY" -le "$y1" ]; then
                    log "row [$y0,$y1] covers target y=$TY"
                    exit 0
                fi
                d=$(( TY - mid )); ad=${d#-}
                n=$(( ad / 3 )); [ "$n" -lt 1 ] && n=1; [ "$n" -gt 12 ] && n=12
                if [ "$d" -gt 0 ]; then
                    log "row mid=$mid target=$TY — down $n"; $WS $(steps "$n" 0 1) >/dev/null 2>&1
                else
                    log "row mid=$mid target=$TY — up $n";   $WS $(steps "$n" 0 -1) >/dev/null 2>&1
                fi ;;
            NOITEM*)
                if [ "$seen" = 1 ]; then log "past the last row — up 1"; $WS mouse:0,-1 >/dev/null 2>&1
                else log "not in the panel yet — down 3"; $WS $(steps 3 0 1) >/dev/null 2>&1; fi ;;
            *)
                log "menu vanished ($probe)"; exit 3 ;;
        esac
    done
    log "could not reach y=$TY"; exit 3 ;;

release) $WS mousebtn:left_up >/dev/null 2>&1 ;;
cancel)  $WS $(steps 60 0 -1) mousebtn:left_up >/dev/null 2>&1 ;;
*) echo "unknown verb $1" >&2; exit 2 ;;
esac
