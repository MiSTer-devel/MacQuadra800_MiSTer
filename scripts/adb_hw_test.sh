#!/usr/bin/env bash
# scripts/adb_hw_test.sh — the two ADB regressions, on hardware, as one command.
#
# 1. CLICK. Pin the cursor into the top-left corner so it sits on the Apple menu
#    title, then send a real button press. The menu must open on the press and
#    close on the release. Before the via6522 shift fix this did nothing at all,
#    because the button is bit 7 of ADB mouse Talk R0 byte 0 and every delivered
#    byte reached the driver shifted one place left -- docs/adb-via-shift.md.
#
#    The menu title is used rather than a desktop icon on purpose: it needs no
#    pixel calibration. Do NOT trust old pixel counts here -- motion used to
#    arrive with dy doubled ({dy[5:0],0}), so every geometry measured before the
#    fix (scripts/mac_shutdown.sh included) was calibrated against a corrupted
#    stream and now overshoots.
#
# 2. PHANTOM INPUT. Send 240 mouseMove messages and NOTHING else. That alone
#    used to open menus and fire keyboard shortcuts, because with the byte
#    shifted the guest read bit 6 of dy where the button belonged: any move with
#    dy >= 0 read as button-down. Afterwards the desktop must look untouched.
#
# mrext's button payloads are `left_down` / `left_up`. `mouseBtn:1` and
# `mouseBtn:0` are accepted by the websocket and logged in /tmp/remote.log but
# do nothing, which is an easy way to conclude "the button is broken" when it
# is not. Confirmed on 2026-08-30: 1/0 inert, left_down/left_up work.
#
# Shots land in scratch/adbhw_*.png; read them, the script cannot judge for you.
#
# Usage: bash scripts/adb_hw_test.sh
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1
[ -r scripts/local.env ] && . scripts/local.env
: "${MISTER_HOST:?set MISTER_HOST in scripts/local.env}"

# 0.02 s is the pacing that works; 0.008 s outruns the ~90 Hz ADB poll and the
# moves are silently dropped.
WS="python scripts/mister_ws.py --host $MISTER_HOST --delay 0.02"

steps() { local n=$1 dx=$2 dy=$3 out=""; while [ "$n" -gt 0 ]; do out="$out mouse:$dx,$dy"; n=$((n-1)); done; echo "$out"; }
shot()  { bash scripts/grab_fresh.sh "scratch/adbhw_$1.png" 2>&1 | tail -1; }
pause() { local n=0; until [ $n -ge "$1" ]; do n=$((n+1)); sleep 1; done; }

echo "== baseline =="
$WS mouse:1,0 mouse:-1,0 >/dev/null 2>&1     # wake any screensaver
pause 2; shot 0_baseline

echo "== 1. real button press on the Apple menu =="
$WS $(steps 60 -12 -12) >/dev/null 2>&1      # pin hard into the top-left corner
$WS $(steps 14 1 0) $(steps 4 0 1) >/dev/null 2>&1  # onto the apple (x~22,y~6)
pause 1; shot 1_hover
$WS mousebtn:left_down >/dev/null 2>&1
pause 2; shot 2_pressed
echo "   -> adbhw_2_pressed.png: the Apple menu must be OPEN."
$WS mousebtn:left_up >/dev/null 2>&1
pause 2; shot 3_released
echo "   -> adbhw_3_released.png: the menu must be CLOSED, nothing selected."

echo "== 2. 240 mouseMove messages, no button, no keys =="
$WS $(steps 120 1 1) $(steps 120 -1 -1) >/dev/null 2>&1
pause 2; shot 4_afterdrag
echo "   -> adbhw_4_afterdrag.png: no menu open, no dialog, nothing typed."
