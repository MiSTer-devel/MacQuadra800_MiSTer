#!/bin/bash
# Golden-bytes test of Main's AppleCD response builders (../Main_MiSTer/
# support/mac/mac_cdrom_resp.cpp + mac_cdrom_play.cpp) against the RTL:
# the host test writes one MCDA blob per TOC shape, verilator/
# tb_cd_audio_dump feeds each to rtl/cd_audio.sv and dumps the three
# response tables it builds, and the test compares the builders' tables
# byte for byte, checks the volume law against scratch/cd_resp_golden/cd_vol_lut.vh and runs
# the playhead unit tests.  Run from WSL (Verilator + g++ live there):
#   wsl.exe -e bash -lc 'bash /mnt/c/Temp/mistercore/MacQuadra800_MiSTer/scripts/cd_resp_golden.sh'
set -e
HERE=$(cd "$(dirname "$0")/.." && pwd)
MAIN=${MAIN:-$HERE/../Main_MiSTer}
OUT=${OUT:-$HERE/scratch/cd_resp_golden}
mkdir -p "$OUT"

bash "$HERE/scripts/sync_main_mac.sh"
echo "== host test build"
g++ -O1 -Wall -Wextra -o "$OUT/cdrom_resp_test" \
    "$MAIN/support/mac/test/cdrom_resp_test.cpp" \
    "$MAIN/support/mac/mac_cdrom_resp.cpp" "$MAIN/support/mac/mac_cdrom_play.cpp" -lm

echo "== blobs"
"$OUT/cdrom_resp_test" gen "$OUT"

echo "== RTL dumps (against the pre-phase-1 cd_audio.sv, the last that built the tables)"
git -C "$HERE" show c6f5ebf:rtl/cd_audio.sv > "$OUT/cd_audio_ref.sv"
git -C "$HERE" show c6f5ebf:rtl/cd_vol_lut.vh > "$OUT/cd_vol_lut.vh"     # the volume law it includes (left the RTL with phase 2)
(cd "$HERE/verilator" && make -s tb_cd_audio_dump >"$OUT/verilator_build.log" 2>&1) || { tail -30 "$OUT/verilator_build.log"; exit 1; }
for b in "$OUT"/*.blob.hex; do
	n=$(basename "$b" .blob.hex)
	"$HERE/verilator/obj_dir_tb/tb_cd_audio_dump" +blob="$b" +out="$OUT/$n.rtl.bin" | grep -v "^- " || true
done

echo "== compare + unit tests"
"$OUT/cdrom_resp_test" check "$OUT" "$HERE/scratch/cd_resp_golden/cd_vol_lut.vh"
