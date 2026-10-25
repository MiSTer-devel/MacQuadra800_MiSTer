#!/bin/bash
# fp_store_changes 2026-10-24: the six tb_quadra_cpu040 adapter cases of one
# tree (verilator/Makefile targets tb_quadra_cpu040 and tb_quadra_cpu040_2x:
# normal / fast / platform responses at 1:1 and 2:1).  Logs: <tree>/adapter.log
# usage: run_adapter.sh <tree>
set -e
export PATH=$HOME/opt/verilator-5.052/bin:$HOME/opt/vbcc/bin:$PATH
T=$1
B=$HOME/mister/q800_fpchg_20261024/$T
cd $B/verilator
date
{ make tb_quadra_cpu040 V=verilator 2>&1; echo "--- 2x"; make tb_quadra_cpu040_2x V=verilator 2>&1; } > $B/adapter.log || true
date
grep -E '^PASS|^FAIL|TIMEOUT|ERROR|Error' $B/adapter.log | head -20
for f in obj_dir_tb_cpu040/normal.log obj_dir_tb_cpu040/fast.log obj_dir_tb_cpu040/platform.log obj_dir_tb_cpu040_2x/normal.log obj_dir_tb_cpu040_2x/fast.log obj_dir_tb_cpu040_2x/platform.log; do
	printf "%-36s %s\n" "$f" "$(grep -E '^PASS|^FAIL' $f | head -1)"
done
echo ADAPTER_DONE
