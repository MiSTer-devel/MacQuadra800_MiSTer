#!/usr/bin/env python3
from pathlib import Path
import argparse,subprocess
r=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description="Check final-WB handoff to dependent legacy instructions.")
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args();d=args.out.resolve();d.mkdir(parents=True,exist_ok=True)
rtl=r/'rtl/ap68040/rtl';exp=r/'rtl/ap68040/experimental' 
asm='''    org 0
    dc.l $7000,start
    rept 254
    dc.l failed
    endr
    org $400
start:
    move.w #$2700,sr
    move.l #$80008000,d0
    movec d0,cacr
    movea.l #$c000,a0
    moveq #0,d1
    move.l #$c080,($c000).l
    move.w #0,($c004).l
    move.l #$12345678,($c008).l
    move.l #$80000000,($c080).l
    nop
    dc.w $2470,$1800
    tst.l (a2)
    bpl failed
    dc.w $3630,$1804
    dbra d3,failed
    cmpi.w #$ffff,d3
    bne failed
    dc.w $2630,$1808
    cmpi.l #$12345678,d3
    bne failed
    dc.w $4870,$1800
    jsr subroutine(pc)
    cmpa.l #$6ffc,a7
    bne failed
    cmpi.l #$c000,(a7)
    bne failed
    move.w #$600d,($f102).l
    stop #$2700
subroutine:
    cmpa.l #$6ff8,a7
    bne failed
    rts
failed:
    move.w #$bad0,($f102).l
    stop #$2700
'''
(d/'test.s').write_text(asm)
(d/'monitor.sv').write_text('''`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module drain_monitor;
integer edges=0; integer dbcc=0, cmp=0, call=0; integer indexed_a2=0, dependent_tst_addr=0;
reg check_empty=0, have_indexed_a2=0;
always @(posedge tb_ap040_program.clk) begin
 if(!tb_ap040_program.nreset) begin check_empty=0; have_indexed_a2=0; end
 else if(`C.ce) begin
 if(check_empty && !`C.pipe_idle) $fatal(1,"pipeline work remained after final WB handoff");
 check_empty=0;
 // The first indexed MOVEA load must retire c080 into A2 before the TST.L (A2)
 // read is launched. The test's BPL then checks the TST's N flag architecturally.
 if(`C.pipe_read_retire && `C.pipe_opcode == 16'h2470) begin
  if(!`C.pipe_we || `C.pipe_wdst != 4'ha || `C.pipe_data !== 32'h0000c080)
   $fatal(1,"indexed A2 load retired wrong data/destination dst=%h data=%h",`C.pipe_wdst,`C.pipe_data);
  have_indexed_a2=1; indexed_a2++;
 end
 if(`C.pipe_load_launch && `C.pipe_load_opcode == 16'h4a92) begin
  if(!have_indexed_a2) $fatal(1,"dependent TST read launched before indexed A2 load retirement");
  if(`C.pipe_load_addr !== 32'h0000c080) $fatal(1,"dependent TST used wrong A2 effective address %h",`C.pipe_load_addr);
  have_indexed_a2=0; dependent_tst_addr++;
 end
 if((`C.pipe_owner || `C.pipe_read_retire) && `C.pipe_retire && `C.pipe_empty_after_retire && !`C.pipe_input && !`C.pipe_cancel) begin
  edges++;
  // These are the following instructions at the final retirement boundary.
  if(`C.epf_ready_pc) case(`C.epf_data[`C.epf_head])
   16'h51cb:dbcc++;16'h0c83:cmp++;16'h4eba:call++;
  endcase
  check_empty=1;
 end
 end
end
final begin
 $display("DRAIN edges=%0d indexed_a2=%0d dependent_tst_addr=%0d dbcc=%0d cmp=%0d call=%0d",edges,indexed_a2,dependent_tst_addr,dbcc,cmp,call);
 if(indexed_a2<3 || dependent_tst_addr<3 || dbcc<3 || cmp<3 || call<3) $fatal(1,"final WB dependency coverage missing");
end
endmodule
''')
def run(cmd,name):
 with (d/name).open('w') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
run(['/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot','-Fbin','-m68040','-no-opt','-o',d/'test.bin',d/'test.s'],'asm.log')
run(['python3',r/'rtl/ap68040/tb/bin2hex.py',d/'test.bin',d/'test.hex'],'hex.log')
units=('ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram')
sources=[r/'rtl/ap68040/tb/tb_ap040_program.v',d/'monitor.sv',exp/'handoff_monitor.sv',rtl/'ap040_core.v',rtl/'ap040_regfile.v',exp/'ap040_pipeline_integer.sv',*[rtl/(u+'.v') for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN']
flags += ['-DAP040_PIPELINE_COMPARE']
run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program','-s','handoff_monitor','-s','drain_monitor',*flags,'-o',d/'test.vvp',*sources],'compile.log')
run(['vvp',d/'test.vvp','+prog='+str(d/'test.hex')],'run.log')
s=(d/'run.log').read_text();assert 'ALL TESTS PASSED' in s and 'FAIL:' not in s,s[-2000:];print(s[-1800:])
