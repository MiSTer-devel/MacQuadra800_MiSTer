#!/bin/bash
# fp_attribution 2026-10-24: build the kernel images (vbcc -O=1023 -cpu=68040
# -fpu=68040, crt0 -DCOPYBACK: user mode, copyback data) and run each on both
# benches with +pcprof.  Two iteration counts per kernel; fpattr.py differences
# them.  Logs, the compiler's assembly and the linked binaries land in out/.
set -e
export VBCC=$HOME/opt/vbcc
B=$HOME/mister/q800_fpattr_20261024
TB=$B/rtl/ap68040_faster/tb
OUT=$B/out
NEW=$B/new_quadra/obj_prog/tb_ap68040
OLD=$B/old32/obj/tb_wombat_prog
mkdir -p $OUT
cp $B/kernels/fpmm.c $B/kernels/fft.c $TB/c/
cd $TB
export ASFLAGS=-DCOPYBACK
# Whetstone: the host reference values, then the images at LOOPS 2 and 4
for n in 2 4; do
	cc -O0 -DHOST -DLOOPS=$n -o build/whet_host c/whet.c -lm
	./build/whet_host > build/whet_ref.h
	CDEFS=-DLOOPS=$n SUFFIX=_$n ./build_c.sh whet > /dev/null
done
# matrix multiply (doubles in memory) 20x20 and 50x50, the register-accumulator
# variant at 20x20, and the FFT at 256 and 1024 points, each at REPS 1 and 2
for n in 20 50; do for r in 1 2; do
	CDEFS="-DN=$n -DREPS=$r" SUFFIX=_${n}_r$r ./build_c.sh fpmm > /dev/null
done; done
for r in 1 2; do
	CDEFS="-DN=20 -DREPS=$r -DREGACC" SUFFIX=_20reg_r$r ./build_c.sh fpmm > /dev/null
done
for n in 256 1024; do for r in 1 2; do
	CDEFS="-DN=$n -DREPS=$r" SUFFIX=_${n}_r$r ./build_c.sh fft > /dev/null
done; done
IMAGES="whet_2 whet_4 fpmm_20_r1 fpmm_20_r2 fpmm_50_r1 fpmm_50_r2 fpmm_20reg_r1 fpmm_20reg_r2 fft_256_r1 fft_256_r2 fft_1024_r1 fft_1024_r2"
ls -la build/*.hex
for i in $(seq 1 240); do [ -x $NEW ] && [ -x $OLD ] && break; sleep 5; done
[ -x $NEW ] || { echo "no $NEW"; exit 1; }
[ -x $OLD ] || { echo "no $OLD"; exit 1; }
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
cp build/whet_?.s build/fpmm_*.s build/fft_*.s build/whet_?.bin build/fpmm_*.bin build/fft_*.bin $OUT/
echo RUN_DONE
