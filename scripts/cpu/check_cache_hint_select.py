#!/usr/bin/env python3
"""Check the candidate cache hint mux over every selector and data bit basis."""
import argparse
from pathlib import Path
import subprocess
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--cache',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=True)
s=a.cache.read_text()
start=s.index('wire [31:0] hint_word0')
end=s.index('// idle_hit without look_hit',start)
fragment=s[start:end]
bench='''module tb;
reg hh0,hh1,hh2,hh3;
reg [11:0] hq_lo;
reg [31:0] data_q0,data_q1,data_q2,data_q3;
'''+fragment+'''
reg [31:0] expected;
integer hits,offset,bitpos,way,array_index,count;
initial begin
count=0;
for(hits=0;hits<16;hits=hits+1) begin
 {hh3,hh2,hh1,hh0}=hits;
 for(offset=0;offset<4;offset=offset+1) begin
  hq_lo=offset<<2;
  for(bitpos=-1;bitpos<128;bitpos=bitpos+1) begin
   data_q0=0;data_q1=0;data_q2=0;data_q3=0;
   if(bitpos>=0) case(bitpos/32)
    0:data_q0=32'b1<<(bitpos%32);
    1:data_q1=32'b1<<(bitpos%32);
    2:data_q2=32'b1<<(bitpos%32);
    3:data_q3=32'b1<<(bitpos%32);
   endcase
   way=hh0?0:hh1?1:hh2?2:3;
   array_index=(way+offset)%4;
   case(array_index)
    0:expected=data_q0;1:expected=data_q1;
    2:expected=data_q2;3:expected=data_q3;
   endcase
   #1;
   if(hint_data_hit!==expected) $fatal(1,"hits=%h offset=%d bit=%d got=%h expected=%h",hits,offset,bitpos,hint_data_hit,expected);
   count=count+1;
  end
 end
end
$display("PASS %0d selector/data-basis cases",count);
$finish;
end
endmodule
'''
(d/'tb.sv').write_text(bench)
for cmd,name in [(['iverilog','-g2012','-s','tb','-o',str(d/'tb.vvp'),str(d/'tb.sv')],'compile.log'),(['vvp',str(d/'tb.vvp')],'run.log')]:
 with (d/name).open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
print((d/'run.log').read_text(),end='')
