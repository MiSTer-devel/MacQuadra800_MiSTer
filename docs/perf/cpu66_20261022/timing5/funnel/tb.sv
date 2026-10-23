module tb;
import ap68040_pkg::*;
logic [6:0] op;
logic [7:0] shk;
logic [1:0] sz;
logic [31:0] a,b,r0,r1;
logic [5:0] cnt,nxq,nx0,nx1;
logic [6:0] nxlq,nxl0,nxl1;
logic [4:0] fi,f0,f1;
logic c0,c1;
ap68040_alu_slow_ref refalu(.op(op),.shk(shk),.sz(sz),.a(a),.b(b),.cnt(cnt),.nx_q(nxq),.nx(nx0),.nxl_q(nxlq),.nxl(nxl0),.flags_in(fi),.res(r0),.flags_out(f0),.sim_c(c0));
ap68040_alu_slow dut(.op(op),.shk(shk),.sz(sz),.a(a),.b(b),.cnt(cnt),.nx_q(nxq),.nx(nx1),.nxl_q(nxlq),.nxl(nxl1),.flags_in(fi),.res(r1),.flags_out(f1),.sim_c(c1));
integer checked=0;
logic [31:0] rng=32'h66a19933;
function automatic logic[31:0] randword();
 rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);return rng;
endfunction
task automatic check;
 #1;nxq=nx0;nxlq=nxl0;#1;
 if({r0,f0,c0,nx0,nxl0} !== {r1,f1,c1,nx1,nxl1})
  $fatal(1,"FAIL funnel op=%0d sz=%0d cnt=%0d b=%h flags=%b expected=%h/%b got=%h/%b",op,sz,cnt,b,fi,r0,f0,r1,f1);
 checked++;
endtask
initial begin
 for(int o=0;o<128;o++) begin
  op=7'(o);shk={op==OP_ROXR,op==OP_ROXL,op==OP_ROR,op==OP_ROL,op==OP_LSR,op==OP_ASR,op==OP_LSL,op==OP_ASL};
  for(int z=0;z<4;z++) for(int n=0;n<64;n++) for(int f=0;f<32;f++) begin
   sz=2'(z);cnt=6'(n);fi=5'(f);a=randword();b=randword();nxq=0;nxlq=0;check();
  end
 end
 $display("PASS: ALU funnel differential %0d vectors, all op/size/count/flag combinations",checked);$finish;
end
endmodule
