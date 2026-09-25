#!/usr/bin/env python3
from pathlib import Path
import argparse,subprocess
r=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description="Require compare oracle to catch operand and writeback errors.")
parser.add_argument('--out',type=Path,required=True,help='output root populated by compare memory oracle')
args=parser.parse_args();d=args.out.resolve();rtl=r/'rtl/ap68040/rtl';out=d/'negative_full';out.mkdir(exist_ok=True)
s=(r/'rtl/ap68040/experimental/ap040_pipeline_integer.sv').read_text()
mutations=[
 ('compare_operand','load_oracle','is_indexcmp(ex_opcode) ? old_dst : dst','dst'),
 ('compare_writeback','load_oracle','legal = 1; writeback = 0; flags = 1; size = word[7:6];', 'legal = 1; writeback = 1; flags = 1; size = word[7:6];'),
]
for name,fixture,before,after in mutations:
 assert s.count(before)>=1,(name,s.count(before))
 module=out/(name+'.sv');module.write_text(s.replace(before,after));fdir=d/fixture
 code=(fdir/'instructions.hex').read_text().splitlines();rows=(fdir/'oracle.trace').read_text().splitlines()
 nreq=0 if fixture=='alu_oracle' else len((fdir/'requests.hex').read_text().splitlines())
 # All final instructions in these fixtures carry an extension.
 end=int(code[-1][:8],16)+4
 with (out/(name+'_compile.log')).open('w') as log:
  subprocess.run(['iverilog','-g2012','-I',str(rtl),'-s','tb_pipeline_pea','-o',str(out/(name+'.vvp')),str(fdir/'tb.sv'),str(module),str(rtl/'ap040_regfile.v'),str(rtl/'ap040_alu.v')],stdout=log,stderr=subprocess.STDOUT,check=True)
 cmd=['vvp',str(out/(name+'.vvp')),'+program='+str(fdir/'instructions.hex'),'+trace='+str(out/(name+'.trace')),'+count='+str(len(code)),'+registers=16','+mode=1','+delay=3','+stores='+str(fdir/'requests.hex'),'+requests='+str(nreq),'+supported='+str(fdir/'supported.hex'),f'+end_pc={end:x}']
 with (out/(name+'.log')).open('w') as log:ret=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 got=(out/(name+'.trace')).read_text().splitlines()
 # Require a semantic mismatch or a request assertion, not an unrelated timeout.
 mismatch=next(((i,a,b) for i,(a,b) in enumerate(zip(got,rows)) if a!=b),None)
 log=(out/(name+'.log')).read_text()
 assert mismatch is not None or ('FATAL' in log and ('request' in log or 'store' in log)),(name,ret.returncode,log[-1000:])
 print('PASS mutation detected:',name,'trace row '+str(mismatch[0]) if mismatch else log[-300:],flush=True)
