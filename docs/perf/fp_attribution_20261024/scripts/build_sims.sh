#!/bin/bash
# fp_attribution 2026-10-24: build the two program benches under
# ~/mister/q800_fpattr_20261024 (a git archive of the Quadra checkout's CPU trees).
#   new_quadra/obj_prog/tb_ap68040  the dual-issue core (rtl/ap68040_faster) with the
#                                   hardware parameters of rtl/quadra_cpu040.sv:
#                                   FPU_PIPE=0 LOOP_PRED=0 EARLY_RES=0 SKID=0 DC1_ATC=0
#                                   DUAL=1 BTIC=1 S1_CLASSES=3'b011 (DIV_STEPS=2 is the core default)
#   old32/obj/tb_wombat_prog        the shipping core (rtl/ap68040 ap040 through wombat_cpu),
#                                   release macro set, +pcprof added to the scratch bench
# usage: build_sims.sh new|old
set -e
export PATH=$HOME/opt/verilator-5.052/bin:$PATH
B=$HOME/mister/q800_fpattr_20261024
JOBS=${JOBS:-8}
case "$1" in
new)
	TB=$B/rtl/ap68040_faster/tb
	RTL=$B/rtl/ap68040_faster/rtl
	WORK=$B/new_quadra
	mkdir -p $WORK
	cd $TB
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
	;;
old)
	W=$B/old32
	mkdir -p $W
	cd $B/rtl
	AP=ap68040/rtl
	DEFS="+define+SIMULATION=1 +define+AP040_EXPERIMENTAL_XSTORE=1 +define+AP040_EXPERIMENTAL_LEA=1 \
	 +define+AP040_EXPERIMENTAL_PIPELINE=1 +define+AP040_EXPERIMENTAL_PIPELINE_LOADS=1 \
	 +define+AP040_EXPERIMENTAL_PIPELINE_STORES=1 +define+AP040_EXPERIMENTAL_PIPELINE_PEA=1 \
	 +define+AP040_EXPERIMENTAL_PIPELINE_P6=1 +define+AP040_PIPELINE_MEMORY_ENTRY=1 \
	 +define+AP040_PIPELINE_COMPARE=1 +define+AP040_PIPELINE_EARLY_DRAIN=1"
	verilator --binary --timing -j $JOBS --build-jobs $JOBS -O3 -Wno-fatal -Wno-lint -Wno-style \
	 -Wno-WIDTH -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC -Wno-IMPLICIT -Wno-PINMISSING -Wno-UNUSEDSIGNAL \
	 -Wno-UNOPTFLAT -Wno-CASEINCOMPLETE -Wno-UNSIGNED -Wno-CMPCONST -Wno-LATCH -Wno-UNDRIVEN \
	 -Wno-MISINDENT -Wno-COMBDLY -Wno-INITIALDLY -Wno-SYNCASYNCNET -Wno-BLKLOOPINIT -Wno-MULTIDRIVEN \
	 -Wno-GENUNNAMED -Wno-TIMESCALEMOD --timescale-override 1ns/1ps \
	 $DEFS -I$AP -I. --top-module tb_wombat_prog --Mdir $W/obj -o tb_wombat_prog \
	 -CFLAGS "-O2 -march=native" \
	 $W/tb_wombat_prog.sv wombat_cpu.sv wombat_store_buffer.sv \
	 $AP/ap040_core.v ap68040/experimental/ap040_pipeline_integer.sv \
	 $AP/ap040_bus_timeout.v $AP/ap040_regfile.v $AP/ap040_alu.v $AP/ap040_muldiv.v \
	 $AP/ap040_mmu.v $AP/ap040_cache.v $AP/ap040_fpu.v $AP/primitives/dpram.v > $W/verilate.log 2>&1 \
	 || { tail -30 $W/verilate.log; echo BUILD_FAILED; exit 1; }
	echo "built $W/obj/tb_wombat_prog"
	;;
*)
	echo "usage: $0 new|old"; exit 2;;
esac
echo BUILD_DONE
