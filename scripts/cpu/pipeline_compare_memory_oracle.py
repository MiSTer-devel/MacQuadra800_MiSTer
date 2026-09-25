#!/usr/bin/env python3
"""Compare extension qualification; generated fixtures and logs stay under --out."""
from pathlib import Path
import argparse
import subprocess, sys
r = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, default=r/'scratch/pipeline_compare')
parser.add_argument('--pipeline-module',type=Path,default=r/'rtl/ap68040/experimental/ap040_pipeline_integer.sv')
parser.add_argument('--indirect-tst',action='store_true',help='also qualify byte/word/long TST (An)')
parser.add_argument('--fast-read-retire',action='store_true',help='also test acknowledgement-edge retirement')
parser.add_argument('--multiply',action='store_true',help='qualify indexed word multiply semantics and opcode admission')
parser.add_argument('--indirect-add',action='store_true',help='qualify byte/word/long ADD (An),Dn')
args = parser.parse_args()
root_out = args.out.resolve()
root_out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(r/'scripts/cpu'))
from pipeline_prototype import workload,encode
import pipeline_address_oracle as address
out=root_out/'load_oracle';out.mkdir(exist_ok=True)
rtl=r/'rtl/ap68040/rtl';exp=r/'rtl/ap68040/experimental';module=args.pipeline_module.resolve()
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
 elif kind=='tst':
  base,size,data=args
  word=0x4a10+(size<<6)+base
  addr=regs[8+base];requests.append((at,addr,data,size))
  sign=1<<((8<<size)-1)
  ccr=(ccr&16)|(8 if data&sign else 4 if data==0 else 0)
 elif kind=='memadd':
  base,dest,size,data=args
  bits=8<<size;mask=(1<<bits)-1;sign=1<<(bits-1)
  word=0xd010+(dest<<9)+(size<<6)+base
  requests.append((at,regs[8+base],data,size))
  old=regs[dest]&mask;total=old+data;value=total&mask
  left=old-(1<<bits) if old&sign else old
  right=data-(1<<bits) if data&sign else data
  overflow=not(-sign<=left+right<sign)
  ccr=(17 if total>mask else 0)|(8 if value&sign else 4 if value==0 else 0)|(2 if overflow else 0)
  regs[dest]=(regs[dest]&~mask)|value
 elif kind=='mul':
  base,index,long,scale,disp,dest,signed=args
  ext=(index<<12)+(long<<11)+(scale<<9)+(disp&255);pc+=2
  word=(0xc1f0 if signed else 0xc0f0)+(dest<<9)+base
  ix=regs[index] if long else ((regs[index]&65535)^32768)-32768
  addr=(regs[8+base]+ix*(1<<scale)+disp)&0xffffffff
  data=((addr^0x8123a5c7)*0x9e3779b1)&65535
  requests.append((at,addr,data,1))
  left=((data^32768)-32768) if signed else data
  right=regs[dest]&65535
  if signed:right=(right^32768)-32768
  result=(left*right)&0xffffffff;regs[dest]=result
  ccr=(ccr&16)|(8 if result&0x80000000 else 4 if result==0 else 0)
 elif kind=='load':
  base,index,long,scale,disp,dest,size=args
  which=(base+index+scale+long)%4
  if which==2:which=3
  if which<2:dest&=7
  at_old=regs[dest]
  ext=(index<<12)+(long<<11)+(scale<<9)+(disp&255);pc+=2
  ix=regs[index] if long else ((regs[index]&65535)^32768)-32768
  addr=(regs[8+base]+ix*(1<<scale)+disp)&0xffffffff
  if which==0:word=0xb030+(dest<<9)+(size<<6)+base
  elif which==1:word=0x4a30+(size<<6)+base
  else:
   word=((1 if size==0 else 3 if size==1 else 2)<<12)+((dest&7)<<9)+(64 if dest>=8 else 0)+(0x28 if which==2 else 0x30)+base
   if which==2:
    displacement=(-32768,-257,-1,0,1,256,32767)[(index+scale)%7]
    ext=displacement&65535;addr=(regs[8+base]+displacement)&0xffffffff
  mask=(1 << (8 << size))-1;sign=1 << ((8 << size)-1)
  data=((addr^0x8123a5c7)*0x9e3779b1)&mask
  requests.append((at,addr,data,size))
  if which==0:
   old=at_old&mask;result=(old-data)&mask
   ccr=(ccr&16)|(8 if result&sign else 4 if result==0 else 0)|(2 if (old^data)&(old^result)&sign else 0)|(1 if data>old else 0)
  elif which==1:ccr=(ccr&16)|(8 if data&sign else 4 if data==0 else 0)
  else:
   regs[dest]=((((data^32768)-32768)&0xffffffff) if size==1 else data) if dest>=8 else ((regs[dest]&~mask)|data)
   if dest<8:ccr=(ccr&16)|(8 if data&sign else 4 if data==0 else 0)
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
if args.indirect_tst:
 for base in range(8):
  for size in range(3):
   sign=1<<((8<<size)-1)
   for value in (0,1,sign-1,sign,2*sign-1):
    for extend in (False,True):
     constant(0,0xffffffff if extend else 0)
     if extend:emit('double',0)
     emit('a',0,base)
     emit('tst',base,size,value)
