#!/usr/bin/env python3
"""Check extracted refill valid-run logic against an independent bounded scan."""
import argparse,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--core',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=True)
s=a.core.read_text();m=re.search(r'reg\s*\[(\d+):0\]\s+brf_valid;',s);assert m
words=int(m[1])+1
start=s.index('reg  [3:0] brf_run');end=s.index('// Combinational within',start)
logic=s[start:end]
tb=f'''`timescale 1ns/1ps
module tb;
reg [{words-1}:0] brf_valid;
{logic}
integer i,j,k,expected,checked=0,base,pattern,outer;
reg stopped;
reg [{words-1}:0] window_mask;
task check;
begin
 #1;
 for(i=0;i<{words};i=i+1) begin
  expected=0;stopped=0;
  for(j=0;j<8;j=j+1) begin
   if(i+j>={words}) stopped=1;
   else if(!brf_valid[i+j]) stopped=1;
   if(!stopped) expected=expected+1;
  end
  if(brf_run[i] !== expected[3:0]) $fatal(1,"valid=%h index=%0d actual=%0d expected=%0d",brf_valid,i,brf_run[i],expected);
 end
 checked++;
end
endtask
initial begin
 brf_valid=0;check;
 brf_valid='1;check;
 // Exhaust all eight-bit windows at every word, with both zero and one
 // surroundings. This includes every end-of-sector truncation pattern.
 for(base=0;base<{words};base=base+1)
  for(outer=0;outer<2;outer=outer+1)
   for(pattern=0;pattern<256;pattern=pattern+1) begin
    window_mask={words}'hff << base;
    brf_valid=outer ? ~window_mask : 0;
    brf_valid=brf_valid | ({words}'(pattern) << base);
    check;
   end
 for(k=0;k<10000;k=k+1) begin
  brf_valid={{ $random, $random, $random, $random }};
  check;
 end
 $display("REFILL_RUN_LENGTHS PASS patterns=%0d words={words}",checked);$finish;
end
endmodule
'''
(d/'tb.sv').write_text(tb)
for cmd,name in [(['iverilog','-g2012','-s','tb','-o',d/'test.vvp',d/'tb.sv'],'compile.log'),(['vvp',d/'test.vvp'],'run.log')]:
 with (d/name).open('w') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
log=(d/'run.log').read_text();assert 'REFILL_RUN_LENGTHS PASS' in log;print(log.strip())
