#!/bin/bash
# The VIA1 Timer 2 lost-interrupt bench against rtl/via6522.sv (iverilog, WSL).
#   wsl.exe -d Ubuntu-24.04 -e bash -lc \
#     'bash /mnt/c/Temp/mistercore/MacQuadra800_MiSTer/docs/resume-20261001/run_via_t2_race.sh'
# 2026-10-01 result on the unfixed via6522.sv: rows A (IFR write $02 on the
# timeout's E clock) and C (T2C-L read on it) print LOST; baseline, B and D set.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
SRCROOT=${1:-$(cd "$HERE/../.." && pwd)}
export PATH=$HOME/local/bin:$PATH
W=${W:-$HOME/viat2}; rm -rf "$W"; mkdir -p "$W"; cd "$W"
tr -d '\r' < "$SRCROOT/rtl/via6522.sv" > via6522.sv
tr -d '\r' < "$HERE/tb_via_t2_race.v" > tb.v
iverilog -g2012 -o t.vvp tb.v via6522.sv && vvp t.vvp | grep -v "ORA WRITE\|  E:"
