#!/bin/bash
# fp_store_changes 2026-10-24: build the probed program bench of one tree
# under ~/mister/q800_fpchg_20261024/<tree> on misterubuntu (a git archive of
# the Quadra checkout's CPU trees at 2987624, with the stage's changes), with
# the hardware parameters of rtl/quadra_cpu040.sv (FPU_PIPE=0 LOOP_PRED=0
# EARLY_RES=0 SKID=0 DC1_ATC=0 DUAL=1 BTIC=1 S1_CLASSES=3'b011; DIV_STEPS=2
# the default).  The bench copy gets the trace + memdump probes
# (scripts/patch_tb_fschg.py); nothing under rtl/ is patched here.
# usage: build_chg.sh <tree>      (base | stageA | stageB)
set -e
export PATH=$HOME/opt/verilator-5.052/bin:$PATH
T=$1
B=$HOME/mister/q800_fpchg_20261024/$T
FS=$HOME/mister/q800_fpchg_20261024/scripts
TB=$B/rtl/ap68040_faster/tb
RTL=$B/rtl/ap68040_faster/rtl
WORK=$B/obj_fs
JOBS=${JOBS:-6}
mkdir -p $WORK $TB/build
cd $TB
[ -f tb_ap68040.sv.orig ] || cp tb_ap68040.sv tb_ap68040.sv.orig
python3 $FS/patch_tb_fschg.py $B/docs/perf/fp_store_trace_20261024/scripts tb_ap68040.sv.orig tb_ap68040.sv
python3 ../tools/ucode.py
verilator --binary --timing -j $JOBS --build-jobs $JOBS -O3 \
	-Wno-fatal -Werror-PINMISSING -Werror-IMPLICIT -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC -Wno-UNUSEDSIGNAL -Wno-PINCONNECTEMPTY \
	--top-module tb_ap68040 --Mdir "$WORK/obj_prog" -o tb_ap68040 \
	-I"$RTL" -I"$RTL/fpu" -CFLAGS "-O2 -march=native" \
	"+define+AP_FPU_PIPE=0" "+define+AP_LOOP_PRED=0" "+define+AP_EARLY_RES=0" "+define+AP_SKID=0" \
	"+define+AP_DC1_ATC=0" "+define+AP_DUAL=1" "+define+AP_BTIC=1" "+define+AP_S1C=3'b011" \
	$RTL/ap68040_pkg.sv $RTL/gen/ap68040_upkg.sv $RTL/ap68040_alu.sv $RTL/ap68040_alu_slow.sv $RTL/ap68040_muldiv.sv \
	$RTL/ap68040_biu.sv $RTL/ap68040_ram.sv $RTL/ap68040_atc.sv $RTL/ap68040_dmu.sv $RTL/ap68040_predec.sv $RTL/ap68040_fetch.sv \
	$RTL/ap68040_decode.sv $RTL/ap68040_useq.sv $RTL/fpu/ap040_fpu.v $RTL/ap68040_fpif.sv $RTL/ap68040_backend.sv \
	$RTL/ap68040_snoop.sv $RTL/ap68040.sv m68040_bus_slave.sv m68040_alt_master.sv tb_ap68040.sv > $WORK/verilate.log 2>&1 \
	|| { tail -30 $WORK/verilate.log; echo BUILD_FAILED; exit 1; }
echo "built $WORK/obj_prog/tb_ap68040"
echo BUILD_DONE
