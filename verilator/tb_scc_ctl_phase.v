/* tb_scc_ctl_phase.v -- an SCC WR0 command must take effect whatever the
 * phase of the register-interface clock enables when the access arrives.
 *
 * WHY THIS EXISTS (2026-10-01): one Mac OS 8.1 boot in about fifteen froze
 * for minutes at "Starting Up..." with the CPU at interrupt level 4.  Every
 * boot opens and closes the async serial driver on the modem port while
 * AppleTalk starts; in the frozen boots the channel-A external/status
 * interrupt never went away.  The ROM's handler acknowledges it with WR0 =
 * $10 (Reset Ext/Status Interrupts), the driver's own storm guard turned
 * the CTS interrupt off in WR15 after 80 interrupts in one tick, and still
 * the interrupt came straight back, thousands of times a second, with the
 * main line never advancing one instruction (Ticks frozen, PC histogram in
 * docs/perf/fix_hw_20261001).
 *
 * iosb.sv consumes an SCC access on a `cen` pulse (clk/4, phase 2) with CS
 * high, and scc.v's write strobes (wreg_a/wreg_b) are high from CS until
 * that pulse.  The external/status logic, though, only looked at the
 * strobe on a `cep` pulse (phase 0).  An access whose CS rose in phase 1 or
 * 2 never saw a cep inside its window and the command was dropped.  The
 * bus acks on cen, so the phase of the NEXT access is fixed by the code
 * between the two: a handler whose instruction timing lands the WR0 write
 * in a dead phase misses every time.
 *
 * Each row raises the channel's external/status interrupt with a CTS (A) or
 * a synthetic DCD-latch change, starts the acknowledging write so that CS
 * rises in clock-enable phase 0, 1, 2 or 3, and checks RR3.
 *
 *   make tb_scc_ctl_phase
 * PASS criterion: last line "RESULT: PASS".
 */

