#!/usr/bin/env python3
"""Check indexed or displacement memory MOVE values, CCRs, aliases and byte guards."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--core',type=Path,required=True)
parser.add_argument('--cache',type=Path,help='explicit cache snapshot (default production cache)')
parser.add_argument('--handoff-monitor',choices=('basic','exact'),help='check the actual read-to-write handoff')
parser.add_argument('--require-early',action='store_true',help='require actual early handoff coverage')
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--require-direct-ea',action='store_true',help='require coverage of source acknowledgement directly entering destination calculation')
parser.add_argument('--vasm',default='/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot')
parser.add_argument('--displacement-destination',action='store_true',help='exercise d16(An) destinations instead of indexed destinations')
parser.add_argument('--simple-destination',type=int,choices=(2,3,4),help='test (An), (An)+ or -(An) destinations')
parser.add_argument('--stack-register',choices=('source','destination'),help='use A7 for one base, including byte adjustment by two')
args=parser.parse_args()
if args.require_early and not args.handoff_monitor: parser.error('require-early requires handoff-monitor')
if args.handoff_monitor and not args.simple_destination: parser.error('handoff-monitor requires simple-destination')
if args.stack_register and not args.simple_destination: parser.error('stack-register requires simple-destination')
if args.simple_destination and args.displacement_destination: parser.error('choose one destination kind')
d=args.out.resolve();d.mkdir(parents=True,exist_ok=True)
rtl=r/'rtl/ap68040/rtl';exp=r/'rtl/ap68040/experimental'

def run(cmd,name):
 with (d/name).open('w') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
asm=' org 0\n dc.l $7000,start\n rept 254\n dc.l failed\n endr\n org $400\nstart:\n move.w #$2700,sr\n move.l #$80008000,d0\n movec d0,cacr\n'
k=0
for suffix,n in [('b',1),('w',2),('l',4)]:
 for value in [0,1,(1<<(n*8-1))-1,1<<(n*8-1),(1<<(n*8))-1,0x55555555&((1<<(n*8))-1)]:
  for mode in (2,3,4,5):
   for alias in (False,True):
    source_step=2 if n==1 and args.stack_register=='source' else n
    k+=1;start=0xb040+(source_step if mode==4 else (-4 if mode==5 else 0));after=start+(source_step if mode==3 else (-source_step if mode==4 else 0))
    idx=32 if k%2 else -32;scale=1<<(k%4);disp=7 if k%3 else -7
    dest=(after if alias else 0xc100)+idx*scale+disp
    ccr=(0x10 if k%2 else 0)+(4 if value==0 else 8 if value&(1<<(n*8-1)) else 0)
    source={2:'(a0)',3:'(a0)+',4:'-(a0)',5:'(4,a0)'}[mode]
    dest_operand=f"({idx*scale+disp},{'a0' if alias else 'a1'})" if args.displacement_destination else f"({disp},{'a0' if alias else 'a1'},d1.l*{scale})"
    after_a0=after;after_a1=0xc100;guard_lo=0xa5;guard_hi=0x5a
    if args.simple_destination:
     dm=args.simple_destination;base=after if alias else 0xc100
     dest_is_sp=(alias and args.stack_register=='source') or (not alias and args.stack_register=='destination')
     dest_step=2 if n==1 and dest_is_sp else n
     dest=base-(dest_step if dm==4 else 0)
     final=base+(dest_step if dm==3 else -dest_step if dm==4 else 0)
     if alias:after_a0=final
     else:after_a1=final
     reg='a0' if alias else 'a1'
     dest_operand={2:f'({reg})',3:f'({reg})+',4:f'-({reg})'}[dm]
     # Source initialization follows guards; account for source/guard overlap.
     raw=value.to_bytes(n,'big')
     if 0xb040<=dest-1<0xb040+n:guard_lo=raw[dest-1-0xb040]
     if 0xb040<=dest+n<0xb040+n:guard_hi=raw[dest+n-0xb040]
    asm+=f''' move.w #{k},($f100).l
 movea.l #${start:x},a0
 movea.l #$c100,a1
 move.l #{idx},d1
 move.b #$a5,(${dest-1:x}).l
 move.b #$5a,(${dest+n:x}).l
 move.{suffix} #${value:x},($b040).l
 move.w #${0x271f if k%2 else 0x270f:x},sr
 move.{suffix} {source},{dest_operand}
 move.w sr,d6
 andi.w #$1f,d6
 cmpi.w #${ccr:x},d6
 bne failed
 cmpi.{suffix} #${value:x},(${dest:x}).l
 bne failed
 cmpi.b #${guard_lo:x},(${dest-1:x}).l
 bne failed
 cmpi.b #${guard_hi:x},(${dest+n:x}).l
 bne failed
 cmpa.l #${after_a0:x},a0
 bne failed
 cmpa.l #${after_a1:x},a1
 bne failed
 cmpi.l #{idx},d1
 bne failed
'''
asm+=' move.w #$600d,($f102).l\n stop #$2700\nfailed:\n move.w #$bad0,($f102).l\n stop #$2700\n'
if args.stack_register: asm=asm.replace('a0' if args.stack_register=='source' else 'a1','a7')
(d/'test.s').write_text(asm)
run([args.vasm,'-Fbin','-m68040','-no-opt','-o',d/'test.bin',d/'test.s'],'asm.log')
assert (d/'test.bin').stat().st_size<0x7000
run(['python3',r/'rtl/ap68040/tb/bin2hex.py',d/'test.bin',d/'test.hex'],'hex.log')
(d/'monitor.sv').write_text('''`timescale 1ns/1ps
`include "ap040_defs.svh"
`define C tb_ap040_program.dut.core
module move_monitor;
integer count=0, direct_ea=0, require_direct=0;
reg [7:0] previous_state=0;
initial if ($value$plusargs("require_direct=%d",require_direct)) begin end
always @(negedge tb_ap040_program.clk) begin
 if (tb_ap040_program.nreset && `C.ce && previous_state==`C.S_MRD && `C.state==`C.S_EA_EXTW2) direct_ea++;
 previous_state=`C.state;
end
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce &&
 `C.state==`C.S_MRD && `C.m_issued && `C.d_ack && !`C.d_err &&
 `C.r_m_ret==`C.S_PIPE_SDONE && `C.p_src==`C.SK_MEM && `C.p_dst==`C.DK_MEM &&
 `C.exec_kind==`C.EK_ALU && `C.alu_op==`AP040_ALU_MOVE && !`C.p_rmw && `C.dst_mode_r==6) count++;
final begin
 $display("MOVE_VALUES acknowledgements=%0d direct_ea=%0d",count,direct_ea);
 if(require_direct && direct_ea==0) $fatal(1,"direct destination calculation was not exercised");
 if(count!=432) $fatal(1,"missing size/mode coverage");
end
endmodule
''')
if args.displacement_destination:
 monitor=d/'monitor.sv'
 monitor.write_text(monitor.read_text().replace('`C.dst_mode_r==6','`C.dst_mode_r==5').replace('`C.state==`C.S_EA_EXTW2','(`C.state==`C.S_EA_DISP || `C.state==`C.S_IMMF)'))
if args.simple_destination:
 monitor=d/'monitor.sv'
 monitor.write_text(monitor.read_text().replace('`C.dst_mode_r==6',f'`C.dst_mode_r=={args.simple_destination}').replace('`C.state==`C.S_EA_EXTW2','`C.state==`C.S_EA_DISP'))
units=('ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram')
sources=[r/'rtl/ap68040/tb/tb_ap040_program.v',d/'monitor.sv',args.core.resolve(),rtl/'ap040_regfile.v',exp/'ap040_pipeline_integer.sv',*[(args.cache.resolve() if u=='ap040_cache' and args.cache else rtl/(u+'.v')) for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN']
monitor_args=[]
if args.handoff_monitor:
 extra='move_read_write_exact_monitor.sv' if args.handoff_monitor=='exact' else 'move_read_write_handoff_monitor.sv'
 sources.append(r/'scripts/cpu'/extra)
 monitor_args=['-s','root_handoff_exact_monitor' if args.handoff_monitor=='exact' else 'root_handoff_monitor']
(d/'identity.json').write_text(json.dumps({'sources':{str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in sources},'flags':flags,'args':{k:str(v) for k,v in vars(args).items()}},indent=2)+'\n')
run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program','-s','move_monitor',*monitor_args,*flags,'-o',d/'test.vvp',*sources],'compile.log')
run(['vvp',d/'test.vvp','+prog='+str(d/'test.hex'),'+require_direct='+str(int(args.require_direct_ea)),'+require_early='+str(int(args.require_early))],'run.log')
s=(d/'run.log').read_text();assert 'ALL TESTS PASSED' in s and all(bad not in s for bad in ('FAIL','FATAL','ERROR')),s[-2500:]
print(k,'fixtures PASS',s[-500:])
