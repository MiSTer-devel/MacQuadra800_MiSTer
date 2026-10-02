/* tb_sysmem_vbuf_gate.sv -- the scaler's HPS port must see nothing until the
 * core's first reset is over.
 *
 * WHY THIS EXISTS (2026-10-02): on some loads the scaler's picture came up
 * displaced or absent and the HPS FPGA-to-SDRAM port stayed broken until the
 * MiSTer was rebooted; how often was a property of the fit (the shipped
 * 20261001 never in 52 loads, a later candidate one load in seven, the
 * 20260930_2 fit almost every load).  The data sat a RANDOM number of beats
 * early (8, 4, 14, 10, 5, 1, 2 on seven loads of that last fit): a write
 * burst had been cut at an arbitrary beat before the first real one.
 *
 * sys/f2sdram_safe_terminator.sv passes its master through until it has seen
 * the reset deasserted once, and sys/ascal.vhd's avl_write_i has no reset
 * value: it keeps whatever it holds when the first reset arrives, a clock or
 * two after configuration.  If that is a 1 the port takes one 16-beat burst
 * after another while Main keeps the core in reset, and the release stops
 * the stream wherever it happens to be.
 *
 * The bench builds the real sysmem_lite (cut out of sys/sysmem.sv by the
 * Makefile; the HPS hard block below is a model) around a master that
 * behaves like ascal's write side with avl_write_i stuck at 1 through the
 * reset, and releases the reset at 16 consecutive clocks, both after the
 * 20 ms start-up reset has run out and before.  PASS = in all 32 units no
 * beat reaches the port before the master's first real burst, and that
 * burst starts on a port that is not inside another one.
 *
 *   make tb_sysmem_vbuf_gate
 */
