#!/bin/bash
# Mirror the Main fork's CD-ROM response builders and playhead into
# verilator/sim/mac/ so the sims compile the very code the box runs
# (sim/cd_window.cpp includes them).  The mirror is gitignored; run this
# (sim_wsl.sh build and cd_resp_golden.sh do) whenever ../Main_MiSTer changes.
set -e
HERE=$(cd "$(dirname "$0")/.." && pwd)
MAIN=${MAIN:-$HERE/../Main_MiSTer}
DST="$HERE/verilator/sim/mac"
mkdir -p "$DST"
for f in mac_cdrom_resp.h mac_cdrom_resp.cpp mac_cdrom_play.h mac_cdrom_play.cpp; do
	cp -p "$MAIN/support/mac/$f" "$DST/$f"
done
git -C "$MAIN" log --oneline -1 > "$DST/MAIN_COMMIT" 2>/dev/null || true
echo "verilator/sim/mac <- $MAIN/support/mac ($(cat "$DST/MAIN_COMMIT"))"
