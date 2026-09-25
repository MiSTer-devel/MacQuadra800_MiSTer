#!/usr/bin/env bash
# Reuse the immutable first-100 payload; NEVER rebuild it with a host toolchain.
# Local simulation only. No FPGA, source edits, cleanup, or accepted-default changes.
set -euo pipefail
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
if [[ $# -ne 3 ]]; then
    echo "Usage: bash scripts/cpu_corpus100_gate.sh RTL_DIR PAYLOAD_HEX BASELINE_RESULTS" >&2
    exit 2
fi
rtl=$(realpath "$1")
payload=$(realpath "$2")
baseline=$(realpath "$3")
tb="$repo/scripts/fixtures/tb_cpu_corpus100.v"
verilator=${CPU_GATE_VERILATOR:-$(command -v verilator)}
[[ -x "$verilator" && -r "$payload" && -r "$baseline" && -r "$tb" ]] || {
    echo 'Missing executable or input fixture.' >&2; exit 2;
}
expected_payload=989ba287ef21d1bfa1c50099b7592af601495aa656ed3494e057243714c1a3fa
expected_tb=b882b14a13e22dbb614044faf1aeb508685fae131b4d1a21836bf798458e898f
[[ $(sha256sum "$payload" | cut -d' ' -f1) == "$expected_payload" ]] || {
    echo 'Payload differs from the established immutable comparison fixture.' >&2; exit 2;
}
[[ $(sha256sum "$tb" | cut -d' ' -f1) == "$expected_tb" ]] || {
    echo 'First-100 testbench identity changed; review before testing.' >&2; exit 2;
}
sources=()
for unit in ap040_tg68k_compat ap040_core ap040_bus16_adapter ap040_bus_timeout \
            ap040_regfile ap040_alu ap040_muldiv ap040_mmu ap040_cache ap040_fpu \
            ap040_walker_cdc primitives/dpram; do
    [[ -r "$rtl/$unit.v" ]] || { echo "Missing RTL: $rtl/$unit.v" >&2; exit 2; }
    sources+=("$rtl/$unit.v")
done
extra_flags=()
if [[ ${CPU_GATE_PIPELINE_COMPARE:-0} == 1 ]]; then
    [[ ${CPU_GATE_PIPELINE:-0} == 1 ]] || { echo "Compare requires CPU_GATE_PIPELINE=1" >&2; exit 2; }
    extra_flags+=(-DAP040_PIPELINE_COMPARE)
fi
if [[ ${CPU_GATE_PIPELINE_EARLY_DRAIN:-0} == 1 ]]; then
    [[ ${CPU_GATE_PIPELINE:-0} == 1 ]] || { echo "Early drain requires CPU_GATE_PIPELINE=1" >&2; exit 2; }
    extra_flags+=(-DAP040_PIPELINE_EARLY_DRAIN)
fi
if [[ ${CPU_GATE_PIPELINE_MEMORY_ENTRY:-0} == 1 ]]; then
    [[ ${CPU_GATE_PIPELINE_P6:-0} == 1 ]] || { echo "Memory entry requires CPU_GATE_PIPELINE_P6=1" >&2; exit 2; }
    extra_flags+=(-DAP040_PIPELINE_MEMORY_ENTRY)
fi
if [[ ${CPU_GATE_PIPELINE_P6:-0} == 1 ]]; then
    [[ ${CPU_GATE_PIPELINE:-0} == 1 ]] || { echo "P6 requires CPU_GATE_PIPELINE=1" >&2; exit 2; }
    extra_flags+=(-DAP040_EXPERIMENTAL_PIPELINE_P6)
fi
if [[ ${CPU_GATE_PIPELINE_PEA:-0} == 1 ]]; then
    [[ ${CPU_GATE_PIPELINE:-0} == 1 ]] || { echo "Pipeline PEA requires CPU_GATE_PIPELINE=1" >&2; exit 2; }
    extra_flags+=(-DAP040_EXPERIMENTAL_PIPELINE_PEA)
fi
if [[ ${CPU_GATE_PIPELINE_PEA_ENTRY_ONLY:-0} == 1 ]]; then
    [[ ${CPU_GATE_PIPELINE_PEA:-0} == 1 ]] || { echo "PEA entry policy requires CPU_GATE_PIPELINE_PEA=1" >&2; exit 2; }
    extra_flags+=(-DAP040_PIPELINE_PEA_ENTRY_ONLY)
fi
if [[ ${CPU_GATE_PIPELINE_STORES:-0} == 1 ]]; then
    [[ ${CPU_GATE_PIPELINE:-0} == 1 ]] || { echo "Pipeline stores require CPU_GATE_PIPELINE=1" >&2; exit 2; }
    extra_flags+=(-DAP040_EXPERIMENTAL_PIPELINE_STORES)
fi
if [[ ${CPU_GATE_PIPELINE_LOADS:-0} == 1 ]]; then
    [[ ${CPU_GATE_PIPELINE:-0} == 1 ]] || { echo "Pipeline loads require CPU_GATE_PIPELINE=1" >&2; exit 2; }
    extra_flags+=(-DAP040_EXPERIMENTAL_PIPELINE_LOADS)
fi
if [[ ${CPU_GATE_LEA:-0} == 1 ]]; then
    extra_flags+=(-DAP040_EXPERIMENTAL_LEA)
fi
if [[ ${CPU_GATE_XSTORE:-0} == 1 ]]; then
    extra_flags+=(-DAP040_EXPERIMENTAL_XSTORE)
fi
if [[ ${CPU_GATE_PIPELINE:-0} == 1 ]]; then
    pipeline="$rtl/../experimental/ap040_pipeline_integer.sv"
    [[ -r "$pipeline" ]] || { echo "Missing experimental pipeline: $pipeline" >&2; exit 2; }
    extra_flags+=(-DAP040_EXPERIMENTAL_PIPELINE)
    sources+=("$pipeline")
fi
out=$(mktemp -d /tmp/cpu-corpus100-gate.XXXXXX)
echo "ARTIFACT_DIR=$out"
sha256sum "${sources[@]}" "$payload" "$tb" "$baseline" | tee "$out/identities.txt"
"$verilator" --binary --timing --build-jobs 8 -Wno-fatal -Wno-BLKLOOPINIT --top-module tb_corpus \
    -Mdir "$out/obj" -I"$rtl" "${extra_flags[@]}" "$tb" "${sources[@]}" > "$out/compile.log" 2>&1 || {
    tail -40 "$out/compile.log"; exit 1;
}
stdbuf -oL "$out/obj/Vtb_corpus" "+prog=$payload" "+results=$out/results.bin" \
    +maxcycles=100000000 | tee "$out/run.log"
# The Verilog testbench uses $finish for failures too: exit zero alone is insufficient.
if grep -qE 'FAIL:|dumping partial results' "$out/run.log" ||
   ! grep -qE 'CORPUS DONE in [0-9]+ cycles' "$out/run.log"; then
    echo "FAIL: incomplete simulation; inspect $out/run.log" >&2; exit 1
fi
python3 "$repo/SingleStepTests/gen/score_vs_oracle.py" cpu "$baseline" \
    "$out/results.bin" --flat-env | tee "$out/score.log"
grep -qE '^100 rows:' "$out/score.log" || {
    echo 'FAIL: comparison did not cover exactly 100 complete records.' >&2; exit 1;
}
echo "PASS: first-100 comparison only, not the full corpus. Artifacts: $out"
