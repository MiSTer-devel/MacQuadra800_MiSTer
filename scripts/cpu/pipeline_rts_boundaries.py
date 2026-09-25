#!/usr/bin/env python3
"""Check RTS stack/target faults, trace, IRQ and split-read fallback."""
import argparse
from pathlib import Path
import subprocess
r = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--core', type=Path, required=True, help='candidate ap040_core.v')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--word-aligned-stack', action='store_true', help='test longword RTS reads from a stack aligned to two bytes, but not four')
parser.add_argument('--vasm', default='/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot')
args = parser.parse_args()
normal_stack = 0x7002 if args.word_aligned_stack else 0x7000
d = args.out.resolve()
d.mkdir(parents=True, exist_ok=True)
rtl = r/'rtl/ap68040/rtl'
exp = r/'rtl/ap68040/experimental'

def run(cmd,name):
 with (d/name).open('w') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
(d/'monitor.sv').write_text(r'''`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module fallback_monitor;
integer count=0,expected=0,kind=0,split_cycles=0;
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce && `C.pc_i==32'h600 && `C.state==`C.S_MRD_B) split_cycles++; reg injected=0;
initial begin
 if($value$plusargs("count=%d",expected)) begin end
 if($value$plusargs("kind=%d",kind)) begin end
end
always @(negedge tb_ap040_program.clk) begin
 if(!tb_ap040_program.nreset) injected=0;
 else begin
  if(kind==1) begin force tb_ap040_program.fberr_armed=1; force tb_ap040_program.fberr_addr=16'h800; end
  if(kind==2 && !injected && `C.pc_i=='h600 && `C.state==`C.S_MRD) begin tb_ap040_program.ipl_lvl=2; injected=1; end
  if(kind==3) force tb_ap040_program.berr_d=tb_ap040_program.nreset && tb_ap040_program.busstate!=1 && tb_ap040_program.addr_out[15:0]==16'h7000;
 end
end
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce && `C.pc_i=='h600 &&
 `C.state==`C.S_MRD && `C.m_issued && `C.d_ack && !`C.d_err && `C.r_m_ret==`C.S_RET2 &&
 `C.ret_kind==`C.RK_RTS && !`C.mem_rdata[0] && !`C.tr_t1 && !`C.tr_t0 && !`C.irq_pend) count++;
final begin
 $display("RTS_ACK eligible=%0d expected=%0d",count,expected);
 if(kind==4 && split_cycles==0) $fatal(1,"split return not exercised");
 if(count!=expected) $fatal(1,"return path coverage missing");
end
endmodule
'''.replace("16'h7000", f"16'h{normal_stack:x}"))
units=('ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram')
sources=[r/'rtl/ap68040/tb/tb_ap040_program.v',d/'monitor.sv',args.core.resolve(),rtl/'ap040_regfile.v',exp/'ap040_pipeline_integer.sv',*[rtl/(u+'.v') for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN']
run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program','-s','fallback_monitor',*flags,'-o',d/'test.vvp',*sources],'compile.log')
for name,kind,sr,target,vec,pc,fa,fmt,count in [
 ('split',4,0x271f,0x800,2,None,None,None,0),
 ('normal',0,0x271f,0x800,2,None,None,None,3),
 ('word_target',0,0x271f,0x802,2,None,None,None,3),
 ('odd',0,0x271f,0x801,3,0x600,0x800,0x200c,0),
 ('target_fault',1,0x271f,0x800,2,0x800,0x800,0x7008,3),
 ('source_fault',3,0x271f,0x800,2,0x600,normal_stack,0x7008,0),
 ('t1',0,0xa71f,0x800,9,0x800,0x600,0x2024,0),
 ('t0',0,0x671f,0x800,9,0x800,0x600,0x2024,0),
 ('irq',2,0x201f,0x800,26,0x800,None,0x68,0),
]:
 vectors=['$7000','start']+['handler' if i==vec else 'failed' for i in range(2,256)]
 stack=0x6fff if name=='split' else normal_stack
 asm=' org 0\n'+''.join(' dc.l '+v+'\n' for v in vectors)+f''' org $400
start:
 move.w #$2700,sr
 moveq #0,d7
 movea.l #${stack:x},a7
 move.l #${target:x},(${stack:x}).l
 clr.w -(a7)
 move.l #$600,-(a7)
 move.w #${sr:x},-(a7)
 rte
 org $600
 rts
 bra failed
handler:
'''
 if pc is None:asm+=' bra failed\n'
 else:
  framesize=60 if fmt==0x7008 else (12 if fmt&0xf000 else 8)
  framebase=(normal_stack if name in ('odd','source_fault') else normal_stack+4)-framesize
  asm+=f''' cmpa.l #${framebase:x},a7
 bne failed
 cmpi.w #${sr:x},(a7)
 bne failed
 cmpi.l #${pc:x},2(a7)
 bne failed
 cmpi.w #${fmt:x},6(a7)
 bne failed
'''
  if fa is not None:asm+=f' cmpi.l #${fa:x},{20 if fmt==0x7008 else 8}(a7)\n bne failed\n'
  if name=='irq':asm+=' move.w #0,($f110).l\n'
  asm+=' tst.l d7\n bne failed\n bra success\n'
 asm+='''success:
 move.w #$600d,($f102).l
 stop #$2700
failed:
 move.w #$bad0,($f102).l
 stop #$2700
'''+f' org ${target&~1:x}\n'
 if pc is None:asm+=f' cmpa.l #${normal_stack+4:x},a7\n bne failed\n bra success\n'
 else:asm+=' moveq #1,d7\n bra failed\n'
 if name=='split':
  asm=asm.replace(' clr.w -(a7)', ' move.l #$c000,d0\n movec d0,itt0\n movec d0,dtt0\n move.l #$8000,d0\n movec d0,tc\n clr.w -(a7)').replace(f'cmpa.l #${normal_stack+4:x},a7','cmpa.l #$7003,a7')
 (d/(name+'.s')).write_text(asm)
 run([args.vasm,'-Fbin','-m68040','-no-opt','-o',d/(name+'.bin'),d/(name+'.s')],name+'_asm.log')
 run(['python3',r/'rtl/ap68040/tb/bin2hex.py',d/(name+'.bin'),d/(name+'.hex')],name+'_hex.log')
 run(['vvp',d/'test.vvp','+prog='+str(d/(name+'.hex')),'+count='+str(count),'+kind='+str(kind)],name+'.log')
 log=(d/(name+'.log')).read_text();assert 'ALL TESTS PASSED' in log and 'FAIL:' not in log,log[-2000:]
 print(name,'PASS',next(l for l in log.splitlines() if l.startswith('RTS_ACK')),flush=True)
