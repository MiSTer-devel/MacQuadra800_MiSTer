#!/usr/bin/env python3
"""Independent P6 qualification; generated fixtures and logs stay under --out."""
from pathlib import Path
import argparse
import subprocess, sys
r = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, default=r/'scratch/pipeline_p6')
parser.add_argument('--module', type=Path, help='isolated pipeline candidate')
parser.add_argument('--alu', type=Path, help='isolated ALU candidate')
args = parser.parse_args()
root_out = args.out.resolve()
root_out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(r/'scripts/cpu'))
from pipeline_prototype import workload,encode
import pipeline_address_oracle as address
out=root_out/'alu_oracle';out.mkdir(exist_ok=True)
rtl=r/'rtl/ap68040/rtl';exp=r/'rtl/ap68040/experimental';module=args.module.resolve() if args.module else exp/'ap040_pipeline_integer.sv'
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
  word=({0:1,1:3,2:2}[size]<<12)+((dest&7)<<9)+(64 if dest>=8 else 0)+0x30+base
  ext=(index<<12)+(long<<11)+(scale<<9)+(disp&255);pc+=2
  ix=regs[index] if long else ((regs[index]&65535)^32768)-32768
  addr=(regs[8+base]+ix*(1<<scale)+disp)&0xffffffff
  data=((addr^0x8123a5c7)*0x9e3779b1)&0xffffffff
  data &= (1 << (8 << size))-1
  requests.append((at,addr,data,size))
  mask=(1 << (8 << size))-1
  regs[dest]=((((data^32768)-32768)&0xffffffff) if size==1 else data) if dest>=8 else ((regs[dest]&~mask)|data)
  if dest<8:ccr=(ccr&16)|(8 if data&(1 << ((8 << size)-1)) else 4 if data==0 else 0)
 else:raise AssertionError(kind)
 code.append((at,word,ext));rows.append(f'{at:08x} {word:04x} {ccr:02x}'+''.join(f' {v:08x}' for v in regs))
def constant(dest,value):
 emit('q',dest,0)
 for bit in range(31,-1,-1):
  emit('double',dest)
  if value&(1<<bit):emit('one',dest)
base_emit=emit
names=('asr','asl','lsr','lsl','roxr','roxl','ror','rol')
def emit(kind,*args):
 global pc,ccr
 if kind not in ('move','shift','lea'):return base_emit(kind,*args)
 at=pc;pc+=2;ext=0
 if kind=='move':
  src,dest=args;word=0x2000+(dest<<9)+src;regs[dest]=regs[src]
  ccr=(ccr&16)|(8 if regs[dest]&0x80000000 else 4 if regs[dest]==0 else 0)
 elif kind=='lea':
  base,dest,disp=args;word=0x41e8+(dest<<9)+base;ext=disp&65535;pc+=2
  regs[8+dest]=(regs[8+base]+disp)&0xffffffff
 else:
  name,size,src,dest,immediate,count=args;bits=8<<size;mask=(1<<bits)-1
  family=names.index(name)//2;left=names.index(name)&1
  field=count&7 if immediate else src
  word=0xe000+(field<<9)+(left<<8)+(size<<6)+(0 if immediate else 32)+(family<<3)+dest
  n=count if immediate else regs[src]&63
  value=regs[dest]&mask;x=(ccr>>4)&1;c=x if family==2 and n==0 else 0;overflow=0
  for step in range(n):
   old=value;carry=((old>>(bits-1))&1) if left else old&1
   if family<2:
    value=((old<<1)&mask) if left else ((old>>1)|((old&(1<<(bits-1))) if family==0 else 0))
    if family==0 and left:overflow|=((old^value)>>(bits-1))&1
    x=carry
   elif family==2:
    value=((old<<1)|x)&mask if left else (old>>1)|(x<<(bits-1));x=carry
   else:value=((old<<1)|carry)&mask if left else (old>>1)|(carry<<(bits-1))
   c=carry
  regs[dest]=(regs[dest]&~mask)|value
  ccr=(x<<4)|(8 if value&(1<<(bits-1)) else 4 if value==0 else 0)|(overflow<<1)|c
 code.append((at,word,ext));rows.append(f'{at:08x} {word:04x} {ccr:02x}'+''.join(f' {v:08x}' for v in regs))
