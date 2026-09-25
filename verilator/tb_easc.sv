//============================================================================
//  tb_easc — directed unit test for rtl/easc.sv.
//
//  The ROM only touches the ASC's FIFO during its own POST, and a full Mac OS
//  boot is billions of cycles away, so waiting for the machine to make a noise
//  is a terrible way to find out whether FIFO mode works. This drives the
//  beat-slave port directly.
//
//    NB: no comment line here may start, right after the slashes, with the
//    simulator's own name -- that parses as a metacomment and errors out.
//      $ V=verilator
//      $ $V --binary --timing -Wno-fatal -Wno-WIDTH -Wno-UNSIGNED \
//            +define+SIMULATION=1 --top-module tb_easc -o tb_easc \
//            <this file> rtl/easc.sv
//      $ ./obj_dir/tb_easc
//
//  Every check prints PASS or FAIL; the run ends with a count.
//============================================================================
`timescale 1ns/1ps

module tb_easc;

reg clk = 0;
always #15 clk = ~clk;          // ~33 MHz

reg         nreset = 0;
reg         sel = 0, write = 0;
reg  [11:2] a = 0;
reg   [3:0] be = 0;
reg  [31:0] wdata = 0;
wire [31:0] rdata;
wire        irq;
wire signed [15:0] sample_l, sample_r;

integer fails = 0;
integer checks = 0;

task check(input cond, input string what);
	begin
		checks = checks + 1;
		if (cond) $display("PASS  %s", what);
		else begin $display("FAIL  %s", what); fails = fails + 1; end
	end
endtask

// SAMPLE_DIV shortened so a pop is 20 clocks, not 1483 — the divider is not
// what is under test and the full rate makes the run 70x longer.
easc #(.SAMPLE_DIV(20)) dut
(
	.clk(clk), .nreset(nreset), .ce(1'b1),
	.sel(sel), .write(write), .a(a), .be(be), .wdata(wdata), .rdata(rdata),
	.irq(irq), .sample_l(sample_l), .sample_r(sample_r)
);

// four consecutive ramp bytes starting at `first`, stepping by `step`
function [31:0] word4(input [7:0] first, input signed [7:0] step);
	reg [7:0] b0, b1, b2, b3;
	begin
		b0 = first;
		b1 = first + step;
		b2 = first + 2*step;
		b3 = first + 3*step;
		word4 = {b0, b1, b2, b3};
	end
endfunction

task bus_write(input [11:0] byte_addr, input [3:0] ben, input [31:0] d);
	begin
		@(posedge clk);
		a <= byte_addr[11:2]; be <= ben; wdata <= d; write <= 1; sel <= 1;
		@(posedge clk);
		sel <= 0; write <= 0; be <= 0;
		@(posedge clk);
		@(posedge clk);
		@(posedge clk);       // let the 4-lane drain finish
		@(posedge clk);
	end
endtask

// write one register byte (big-endian lanes: be[3] is byte at a+0)
task reg_write(input [11:0] byte_addr, input [7:0] d);
	reg [3:0] ben;
	reg [31:0] dd;
	begin
		case (byte_addr[1:0])
			2'd0: begin ben = 4'b1000; dd = {d, 24'd0}; end
			2'd1: begin ben = 4'b0100; dd = {8'd0, d, 16'd0}; end
			2'd2: begin ben = 4'b0010; dd = {16'd0, d, 8'd0}; end
			default: begin ben = 4'b0001; dd = {24'd0, d}; end
		endcase
		bus_write({byte_addr[11:2], 2'b00}, ben, dd);
	end
endtask

task bus_read(input [11:0] byte_addr, output [31:0] d);
	begin
		@(posedge clk);
		a <= byte_addr[11:2]; be <= 4'b1111; write <= 0; sel <= 1;
		@(posedge clk);
		d = rdata;
		sel <= 0;
		@(posedge clk);
	end
endtask

reg trace_push = 0;
always @(posedge clk)
	if (trace_push && dut.push_do)
		$display("      PUSH wrptr=%0d lane=%0d be=%b byte=%02x bank=%0d",
		         dut.push_ptr, dut.push_ptr[1:0], dut.pa_be, dut.push_byte, dut.pa_bank);

reg trace_pops = 0;
always @(posedge clk)
	if (trace_pops && dut.pop_a)
		$write("%02x ", dut.fifo_a_byte);

reg [31:0] rv;
integer i;
integer nonzero_l, nonzero_r, distinct_l;
reg signed [15:0] prev_l;

initial begin
	repeat (4) @(posedge clk);
	nreset <= 1;
	repeat (4) @(posedge clk);

	// ---------------------------------------------------------------- FIFO
	$display("--- FIFO mode ---");
	reg_write(12'h802, 8'h02);                 // control: CONTROL_STEREO
	reg_write(12'h801, 8'h01);                 // mode = 1 (FIFO)
	bus_read(12'h800, rv);
	check(rv[23:16] == 8'h01, "mode reads back 1");

	bus_read(12'h804, rv);
	$display("      stat after reset = %02x", rv[31:24]);
	// bits: 0 = A under half, 1 = A FULL, 2/3 = same for B.  An empty FIFO is
	// under-half but NOT full, so this reads 0x05.  It used to read 0x0F,
	// because bit 1 folded in (cap == 0) -- reporting empty as full is what
	// wedged Mac OS; see the fifo_stat comment in rtl/easc.sv.
	check(rv[31:24] == 8'h05, "an empty FIFO is under-half but NOT full (stat = 0x05)");

	// 8 longwords = 32 bytes into FIFO A, a rising ramp.  NB: an expression
	// like {8'h80 + i*4, ...} promotes each operand to 32 bits (i is an
	// integer), making the concatenation 128 bits wide so only the last byte
	// survives -- build the word explicitly.
	for (i = 0; i < 8; i = i + 1)
		bus_write(12'h000, 4'b1111, word4(8'h80 + i*4, 1));
	// and a falling ramp into FIFO B
	for (i = 0; i < 8; i = i + 1)
		bus_write(12'h400, 4'b1111, word4(8'h80 - i*4, -1));

	// the chip is already playing while it is being filled (SAMPLE_DIV is 20
	// here), so a few bytes have popped by the time the last write lands
	$display("      cap_a=%0d cap_b=%0d after 32+32 bytes", dut.cap_a, dut.cap_b);
	check(dut.cap_a >= 24 && dut.cap_a <= 32, "FIFO A took the longword writes");
	check(dut.cap_b >= 24 && dut.cap_b <= 32, "FIFO B took the longword writes");

	bus_read(12'h804, rv);
	check(rv[31:24] == 8'h05, "32 bytes in: both FIFOs under half, neither full");

	// let it play out: 32 samples at SAMPLE_DIV=20
	trace_pops = 1;
	nonzero_l = 0; nonzero_r = 0; distinct_l = 0; prev_l = 0;
	for (i = 0; i < 32*20 + 40; i = i + 1) begin
		@(posedge clk);
		if (sample_l != 0) nonzero_l = nonzero_l + 1;
		if (sample_r != 0) nonzero_r = nonzero_r + 1;
		if (sample_l != prev_l) begin distinct_l = distinct_l + 1; prev_l = sample_l; end
	end
	trace_pops = 0;
	check(dut.cap_a == 0 && dut.cap_b == 0, "both FIFOs drained");
	check(nonzero_l > 0, "left channel produced samples");
	check(nonzero_r > 0, "right channel produced samples");
	$display("      distinct left values = %0d", distinct_l);
	check(distinct_l >= 16, "left channel followed the ramp");

	// $80 is the offset-binary centre -> 0; $84 -> +4 in the top 8 bits
	reg_write(12'h803, 8'h80);                 // fifomode bit7: clear
	check(dut.cap_a == 0, "fifomode bit 7 cleared FIFO A");

	bus_write(12'h000, 4'b1000, {8'hC0, 24'd0});   // one byte, +64
	repeat (60) @(posedge clk);
	check(sample_l == 16'sh4000, "a $C0 byte plays as +0x4000 (offset binary, top 8 bits)");

	bus_write(12'h400, 4'b1000, {8'h40, 24'd0});   // one byte, -64
	repeat (60) @(posedge clk);
	check(sample_r == -16'sh4000, "a $40 byte plays as -0x4000 on the right");

	// mono: with CONTROL_STEREO clear, FIFO A must come out of both channels
	reg_write(12'h802, 8'h00);
	reg_write(12'h803, 8'h80);
	bus_write(12'h000, 4'b1000, {8'hC0, 24'd0});
	repeat (60) @(posedge clk);
	check(sample_l == 16'sh4000 && sample_r == 16'sh4000,
	      "CONTROL_STEREO clear mirrors FIFO A to both channels");

	// ---- interrupt: an EDGE, never a level -------------------------------
	// An idle chip in FIFO mode must NOT interrupt. A level condition here
	// ("cap < 512") makes an empty FIFO a 22 kHz interrupt source the guest
	// cannot switch off, which hangs the machine.
	reg_write(12'h802, 8'h02);          // stereo again
	reg_write(12'h803, 8'h80);          // clear both FIFOs
	bus_read(12'h804, rv);              // clear any latched irq
	repeat (400) @(posedge clk);        // 20 sample ticks with empty FIFOs
	check(irq == 1'b0, "an empty FIFO does not interrupt (no storm)");

	// fill past half, then let it drain through the half-way mark
	for (i = 0; i < 160; i = i + 1)
		bus_write(12'h000, 4'b1111, word4(8'h90, 1));
	$display("      cap_a=%0d after the big fill", dut.cap_a);
	bus_read(12'h804, rv);              // clear
	check(irq == 1'b0, "irq clear after a FIFOSTAT read");
	while (dut.cap_a > 505) @(posedge clk);
	check(irq == 1'b1, "irq raised as the FIFO drains through half-empty");

	// ------------------------------------------------------------ wavetable
	$display("--- wavetable mode ---");
	reg_write(12'h801, 8'h02);                 // mode = 2
	// fill all four banks with $FF so the mix is unambiguous
	for (i = 0; i < 512; i = i + 1)
		bus_write(i*4, 4'b1111, 32'hFFFFFFFF);
	reg_write(12'h815, 8'h01);                 // voice 0 increment high byte
	repeat (200) @(posedge clk);
	check(sample_l == 16'sh7F00, "four $FF voices mix to +0x7F00 (MAME sum*64)");

	for (i = 0; i < 512; i = i + 1)
		bus_write(i*4, 4'b1111, 32'h00000000);
	repeat (200) @(posedge clk);
	check(sample_l == -16'sh8000, "four $00 voices mix to -0x8000");

	$display("--- %0d checks, %0d failures ---", checks, fails);
	if (fails) $display("TB FAILED"); else $display("TB PASSED");
	$finish;
end

endmodule
