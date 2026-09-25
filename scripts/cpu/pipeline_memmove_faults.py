#!/usr/bin/env python3
"""Check precise faults and address-register rollback for memory MOVE."""
import argparse
from pathlib import Path
import subprocess
r = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--core', type=Path, required=True, help='candidate ap040_core.v')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--vasm', default='/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot')
parser.add_argument('--displacement-destination',action='store_true',help='exercise d16(An) destinations instead of indexed destinations')
parser.add_argument('--source-extension', choices=['d16','indexed'], help='exercise early source reads and require their coverage')
parser.add_argument('--simple-destination',type=int,choices=(2,3,4),help='test (An), (An)+ or -(An) destinations')
args = parser.parse_args()
if args.simple_destination and args.displacement_destination: parser.error('choose one destination kind')
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
integer shortcuts=0,expected=0,early_reads=0,early_expected=0;
initial if($value$plusargs("early=%d",early_expected)) begin end
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce &&
 `C.hint_early_read && `C.p_dst==`C.DK_MEM) early_reads++;
integer persistent=0;
initial if($value$plusargs("persistent=%d",persistent)) begin end
always @(negedge tb_ap040_program.clk) if(persistent && tb_ap040_program.nreset) begin force tb_ap040_program.fberr_armed=1; force tb_ap040_program.fberr_addr=16'h2000; end
initial if($value$plusargs("shortcuts=%d",expected)) begin end
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce &&
 `C.state==`C.S_MRD && `C.m_issued && `C.d_ack && !`C.d_err &&
 `C.r_m_ret==`C.S_PIPE_SDONE && `C.p_src==`C.SK_MEM && `C.p_dst==`C.DK_MEM &&
 `C.exec_kind==`C.EK_ALU && `C.alu_op==`AP040_ALU_MOVE && !`C.p_rmw && `C.dst_mode_r==6) shortcuts++;
final begin
 $display("MOVE_ACK shortcuts=%0d expected=%0d early_reads=%0d early_expected=%0d",shortcuts,expected,early_reads,early_expected);
 if(early_reads!=early_expected) $fatal(1,"missing early source read coverage");
 if(shortcuts!=expected) $fatal(1,"missing MOVE acknowledgement coverage");
end
endmodule
''')
if args.displacement_destination:
 monitor=d/'monitor.sv'
 monitor.write_text(monitor.read_text().replace('`C.dst_mode_r==6','`C.dst_mode_r==5').replace('`C.state==`C.S_EA_EXTW2','`C.state==`C.S_IMMF'))
if args.simple_destination:
 monitor=d/'monitor.sv'
 monitor.write_text(monitor.read_text().replace('`C.dst_mode_r==6',f'`C.dst_mode_r=={args.simple_destination}'))
units=('ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram')
sources=[r/'rtl/ap68040/tb/tb_ap040_program.v',d/'monitor.sv',args.core.resolve(),rtl/'ap040_regfile.v',exp/'ap040_pipeline_integer.sv',*[rtl/(u+'.v') for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN']
run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program','-s','fallback_monitor',*flags,'-o',d/'test.vvp',*sources],'compile.log')
for name,source,src_addr,dst_addr,loc,fa,sr,count in [
 ('source','(a0)',0xf140,0xc100,0x600,0xf140,0x271f,0),
 ('source_postinc','(a0)+',0xf140,0xc100,0x600,0xf140,0x271f,0),
 ('source_predec','-(a0)',0xf142,0xc100,0x600,0xf140,0x271f,0),
 ('destination','(a0)',0xc000,0xf140,0x600,0xf140,0x2718,3),
 ('postinc_destination','(a0)+',0xc000,0xf140,0x600,0xf140,0x2718,3),
 ('predec_destination','-(a0)',0xc002,0xf140,0x600,0xf140,0x2718,3),
 ('extension','(a0)',0xc000,0xc100,0x1ffe,0x2000,0x271f,3),
]:
 if args.simple_destination:
  if name=='extension':continue # no destination extension in these modes
  if args.simple_destination==4:dst_addr+=2 # predecrement targets original destination
 early_expected=0
 if args.source_extension and source=='(a0)' and name!='extension':
  source='(0,a0)' if args.source_extension=='d16' else '(0,a0,d1.l)'
  early_expected=3
  if args.source_extension=='d16': loc=0x63e
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
 if name=='extension':
  asm=asm.replace('move.l #$80008000,d0','moveq #0,d0')
  asm+=' move.w #$2000,($f154).l\n'
 asm+=f""" move.w #$271f,sr
 jmp (${loc:x}).l
 org ${loc:x}
faulting:
 move.w {source},(0,a1,d1.l)
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
 if name=='extension':
  start=asm.index('handler:');handler=asm[start:];asm=asm[:start]
  i=asm.index(' org $1ffe');asm=asm[:i]+' bra failed\n'+handler+asm[i:]
 if args.displacement_destination: asm=asm.replace('(0,a1,d1.l)','(0,a1)')
 if args.simple_destination: asm=asm.replace('(0,a1,d1.l)',{2:'(a1)',3:'(a1)+',4:'-(a1)'}[args.simple_destination])
 (d/(name+'.s')).write_text(asm)
 run([args.vasm,'-Fbin','-m68040','-no-opt','-o',d/(name+'.bin'),d/(name+'.s')],name+'_asm.log')
 run(['python3',r/'rtl/ap68040/tb/bin2hex.py',d/(name+'.bin'),d/(name+'.hex')],name+'_hex.log')
 run(['vvp',d/'test.vvp','+prog='+str(d/(name+'.hex')),'+shortcuts='+str(count),'+early='+str(early_expected),'+persistent='+str(int(name=='extension'))],name+'.log')
 log=(d/(name+'.log')).read_text();assert 'ALL TESTS PASSED' in log and 'FAIL:' not in log,log[-2400:]
 print(name,'PASS',next(l for l in log.splitlines() if l.startswith('MOVE_ACK')),flush=True)
