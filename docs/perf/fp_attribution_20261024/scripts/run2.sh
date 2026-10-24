#!/bin/bash
# fp_attribution 2026-10-24, second pass:
#  - the dual-core bench gets the FPU background-wait accounting (patch_tb_fpw.py
#    on the scratch copy of tb_ap68040.sv) and is rebuilt;
#  - the matrix-multiply and FFT images are built at REPS 2 and 4 instead of 1 and
#    2 (vbcc unrolls a REPS=1 loop away, which shifts the code after it and spoils
#    the per-address differencing); Whetstone stays at LOOPS 2 and 4;
#  - every image runs on both benches with +pcprof; logs, assembly and binaries in out2/.
set -e
export VBCC=$HOME/opt/vbcc
export PATH=$HOME/opt/verilator-5.052/bin:$PATH
B=$HOME/mister/q800_fpattr_20261024
TB=$B/rtl/ap68040_faster/tb
OUT=$B/out2
NEW=$B/new_quadra/obj_prog/tb_ap68040
OLD=$B/old32/obj/tb_wombat_prog
mkdir -p $OUT
cd $TB
[ -f tb_ap68040.sv.orig ] || cp tb_ap68040.sv tb_ap68040.sv.orig
python3 $B/kernels/patch_tb_fpw.py tb_ap68040.sv.orig tb_ap68040.sv
rm -rf $B/new_quadra/obj_prog
date; $B/build_sims.sh new; date
export ASFLAGS=-DCOPYBACK
for n in 2 4; do
	cc -O0 -DHOST -DLOOPS=$n -o build/whet_host c/whet.c -lm
	./build/whet_host > build/whet_ref.h
	CDEFS=-DLOOPS=$n SUFFIX=_$n ./build_c.sh whet > /dev/null
done
for n in 20 40; do for r in 2 4; do
	CDEFS="-DN=$n -DREPS=$r" SUFFIX=_${n}_r$r ./build_c.sh fpmm > /dev/null
done; done
for r in 2 4; do
	CDEFS="-DN=20 -DREPS=$r -DREGACC" SUFFIX=_20reg_r$r ./build_c.sh fpmm > /dev/null
done
for n in 256 1024; do for r in 2 4; do
	CDEFS="-DN=$n -DREPS=$r" SUFFIX=_${n}_r$r ./build_c.sh fft > /dev/null
done; done
IMAGES="whet_2 whet_4 fpmm_20_r2 fpmm_20_r4 fpmm_40_r2 fpmm_40_r4 fpmm_20reg_r2 fpmm_20reg_r4 fft_256_r2 fft_256_r4 fft_1024_r2 fft_1024_r4"
ls -la build/whet_?.bin build/fpmm_*_r?.bin build/fft_*_r?.bin
date
for img in $IMAGES; do
	( $NEW +prog=build/$img.hex +pcprof +prof +timeout=400000000 > $OUT/$img.new.log 2>&1 || true ) &
	( $OLD +prog=build/$img.hex +pcprof +latency=0 +timeout=400000000 > $OUT/$img.old.log 2>&1 || true ) &
done
wait
date
for f in $OUT/*.log; do
	printf "%-24s %s\n" "$(basename $f)" "$(grep -E '^(PASS|FAIL)' $f | head -1 | cut -c1-140)"
done
cp build/whet_?.s build/fpmm_*_r?.s build/fft_*_r?.s build/whet_?.bin build/fpmm_*_r?.bin build/fft_*_r?.bin $OUT/
cp tb_ap68040.sv $OUT/tb_ap68040_patched.sv
echo RUN2_DONE
