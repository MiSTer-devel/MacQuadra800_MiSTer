#!/usr/bin/env python3
"""Independent P6 qualification; generated fixtures and logs stay under --out."""
from pathlib import Path
import argparse
import subprocess, sys
r = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, default=r/'scratch/pipeline_p6')
parser.add_argument("--vasm", default="/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot")
args = parser.parse_args()
root_out = args.out.resolve()
root_out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(r/'scripts/cpu'))
d=root_out/'faults';d.mkdir(exist_ok=True)
rtl=r/'rtl/ap68040/rtl';exp=r/'rtl/ap68040/experimental'
(d/'monitor.sv').write_text('''`timescale 1ns/1ps
module indexed_fault_monitor;
integer count=0;
always @(posedge tb_ap040_program.clk)
 if(tb_ap040_program.nreset && tb_ap040_program.dut.core.ce && tb_ap040_program.dut.core.pipe_load_launch && tb_ap040_program.dut.core.pipe_load_pc==32'h600) count=count+1;
final begin
 $display("INDEXED FAULT launches=%0d",count);
 if(count!=3) $fatal(1,"indexed fault coverage missing");
end
endmodule
''')
units=('ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram')
sources=[r/'rtl/ap68040/tb/tb_ap040_program.v',d/'monitor.sv',exp/'handoff_monitor.sv',rtl/'ap040_core.v',rtl/'ap040_regfile.v',exp/'ap040_pipeline_integer.sv',*[rtl/(u+'.v') for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_FORCE_DECODE']
with (d/'compile.log').open('w') as f:subprocess.run(['iverilog','-g2012','-I',str(rtl),'-s','tb_ap040_program','-s','handoff_monitor','-s','indexed_fault_monitor',*flags,'-o',str(d/'test.vvp'),*map(str,sources)],stdout=f,stderr=subprocess.STDOUT,check=True)
for name,opcode,sr in [('movea_word',0x3670,0x271f),('move_word',0x3630,0x271f),('store_word',0x3183,0x2718)]:
 asm=f'''    org 0
    dc.l $7000,start
    dc.l handler
    rept 29
    dc.l failed
    endr
    dc.l $600
    rept 223
    dc.l failed
    endr
    org $400
start:
    move.w #$2700,sr
    move.l #$80008000,d0
    movec d0,cacr
    movea.l #$f100,a0
    movea.l #$deadbeef,a3
    move.l #$fedcba98,d3
    moveq #$40,d1
    moveq #$66,d2
    move.w #$271f,sr
    trap #0
    org $600
faulting:
    dc.w ${opcode:04x},$1800
    moveq #7,d2
    bra failed
handler:
    cmpi.w #${sr:04x},(a7)
    bne failed
    cmpi.l #faulting,2(a7)
    bne failed
    cmpi.l #$f140,20(a7)
    bne failed
    cmpa.l #$f100,a0
    bne failed
    cmpa.l #$deadbeef,a3
    bne failed
    cmpi.l #$fedcba98,d3
    bne failed
    cmpi.l #$40,d1
    bne failed
    cmpi.l #$66,d2
    bne failed
    move.w 6(a7),d0
    andi.w #$f000,d0
    cmpi.w #$7000,d0
    bne failed
    move.w #$600d,($f102).l
    stop #$2700
failed:
    move.w #$6fad,($f100).l
    move.w #$bad0,($f102).l
    stop #$2700
'''
 p=d/(name+'.s');p.write_text(asm)
 with (d/(name+'_assemble.log')).open('w') as f:
  subprocess.run([args.vasm,'-Fbin','-m68040','-no-opt','-o',str(d/(name+'.bin')),str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
 subprocess.run(['python3',str(r/'rtl/ap68040/tb/bin2hex.py'),str(d/(name+'.bin')),str(d/(name+'.hex'))],capture_output=True,check=True)
 with (d/(name+'.log')).open('w') as f:subprocess.run(['vvp',str(d/'test.vvp'),'+prog='+str(d/(name+'.hex'))],stdout=f,stderr=subprocess.STDOUT,check=True)
 log=(d/(name+'.log')).read_text();assert 'ALL TESTS PASSED' in log and 'FAIL:' not in log and 'INDEXED FAULT launches=3' in log,log[-3000:]
 print(name,'PASS',next(l for l in log.splitlines() if l.startswith('HANDOFF')),flush=True)
