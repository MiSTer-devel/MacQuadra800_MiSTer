// tb_quadra_cpu040: the pipelined AP68040 through quadra_cpu040 against a
// memory that answers the way quadra800 does -- a registered one-clock ack
// after 1..4 clocks, re-accepting a held request only after its own ack,
// right-aligned data -- running tb_cpu040/prog.s.  Mailbox at $5000000x:
// +0 the result ($A5A5A5A5 = pass), +4 drops the level 1 interrupt.
`timescale 1ns/1ps
module tb_quadra_cpu040;
reg clk = 0;
always #5 clk = ~clk;
reg nreset = 0;

wire        bus_req, bus_write, bus_instr;
wire  [1:0] bus_size;
wire [31:0] bus_addr, bus_wdata;
wire  [2:0] bus_fc;
reg         bus_ack = 0;
reg  [31:0] bus_rdata = 0;
reg   [2:0] ipl = 3'b111;

quadra_cpu040 dut (
	.clk(clk), .nreset(nreset), .ce(1'b1),
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

reg [7:0] mem [0:65535];
reg [31:0] words [0:16383];
integer i;
initial begin
	for (i = 0; i < 65536; i = i + 1) mem[i] = 0;
	for (i = 0; i < 16384; i = i + 1) words[i] = 0;
	$readmemh("tb_cpu040/prog.hex", words);
	for (i = 0; i < 16384; i = i + 1) begin
		mem[4*i] = words[i][31:24]; mem[4*i+1] = words[i][23:16];
		mem[4*i+2] = words[i][15:8]; mem[4*i+3] = words[i][7:0];
	end
end

integer nbytes;
reg busy = 0;
reg fast = 0;
reg storm = 0;
integer storm_iacks = 0;
reg [31:0] port_cnt = 0;
initial fast = $test$plusargs("fast");
reg [2:0] wait_n;
reg [31:0] lfsr = 32'h1234567;
integer beats = 0, reads = 0, writes = 0, cyc = 0;
always @(posedge clk) begin
	cyc <= cyc + 1;
	lfsr <= {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};
	bus_ack <= 0;
	// an ack in the clock after the request (quadra800's retained-line hit)
	// or 1..4 clocks later
	if (!busy && bus_req && !bus_ack && !(fast && lfsr[3])) begin
		busy <= 1;
		wait_n <= {1'b0, lfsr[1:0]};
	end
	else if (busy || (bus_req && !bus_ack)) begin
		if (busy && wait_n != 0) wait_n <= wait_n - 1;
		else begin
			busy <= 0;
			bus_ack <= 1;
			beats <= beats + 1;
			if (beats < 60 || $test$plusargs("trace")) $display("%0d %s sz%0d %h %h tm%0d", cyc, bus_write?"W":"R", bus_size, bus_addr, bus_write?bus_wdata:{mem[bus_addr[15:0]],mem[bus_addr[15:0]+1],mem[bus_addr[15:0]+2],mem[bus_addr[15:0]+3]}, bus_fc);
			nbytes = (bus_size == 0) ? 1 : (bus_size == 1) ? 2 : 4;
			if (bus_addr[31:28] == 4'h5) begin
				if (bus_write && bus_addr[3:0] == 0) begin
					if (bus_wdata == 32'hA5A5A5A5) begin
						$display("PASS: %0d cycles, %0d beats", cyc, beats);
						$finish;
					end
					else begin $display("FAIL: test %0h at cycle %0d", bus_wdata, cyc);
					$finish; end
				end
				if (bus_write && bus_addr[3:0] == 4) ipl <= 3'b111;
				if (bus_write && bus_addr[3:0] == 8) begin
					if (!bus_wdata[0]) $display("storm: %0d interrupts during the copy, %0d port reads", storm_iacks, port_cnt);
					storm <= bus_wdata[0]; port_cnt <= 0;
				end
				bus_rdata <= 0;
				if (!bus_write && bus_addr[4]) begin
					// the read-to-pop port: each read returns the next count
					bus_rdata <= port_cnt;
					port_cnt  <= port_cnt + 1;
				end
			end
			else if (bus_write) begin
				writes <= writes + 1;
				for (i = 0; i < nbytes; i = i + 1)
					mem[(bus_addr[15:0] + i) & 16'hffff] <= bus_wdata >> (8*(nbytes-1-i));
			end
			else begin
				reads <= reads + 1;
				bus_rdata <= (nbytes == 1) ? {24'd0, mem[bus_addr[15:0]]} :
				             (nbytes == 2) ? {16'd0, mem[bus_addr[15:0]], mem[bus_addr[15:0]+1]} :
				             {mem[bus_addr[15:0]], mem[bus_addr[15:0]+1], mem[bus_addr[15:0]+2], mem[bus_addr[15:0]+3]};
			end
			if (bus_size == 2 && bus_addr[1:0] != 0) begin
				$display("ERROR: misaligned long beat %h", bus_addr); $finish;
			end
		end
	end
	if (cyc == 20000) ipl <= 3'b110;      // level 1 pending from here (masked until test 5)
	// the storm: a level 1 interrupt every 23..86 clocks while test 7 copies
	if (storm && ipl == 3'b111 && lfsr[5:0] == 6'd0) ipl <= 3'b110;
	if (storm && dut.iack) storm_iacks <= storm_iacks + 1;
	if (cyc > 2000000) begin $display("TIMEOUT pc %h beats %0d halted %b", dut.dbg_pc, beats, dut.dbg_halted); $finish; end
end
initial begin
	repeat (20) @(posedge clk);
	nreset = 1;
end
endmodule
