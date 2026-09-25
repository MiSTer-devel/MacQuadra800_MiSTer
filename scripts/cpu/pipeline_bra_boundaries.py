#!/usr/bin/env python3
"""Check pipeline BRA target faults, backward displacement and younger-read cancellation."""
import argparse
from pathlib import Path
import subprocess
r = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--core', type=Path, required=True, help='candidate ap040_core.v')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--pipeline-module', type=Path, default=r/'rtl/ap68040/experimental/ap040_pipeline_integer.sv')
parser.add_argument('--vasm', default='/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot')
args = parser.parse_args()
d = args.out.resolve()
d.mkdir(parents=True, exist_ok=True)
rtl = r/'rtl/ap68040/rtl'
exp = r/'rtl/ap68040/experimental'

def run(cmd,name):
 with (d/name).open('w') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
monitor=r'''`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module boundary_monitor;
integer count=0,kind=0;
initial if($value$plusargs("kind=%d",kind)) begin end
always @(negedge tb_ap040_program.clk) if(kind==1 && tb_ap040_program.nreset) begin
 force tb_ap040_program.fberr_armed=1; force tb_ap040_program.fberr_addr=16'h680;
end
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce) begin
 if(`C.pipe_owner && `C.pipe_retire && `C.pipe_opcode[15:8]==8'h60) count++;
 if(kind==0 && `C.pipe_load_launch && `C.pipe_load_addr==32'hf140) $fatal(1,"wrong-path read launched");
end
final begin $display("BRA_BOUNDARY count=%0d",count);if(count!=3) $fatal(1,"BRA pipeline coverage missing");end
endmodule
'''
(d/'monitor.sv').write_text(monitor)
units=('ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram')
sources=[r/'rtl/ap68040/tb/tb_ap040_program.v',d/'monitor.sv',exp/'handoff_monitor.sv',args.core.resolve(),rtl/'ap040_regfile.v',args.pipeline_module.resolve(),*[rtl/(u+'.v') for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN']
run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program','-s','handoff_monitor','-s','boundary_monitor',*flags,'-o',d/'test.vvp',*sources],'compile.log')
for name,kind,entry,branch,target in [('wrong_read',0,0x600,0x6004,0x60a),('target_fault',1,0x600,0x607a,0x680),('backward',2,0x680,0x6082,0x608)]:
 vectors=['$7000','start']+['handler' if i==2 and kind==1 else 'failed' for i in range(2,256)]
 asm=' org 0\n'+''.join(' dc.l '+v+'\n' for v in vectors)+f''' org $400
start:
 move.w #$2700,sr
 move.l #$80008000,d0
 movec d0,cacr
 movea.l #$c000,a0
 movea.l #$f140,a1
 moveq #0,d1
 moveq #1,d3
 moveq #0,d7
 clr.l (a0)
 clr.w -(a7)
 move.l #${entry:x},-(a7)
 move.w #$2710,-(a7)
 rte
handler:
 cmpi.w #$2710,(a7)
 bne failed
 cmpi.l #$680,2(a7)
 bne failed
 cmpi.w #$7008,6(a7)
 bne failed
 cmpi.l #$680,20(a7)
 bne failed
 tst.l d7
 bne failed
 bra success
success:
 move.w #$600d,($f102).l
 stop #$2700
failed:
 move.w #$bad0,($f102).l
 stop #$2700
'''
 targetcode=' tst.l d7\n bne failed\n cmpi.l #1,d3\n bne failed\n bra success\n'
 if kind==2:asm+=f' org ${target:x}\n'+targetcode
 asm+=f' org ${entry:x}\n dc.w $b6b0,$1800\n dc.w ${branch:04x}\n move.w (a1),d7\n nop\n'
 if kind!=2:asm+=f' org ${target:x}\n'+targetcode
 (d/(name+'.s')).write_text(asm)
 run([args.vasm,'-Fbin','-m68040','-no-opt','-o',d/(name+'.bin'),d/(name+'.s')],name+'_asm.log')
 run(['python3',r/'rtl/ap68040/tb/bin2hex.py',d/(name+'.bin'),d/(name+'.hex')],name+'_hex.log')
 run(['vvp',d/'test.vvp','+prog='+str(d/(name+'.hex')),'+kind='+str(kind)],name+'.log')
 s=(d/(name+'.log')).read_text();assert 'ALL TESTS PASSED' in s and 'FAIL:' not in s,s[-2000:]
 print(name,'PASS',next(l for l in s.splitlines() if l.startswith('BRA_BOUNDARY')),flush=True)
