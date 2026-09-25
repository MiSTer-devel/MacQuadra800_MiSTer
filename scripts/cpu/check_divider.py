from pathlib import Path
import argparse,hashlib,json,random,subprocess
parser=argparse.ArgumentParser(description="Check division against Python integer arithmetic, including signed overflow and CE stalls.")
parser.add_argument('--module',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True)
mode=parser.add_mutually_exclusive_group()
mode.add_argument('--bounded-high',action='store_true',help='expect eight skipped rounds when upper dividend magnitude is below divisor magnitude')
mode.add_argument('--short-dividend',action='store_true',help='expect eight skipped rounds for dividend magnitudes below 2**32')
args=parser.parse_args()
out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
module=args.module.resolve()
(out/'identity.json').write_text(json.dumps({'module':str(module),'sha256':hashlib.sha256(module.read_bytes()).hexdigest(),'short_dividend':args.short_dividend,'bounded_high':args.bounded_high,'seed':20260920},indent=2))
rng=random.Random(20260920)
cases=[]
edge=[0,1,2,3,0x7fff,0x8000,0xffff,0x10000,0x7fffffff,0x80000000,0xffffffff,0x100000000,0x7fffffffffffffff,0x8000000000000000,0xffffffffffffffff]
for sign in [0,1]:
 for a in edge[:11]:
  if a:
   for d in edge: cases.append((sign,a,d))
 for i in range(12000):
  a=rng.getrandbits(32) or 1
  d=rng.getrandbits([16,32,64][i%3])
  if sign and i%2: d=(-d)&((1<<64)-1)
  cases.append((sign,a,d))
# Exercise the short/full boundary explicitly, including nonzero seeded
# remainders and low words at both carry extremes.
for sign in [0,1]:
 for a in edge[1:11]:
  aa=a-(1<<32) if sign and a>>31 else a
  for upper in [abs(aa)-1,abs(aa),abs(aa)+1]:
   if upper >= (1<<32): continue
   for lower in [0,1,0xffffffff]:
    d=(upper<<32)|lower
    cases.append((sign,a,d))
    if sign: cases.append((sign,a,(-d)&((1<<64)-1)))
lines=[]
for sign,a,d in cases:
 aa=a-(1<<32) if sign and a>>31 else a
 dd=d-(1<<64) if sign and d>>63 else d
 q=abs(dd)//abs(aa)
 if (aa<0)!=(dd<0):q=-q
 rem=dd-q*aa
 ov=not (-(1<<31)<=q<(1<<31)) if sign else not (0<=q<(1<<32))
 fast=(args.short_dividend and abs(dd)<(1<<32)) or (args.bounded_high and (abs(dd)>>32)<abs(aa))
 lines.append(f'{sign:x}{a:08x}{d:016x}{q&0xffffffff:08x}{rem&0xffffffff:08x}{int(ov):x}{int(fast):x}')
(out/'vectors.hex').write_text('\n'.join(lines)+'\n')
tb='''`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg nreset=0,ce=1,start=0,sign_op=0;
reg [31:0] a=0,hi=0,lo=0;
wire done;wire [31:0] q,r;wire ovf;
ap040_muldiv dut(.clk(clk),.nreset(nreset),.ce(ce),.start(start),.is_div(1'b1),.sign_op(sign_op),.op_a(a),.op_hi(hi),.op_lo(lo),.done(done),.res_hi(r),.res_lo(q),.ovf(ovf));
reg [171:0] vectors[0:COUNT-1];
reg [31:0] eq,er;reg eo,fast;integer i,ticks,wall,shorts=0,longs=0;
initial begin
$readmemh("VECTORS",vectors);
repeat(2) @(negedge clk);nreset=1;
for(i=0;i<COUNT;i=i+1) begin
{sign_op,a,hi,lo,eq,er,eo,fast}={vectors[i][168],vectors[i][167:136],vectors[i][135:104],vectors[i][103:72],vectors[i][71:40],vectors[i][39:8],vectors[i][4],vectors[i][0]};
start=1;ce=1;@(negedge clk);start=0;ticks=0;wall=0;
while(!done) begin
ce=(wall%4)!=2;wall=wall+1;
if(ce) ticks=ticks+1;
@(negedge clk);
if(wall>40) $fatal(1,"timeout vector %0d",i);
end
if(q!==eq || r!==er || ovf!==eo) $fatal(1,"arithmetic vector %0d q=%h/%h r=%h/%h ov=%b/%b",i,q,eq,r,er,ovf,eo);
if(ticks != (fast ? 9:17)) $fatal(1,"latency vector %0d ticks=%0d fast=%b",i,ticks,fast);
if(fast) shorts++;else longs++;
ce=1;@(negedge clk);
end
$display("DIVIDER PASS vectors=%0d short=%0d full=%0d ce_stalls=PASS",COUNT,shorts,longs);$finish;
end
endmodule
'''.replace('COUNT',str(len(cases))).replace('VECTORS',str(out/'vectors.hex'))
(out/'tb.sv').write_text(tb)
subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/'test.vvp'),str(out/'tb.sv'),str(module)],check=True)
r=subprocess.run(['vvp',str(out/'test.vvp')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(out/'check.log').write_text(r.stdout);print(r.stdout);r.check_returncode()
