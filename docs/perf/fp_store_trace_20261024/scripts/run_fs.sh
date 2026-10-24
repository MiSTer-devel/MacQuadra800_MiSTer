#!/bin/bash
# fp_store_trace 2026-10-24: assemble kernels/fpstore.s, run it on both benches
# with +pcprof (the STAMP lines give each kernel's cycles), then capture the
# per-cycle trace of every kernel's second pass on both cores.  Logs in fs/out/.
set -e
B=$HOME/mister/q800_fpstore_20261024
FS=$B/fs
OUT=$FS/out
NEW=$B/new_quadra/obj_prog/tb_ap68040
OLD=$B/old32/obj/tb_wombat_prog
mkdir -p $OUT
cd $FS
$HOME/opt/vbcc/bin/vasmm68k_mot -quiet -Fbin -m68040 -no-opt -L $OUT/fpstore.lst -o $OUT/fpstore.bin kernels/fpstore.s
python3 $B/rtl/ap68040_faster/tb/bin2hex.py $OUT/fpstore.bin $OUT/fpstore.hex
ls -la $OUT/fpstore.bin
date
if [ -x $NEW ]; then
	$NEW +prog=$OUT/fpstore.hex +pcprof +timeout=4000000 > $OUT/new.log 2>&1 || true
	echo "--- dual core"; grep -E "^(STAMP|PASS|FAIL)" $OUT/new.log
fi
if [ -x $OLD ]; then
	$OLD +prog=$OUT/fpstore.hex +pcprof +latency=0 +timeout=4000000 > $OUT/old.log 2>&1 || true
	echo "--- shipping core"; grep -E "^(STAMP|PASS|FAIL)" $OUT/old.log
fi
# the second pass of each kernel starts at its even opening tag
for t in 0x20 0x30 0x40 0x50 0x60 0x70 0x80 0x90 0xA0 0xB0 0xC0 0xD0 0xE0 0xF0; do
	d=$((t))
	len=420
	case $t in 0x90|0xA0) len=700;; esac
	if [ -x $NEW ]; then
		( $NEW +prog=$OUT/fpstore.hex +fstag=$d +fslen=$len +timeout=4000000 > $OUT/new_trace_$t.log 2>&1 || true ) &
	fi
	if [ -x $OLD ]; then
		( $OLD +prog=$OUT/fpstore.hex +fstag=$d +fslen=$len +latency=0 +timeout=4000000 > $OUT/old_trace_$t.log 2>&1 || true ) &
	fi
done
wait
date
ls -la $OUT/*.log | wc -l
echo RUN_DONE
