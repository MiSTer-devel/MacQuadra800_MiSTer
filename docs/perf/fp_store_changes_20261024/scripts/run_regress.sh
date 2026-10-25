#!/bin/bash
# fp_store_changes 2026-10-24: the CPU regression of one tree -- tb/run_tests.sh
# (45 programs x 5 bus configurations = 225 cases, as docs/perf/fpu_pipe_20261024's
# cpu-regression.log) with the hardware parameters, on the PRISTINE bench of
# the tree (its own build via build_sim.sh into obj_rt/).  Log: <tree>/regress.log
# usage: run_regress.sh <tree>
set -e
export PATH=$HOME/opt/verilator-5.052/bin:$HOME/opt/vbcc/bin:$PATH
export VASM=$HOME/opt/vbcc/bin/vasmm68k_mot
T=$1
B=$HOME/mister/q800_fpchg_20261024/$T
cd $B/rtl/ap68040_faster/tb
# run_tests.sh builds the bench from tb_ap68040.sv: make sure it is the pristine one
[ -f tb_ap68040.sv.orig ] && cp tb_ap68040.sv.orig tb_ap68040.sv
export DEFS="+define+AP_FPU_PIPE=0 +define+AP_LOOP_PRED=0 +define+AP_EARLY_RES=0 +define+AP_SKID=0 +define+AP_DC1_ATC=0 +define+AP_DUAL=1 +define+AP_BTIC=1 +define+AP_S1C=3'b011"
export WORK=$B/obj_rt
export JOBS=${JOBS:-6}
mkdir -p $WORK build
date
./run_tests.sh > $B/regress.log 2>&1 || true
date
tail -3 $B/regress.log
grep -c " PASS " $B/regress.log || true
echo REGRESS_DONE
