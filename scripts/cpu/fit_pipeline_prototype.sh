#!/usr/bin/env bash
# Standalone feasibility fit only. Run as a systemd user unit for persistence.
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
quartus=${QUARTUS_BIN:-/home/alans/intelFPGA_lite/quartus/bin}
out=${1:-"$repo/scratch/pipeline_prototype/fit_clock_pin_v2"}
if pgrep -x 'quartus_(sh|map|fit|sta|asm)' >/dev/null; then
    echo 'Another Quartus flow is running; wait for it to finish.' >&2
    exit 1
fi
mkdir "$out"
out=$(realpath "$out")
cat > "$out/prototype.qpf" <<'EOF'
PROJECT_REVISION = "prototype"
EOF
cat > "$out/prototype.qsf" <<EOF
set_global_assignment -name FAMILY "Cyclone V"
set_global_assignment -name DEVICE 5CSEBA6U23I7
set_global_assignment -name TOP_LEVEL_ENTITY ap040_pipeline_integer
set_global_assignment -name SEED 21
set_global_assignment -name NUM_PARALLEL_PROCESSORS 4
set_global_assignment -name SEARCH_PATH "$repo/rtl/ap68040/rtl"
set_global_assignment -name SYSTEMVERILOG_FILE "$repo/rtl/ap68040/experimental/ap040_pipeline_integer.sv"
set_global_assignment -name VERILOG_FILE "$repo/rtl/ap68040/rtl/ap040_alu.v"
set_global_assignment -name VERILOG_FILE "$repo/rtl/ap68040/rtl/ap040_regfile.v"
set_global_assignment -name SDC_FILE prototype.sdc
set_location_assignment PIN_V11 -to clk
set_instance_assignment -name IO_STANDARD "3.3-V LVTTL" -to clk
EOF
# Only top-level data/control ports are virtual; retain a real clock input.
for port in 'external_a[*]' 'external_b[*]' 'external_ccr[*]' \
    'read_src[*]' 'read_dst[*]' in_supported kill_younger idle nreset ce flush in_valid in_ready 'in_pc[*]' 'in_opcode[*]' \
    retire_ready retire_valid 'retire_pc[*]' 'retire_opcode[*]' retire_we \
    'retire_dst[*]' 'retire_data[*]' 'retire_ccr[*]' fallback_valid \
    'fallback_pc[*]' 'fallback_opcode[*]'; do
    printf 'set_instance_assignment -name VIRTUAL_PIN ON -to "%s"\n' "$port" >> "$out/prototype.qsf"
done
cat > "$out/prototype.sdc" <<'EOF'
create_clock -name clk -period 30.303 [get_ports clk]
derive_clock_uncertainty
set_input_delay -clock clk 0 [remove_from_collection [all_inputs] [get_ports clk]]
set_output_delay -clock clk 0 [all_outputs]
EOF
sha256sum "$repo/rtl/ap68040/experimental/ap040_pipeline_integer.sv" \
    "$repo/rtl/ap68040/rtl/ap040_alu.v" "$repo/rtl/ap68040/rtl/ap040_regfile.v" > "$out/identities.txt"
cd "$out"
"$quartus/quartus_sh" --flow compile prototype > flow.log 2>&1
cat prototype.fit.summary prototype.sta.summary
