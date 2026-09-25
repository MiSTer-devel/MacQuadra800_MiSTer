#!/bin/bash
# run_corpus.sh — build a bench payload, simulate it against the AP68040
# core, extract the JSONL results and score them against the Quadra 800
# hardware capture.
#
#   usage: run_corpus.sh [cpu|fpu|saverestore|integration]   (default cpu)
#
#   SIM           iverilog (default) or verilator
#   AP68040_RTL   path to the core rtl/ (default: the rtl/ap68040 submodule)
#   CDEFS         forwarded to make (e.g. -DLAST_TEST_INDEX=9 for smoke)
#   ORACLE        capture to score against (default per suite)
set -euo pipefail
cd "$(dirname "$0")"

SUITE="${1:-cpu}"
SIM="${SIM:-iverilog}"
RTL="${AP68040_RTL:-$(cd ../../.. && pwd)/rtl/ap68040/rtl}"
IVERILOG="${IVERILOG:-$HOME/.local/bin/iverilog}"
VVP="${VVP:-$HOME/.local/bin/vvp}"
VERILATOR="${VERILATOR:-$HOME/.local/bin/verilator}"
WORK=build

case "$SUITE" in
    cpu)         DEF_ORACLE=../../results/cpu/hardware_quadra800_2026-08-28.jsonl ;;
    fpu)         DEF_ORACLE=../../results/fpu/hardware_quadra800_2026-08-28.jsonl ;;
    saverestore) DEF_ORACLE=../../results/cpu_fpu/hardware_saverestore_2026-08-28.jsonl ;;
    integration) DEF_ORACLE=../../results/cpu_fpu/hardware_quadra800_2026-08-28.jsonl ;;
    mmu)         DEF_ORACLE=../../results/mmu/hardware_full_quadra800_2026-08-28.jsonl ;;
    *) echo "unknown suite $SUITE"; exit 1 ;;
esac
ORACLE="${ORACLE:-$DEF_ORACLE}"
PAYLOAD="$WORK/payload_${SUITE}_sim.bin"

[[ -d "$RTL" ]] || { echo "AP68040 rtl not found at $RTL"; exit 1; }
# CDEFS is not a make dependency (the finding-23 footgun): always rebuild
# the corpus-bearing objects so a narrowed smoke build cannot go stale.
rm -f "$WORK"/bench_main.o "$WORK"/fpu_bench_main.o \
      "$WORK"/cpu_fpu_bench_main.o "$WORK"/cpu_fpu_save_restore_bench_main.o \
      "$WORK"/mmu_bench_main_full.o
make payloads CDEFS="${CDEFS:-}"

# hex image: reset vectors @0 (SP=$80000, PC=$40000), payload @$40000
python3 - "$PAYLOAD" "$WORK/$SUITE.hex" <<'PY'
import sys
data = open(sys.argv[1], "rb").read()
if len(data) % 2: data += b"\0"
with open(sys.argv[2], "w") as out:
    out.write("@0\n0008 0000 0004 0000\n")          # SP $80000, PC $40000
    out.write("@20000\n")                            # word address of $40000
    for i in range(0, len(data), 2):
        out.write("%02x%02x\n" % (data[i], data[i+1]))
PY

SRC="$RTL/ap040_tg68k_compat.v $RTL/ap040_core.v $RTL/ap040_bus16_adapter.v \
     $RTL/ap040_bus_timeout.v $RTL/ap040_regfile.v $RTL/ap040_alu.v \
     $RTL/ap040_muldiv.v $RTL/ap040_mmu.v $RTL/ap040_cache.v $RTL/ap040_fpu.v \
     $RTL/ap040_walker_cdc.v $RTL/primitives/dpram.v"

if [[ "$SIM" == verilator ]]; then
    "$VERILATOR" --binary --timing -j 8 -Wno-fatal -Wno-BLKLOOPINIT --top-module tb_corpus \
        -Mdir "$WORK/obj_$SUITE" -I"$RTL" tb_corpus.v $SRC \
        > "$WORK/verilate_$SUITE.log" 2>&1 || { tail -20 "$WORK/verilate_$SUITE.log"; exit 1; }
    stdbuf -oL "$WORK/obj_$SUITE/Vtb_corpus" +prog="$WORK/$SUITE.hex" \
        +results="$WORK/results_$SUITE.bin" \
        ${MAXCYCLES:+"+maxcycles=$MAXCYCLES"} | tee "$WORK/run_$SUITE.log"
else
    "$IVERILOG" -g2012 -I "$RTL" -o "$WORK/tb_corpus.vvp" tb_corpus.v $SRC
    stdbuf -oL "$VVP" "$WORK/tb_corpus.vvp" +prog="$WORK/$SUITE.hex" \
           +results="$WORK/results_$SUITE.bin" \
           ${MAXCYCLES:+"+maxcycles=$MAXCYCLES"} | tee "$WORK/run_$SUITE.log"
fi
grep -q "CORPUS DONE" "$WORK/run_$SUITE.log" || { echo "simulation did not finish"; exit 1; }

python3 - "$WORK/results_$SUITE.bin" "$WORK/results_$SUITE.jsonl" <<'PY'
import sys
raw = open(sys.argv[1], "rb").read().replace(b"\0", b"")
rows = [l for l in raw.split(b"\n") if l[:1] == b"{"]
open(sys.argv[2], "wb").write(b"\n".join(rows) + (b"\n" if rows else b""))
print(f"{len(rows)} result rows")
PY

# --flat-env: this is the bare flat-RAM TB (finding 32); machine runs score strictly
python3 ../../gen/score_vs_oracle.py "$SUITE" "$ORACLE" "$WORK/results_$SUITE.jsonl" --flat-env
