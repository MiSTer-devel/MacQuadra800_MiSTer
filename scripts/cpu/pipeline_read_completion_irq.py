#!/usr/bin/env python3
"""Check IRQ priority at the exact acknowledgement of a pipeline read."""
import argparse
from pathlib import Path
import subprocess
r = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--core', type=Path, required=True, help='candidate ap040_core.v')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--pipeline-module', type=Path, default=r/'rtl/ap68040/experimental/ap040_pipeline_integer.sv')
parser.add_argument('--vasm', default='/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot')
parser.add_argument('--tst-size',choices=('b','w','l'),help='exercise TST (An) instead of MOVE.L')
args = parser.parse_args()
d = args.out.resolve()
d.mkdir(parents=True, exist_ok=True)
rtl = r/'rtl/ap68040/rtl'
exp = r/'rtl/ap68040/experimental'

def run(cmd,name):
 with (d/name).open('w') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
monitor='''`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module boundary_monitor;
integer injections=0,cancels=0; reg injected=0,finished=0;
always @(negedge tb_ap040_program.clk) begin
 if(!tb_ap040_program.nreset) begin
  injected=0; finished=0; release `C.irq_pend; release `C.irq_take_lvl;
 end else if(!injected && `C.ce && `C.state==`C.S_MRD && `C.pipe_load_active &&
             `C.m_issued && `C.d_ack && !`C.d_err && `C.integer_pipeline.ex_pc=='h600) begin
  tb_ap040_program.ipl_lvl=2; force `C.irq_pend=1; force `C.irq_take_lvl=3'd2;
  injected=1; injections++;
 end else if(finished) begin release `C.irq_pend; release `C.irq_take_lvl; end
end
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce) begin
 if(injected && !finished && `C.pipe_read_retire) $fatal(1,"read retired past pending IRQ");
 if(`C.pipe_cancel) begin finished=1; if(`C.pipe_pc=='h600) cancels++; end
end
final begin
 $display("READ_BOUNDARY injections=%0d cancels=%0d",injections,cancels);
 if(injections!=3 || cancels!=3) $fatal(1,"missing read completion IRQ coverage");
end
endmodule
'''
(d/'monitor.sv').write_text(monitor)
units=('ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram')
sources=[r/'rtl/ap68040/tb/tb_ap040_program.v',d/'monitor.sv',args.core.resolve(),rtl/'ap040_regfile.v',args.pipeline_module.resolve(),*[rtl/(u+'.v') for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN','-DAP040_PIPELINE_FORCE_DECODE']
run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program','-s','boundary_monitor',*flags,'-o',d/'test.vvp',*sources],'compile.log')
assembly=exp/'irq_load.s'
if args.tst_size:
 assembly=d/'irq_tst.s'
 source=(exp/'irq_load.s').read_text()
 source=source.replace('    jmp ($600).l', '    move.w #$201f,sr\n    jmp ($600).l')
 source=source.replace('    move.l (a0),d1',f'    tst.{args.tst_size} (a0)')
 # Use the same positive, nonzero operand for every width (big endian).
 source=source.replace('move.l #$55,($c000).l',f'move.{args.tst_size} #$55,($c000).l')
 source=source.replace('    cmpi.l #$55,d1','    cmpi.l #0,d1')
 source=source.replace('handler:\n','handler:\n    cmpi.w #$2010,(a7)\n    bne failed\n')
 assembly.write_text(source)
run([args.vasm,'-Fbin','-m68040','-no-opt','-o',d/'test.bin',assembly],'asm.log')
run(['python3',r/'rtl/ap68040/tb/bin2hex.py',d/'test.bin',d/'test.hex'],'hex.log')
run(['vvp',d/'test.vvp','+prog='+str(d/'test.hex')],'run.log')
log=(d/'run.log').read_text(); assert 'ALL TESTS PASSED' in log,log[-2000:]
print(log[-1200:])