for i,v in enumerate((0x80000001,0x7fffffff,0x1234abcd,0xffffffff,0x8001,0x10001,0,0x89abcdef)):constant(i,v)
for name in names:
 for size in range(3):
  for src in range(8):
   constant(7, 0x89abcdef)
   for dest in range(8):
    for count in (0,1,7,8,15,16,31,32,33,63):
     emit('move',7,dest);emit('q',src,count);emit('shift',name,size,src,dest,False,count)
  constant(6, 0x80000001)
  for dest in range(8):
   for count in range(1,9):
    emit('move',6,dest);emit('shift',name,size,0,dest,True,count)
for i,v in enumerate((0x80000001,0x7fffffff,0x1234abcd,0xffffffff,0x8001,0x10001,0,0x89abcdef)):
 constant(i,v);emit('a',i,i)
for base in range(8):
 for dest in range(8):
  for disp in (-32768,-257,-1,0,1,256,32767):emit('lea',base,dest,disp)
for i in range(64):emit('lea',7,7,32767 if i&1 else -32768)
supported={encode(op) for op in workload()}|{address.encode(op) for op in address.workload()}|set(range(0x4870,0x4878))
for src in range(16):
 for dst in range(8):
  for sz in ((1,2,3) if src<8 else (2,3)):
   for mode in (2,3,4):supported.add((sz<<12)+(dst<<9)+(mode<<6)+src)
for countreg in range(8):
 for dest in range(8):
  for size in range(3):
   for kind in range(4):
    for left in range(2):
     for reg in range(2):supported.add(0xe000+(countreg<<9)+(left<<8)+(size<<6)+(reg<<5)+(kind<<3)+dest)
for base in range(8):
 for dest in range(8):supported.add(0x41e8+(dest<<9)+base)
(out/'instructions.hex').write_text('\n'.join(f'{at:08x}{op:04x}{ext:04x}' for at,op,ext in code)+'\n')
(out/'oracle.trace').write_text('\n'.join(rows)+'\n');(out/'requests.hex').write_text('0\n')
(out/'supported.hex').write_text('\n'.join(str(int(w in supported)) for w in range(65536))+'\n')
s=(exp/'tb_pipeline_pea.sv').read_text().replace('.ENABLE_PEA(1))','.ENABLE_PEA(1), .ENABLE_SHIFTS(1), .ENABLE_DISP_LEA(1))')
s=s.replace('code [0:32767]', 'code [0:131071]')
tb=out/'tb.sv';tb.write_text(s)
with (out/'compile.log').open('w') as f:subprocess.run(['iverilog','-g2012','-I',str(rtl),'-s','tb_pipeline_pea','-o',str(out/'test.vvp'),str(tb),str(module),str(rtl/'ap040_regfile.v'),str(args.alu.resolve() if args.alu else rtl/'ap040_alu.v')],stdout=f,stderr=subprocess.STDOUT,check=True)
for mode in (0,1,2,3,4,5):
 name=f'm{mode}'
 cmd=['vvp',str(out/'test.vvp'),'+program='+str(out/'instructions.hex'),'+trace='+str(out/(name+'.trace')),'+count='+str(len(code)),'+registers=16','+mode='+str(mode),'+delay=0','+stores='+str(out/'requests.hex'),'+requests=0','+supported='+str(out/'supported.hex'),f'+end_pc={pc:x}']
 with (out/(name+'.log')).open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 got=(out/(name+'.trace')).read_text().splitlines();assert got==rows,next(((i,x,y) for i,(x,y) in enumerate(zip(got,rows)) if x!=y),(len(got),len(rows)))
 print(name,len(code),'retirements PASS',flush=True)
