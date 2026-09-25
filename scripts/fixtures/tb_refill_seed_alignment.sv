`timescale 1ns/1ps
module tb;
reg clk=0; always #5 clk=~clk;
reg brf_seed_req=0;reg [4:0] brf_seed_a;reg[3:0]brf_seed_n;
reg dgo=0;reg[3:0]dbrf_seed_n_early=0;reg[15:0]dbrf_seed_word_early[0:7];
reg[31:0]brf_data[0:15];reg[15:0]epf_data[0:7];reg[15:0]expected_words[0:31];
integer trial,offset,n,i,cases=0;reg[15:0]expect_word;
always @(posedge clk) begin
// CANDIDATE_SEED_BLOCK
end
initial begin
for(trial=0;trial<32;trial=trial+1) begin
 for(i=0;i<32;i=i+1) expected_words[i]=$random;
 for(i=0;i<16;i=i+1)brf_data[i]={expected_words[2*i],expected_words[2*i+1]};
 for(offset=0;offset<32;offset=offset+1) begin
  for(n=0;n<=8 && n<=32-offset;n=n+1) begin
   @(negedge clk);
   brf_seed_req=1;brf_seed_a=offset;brf_seed_n=n;
   for(i=0;i<8;i=i+1)epf_data[i]=16'h5aa5;
   @(posedge clk);#1;
   for(i=0;i<8;i=i+1) begin
    expect_word=i<n?expected_words[offset+i]:16'h5aa5;
    if(epf_data[i]!==expect_word)$fatal(1,"offset=%0d n=%0d i=%0d actual=%h expected=%h",offset,n,i,epf_data[i],expect_word);
   end
   cases=cases+1;
  end
 end
end
$display("SEED_ALIGNMENT PASS cases=%0d offsets=32 trials=32 masked_outputs=checked",cases);$finish;
end
endmodule
