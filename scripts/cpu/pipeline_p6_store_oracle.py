#!/usr/bin/env python3
"""Independent P6 qualification; generated fixtures and logs stay under --out."""
from pathlib import Path
import argparse
import subprocess, sys
r = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, default=r/'scratch/pipeline_p6')
args = parser.parse_args()
root_out = args.out.resolve()
root_out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(r/'scripts/cpu'))
from pipeline_prototype import workload,encode
import pipeline_address_oracle as address
out=root_out/'store_oracle';out.mkdir(exist_ok=True)
rtl=r/'rtl/ap68040/rtl';exp=r/'rtl/ap68040/experimental';module=exp/'ap040_pipeline_integer.sv'
regs=[0]*16;ccr=0;pc=0x400;code=[];rows=[];requests=[]
def emit(kind,*args):
 global pc,ccr
 at=pc;ext=0;pc+=2
 if kind=='q':
  dest,v=args;word=0x7000+(dest<<9)+(v&255);regs[dest]=v&0xffffffff
  ccr=(ccr&16)|(8 if v<0 else 4 if v==0 else 0)
 elif kind=='a':
  src,dest=args;word=0x2040+(dest<<9)+src;regs[8+dest]=regs[src]
 elif kind in ('double','one'):
  dest,=args;old=regs[dest];v=old if kind=='double' else 1
  word=(0xd080+(dest<<9)+dest) if kind=='double' else 0x5280+dest
  full=old+v;result=full&0xffffffff;regs[dest]=result
  ccr=(17 if full>0xffffffff else 0)|(8 if result&0x80000000 else 4 if result==0 else 0)
  if (~(old^v)&(result^old))&0x80000000:ccr|=2
 elif kind=='load':
  base,index,long,scale,disp,dest,size=args
  word=({0:1,1:3,2:2}[size]<<12)+(base<<9)+(6<<6)+dest
  ext=(index<<12)+(long<<11)+(scale<<9)+(disp&255);pc+=2
  ix=regs[index] if long else ((regs[index]&65535)^32768)-32768
  addr=(regs[8+base]+ix*(1<<scale)+disp)&0xffffffff
  data=regs[dest]
  requests.append((at,addr,data,size))
  masked=data&((1 << (8 << size))-1)
  ccr=(ccr&16)|(8 if masked&(1 << ((8 << size)-1)) else 4 if masked==0 else 0)
 else:raise AssertionError(kind)
 code.append((at,word,ext));rows.append(f'{at:08x} {word:04x} {ccr:02x}'+''.join(f' {v:08x}' for v in regs))
def constant(dest,value):
 emit('q',dest,0)
 for bit in range(31,-1,-1):
  emit('double',dest)
  if value&(1<<bit):emit('one',dest)
for i,v in enumerate((0x8001,0x10001,0xdead8001,0x80000000,0xffffffff,0x7fffffff,0x1234ffff,0)):
 constant(i,v)
for base in range(8):
 for index in range(16):
  for long in (0,1):
   for scale in range(4):
    for kind in range(5):
     emit('a',(base+index)%8,base)
     if index>=8:emit('a',(index+scale)%8,index-8)
     dest=(base+index+scale)%8+(8 if kind in (1,2) else 0)
     emit('load',base,index,long,scale,(-128,-1,0,127)[(base+index+scale+long)%4],dest,2 if kind in (0,1) else 1 if kind in (2,3) else 0)
assert len(code)<32768
(out/'instructions.hex').write_text('\n'.join(f'{at:08x}{op:04x}{ext:04x}' for at,op,ext in code)+'\n')
(out/'requests.hex').write_text('\n'.join(f'{at:08x}{addr:08x}{data:08x}{sz:x}' for at,addr,data,sz in requests)+'\n')
(out/'oracle.trace').write_text('\n'.join(rows)+'\n')
supported={encode(op) for op in workload()}|{address.encode(op) for op in address.workload()}|set(range(0x4870,0x4878))
for src in range(16):
 for dst in range(8):
  for sz in ((1,2,3) if src<8 else (2,3)):
   for mode in (2,3,4,6):supported.add((sz<<12)+(dst<<9)+(mode<<6)+src)
for base in range(8):
 for dest in range(16):
  for size in ((2,3) if dest>=8 else (1,2,3)):
   supported.add((size<<12)+((dest&7)<<9)+(64 if dest>=8 else 0)+0x30+base)
(out/'supported.hex').write_text('\n'.join(str(int(w in supported)) for w in range(65536))+'\n')
s=(exp/'tb_pipeline_pea.sv').read_text().replace('.ENABLE_PEA(1))','.ENABLE_PEA(1), .ENABLE_INDEXLOAD(1))')
tb=out/'tb.sv';tb.write_text(s)
with (out/'compile.log').open('w') as f:
 subprocess.run(['iverilog','-g2012','-I',str(rtl),'-s','tb_pipeline_pea','-o',str(out/'test.vvp'),str(tb),str(module),str(rtl/'ap040_regfile.v'),str(rtl/'ap040_alu.v')],stdout=f,stderr=subprocess.STDOUT,check=True)
for mode in (0,1):
 for delay in (0,1,3,8):
  name=f'm{mode}_d{delay}'
  cmd=['vvp',str(out/'test.vvp'),'+program='+str(out/'instructions.hex'),'+trace='+str(out/(name+'.trace')),'+count='+str(len(code)),'+registers=16','+mode='+str(mode),'+delay='+str(delay),'+stores='+str(out/'requests.hex'),'+requests='+str(len(requests)),'+supported='+str(out/'supported.hex'),f'+end_pc={pc:x}']
  with (out/(name+'.log')).open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
  got=(out/(name+'.trace')).read_text().splitlines()
  assert got==rows,next(((i,x,y) for i,(x,y) in enumerate(zip(got,rows)) if x!=y),(len(got),len(rows)))
  print(name,len(code),'retirements',len(requests),'indexed stores PASS',flush=True)
