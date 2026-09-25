#!/usr/bin/env bash
# cpu_gates_wsl.sh -- the CPU-only simulation gates for an AP68040 tree, run
# inside WSL (Verilator 5.020, iverilog/vvp/vasm from ~/local/bin).
#
#   wsl.exe -e bash -lc 'bash /mnt/c/.../scripts/cpu_gates_wsl.sh <ap68040 dir> <label>'
#
# Copies the tree to ~/ap040_<label> (CRLF stripped), then runs
#   1. the AP68040 self-test suite (tb/run_tests.sh, 11 benches),
#   2. bench_loop with the per-state profile (phase 0/1 cycle counts),
#      and pipe_bench (BSR/RTS, LINK/UNLK, MOVEM, forward Bcc; S_FETCH/DECODE/MRD/MWR
#      of phase 0 printed: step 1 149182, redirect hints 147682, in-place pops 137684),
#      and branch_bench (BSR.W/JSR abs.L/JSR d16(PC)/BRA.W/JMP abs.L with the JSR (An)
#      and Bcc.W controls; before the early redirect 129778, with it 118784),
#   3. the first-100 silicon corpus gate (scripts/cpu_corpus100_gate.sh):
#      "CORPUS DONE in N cycles" and "REAL diffs: 0".
# A pure area/code optimisation must leave every cycle count unchanged
# (checkpoint 15: bench_loop 94368 / 95166, corpus 33335739).
set -u
SRC="${1:?ap68040 dir}"; LABEL="${2:?label}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$HOME/local/bin:$PATH"
W="$HOME/ap040_$LABEL"
rm -rf "$W"; mkdir -p "$W"
rsync -a --exclude .git "$SRC/" "$W/"
find "$W" -type f \( -name "*.sh" -o -name "*.v" -o -name "*.sv" -o -name "*.svh" -o -name "*.s" -o -name "*.py" \) -exec sed -i 's/\r$//' {} +
echo "== AP suite ($LABEL)"
( cd "$W/tb" && bash run_tests.sh > "$W/tests.log" 2>&1 )
grep -E "pass|FAIL|ALL TESTS|FAILURES" "$W/tests.log" | sed 's/^/   /'
echo "== bench_loop ($LABEL)"
( cd "$W/tb" && vvp build/tb_prog.vvp +prog=build/bench_loop.hex +prof +memlat > "$W/bench.log" 2>&1 )
grep -E "phase . passed|TESTS" "$W/bench.log" | sed 's/^/   /'
echo "== pipe_bench ($LABEL)"
( cd "$W/tb" && vvp build/tb_prog.vvp +prog=build/pipe_bench.hex +prof +memlat > "$W/pipe.log" 2>&1 )
grep -E "phase . passed|FAIL" "$W/pipe.log" | sed 's/^/   /'
grep -E "PROF   state (3|4|9|10):" "$W/pipe.log" | head -4 | sed 's/^/   /'
echo "== branch_bench ($LABEL)"
( cd "$W/tb" && vvp build/tb_prog.vvp +prog=build/branch_bench.hex +prof +memlat > "$W/branch.log" 2>&1 )
grep -E "phase . passed|FAIL" "$W/branch.log" | sed 's/^/   /'
grep -E "PROF   state (3|4|9|10|51|52|55|56|57):" "$W/branch.log" | head -9 | sed 's/^/   /'
echo "== corpus gate ($LABEL)"
sed -i 's/\r$//' "$REPO/scripts/cpu_corpus100_gate.sh"
bash "$REPO/scripts/cpu_corpus100_gate.sh" "$W/rtl" "$REPO/scripts/fixtures/corpus100/cpu.hex" "$REPO/scripts/fixtures/corpus100/results.bin" > "$W/gate.log" 2>&1
grep -E "CORPUS DONE|REAL diffs|^PASS|^FAIL|rows:" "$W/gate.log" | sed 's/^/   /'
