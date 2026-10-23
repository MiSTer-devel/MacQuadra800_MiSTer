// Exact extracted A/UX SetUpTimeK through the CPU adapter and real VIA.
// Run at 1x/2x CPU/bus with +floor=0/4; +expect_stall checks the overflow.
`timescale 1ns/1ps
module tb_aux_timek;
reg clk = 0;
always #5 clk = ~clk;
`ifdef CPU_AP68040_2X
// PCLK rises at every BCLK edge (rising and falling), as phase-aligned
// 66/33 MHz PLL outputs do. The memory and adapter still use BCLK.
reg clk_cpu = 1;
always #2.5 clk_cpu = ~clk_cpu;
always @(posedge clk_cpu) if (nreset) begin
	#0.001; // observe both coincident testbench clock updates
	if (dut.cpu_bclk_en !== clk)
		$fatal(1, "PCLK/BCLK enable phase mismatch");
end
`endif
reg nreset = 0;

wire        bus_req, bus_write, bus_instr;
wire  [1:0] bus_size;
wire [31:0] bus_addr, bus_wdata;
wire  [2:0] bus_fc;
reg         bus_ack = 0;
reg  [31:0] bus_rdata = 0;
reg   [2:0] ipl = 3'b111;

integer floor_arg = 0;
initial if ($value$plusargs("floor=%d", floor_arg)) begin end
quadra_cpu040 dut (
 .dbcc_floor_test(floor_arg[3:0]),
	.clk(clk), .nreset(nreset), .ce(1'b1),
`ifdef CPU_AP68040_2X
	.clk_cpu(clk_cpu),