`timescale 1ns/1ps

module tb_scc_ctl_phase;

	reg clk = 0;
	always #15.1515 clk = ~clk;

	reg nreset = 0;

	reg         sel   = 0;
	reg         write = 0;
	reg  [27:2] addr  = 0;
	reg   [3:0] be    = 4'b0000;
	reg  [31:0] wdata = 0;
	wire [31:0] rdata;
	wire        ack;
	reg         cts   = 1;

	integer errors = 0;

	iosb dut (
		.clk(clk), .nreset(nreset), .ce(1'b1),
		.sel(sel), .write(write), .addr(addr), .be(be),
		.wdata(wdata), .rdata(rdata), .ack(ack), .sdma_fault(),
		.vbl_irq(1'b0), .scsi_irq(1'b0), .scsi_drq(1'b0), .asc_irq(1'b0),
		.scc_rxd_a(1'b1), .scc_txd_a(),
		.scc_cts_a(cts), .scc_rts_a(),
		.scc_rxd_b(1'b1), .scc_txd_b(),
		.ipl_n(), .audio_l(), .audio_r(),
		.img_mounted(1'b0), .img_size(64'd0),
		.io_lba(), .io_rd(), .io_wr(), .io_ack(1'b0),
		.sd_buff_addr(8'd0), .sd_buff_dout(16'd0), .sd_buff_din(), .sd_buff_wr(1'b0),
		.ps2_key(11'd0), .ps2_mouse(25'd0),
		.timestamp(33'd0)
	);

	// One beat, as tb_iosb_scc drives it.  With phase >= 0 the beat is timed
	// so that scc_cs rises while the clock-enable divider shows `phase`.
	integer cs_phase;
	task beat(input integer a, input integer is_write, input [7:0] d,
	          output [7:0] rd, input integer phase);
		begin
			@(negedge clk);
			// sel set now is sampled on the next rising edge, where scc_cs is
			// registered; the divider then shows (value now + 1) & 3
			if (phase >= 0)
				while (((dut.scc_clkdiv + 1) & 3) != phase) @(negedge clk);
			addr  = a[27:2];
			be    = a[1] ? 4'b0010 : 4'b1000;
			wdata = a[1] ? {16'h0000, d, 8'h00} : {d, 24'h000000};
			write = is_write[0];
			sel   = 1;
			@(negedge clk);
			cs_phase = dut.scc_cs ? dut.scc_clkdiv : -1;
			while (!ack) @(negedge clk);
			rd = a[1] ? rdata[15:8] : rdata[31:24];
			sel   = 0;
			write = 0;
			@(negedge clk);
		end
	endtask

	reg [7:0] dummy;
	task wr_reg(input integer ctl_addr, input [3:0] regno, input [7:0] val);
		begin
			beat(ctl_addr, 1, (regno > 7) ? {4'b0000, 1'b1, regno[2:0]} : {4'd0, regno}, dummy, -1);
			beat(ctl_addr, 1, val, dummy, -1);
		end
	endtask
	task rd_reg(input integer ctl_addr, input [3:0] regno, output [7:0] val);
		begin
			beat(ctl_addr, 1, (regno > 7) ? {4'b0000, 1'b1, regno[2:0]} : {4'd0, regno}, dummy, -1);
			beat(ctl_addr, 0, 8'h00, val, -1);
		end
	endtask

	localparam OFF   = 32'h50000000;
	localparam A_CTL = 32'h5000C002 - OFF;
	localparam B_CTL = 32'h5000C000 - OFF;

	reg [7:0] rr3;
	integer p;

	initial begin
		nreset = 0;
		repeat (40) @(posedge clk);
		nreset = 1;
		repeat (40) @(posedge clk);

		wr_reg(A_CTL, 9, 8'hC0);            // hardware reset
		repeat (40) @(posedge clk);
		wr_reg(A_CTL, 15, 8'h20);           // CTS interrupt enable
		wr_reg(A_CTL, 1,  8'h01);           // external/status master enable
		wr_reg(A_CTL, 9,  8'h0A);           // MIE, no vector
		beat(A_CTL, 1, 8'h10, dummy, -1);   // start from a clean latch
		beat(A_CTL, 1, 8'h10, dummy, -1);
		repeat (20) @(posedge clk);

		$display("== channel A: Reset Ext/Status (WR0 = $10) in each CS phase ==");
		for (p = 0; p < 4; p = p + 1) begin
			cts = ~cts;                     // a CTS edge raises the interrupt
			repeat (24) @(posedge clk);
			rd_reg(A_CTL, 3, rr3);
			if (!rr3[3]) begin
				$display("FAIL phase %0d: the CTS edge did not raise ext/status A (RR3=%02x)", p, rr3);
				errors = errors + 1;
			end
			beat(A_CTL, 1, 8'h10, dummy, p);
			if (cs_phase != p) begin
				$display("FAIL phase %0d: CS rose in phase %0d (bench timing)", p, cs_phase);
				errors = errors + 1;
			end
			repeat (12) @(posedge clk);
			rd_reg(A_CTL, 3, rr3);
			if (rr3[3]) begin
				$display("FAIL CS phase %0d: ext/status A still pending after WR0=$10 (RR3=%02x) -- the command was dropped", p, rr3);
				errors = errors + 1;
				// clear it for the next row with as many tries as it takes
				repeat (4) beat(A_CTL, 1, 8'h10, dummy, 0);
			end
			else $display("  ok  CS phase %0d: ext/status A cleared", p);
		end

		$display("== channel A: the interrupt enable in WR15 must not matter to the acknowledge ==");
		// the driver's storm guard: WR15 = $80 between the edge and the reset
		for (p = 0; p < 4; p = p + 1) begin
			wr_reg(A_CTL, 15, 8'h20);
			cts = ~cts;
			repeat (24) @(posedge clk);
			wr_reg(A_CTL, 15, 8'h80);
			beat(A_CTL, 1, 8'h10, dummy, p);
			repeat (12) @(posedge clk);
			rd_reg(A_CTL, 3, rr3);
			if (rr3[3]) begin
				$display("FAIL CS phase %0d: ext/status A still pending with CTS IE off (RR3=%02x)", p, rr3);
				errors = errors + 1;
				repeat (4) beat(A_CTL, 1, 8'h10, dummy, 0);
			end
			else $display("  ok  CS phase %0d: cleared with CTS IE off", p);
		end

		if (errors == 0) $display("RESULT: PASS");
		else             $display("RESULT: FAIL (errors=%0d)", errors);
		$finish;
	end

	initial begin
		#200_000_000;
		$display("RESULT: FAIL (timeout)");
		$finish;
	end
endmodule
