// Differential qualification for pipeline_subset_alu.patch.
// Compile with the candidate ALU and an original renamed ap040_alu_reference.
`timescale 1ns/1ps
module tb;
reg [5:0] op=0,shcnt=0;
reg [1:0] size=0;
reg [31:0] a=0,b=0;
reg [4:0] flags_in=0;
wire [31:0] result,ref_result;
wire [4:0] flags_out,fast_flags,ref_flags,ref_fast;
wire fast_ok,ref_ok;
ap040_alu #(.PIPELINE_SUBSET(1)) dut(.*);
ap040_alu_reference refalu(.op(op),.size(size),.shcnt(shcnt),.a(a),.b(b),.flags_in(flags_in),.result(ref_result),.flags_out(ref_flags),.fast_flags(ref_fast),.fast_ok(ref_ok));
integer o,s,c,f,i,checks=0,seed=20260920;
initial begin
for(o=0;o<=28;o=o+1) if(o==0||o==1||o==3||o==5||o==6||o==7||o==8||o==13||o>=21)
 for(s=0;s<3;s=s+1) for(c=0;c<64;c=c+1) for(f=0;f<32;f=f+1)
  for(i=0;i<4;i=i+1) begin
   op=o;size=s;shcnt=c;flags_in=f;
   a=$random(seed);b=$random(seed);
   if(i==0) begin a=0;b=0;end
   if(i==1) begin a=32'hffffffff;b=32'h80008080;end
   #1;
   if({result,flags_out,fast_flags,fast_ok} !== {ref_result,ref_flags,ref_fast,ref_ok})
    $fatal(1,"subset mismatch op=%d size=%d count=%d flags=%h a=%h b=%h",op,size,shcnt,flags_in,a,b);
   checks=checks+1;
  end
$display("PASS subset equivalence %0d comparisons",checks);$finish;
end
endmodule
