#!/bin/bash
# fp_attribution 2026-10-24, sensitivity: the dual core with FPU_PIPE=1 (everything
# else the Quadra parameters) on the three in-cache kernels, logs out2/*.newpipe.log
set -e
export PATH=$HOME/opt/verilator-5.052/bin:$PATH
B=$HOME/mister/q800_fpattr_20261024
TB=$B/rtl/ap68040_faster/tb
RTL=$B/rtl/ap68040_faster/rtl
WORK=$B/new_pipe
OUT=$B/out2
mkdir -p $WORK
cd $TB
verilator --binary --timing -j 8 --build-jobs 8 -O3 \
	-Wno-fatal -Werror-PINMISSING -Werror-IMPLICIT -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC -Wno-UNUSEDSIGNAL -Wno-PINCONNECTEMPTY \
	--top-module tb_ap68040 --Mdir "$WORK/obj_prog" -o tb_ap68040 \
	-I"$RTL" -I"$RTL/fpu" -CFLAGS "-O2 -march=native" \
	"+define+AP_FPU_PIPE=1" "+define+AP_LOOP_PRED=0" "+define+AP_EARLY_RES=0" "+define+AP_SKID=0" \
	"+define+AP_DC1_ATC=0" "+define+AP_DUAL=1" "+define+AP_BTIC=1" "+define+AP_S1C=3'b011" \
	$RTL/ap68040_pkg.sv $RTL/gen/ap68040_upkg.sv $RTL/ap68040_alu.sv $RTL/ap68040_alu_slow.sv $RTL/ap68040_muldiv.sv \
	$RTL/ap68040_biu.sv $RTL/ap68040_ram.sv $RTL/ap68040_atc.sv $RTL/ap68040_dmu.sv $RTL/ap68040_predec.sv $RTL/ap68040_fetch.sv \
	$RTL/ap68040_decode.sv $RTL/ap68040_useq.sv $RTL/fpu/ap040_fpu.v $RTL/ap68040_fpif.sv $RTL/ap68040_backend.sv \
	$RTL/ap68040_snoop.sv $RTL/ap68040.sv m68040_bus_slave.sv m68040_alt_master.sv tb_ap68040.sv > $WORK/verilate.log 2>&1 \
	|| { tail -30 $WORK/verilate.log; echo BUILD_FAILED; exit 1; }
echo built
for img in whet_2 whet_4 fpmm_20_r2 fpmm_20_r4 fft_256_r2 fft_256_r4 fpmm_20reg_r2 fpmm_20reg_r4; do
	( $WORK/obj_prog/tb_ap68040 +prog=build/$img.hex +pcprof +prof +timeout=400000000 > $OUT/$img.newpipe.log 2>&1 || true ) &
done
wait
for f in $OUT/*.newpipe.log; do printf "%-26s %s %s\n" "$(basename $f)" "$(grep -E "^(PASS|FAIL)" $f | head -1 | cut -c1-90)" "$(grep PCFPW_LOST $f)"; done
echo RUNPIPE_DONE
