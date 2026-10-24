#!/bin/bash
# fp_attribution 2026-10-24, third pass: re-patch the dual-core bench (the
# background-operation address is now the last FPU uop that left EX), rebuild it
# and rerun the twelve images on the dual core only (the old-core logs in out2/
# stand).  The images are the ones run2.sh built.
set -e
export PATH=$HOME/opt/verilator-5.052/bin:$PATH
B=$HOME/mister/q800_fpattr_20261024
TB=$B/rtl/ap68040_faster/tb
OUT=$B/out2
NEW=$B/new_quadra/obj_prog/tb_ap68040
cd $TB
python3 $B/kernels/patch_tb_fpw.py tb_ap68040.sv.orig tb_ap68040.sv
rm -rf $B/new_quadra/obj_prog
date; $B/build_sims.sh new; date
IMAGES="whet_2 whet_4 fpmm_20_r2 fpmm_20_r4 fpmm_40_r2 fpmm_40_r4 fpmm_20reg_r2 fpmm_20reg_r4 fft_256_r2 fft_256_r4 fft_1024_r2 fft_1024_r4"
for img in $IMAGES; do
	( $NEW +prog=build/$img.hex +pcprof +prof +timeout=400000000 > $OUT/$img.new.log 2>&1 || true ) &
done
wait
date
for f in $OUT/*.new.log; do
	printf "%-24s %s %s\n" "$(basename $f)" "$(grep -E '^(PASS|FAIL)' $f | head -1 | cut -c1-100)" "$(grep PCFPW_LOST $f)"
done
cp tb_ap68040.sv $OUT/tb_ap68040_patched.sv
echo RUN3_DONE
