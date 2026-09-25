#!/usr/bin/env python3
"""Check precise CLR or immediate-MOVE faults, flags, and register rollback."""
import argparse
from pathlib import Path
import subprocess
r = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--core', type=Path, required=True, help='candidate ap040_core.v')
parser.add_argument('--immediate-value',choices=('negative','zero','positive'),default='negative',help='value class for immediate MOVE flag checks')
parser.add_argument('--immediate-move',action='store_true',help='test immediate MOVE stores instead of CLR')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--vasm', default='/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot')
args = parser.parse_args()
d = args.out.resolve()
d.mkdir(parents=True, exist_ok=True)
rtl = r/'rtl/ap68040/rtl'
exp = r/'rtl/ap68040/experimental'

def run(cmd,name):
 with (d/name).open('w') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
(d/'monitor.sv').write_text(r'''`timescale 1ns/1ps
`include "ap040_defs.svh"
`define C tb_ap040_program.dut.core
module fallback_monitor;
integer shortcuts=0,expected=0; reg [31:0] site=0;
initial if($value$plusargs("site=%h",site)) begin end
integer persistent=0;
initial if($value$plusargs("persistent=%d",persistent)) begin end
always @(negedge tb_ap040_program.clk) if(persistent && tb_ap040_program.nreset) begin force tb_ap040_program.fberr_armed=1; force tb_ap040_program.fberr_addr=16'h2000; end
initial if($value$plusargs("shortcuts=%d",expected)) begin end
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce &&
 `C.state==`C.S_PIPE_DEA && `C.pc_i==site && !`C.p_rmw &&
 `C.exec_kind==`C.EK_ALU && `C.alu_op==`AP040_ALU_CLR) shortcuts++;
final begin
 $display("CLR_EA shortcuts=%0d expected=%0d",shortcuts,expected);
 if(shortcuts!=expected) $fatal(1,"missing target store effective-address coverage");
end
endmodule
''')
if args.immediate_move:
 monitor=d/'monitor.sv'
 monitor.write_text(monitor.read_text().replace('`C.alu_op==`AP040_ALU_CLR', '(`C.alu_op==`AP040_ALU_MOVE && `C.p_src==`C.SK_IMM)').replace('CLR_EA','IMM_MOVE_EA'))
units=('ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram')
sources=[r/'rtl/ap68040/tb/tb_ap040_program.v',d/'monitor.sv',args.core.resolve(),rtl/'ap040_regfile.v',exp/'ap040_pipeline_integer.sv',*[rtl/(u+'.v') for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN']
run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program','-s','fallback_monitor',*flags,'-o',d/'test.vvp',*sources],'compile.log')
# The shared bench executes each program in three bus/CE timing phases.
# Simple post/preincrement destinations bypass S_PIPE_DEA in ea_operand_start;
# they are rollback controls, with zero expected hits on the changed path.
for name,instruction,src_addr,dst_addr,loc,fa,sr,count in [
 ('byte_indexed','clr.b (0,a1,d1.l)',0xc000,0xf140,0x600,0xf140,0x2714,3),
 ('word_indexed','clr.w (0,a1,d1.l)',0xc000,0xf140,0x600,0xf140,0x2714,3),
 ('long_indexed','clr.l (0,a1,d1.l)',0xc000,0xf140,0x600,0xf140,0x2714,3),
 ('postinc','clr.w (a1)+',0xc000,0xf140,0x600,0xf140,0x2714,0),
 ('predec','clr.w -(a1)',0xc000,0xf142,0x600,0xf140,0x2714,0),
 ('absolute','clr.w ($f140).l',0xc000,0xf140,0x600,0xf140,0x2714,3),
 ('destination_extension','clr.w (0,a1,d1.l)',0xc000,0xc100,0x1ffc,0x2000,0x271f,0),
 ('extension','clr.w (0,a1,d1.l)',0xc000,0xc100,0x1ffe,0x2000,0x271f,0),
]:
 if name=='destination_extension' and not args.immediate_move: continue
 if args.immediate_move:
  mnemonic,operand=instruction.split(' ',1)
  value={'b':'$81','w':'$8001','l':'$80000001'}[mnemonic[-1]]
  if args.immediate_value!='negative': value='0' if args.immediate_value=='zero' else '1'
  instruction=f'move.{mnemonic[-1]} #{value},{operand}'
  if not name.endswith('extension'): sr={'negative':0x2718,'zero':0x2714,'positive':0x2710}[args.immediate_value]  # X preserved; N/Z reflect the selected value
 asm=' org 0\n dc.l $7000,start,handler\n'+''.join(' dc.l failed\n' for _ in range(253))+f""" org $400
start:
 move.w #$2700,sr
 move.l #$80008000,d0
 movec d0,cacr
 movea.l #${src_addr:x},a0
 movea.l #${dst_addr:x},a1
 moveq #0,d1
 moveq #$66,d2
 move.w #$8001,($c000).l
 move.w #$5555,($c100).l
"""
 # A persistent bus fault covers demand retry after a speculative fetch fails.
 if name.endswith('extension'):
  asm=asm.replace('move.l #$80008000,d0','moveq #0,d0')
  asm+=' move.w #$2000,($f154).l\n'
 asm+=f""" move.w #$271f,sr
 jmp (${loc:x}).l
 org ${loc:x}
faulting:
 {instruction}
 moveq #7,d2
 bra failed
handler:
 cmpi.w #${sr:x},(a7)
 bne failed
 cmpi.l #faulting,2(a7)
 bne failed
 cmpi.l #${fa:x},20(a7)
 bne failed
 cmpa.l #${src_addr:x},a0
 bne failed
 cmpa.l #${dst_addr:x},a1
 bne failed
 tst.l d1
 bne failed
 cmpi.l #$66,d2
 bne failed
 cmpi.w #$5555,($c100).l
 bne failed
 move.w 6(a7),d0
 andi.w #$f000,d0
 cmpi.w #$7000,d0
 bne failed
 move.w #$600d,($f102).l
 stop #$2700
failed:
 move.w #$bad0,($f102).l
 stop #$2700
"""
 # Keep the handler outside the page whose instruction fetch is deliberately faulted.
 if name.endswith('extension'):
  start=asm.index('handler:');handler=asm[start:];asm=asm[:start]
  i=asm.index(f' org ${loc:x}');asm=asm[:i]+' bra failed\n'+handler+asm[i:]
 (d/(name+'.s')).write_text(asm)
 run([args.vasm,'-Fbin','-m68040','-no-opt','-o',d/(name+'.bin'),d/(name+'.s')],name+'_asm.log')
 run(['python3',r/'rtl/ap68040/tb/bin2hex.py',d/(name+'.bin'),d/(name+'.hex')],name+'_hex.log')
 run(['vvp',d/'test.vvp','+prog='+str(d/(name+'.hex')),'+shortcuts='+str(count),f'+site={loc:x}','+persistent='+str(int(name.endswith('extension')))],name+'.log')
 log=(d/(name+'.log')).read_text();assert 'ALL TESTS PASSED' in log and 'FAIL:' not in log,log[-2400:]
 print(name,'PASS',next(l for l in log.splitlines() if l.startswith(('CLR_EA','IMM_MOVE_EA'))),flush=True)