`timescale 1ns/1ps

// ---------------------------------------------------------------------------
// The HPS hard block, as far as sysmem_lite uses it: the 100 MHz user clock
// and three Avalon-MM ports.  Port 0 (the scaler's) counts write beats per
// burst the way a bursting slave does: address and burstcount are taken on
// the first beat it sees while idle.
module sysmem_HPS_fpga_interfaces
(
	output wire         h2f_rst_n,
	input  wire         f2h_cold_rst_req_n,
	input  wire         f2h_warm_rst_req_n,
	output wire         h2f_user0_clk,
	input  wire [27:0]  f2h_sdram0_ADDRESS,
	input  wire [7:0]   f2h_sdram0_BURSTCOUNT,
	output wire         f2h_sdram0_WAITREQUEST,
	output wire [127:0] f2h_sdram0_READDATA,
	output wire         f2h_sdram0_READDATAVALID,
	input  wire         f2h_sdram0_READ,
	input  wire [127:0] f2h_sdram0_WRITEDATA,
	input  wire [15:0]  f2h_sdram0_BYTEENABLE,
	input  wire         f2h_sdram0_WRITE,
	input  wire         f2h_sdram0_clk,
	input  wire [28:0]  f2h_sdram1_ADDRESS,
	input  wire [7:0]   f2h_sdram1_BURSTCOUNT,
	output wire         f2h_sdram1_WAITREQUEST,
	output wire [63:0]  f2h_sdram1_READDATA,
	output wire         f2h_sdram1_READDATAVALID,
	input  wire         f2h_sdram1_READ,
	input  wire [63:0]  f2h_sdram1_WRITEDATA,
	input  wire [7:0]   f2h_sdram1_BYTEENABLE,
	input  wire         f2h_sdram1_WRITE,
	input  wire         f2h_sdram1_clk,
	input  wire [28:0]  f2h_sdram2_ADDRESS,
	input  wire [7:0]   f2h_sdram2_BURSTCOUNT,
	output wire         f2h_sdram2_WAITREQUEST,
	output wire [63:0]  f2h_sdram2_READDATA,
	output wire         f2h_sdram2_READDATAVALID,
	input  wire         f2h_sdram2_READ,
	input  wire [63:0]  f2h_sdram2_WRITEDATA,
	input  wire [7:0]   f2h_sdram2_BYTEENABLE,
	input  wire         f2h_sdram2_WRITE,
	input  wire         f2h_sdram2_clk
);
	reg clk = 0;
	always #5 clk = ~clk;
	assign h2f_user0_clk = clk;
	assign h2f_rst_n     = 1'b1;

	assign {f2h_sdram1_WAITREQUEST, f2h_sdram1_READDATAVALID} = 2'b00;
	assign {f2h_sdram2_WAITREQUEST, f2h_sdram2_READDATAVALID} = 2'b00;
	assign f2h_sdram1_READDATA = 64'd0;
	assign f2h_sdram2_READDATA = 64'd0;
	assign f2h_sdram0_READDATA = 128'd0;
	assign f2h_sdram0_READDATAVALID = 1'b0;

	// Main releases the port resets (fpgaportrst) a little after the FPGA
	// has entered user mode; until then the port ignores its inputs
	integer cyc = 0;
	wire    port_on = (cyc >= 1000);

	// some back-pressure, so the terminator's and the master's waitrequest
	// handling is exercised
	reg [7:0] lfsr = 8'h5A;
	assign f2h_sdram0_WAITREQUEST = port_on && (lfsr[2:0] == 3'd0);

	reg        inburst = 0;       // inside a write burst
	reg  [7:0] left    = 0;       // beats it still wants
	integer    beats   = 0;       // write beats taken since the port came up
	integer    bursts  = 0;
	wire       beat = port_on && f2h_sdram0_WRITE && !f2h_sdram0_WAITREQUEST;
	always @(posedge f2h_sdram0_clk) begin
		cyc  <= cyc + 1;
		lfsr <= {lfsr[6:0], lfsr[7] ^ lfsr[5] ^ lfsr[4] ^ lfsr[3]};
		if (beat) begin
			beats <= beats + 1;
			if (!inburst) begin
				bursts <= bursts + 1;
				if (f2h_sdram0_BURSTCOUNT > 8'd1) begin
					inburst <= 1;
					left    <= f2h_sdram0_BURSTCOUNT - 8'd1;
				end
			end
			else begin
				left <= left - 8'd1;
				if (left == 8'd1) inburst <= 0;
			end
		end
	end
endmodule

// ---------------------------------------------------------------------------
// ascal's Avalon write side, as far as the port sees it: asserted
// asynchronously and released on a clock like avl_reset_na, 16-beat bursts,
// and avl_write_i NOT in the reset branch -- it holds its value through the
// reset.  STUCK is that value at configuration.
module scaler_like #(parameter STUCK = 1)
(
	input  wire         clk,
	input  wire         reset_na,
	output reg          write,
	output wire         read,
	output wire [7:0]   burstcount,
	output wire [27:0]  address,
	output wire [127:0] writedata,
	output wire [15:0]  byteenable,
	input  wire         waitrequest,
	output reg          first_beat      // the first beat of the first real burst is on the bus
);
	assign read       = 1'b0;
	assign burstcount = 8'd16;
	assign address    = 28'h2000000;
	assign writedata  = {4{32'hC0FFEE00}};
	assign byteenable = 16'hFFFF;

	reg rst_n = 0;
	always @(posedge clk or negedge reset_na)
		if (!reset_na) rst_n <= 1'b0;
		else           rst_n <= 1'b1;

	reg        st   = 0;
	reg  [4:0] cnt  = 0;
	reg  [7:0] gap  = 0;
	reg        seen = 0;
	initial write = STUCK[0];
	initial first_beat = 0;

	always @(posedge clk or negedge rst_n) begin
		if (!rst_n) begin
			st  <= 0;
			gap <= 0;
		end
		else begin
			write      <= 1'b0;
			first_beat <= 1'b0;
			case (st)
			1'b0: begin
				gap <= gap + 8'd1;
				if (gap == 8'd40) begin st <= 1'b1; cnt <= 0; gap <= 0; end
			end
			1'b1: begin
				write <= 1'b1;
				if (!write && !seen) begin first_beat <= 1'b1; seen <= 1'b1; end
				if (write && !waitrequest) begin
					cnt <= cnt + 5'd1;
					if (cnt == 5'd15) begin write <= 1'b0; st <= 1'b0; end
				end
			end
			endcase
		end
	end
endmodule

// ---------------------------------------------------------------------------
// One "load": sysmem_lite, the master, and sys_top's reset_req released at
// clock RELEASE.
module unit #(parameter RELEASE = 2000100, parameter ID = 0) ();
	reg  bad_early  = 0;       // a beat reached the port before the first real burst
	reg  bad_inside = 0;       // the first real burst began inside another one
	wire clk;
	reg  reset_req = 1;
	wire reset_out;

	wire         vbuf_waitrequest, vbuf_write, vbuf_read, first_beat;
	wire [7:0]   vbuf_burstcount;
	wire [27:0]  vbuf_address;
	wire [127:0] vbuf_writedata;
	wire [15:0]  vbuf_byteenable;

	sysmem_lite sysmem
	(
		.clock(clk), .reset_out(reset_out),
		.reset_hps_cold_req(1'b0), .reset_hps_warm_req(1'b0), .reset_core_req(reset_req),
		.ram1_clk(clk), .ram1_address(29'd0), .ram1_burstcount(8'd0), .ram1_waitrequest(),
		.ram1_readdata(), .ram1_readdatavalid(), .ram1_read(1'b0), .ram1_writedata(64'd0),
		.ram1_byteenable(8'd0), .ram1_write(1'b0),
		.ram2_clk(clk), .ram2_address(29'd0), .ram2_burstcount(8'd0), .ram2_waitrequest(),
		.ram2_readdata(), .ram2_readdatavalid(), .ram2_read(1'b0), .ram2_writedata(64'd0),
		.ram2_byteenable(8'd0), .ram2_write(1'b0),
		.vbuf_clk(clk), .vbuf_address(vbuf_address), .vbuf_burstcount(vbuf_burstcount),
		.vbuf_waitrequest(vbuf_waitrequest), .vbuf_writedata(vbuf_writedata),
		.vbuf_byteenable(vbuf_byteenable), .vbuf_write(vbuf_write),
		.vbuf_readdata(), .vbuf_readdatavalid(), .vbuf_read(vbuf_read)
	);

	scaler_like #(.STUCK(1)) scaler
	(
		.clk(clk), .reset_na(~reset_req),
		.write(vbuf_write), .read(vbuf_read), .burstcount(vbuf_burstcount),
		.address(vbuf_address), .writedata(vbuf_writedata), .byteenable(vbuf_byteenable),
		.waitrequest(vbuf_waitrequest), .first_beat(first_beat)
	);

	integer cyc = 0;
	reg     real_seen = 0;
	always @(posedge clk) begin
		cyc <= cyc + 1;
		if (cyc == RELEASE) reset_req <= 0;
		if (!real_seen && sysmem.fpga_interfaces.beats != 0 && !first_beat) bad_early <= 1;
		if (first_beat && !real_seen) begin
			real_seen <= 1;
			if (sysmem.fpga_interfaces.inburst) bad_inside <= 1;
		end
		// the 20 ms start-up reset, then a few thousand clocks of traffic
		if (cyc == 2000100 + 6000) begin
			if (bad_early || bad_inside) begin
				$display("FAIL unit %0d (%0s release, offset %0d):%0s%0s", ID, ID < 16 ? "late" : "early", ID % 16,
				         bad_early  ? " beats reached the port during the reset;" : "",
				         bad_inside ? " the first real burst began inside a cut one" : "");
				tb_sysmem_vbuf_gate.nbad = tb_sysmem_vbuf_gate.nbad + 1;
			end
			tb_sysmem_vbuf_gate.ndone = tb_sysmem_vbuf_gate.ndone + 1;
		end
	end
endmodule

module tb_sysmem_vbuf_gate;
	integer ndone = 0, nbad = 0;
	genvar g;
	generate
		for (g = 0; g < 16; g = g + 1) begin : late     // released after the start-up reset
			unit #(.RELEASE(2000100 + g), .ID(g)) u ();
		end
		for (g = 0; g < 16; g = g + 1) begin : early    // released while it still runs
			unit #(.RELEASE(5000 + g), .ID(16 + g)) u ();
		end
	endgenerate

	initial begin
		wait (ndone == 32);
		if (nbad == 0) $display("RESULT: PASS (32 units)");
		else           $display("RESULT: FAIL (%0d of 32 units)", nbad);
		$finish;
	end
endmodule
