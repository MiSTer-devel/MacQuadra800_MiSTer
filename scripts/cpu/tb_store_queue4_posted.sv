`timescale 1ns/1ps
module tb_posted;
reg clk=0; always #5 clk=~clk;
reg nreset=0,ce=1,req=0,ack=0,err=0;
reg [31:0] addr=0,data=0;
reg [1:0] size=0;
reg [2:0] fc=0;
reg instr=0;
wire sack,mreq,mwrite,minstr,pending;
wire [31:0] ma,md;
wire [1:0] ms;
wire [2:0] mf;
wombat_store_buffer dut(.clk(clk),.nreset(nreset),.ce(ce),.buffer_writes(1'b1),
.s_req(req),.s_posted(1'b1),.s_write(1'b1),.s_instr(instr),.s_size(size),
.s_addr(addr),.s_wdata(data),.s_fc(fc),.s_ack(sack),.s_rdata(),
.m_req(mreq),.m_write(mwrite),.m_instr(minstr),.m_size(ms),.m_addr(ma),
.m_wdata(md),.m_fc(mf),.m_ack(ack),.m_rdata(32'b0),.m_err(err),.pending(pending));
reg [31:0] ea[0:10000],ed[0:10000];
reg [1:0] es[0:10000];
reg [2:0] ef[0:10000];
reg ei[0:10000];
integer head=0,tail=0,t=0,serial=0;
integer simultaneous[0:4];
integer full_stalls=0,frozen=0,error_drains=0;
integer seed=97;
reg [31:0] rng;
reg held=0;
integer before_count;
task tick;
begin
 #1;
 before_count=tail-head;
 if(ce) begin
  if(mreq && (ack||err)) begin
   if(head==tail) $fatal(1,"unexpected downstream write");
   if(!mwrite || {ma,md,ms,mf,minstr} !== {ea[head],ed[head],es[head],ef[head],ei[head]})
    $fatal(1,"write mismatch at %0d",head);
   head=head+1;
   if(err) error_drains=error_drains+1;
  end
  if(req && sack) begin
   ea[tail]=addr;ed[tail]=data;es[tail]=size;ef[tail]=fc;ei[tail]=instr;
   tail=tail+1;
   if(mreq&&(ack||err)) simultaneous[before_count]=simultaneous[before_count]+1;
  end
  if(req&&!sack&&before_count==4) full_stalls=full_stalls+1;
  held=req&&!sack;
 end else frozen=frozen+1;
 @(posedge clk); #1;
 if(dut.count !== (tail-head)) $fatal(1,"count mismatch expected %0d actual %0d",tail-head,dut.count);
 if(pending !== (tail!=head)) $fatal(1,"pending mismatch");
 @(negedge clk);
end
endtask
initial begin
 for(t=0;t<5;t=t+1) simultaneous[t]=0;
 repeat(3) @(negedge clk);
 nreset=1;
 for(t=0;t<6000;t=t+1) begin
  rng=$random(seed);
  ce=rng[2:0]!=0;
  ack=mreq && rng[4:3]==0;
  err=mreq && !ack && rng[8:5]==0;
  if(!held) begin
   req=rng[10:9]!=0;
   addr=32'h1000+serial*4;data=32'hfedc0000^serial;
   size=serial%3;fc=serial%8;instr=serial%2;
   if(req) serial=serial+1;
  end
  tick();
 end
 // Finish the outstanding upstream request before draining everything.
 ce=1;
 while(held) begin ack=mreq;err=0;tick();end
 req=0;err=0;
 while(pending) begin ack=mreq;tick();end
 ack=0;
 if(tail<100 || full_stalls==0 || frozen==0 || error_drains==0) $fatal(1,"missing stress coverage");
 for(t=1;t<4;t=t+1) if(simultaneous[t]==0) $fatal(1,"missing simultaneous count %0d",t);
 $display("PASS writes=%0d simultaneous1/2/3=%0d/%0d/%0d full_stalls=%0d frozen=%0d error_drains=%0d",tail,simultaneous[1],simultaneous[2],simultaneous[3],full_stalls,frozen,error_drains);
 $finish;
end
initial begin #1000000;$fatal(1,"timeout");end
endmodule
