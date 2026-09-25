#!/bin/bash
# Run the oracle-checked Speedometer 4.02 kernel fixtures against one RTL tree
# and print one line per kernel.  Each fixture executes the unchanged
# Speedometer machine code through wombat_cpu (cache, MMU, store buffer,
# pipeline; production macros) on a controlled-latency RAM model, checks the
# result against an independent Python oracle, and requires a corrupted copy
# to fail.  Cycle counts compare CPU variants; they are not Mix scores.
#
# usage: scripts/cpu/speedometer_suite.sh <tree> [out-dir] [latency]
#   <tree>   a directory holding rtl/ (e.g. `git archive HEAD rtl | tar -x -C <tree>`);
#            never point it at the live checkout while someone edits rtl/.
#   out-dir  default scratch/suite_<tree-basename>
#   latency  RAM latency, default 3
#
# Whetstone, Dhrystone, Permutations and Queens still run from their own
# runners (scratch/p179_ea_decode_20260922/run_*.py, profile_*.py) and are
# not covered here.
set -u
R=$(cd "$(dirname "$0")/../.." && pwd)
tree=$(cd "$1" && pwd)
out=${2:-$R/scratch/suite_$(basename "$tree")}
lat=${3:-3}
res="/home/alans/mister/MacQuadra800_fixtures/Speedometer 4.02.rsrc"
mkdir -p "$out"
[ -d "$tree/rtl/ap68040/tb" ] || git -C "$R" archive HEAD rtl/ap68040/tb | tar -x -C "$tree"

run() {  # name, command...
	local n=$1; shift
	( "$@" > "$out/$n.log" 2>&1; echo "EXIT $?" >> "$out/$n.log" ) &
}
run towers python3 "$R/scripts/cpu/profile_towers.py" "$res" --out "$out/towers" --rtl-root "$tree/rtl" --latencies "$lat" --negative-control
run puzzle python3 "$R/scripts/cpu/profile_puzzle.py" "$res" --out "$out/puzzle" --rtl-root "$tree" --latencies "$lat"
run quick  python3 "$R/scripts/cpu/profile_quick_v2.py" "$res" --out "$out/quick" --rtl-root "$tree" --latencies "$lat"
run matrix python3 "$R/scripts/cpu/profile_matrix_v2.py" "$res" --out "$out/matrix" --rtl-root "$tree" --latencies "$lat"
run sieve  python3 "$R/scripts/cpu/profile_sieve_v2.py" "$res" --out "$out/sieve" --rtl-root "$tree" --latencies "$lat"
run bubble python3 "$R/scripts/cpu/profile_bubble_v2.py" "$res" --out "$out/bubble" --rtl-root "$tree" --latencies "$lat"
wait
fail=0
for n in towers puzzle quick matrix sieve bubble; do
	line=$(grep -h -m1 "^FIXTURE $n PASS" "$out/$n.log")
	ctl=$(grep -h -m1 -i -E 'fail(ed)?[- ]as[- ]required' "$out/$n.log")
	if [ -n "$line" ] && [ -n "$ctl" ] && grep -q '^EXIT 0' "$out/$n.log"; then
		echo "$line" | sed 's/ wall=.*//'
	else
		echo "FIXTURE $n FAIL (see $out/$n.log)"; fail=1
	fi
done
exit $fail
