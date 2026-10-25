#!/bin/bash
# fp_store_changes 2026-10-24: the core-level differential test.  N random FP
# store programs (scripts/fpdiff_gen.py) run on the base tree's probed bench
# and on <tree>'s; both must PASS and their memory dumps ($40000-$7E000: the
# data buffer with FPSR/FPIAR after every command, the predecrement area, the
# exception log) must be identical.  Results in fpdiff/<tree>/.
# usage: run_fpdiff.sh <tree> [first seed] [count] [commands per program]
set -e
T=$1; S0=${2:-1}; N=${3:-14}; NC=${4:-1500}
R=$HOME/mister/q800_fpchg_20261024
FS=$R/scripts
OUT=$R/fpdiff/$T
BASE=$R/base/obj_fs/obj_prog/tb_ap68040
NEW=$R/$T/obj_fs/obj_prog/tb_ap68040
mkdir -p $OUT
cd $OUT
fail=0
for s in $(seq $S0 $((S0 + N - 1))); do
	python3 $FS/fpdiff_gen.py $s p$s.s $NC > /dev/null
	$HOME/opt/vbcc/bin/vasmm68k_mot -quiet -Fbin -m68040 -no-opt -o p$s.bin p$s.s
	python3 $R/base/rtl/ap68040_faster/tb/bin2hex.py p$s.bin p$s.hex
	( $BASE +prog=p$s.hex +memdump=$OUT/p$s.base.dump +timeout=20000000 > p$s.base.log 2>&1 || true ) &
	( $NEW  +prog=p$s.hex +memdump=$OUT/p$s.new.dump  +timeout=20000000 > p$s.new.log 2>&1 || true ) &
	wait
	rb=$(grep -E "^(PASS|FAIL)" p$s.base.log | head -1 | cut -c1-60)
	rn=$(grep -E "^(PASS|FAIL)" p$s.new.log | head -1 | cut -c1-60)
	nx=$(python3 - p$s.base.dump <<'EOF'
import sys
n=0
for l in open(sys.argv[1]):
    a,v=l.split()
    if 0x7C000 <= int(a,16) < 0x7E000 and v != "00000000": n+=1
print(n*4//6)
EOF
)
	if cmp -s p$s.base.dump p$s.new.dump && [[ "$rb" == PASS* ]] && [[ "$rn" == PASS* ]]; then
		echo "seed $s: SAME ($NC commands, ~$nx exceptions logged) | $rb | $rn"
	else
		echo "seed $s: DIFFER | $rb | $rn"; fail=1
		cmp p$s.base.dump p$s.new.dump | head -2
	fi
done | tee summary.txt
grep -q DIFFER $OUT/summary.txt && { echo FPDIFF_FAILURES; exit 1; }
echo FPDIFF_ALL_SAME