`endif
	.ipl(ipl), .ipl_autovector(1'b1), .berr(1'b0), .stall_hold(1'b0), .dbg_stall_flt(),
	.cache_line_valid(1'b0), .cache_line_tag(28'd0), .cache_line_data(128'd0), .store_buffer_ok(1'b1),
	.bus_req(bus_req), .bus_write(bus_write), .bus_instr(bus_instr), .bus_size(bus_size),
	.bus_addr(bus_addr), .bus_wdata(bus_wdata), .bus_fc(bus_fc), .bus_ack(bus_ack), .bus_rdata(bus_rdata),
	.walker_req(), .walker_we(), .walker_addr(), .walker_wdat(),
	.walker_ack(1'b0), .walker_data(32'd0), .walker_berr(1'b0),
	.snoop_stb(1'b0), .snoop_addr(32'd0),
	.nresetout(), .nmi_ack_toggle(), .cacr_out(), .vbr_out(), .debug_busy(),
	.debug_fault(), .debug_halted(), .debug_status(), .debug_status2()
);

reg [7:0] mem [0:524287];
reg [31:0] words [0:131071];
integer i;
initial begin
 for(i=0;i<524288;i++)mem[i]=0;
 for(i=0;i<131072;i++)words[i]=0;
 $readmemh("prog.hex",words);
 for(i=0;i<131072;i++)begin
  mem[4*i]=words[i][31:24]; mem[4*i+1]=words[i][23:16];
  mem[4*i+2]=words[i][15:8];mem[4*i+3]=words[i][7:0];
 end
end
reg [4:0] ediv=0;
reg ephase=0;
wire e_rising=ediv==20 && !ephase;
wire e_falling=ediv==20 && ephase;
always @(posedge clk)begin
 if(!nreset)begin ediv<=0;ephase<=0;end
 else if(ediv==20)begin ediv<=0;ephase<=!ephase;end
 else ediv<=ediv+1'b1;
end
reg [3:0] via_addr=0;
reg via_wen=0,via_ren=0;
reg [7:0] via_din=0;
wire [7:0] via_dout;
via6522 via(
 .clock(clk),.rising(e_rising),.falling(e_falling),.timer_tick(e_falling),.reset(!nreset),
 .addr(via_addr),.wen(via_wen),.ren(via_ren),.data_in(via_din),.data_out(via_dout),
 .phi2_ref(),.port_a_o(),.port_a_t(),.port_a_i(8'hff),
 .port_b_o(),.port_b_t(),.port_b_i(8'hff),
 .ca1_i(1'b1),.ca2_o(),.ca2_i(1'b1),.ca2_t(),
 .cb1_o(),.cb1_i(1'b1),.cb1_t(),.cb2_o(),.cb2_i(1'b1),.cb2_t(),
 .ca2_lvl_i(1'b0),.cb2_lvl_i(1'b0),.irq(),.dbg_irq_state(),.sr_active(),
 .sr_ext_complete(1'b0),.sr_ext_load(1'b0),.sr_ext_data(8'd0));
integer state=0,cyc=0,nbytes=0,beats=0,timer_reads=0,overflows=0;
reg [31:0] addr=0,wdata=0,result0=0,result1=0;
reg wr=0;
`ifdef CPU_AP68040_2X
wire chk_clk=clk_cpu;
`else
wire chk_clk=clk;
`endif
always @(posedge chk_clk)if(nreset && dut.cpu.be.wb_commit &&
 dut.cpu.be.wb_u.pc==32'h55d12 && dut.cpu.be.wb_res[15:0]==0)begin
 overflows<=overflows+1;
 if(overflows==0)$display("CALIBRATION_OVERFLOW: D2.W doubled to zero at bus cycle %0d",cyc);
end
always @(posedge clk)begin
 cyc<=cyc+1;
 bus_ack<=0;
 case(state)
 0:if(nreset && bus_req && !bus_ack)begin
  addr<=bus_addr;wdata<=bus_wdata;wr<=bus_write;
  nbytes<=(bus_size==0)?1:((bus_size==1)?2:4);
  if(bus_addr[31:13]==(32'h50f00000>>13))begin
   via_addr<=bus_addr[12:9];via_din<=bus_wdata[7:0];
   via_wen<=bus_write;via_ren<=!bus_write;state<=2;
  end else state<=1;
 end
 1:begin
  state<=0;bus_ack<=1;beats<=beats+1;
  if(addr[31:28]==4'h5)begin
   if(wr && addr==32'h50000004)result0<=wdata;
   if(wr && addr==32'h50000008)result1<=wdata;
   if(wr && addr==32'h50000000)begin
    if(wdata!=32'ha5a5a5a5 || result0==0 || result1==0 || $test$plusargs("expect_stall"))
     $fatal(1,"Unexpected calibration completion signature=%h result0=%0d result1=%0d",wdata,result0,result1);
    $display("PASS: exact SetUpTimeK returned, floor=%0d loops=%0d/%0d cycles=%0d timer_reads=%0d",floor_arg,result0,result1,cyc,timer_reads);
    $finish;
   end
   bus_rdata<=0;
  end else if(wr)begin
   for(i=0;i<nbytes;i++)mem[(addr+i)&19'h7ffff]<=wdata>>(8*(nbytes-1-i));
  end else begin
   bus_rdata<=nbytes==1?{24'd0,mem[addr[18:0]]}:
              nbytes==2?{16'd0,mem[addr[18:0]],mem[addr[18:0]+1]}:
              {mem[addr[18:0]],mem[addr[18:0]+1],mem[addr[18:0]+2],mem[addr[18:0]+3]};
  end
 end
 2:if(e_falling)begin via_wen<=0;via_ren<=0;state<=3;end
 3:begin
  bus_rdata<={4{via_dout}};bus_ack<=1;state<=0;beats<=beats+1;
  if(!wr && via_addr==8)timer_reads<=timer_reads+1;
 end
 endcase
 if(cyc>1000000)begin
  if(!$test$plusargs("expect_stall") || overflows==0 || timer_reads<100)
   $fatal(1,"Calibration timeout pc=%h overflow=%0d reads=%0d",dut.dbg_pc,overflows,timer_reads);
  $display("PASS: reproduced exact SetUpTimeK stall, floor=%0d pc=%h overflows=%0d timer_reads=%0d",floor_arg,dut.dbg_pc,overflows,timer_reads);
  $finish;
 end
end
initial begin repeat(20)@(posedge clk);nreset=1;end
endmodule
