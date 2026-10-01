#!/bin/bash
# Run t_aux_copyout (now rtl/ap68040/tb/asm/t_aux_copyout.s; and any other *.s
# in this directory or rtl/ap68040/tb/asm named on the command line) on the vendored AP68040 in two macro sets:
#   rel  = the 20261001 release's ten AP040_* macros (MacQuadra800.qsf)
#   base = the self-test suite's configuration (LEA + XSTORE only)
# Run inside WSL (iverilog/vvp/vasmm68k_mot in ~/local/bin):
#   wsl.exe -d Ubuntu-24.04 -e bash -lc \
#     'bash /mnt/c/Temp/mistercore/MacQuadra800_MiSTer/docs/resume-20261001/run_aux_copyout.sh'
#   ... run_aux_copyout.sh [srcroot] [test ...]     srcroot = a checkout (default: this one)
# The working copy goes to $W (default ~/auxco); the bench is patched there to
# dump $3000-$3FFF on FAILURE too (+dump=FILE), which the stock bench only does
# on success.  dump.py-style decode: cnt_aerr $3600, last_ssw $3602, last_fa
# $3604, last_pc $3608, pass $360E, first_ssw $3610, first_fa $3614.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
SRCROOT=${1:-$(cd "$HERE/../.." && pwd)}; shift || true
TESTS=${*:-t_aux_copyout}
W=${W:-$HOME/auxco}
export PATH=$HOME/local/bin:$PATH
rm -rf "$W"; mkdir -p "$W"
cp -r "$SRCROOT/rtl/ap68040/rtl" "$W/rtl"
cp -r "$SRCROOT/rtl/ap68040/tb" "$W/tb"
mkdir -p "$W/exp"
[ -d "$SRCROOT/rtl/ap68040/experimental" ] && cp -r "$SRCROOT/rtl/ap68040/experimental/." "$W/exp/"
find "$W" -type f \( -name "*.v" -o -name "*.sv" -o -name "*.svh" -o -name "*.py" -o -name "*.s" \) -exec sed -i 's/\r$//' {} +
for f in "$HERE"/*.s; do [ -f "$f" ] || continue; cp "$f" "$W/tb/asm/"; sed -i 's/\r$//' "$W/tb/asm/$(basename "$f")"; done
python3 -c 'import sys;p=sys.argv[1];s=open(p).read();open(p,"w").write(s.replace("if (errors == 0 && $value$plusargs(\"dump=","if ($value$plusargs(\"dump="))' "$W/tb/tb_ap040_program.v"
RTL=$W/rtl
SRC="$RTL/ap040_tg68k_compat.v $RTL/ap040_core.v $RTL/ap040_bus16_adapter.v \
     $RTL/ap040_bus_timeout.v $RTL/ap040_regfile.v $RTL/ap040_alu.v \
     $RTL/ap040_muldiv.v $RTL/ap040_mmu.v $RTL/ap040_cache.v $RTL/ap040_fpu.v \
     $RTL/ap040_walker_cdc.v $RTL/primitives/dpram.v $(ls $W/exp/ap040_pipeline_integer.sv 2>/dev/null)"
REL="-DAP040_EXPERIMENTAL_XSTORE -DAP040_EXPERIMENTAL_LEA -DAP040_EXPERIMENTAL_PIPELINE \
     -DAP040_EXPERIMENTAL_PIPELINE_LOADS -DAP040_EXPERIMENTAL_PIPELINE_STORES \
     -DAP040_EXPERIMENTAL_PIPELINE_PEA -DAP040_EXPERIMENTAL_PIPELINE_P6 \
     -DAP040_PIPELINE_MEMORY_ENTRY -DAP040_PIPELINE_COMPARE -DAP040_PIPELINE_EARLY_DRAIN"
BASE="-DAP040_EXPERIMENTAL_XSTORE -DAP040_EXPERIMENTAL_LEA"
cd "$W/tb"
for t in $TESTS; do
  vasmm68k_mot -Fbin -m68040 -no-opt -o "$W/$t.bin" "asm/$t.s" > "$W/$t.asm.log" || { cat "$W/$t.asm.log"; exit 1; }
  python3 bin2hex.py "$W/$t.bin" "$W/$t.hex"
done
for cfg in rel base; do
  eval FL=\$$(echo $cfg | tr a-z A-Z)
  iverilog -g2012 $FL -I "$RTL" -o "$W/tb_prog_$cfg.vvp" tb_ap040_program.v $SRC 2> "$W/build_$cfg.log" || { tail "$W/build_$cfg.log"; exit 1; }
done
for t in $TESTS; do
  for cfg in rel base; do
    vvp "$W/tb_prog_$cfg.vvp" "+prog=$W/$t.hex" +dump="$W/${t}_$cfg.dump" ${VVPARGS:-} > "$W/${t}_$cfg.log" 2>&1
    printf '%-22s %-5s ' "$t" "$cfg"
    grep -E "ALL TESTS PASSED|FAIL|failcode|passed \(|timeout" "$W/${t}_$cfg.log" | tr '\n' ' ' | cut -c1-300; echo
    [ -f "$W/${t}_$cfg.dump" ] && python3 - "$W/${t}_$cfg.dump" <<'EOF'
import sys
w=[l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith("//")]
W=lambda a:int(w[(a-0x3000)>>1],16); L=lambda a:(W(a)<<16)|W(a+2)
print("    faults=%d first_ssw=%04x first_fa=%08x last_ssw=%04x last_fa=%08x last_pc=%08x pass=%d"
      %(W(0x3600),W(0x3610),L(0x3614),W(0x3602),L(0x3604),L(0x3608),W(0x360e)))
EOF
  done
done
