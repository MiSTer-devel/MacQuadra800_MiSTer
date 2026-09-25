"""Cycle-write miter for the early dgo BRF payload selector.

Run with --core pointing at the candidate AP040 core and --out at a fresh
scratch directory. The generated bench extracts the candidate's actual early
selector wires and final seed block, then checks them against an independent
linear-halfword oracle.
"""
import argparse
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--core', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--negative-control', action='store_true', help='also prove a lane-select +1 mutation is rejected')
args=parser.parse_args()
out=args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
src=args.core.read_text()
start=src.index('wire [3:0] dbrf_seed_n_early')
end=src.index('end endgenerate',start)+len('end endgenerate')
wires=src[start:end]
# Extract the exact final seed body, but bind its temporary data registers from the testbench.
bs=src.index('\t\tif (brf_seed_req) begin : brf_seed_data')
be=src.index('\n\t\t// Queue bookkeeping',bs)
block=src[bs:be]
# Strip core-block indentation for embedding and drop the named begin scope only via direct text use.
header='''`timescale 1ns/1ps
module tb;
reg clk=0; always #5 clk=~clk;
reg [31:0] dbrf_a_early=0;
reg [31:0] brf_data [0:15];
reg [3:0] brf_run [0:31];
reg [4:0] brf_seed_a=0;
reg [3:0] brf_seed_n=0;
reg brf_seed_req=0, dgo=0;
reg [15:0] epf_data [0:7];
reg append=0; reg [2:0] append_slot=0; reg [15:0] append_value=16'hdada;
integer seed=32'h52a9c731, trial, addr, n, i, lane, row, idx, cases=0;
reg [15:0] expected [0:7];
'''
# Replace only whitespace? retain exact candidate RTL text.
tb=header+wires+'\n'
tb+='''always @(posedge clk) begin
 if (append) epf_data[append_slot] <= append_value;
'''+block+'''
end

task check_seed;
 integer k, half_idx, word_idx;
 begin
  // Allow the candidate combinational run-count mux to settle after the
  // test updates target/run at negedge.
  #1;
  if(dgo && brf_seed_req && (brf_seed_a !== dbrf_a_early[5:1] || brf_seed_n !== dbrf_seed_n_early))
   $fatal(1,"dgo seed precondition mismatch a=%h early=%h n=%0d early_n=%0d",brf_seed_a,dbrf_a_early[5:1],brf_seed_n,dbrf_seed_n_early);
  // Independent reference: linear halfword address, wrapped within the
  // 32-halfword/64-byte sector, then select upper/lower half of its longword.
  for(k=0;k<8;k=k+1) begin
   half_idx=(brf_seed_a+k)&31;
   word_idx=half_idx>>1;
   if(k<brf_seed_n)
    expected[k]=half_idx[0] ? brf_data[word_idx][15:0] : brf_data[word_idx][31:16];
   else expected[k]=epf_data[k];
  end
  @(posedge clk); #1;
  for(k=0;k<8;k=k+1) begin
   if(k<brf_seed_n && epf_data[k] !== expected[k])
    $fatal(1,"seed mismatch dgo=%0d target=%h seed=%h n=%0d slot=%0d got=%h want=%h",dgo,dbrf_a_early,brf_seed_a,brf_seed_n,k,epf_data[k],expected[k]);
   if(k>=brf_seed_n && !(append && append_slot==k) && epf_data[k] !== 16'h5aa5)
    $fatal(1,"masked slot changed target=%h n=%0d slot=%0d got=%h",dbrf_a_early,brf_seed_n,k,epf_data[k]);
   if(k>=brf_seed_n && append && append_slot==k && epf_data[k] !== append_value)
    $fatal(1,"masked slot lost append target=%h n=%0d slot=%0d got=%h",dbrf_a_early,brf_seed_n,k,epf_data[k]);
  end
  cases=cases+1;
 end
endtask

initial begin
 // Sweep all 32 halfword positions, all output lengths, and randomized BRF contents.
 for(trial=0;trial<64;trial=trial+1) begin
  for(i=0;i<16;i=i+1) brf_data[i]={$random(seed),$random(seed)};
  for(addr=0;addr<32;addr=addr+1) begin
   for(n=0;n<=8;n=n+1) begin
    @(negedge clk);
    dbrf_a_early=(addr<<1); brf_seed_a=addr; brf_seed_n=n;
    brf_run[addr]=n; dgo=1; brf_seed_req=1; append=0;
    for(i=0;i<8;i=i+1) epf_data[i]=16'h5aa5;
    check_seed();
    // Same-cycle append and seed: final seed assignment must retain priority.
    @(negedge clk); append=1; append_slot=n<8?n:7; append_value=16'hc000|addr;
    for(i=0;i<8;i=i+1) epf_data[i]=16'h5aa5;
    check_seed();
    // Generic (non-dgo) seed must remain the original lane path.
    @(negedge clk); append=0; dgo=0; brf_seed_req=1; brf_seed_a=addr; brf_seed_n=n;
    for(i=0;i<8;i=i+1) epf_data[i]=16'h5aa5;
    check_seed();
   end
  end
 end
 // dgo with no seed request is a same-stream no-op, even though its target/count wires toggle.
 @(negedge clk); dgo=1; brf_seed_req=0; dbrf_a_early=32'h3e; brf_run[31]=8;
 for(i=0;i<8;i=i+1) epf_data[i]=16'h5aa5;
 @(posedge clk); #1;
 for(i=0;i<8;i=i+1) if(epf_data[i]!==16'h5aa5) $fatal(1,"no-op dgo wrote slot=%0d",i);
 $display("DGO_BRF_MITER PASS cases=%0d target_positions=32 counts=0..8 trials=64 generic=covered append_priority=covered no_seed_noop=covered",cases);
 $finish;
end
endmodule
'''
tb_path=out/'tb_early_miter.sv'
tb_path.write_text(tb)
with (out/'compile.log').open('w') as f:
 subprocess.run(['iverilog','-g2012','-s','tb','-o',out/'early.vvp',tb_path],stdout=f,stderr=subprocess.STDOUT,check=True)
with (out/'run.log').open('w') as f:
 subprocess.run(['vvp',out/'early.vvp'],stdout=f,stderr=subprocess.STDOUT,check=True)
run_text=(out/'run.log').read_text()
if 'DGO_BRF_MITER PASS cases=55296' not in run_text:
 raise SystemExit('positive miter summary missing; see '+str(out/'run.log'))
print(run_text.strip())
if args.negative_control:
 negative=out/'tb_early_miter_negative.sv'
 mutated=tb.replace('dbrf_a_early[3:1] + dbrf_lane;', 'dbrf_a_early[3:1] + dbrf_lane + 1;')
 if mutated==tb: raise SystemExit('negative-control mutation point not found')
 negative.write_text(mutated)
 with (out/'negative_compile.log').open('w') as f:
  subprocess.run(['iverilog','-g2012','-s','tb','-o',out/'early_negative.vvp',negative],stdout=f,stderr=subprocess.STDOUT,check=True)
 with (out/'negative_run.log').open('w') as f:
  result=subprocess.run(['vvp',out/'early_negative.vvp'],stdout=f,stderr=subprocess.STDOUT)
 negative_text=(out/'negative_run.log').read_text()
 if result.returncode==0 or 'seed mismatch' not in negative_text:
  raise SystemExit('mutated lane selector was not rejected by the intended data check')
 print('NEGATIVE CONTROL PASS: lane-select +1 mutation rejected by seed mismatch')