if args.multiply:
 for base in range(8):
  emit('q',0,-1);emit('double',0);emit('a',0,base)
  for dest in range(8):
   emit('q',dest,-3)
   for signed in (False,True):
    for long in (0,1):
     for scale in range(4):
      emit('mul',base,(base+dest)%16,long,scale,(-128,-1,0,127)[scale],dest,signed)
if args.indirect_add:
 for base in range(8):
  emit('q',0,-1);emit('a',0,base)
  for dest in range(8):
   for size in range(3):
    emit('q',dest,-1)
    sign=1<<((8<<size)-1)
    for data in (0,1,sign-1,sign,2*sign-1,2*sign-2):emit('memadd',base,dest,size,data)
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
for base in range(8):
 for size in range(3):
  supported.add(0x4a00+(size<<6)+base)
  supported.add(0x4a30+(size<<6)+base)
  for dest in range(8):supported.add(0xb030+(dest<<9)+(size<<6)+base)
 for dest in range(16):
  for size in ((2,3) if dest>=8 else (1,2,3)):
   supported.add((size<<12)+((dest&7)<<9)+(64 if dest>=8 else 0)+0x28+base)
for src in range(16):
 for dest in range(8):
  for sz in ((1,2,3) if src<8 else (2,3)):
   supported.add((sz<<12)+(dest<<9)+(5<<6)+src)
for base in range(8):
 for dest in range(16):
  for size in ((2,3) if dest>=8 else (1,2,3)):
   supported.discard((size<<12)+((dest&7)<<9)+(64 if dest>=8 else 0)+0x28+base)
for src in range(16):
 for dest in range(8):
  for size in ((1,2,3) if src<8 else (2,3)):
   supported.discard((size<<12)+(dest<<9)+(5<<6)+src)
if args.indirect_tst:
 supported.update(0x4a10+(size<<6)+base for size in range(3) for base in range(8))
if args.multiply:
 supported.update(base+(dest<<9)+opcode for base in range(8) for dest in range(8) for opcode in (0xc0f0,0xc1f0))
if args.indirect_add:
 supported.update(0xd010+(dest<<9)+(size<<6)+base for base in range(8) for dest in range(8) for size in range(3))
(out/'supported.hex').write_text('\n'.join(str(int(w in supported)) for w in range(65536))+'\n')
s=(exp/'tb_pipeline_pea.sv').read_text().replace('.ENABLE_PEA(1))','.ENABLE_PEA(1), .ENABLE_INDEXLOAD(1), .ENABLE_COMPARE(1))')
if args.fast_read_retire:s=s.replace('.ENABLE_COMPARE(1))', '.ENABLE_COMPARE(1), .ENABLE_FAST_READ_RETIRE(1))')
s=s.replace('.empty_after_retire(), .*', '.empty_after_retire(), .retire_wb_valid(), .retire_branch_taken(), .*')
s=s.replace(".load_data(32'd0)", '.load_data(response_data)')
s=s.replace('reg load_ack=0,pending=0;', "reg [31:0] response_data=0;\n    reg load_ack=0,pending=0;")
s=s.replace('if(!load_write) $fatal(1,"unexpected read");', 'if(load_write) $fatal(1,"unexpected write");')
s=s.replace("held={load_pc,load_addr,load_wdata,2'b0,load_size};", "held={load_pc,load_addr,expected_stores[req_count][35:4],2'b0,load_size};\n                    response_data=held[35:4];")
s=s.replace("{load_pc,load_addr,load_wdata,2'b0,load_size}", "{load_pc,load_addr,held[35:4],2'b0,load_size}")
s=s.replace('        extension_valid=1;\n        fd =', '''        for(i=0;i<8;i=i+1) begin
            in_opcode=16'h3070+i; extension=16'h0100; extension_valid=1;
            #1;if(in_supported) $fatal(1,"full indexed-load extension admitted");
            extension=0; extension_valid=0;
            #1;if(in_supported) $fatal(1,"missing indexed-load extension admitted");
        end
        extension_valid=1;
        fd =''')
if args.multiply:
 s=s.replace('        extension_valid=1;\n        fd =', """        for(i=0;i<128;i=i+1) begin
            in_opcode=16'hc0f0+((i/16)<<9)+((i%16)/8)*256+(i%8);
            extension=16'h0100; extension_valid=1;
            #1;if(in_supported) $fatal(1,"full multiply extension admitted");
            extension=0; extension_valid=0;
            #1;if(in_supported) $fatal(1,"missing multiply extension admitted");
        end
        extension_valid=1;
        fd =""")
if args.fast_read_retire:
 s=s.replace('endmodule', '    integer fast_read_commits=0;\n    always @(posedge clk) if(dut.fast_read_retire) fast_read_commits++;\n    final begin\n        $display("FAST_READ commits=%0d",fast_read_commits);\n        if(delay>0 && fast_read_commits==0) $fatal(1,"fast read retirement was not exercised");\n    end\nendmodule')
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
  print(name,len(code),'retirements',len(requests),'memory reads PASS',flush=True)
