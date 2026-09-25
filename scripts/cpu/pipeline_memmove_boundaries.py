#!/usr/bin/env python3
"""Check memory MOVE retirement boundaries and split-source fallback."""
import argparse
import json
import hashlib
from pathlib import Path
import subprocess
r = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--core', type=Path, required=True, help='candidate ap040_core.v')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--cache', type=Path)
parser.add_argument('--handoff-monitor', action='store_true')
parser.add_argument('--require-early', action='store_true')
parser.add_argument('--vasm', default='/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot')
parser.add_argument('--displacement-destination',action='store_true',help='exercise d16(An) destinations instead of indexed destinations')
parser.add_argument('--simple-destination',type=int,choices=(2,3,4))
args = parser.parse_args()
if args.require_early and not args.handoff_monitor: parser.error('require-early needs handoff-monitor')
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
integer shortcuts=0,expected=0,split_cycles=0;
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce && `C.pc_i==32'h600 && `C.state==`C.S_MRD_B) split_cycles++; reg injected=0; integer irq=0;
initial if($value$plusargs("irq=%d",irq)) begin end
always @(negedge tb_ap040_program.clk) if(!tb_ap040_program.nreset) injected=0; else if(irq && !injected && `C.pc_i==32'h600 && `C.state==`C.S_MRD) begin tb_ap040_program.ipl_lvl=2; injected=1; end
integer persistent=0;
initial if($value$plusargs("persistent=%d",persistent)) begin end
always @(negedge tb_ap040_program.clk) if(persistent && tb_ap040_program.nreset) begin force tb_ap040_program.fberr_armed=1; force tb_ap040_program.fberr_addr=16'h2000; end
initial if($value$plusargs("shortcuts=%d",expected)) begin end
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce &&
 `C.state==`C.S_MRD && `C.m_issued && `C.d_ack && !`C.d_err &&
 `C.r_m_ret==`C.S_PIPE_SDONE && `C.p_src==`C.SK_MEM && `C.p_dst==`C.DK_MEM &&
 `C.exec_kind==`C.EK_ALU && `C.alu_op==`AP040_ALU_MOVE && !`C.p_rmw && `C.dst_mode_r==6) shortcuts++;
final begin
 $display("MOVE_ACK shortcuts=%0d expected=%0d",shortcuts,expected);
 if(expected==0 && split_cycles==0) $fatal(1,"split fallback not covered");
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
sources=[r/'rtl/ap68040/tb/tb_ap040_program.v',d/'monitor.sv',args.core.resolve(),rtl/'ap040_regfile.v',exp/'ap040_pipeline_integer.sv',*[(args.cache.resolve() if u=='ap040_cache' and args.cache else rtl/(u+'.v')) for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN']
extra=[]
if args.handoff_monitor:
 sources.append(r/'scripts/cpu/move_read_write_handoff_monitor.sv')
 extra=['-s','root_handoff_monitor']
(d/'identity.json').write_text(json.dumps({'sources':{str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in sources},'flags':flags},indent=2)+'\n')
run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program','-s','fallback_monitor',*extra,*flags,'-o',d/'test.vvp',*sources],'compile.log')
for name in (('irq','t1','alias','split') if (args.displacement_destination or args.simple_destination) else ('irq','t1','alias','full','split')):
 src=0xcfff if name=='split' else 0xc000
 dst=0xc102 if name=='alias' else 0xc100
 initial_a1=0xc100;final_a1=0xc002 if name=='alias' else 0xc100
 if args.simple_destination:
  dm=args.simple_destination
  initial_a1=0xc102 if dm==4 else 0xc100
  base=0xc002 if name=='alias' else initial_a1
  dst=base-(2 if dm==4 else 0)
  final_a1=base+(2 if dm==3 else -2 if dm==4 else 0)
 sr=0x2010 if name=='irq' else (0xa710 if name=='t1' else 0x2710)
 vec=26 if name=='irq' else 9
 vectors=['$7000','start']+['handler' if i==vec else 'failed' for i in range(2,256)]
 asm=' org 0\n'+''.join(' dc.l '+v+'\n' for v in vectors)+f""" org $400
start:
 move.w #$2700,sr
 move.l #$80008000,d0
 movec d0,cacr
 movea.l #${src:x},a0
 movea.l #${initial_a1:x},a1
 moveq #0,d1
 moveq #$66,d2
 move.w #$8001,(${src:x}).l
"""
 if name=='alias':asm+=' movea.l #$c000,a1\n move.w #$8001,($c000).l\n'
 if name=='split':asm+=' move.l #$c000,d0\n movec d0,itt0\n movec d0,dtt0\n move.l #$8000,d0\n movec d0,tc\n'
 asm+=f""" clr.w -(a7)
 move.l #$600,-(a7)
 move.w #${sr:x},-(a7)
 rte
 org $600
"""
 if name=='alias':asm+=' move.w (a1)+,($100,a1,d1.l)\n'
 elif name=='full':asm+=' dc.w $3390,$1910\n'
 else:asm+=' move.w (a0),(0,a1,d1.l)\n'
 asm+='after:\n'
 if name in ('irq','t1'):asm+=' bra failed\nhandler:\n'
 else:asm+=' bra checks\nhandler:\n bra failed\nchecks:\n'
 if name in ('irq','t1'):
  asm+=f""" cmpi.w #${sr+8:x},(a7)
 bne failed
 cmpi.l #after,2(a7)
 bne failed
 cmpi.w #${0x68 if name=='irq' else 0x2024:x},6(a7)
 bne failed
"""
  if name=='irq':asm+=' move.w #0,($f110).l\n'
  else:asm+=' cmpi.l #$600,8(a7)\n bne failed\n'
 asm+=f""" cmpi.w #$8001,(${dst:x}).l
 bne failed
 cmpa.l #${final_a1:x},a1
 bne failed
 cmpa.l #${src:x},a0
 bne failed
 cmpi.l #$66,d2
 bne failed
 move.w #$600d,($f102).l
 stop #$2700
failed:
 move.w #$bad0,($f102).l
 stop #$2700
"""
 if args.simple_destination:
  operand={2:'(a1)',3:'(a1)+',4:'-(a1)'}[args.simple_destination]
  asm=asm.replace('(0,a1,d1.l)',operand).replace('($100,a1,d1.l)',operand)
 if args.displacement_destination: asm=asm.replace('(0,a1,d1.l)','(0,a1)').replace('($100,a1,d1.l)','($100,a1)')
 (d/(name+'.s')).write_text(asm)
 run([args.vasm,'-Fbin','-m68040','-no-opt','-o',d/(name+'.bin'),d/(name+'.s')],name+'_asm.log')
 run(['python3',r/'rtl/ap68040/tb/bin2hex.py',d/(name+'.bin'),d/(name+'.hex')],name+'_hex.log')
 run(['vvp',d/'test.vvp','+prog='+str(d/(name+'.hex')),'+shortcuts='+str(0 if name=='split' else 3),'+irq='+str(int(name=='irq')),'+require_early='+str(int(args.require_early and name!='split'))],name+'.log')
 log=(d/(name+'.log')).read_text();assert 'ALL TESTS PASSED' in log and all(x not in log for x in ('FAIL','FATAL','ERROR')),log[-2400:]
 print(name,'PASS',next(l for l in log.splitlines() if l.startswith('MOVE_ACK')),flush=True)
