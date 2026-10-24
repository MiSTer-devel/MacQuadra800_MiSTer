#!/usr/bin/env python3
# fp_store_trace 2026-10-24: add a per-cycle trace to a SCRATCH copy of the
# shipping core's program bench (docs/perf/fp_attribution_20261024/scripts/
# tb_wombat_prog.sv): +fstag=<n> +fslen=<cycles> prints, from the cycle after
# the stamp with tag <n>, the sequencer state, the dispatched instruction's
# address, the FPU handshake (fpu_req, fpu_done, fpu_accepted, fpu_bg, the
# FPU's fst), the store loop (fp_st, fp_n), the memory issue (mgo/mgo_wr) and
# the bus (req, wr, addr, ack).  Nothing in the core changes.
import sys
src = open(sys.argv[1]).read()

anchor = " initial begin\n  if(!$value$plusargs(\"prog=%s\",path))"
assert src.count(anchor) == 1, "anchor not found"
block = ''' // fp_store_trace: +fstag=<n>,+fslen=<cycles>: one line a cycle from the stamp
 integer fs_tag=-1, fs_len=400, fs_from=-1, fs_to=-1;
 initial begin
  if(!$value$plusargs("fstag=%d",fs_tag)) fs_tag=-1;
  if(!$value$plusargs("fslen=%d",fs_len)) fs_len=400;
 end
 always @(posedge clk) if(nreset && fs_from>=0 && cycles>=fs_from && cycles<fs_to)
  $display("%8d st=%0d pc=%08x | fp req=%b done=%b acc=%b bg=%b fst=%0d st=%b n=%0d | mgo=%b wr=%b | bus req=%b wr=%b a=%08x sz=%0d ack=%b | disp=%b",
   cycles, dut.core.state, dut.core.pc_i, dut.core.fpu_req, dut.core.fpu_done, dut.core.fpu_accepted,
   dut.core.fpu_bg, dut.core.g_fpu.fpu.fst, dut.core.fp_st, dut.core.fp_n, dut.core.mgo, dut.core.mgo_wr,
   req, wr, addr, size, ack, dut.core.perf_dispatch_toggle);
'''
src = src.replace(anchor, block + anchor)

old_stamp = '''     $display("STAMP tag=%04x cycles=%0d bus_transactions=%0d dispatches=%0d",saved_data[15:0],cycles-stamp_prev,nacc,ndisp);
'''
new_stamp = '''     $display("STAMP tag=%04x cycles=%0d bus_transactions=%0d dispatches=%0d at=%0d",saved_data[15:0],cycles-stamp_prev,nacc,ndisp,cycles);
     if(fs_tag>=0 && fs_from<0 && saved_data[15:0]==fs_tag[15:0]) begin fs_from=cycles+1; fs_to=fs_from+fs_len; $display("%8d FSTRACE start: stamp tag %04x",cycles,fs_tag[15:0]); end
'''
assert src.count(old_stamp) == 1, "STAMP display not found"
src = src.replace(old_stamp, new_stamp)
open(sys.argv[2], "w").write(src)
print("patched", sys.argv[2])
