// tb_rtc_pram -- rtl/rtc3430042.sv: the XPRAM over the VIA bit-bang protocol
// and the platform's host port (the .nvr image load/save path) side by side.
//
//   make tb_rtc_pram
//
// Checks: power-up zeros; a 128-word host load is what the guest reads and
// what the host port reads back; a guest write (extended $38 path and the
// classic slot path) raises pram_wr_stb exactly once and shows up on the
// host side; the guest's write-protect bit stops guest writes but not host
// writes; the wall clock seeded from the host timestamp survives a load.
`timescale 1ns/1ps
module tb_rtc_pram;

reg clk = 0;
always #15 clk = ~clk;                    // 33 MHz

reg         nreset = 0;
reg         ce_n = 1, clk_in = 1, data_in = 1;
wire        data_out, data_oe;
reg         h_we = 0;
reg   [6:0] h_addr = 0;
reg  [15:0] h_wdata = 0;
wire [15:0] h_rdata;
wire        pram_wr_stb;
reg  [32:0] timestamp = 33'd0;

rtc3430042 #(.SEC_DIV(33000000)) dut (
	.clk(clk), .nreset(nreset), .timestamp(timestamp),
	.ce_n(ce_n), .clk_in(clk_in), .data_in(data_in),
	.data_out(data_out), .data_oe(data_oe),
	.h_we(h_we), .h_addr(h_addr), .h_wdata(h_wdata), .h_rdata(h_rdata),
	.pram_wr_stb(pram_wr_stb)
);

integer errors = 0;
integer stb_count = 0;
always @(posedge clk) if (pram_wr_stb) stb_count = stb_count + 1;

task tick;
	repeat (20) @(posedge clk);
endtask

// the chip samples data on the clock's falling edge, MSB first
task send_byte(input [7:0] b);
	integer i;
	begin
		for (i = 7; i >= 0; i = i - 1) begin
			data_in = b[i]; clk_in = 1; tick;
			clk_in = 0; tick;
		end
	end
endtask

// ... and drives its output bit from the falling edge
task recv_byte(output [7:0] b);
	integer i;
	begin
		for (i = 7; i >= 0; i = i - 1) begin
			clk_in = 1; tick;
			clk_in = 0; tick;
			if (!data_oe) begin $display("FAIL: chip not driving during a read"); errors = errors + 1; end
			b[i] = data_out;
		end
	end
endtask

task select;   begin clk_in = 1; ce_n = 0; tick; end endtask
task deselect; begin ce_n = 1; tick; end endtask

// $38 extended command: {0011 1aaa} {aaaaa 00} then data (write) or the
// chip's byte (read, command bit 7 set)
task xp_write(input [7:0] a, input [7:0] d);
	begin
		select;
		send_byte(8'h38 | {5'd0, a[7:5]});
		send_byte({1'b0, a[4:0], 2'b00});
		send_byte(d);
		deselect;
	end
endtask

task xp_read(input [7:0] a, output [7:0] d);
	begin
		select;
		send_byte(8'hB8 | {5'd0, a[7:5]});
		send_byte({1'b0, a[4:0], 2'b00});
		recv_byte(d);
		deselect;
	end
endtask

// classic command: {r/w, rrrrr, 00}; the 16 PRAM slot bytes are r = 1xxxx
// (XPRAM 16..31) and the 4 classic bytes r = 010xx (XPRAM 8..11)
task cl_write(input [4:0] r, input [7:0] d);
	begin
		select; send_byte({1'b0, r, 2'b00}); send_byte(d); deselect;
	end
endtask

task cl_read(input [4:0] r, output [7:0] d);
	begin
		select; send_byte({1'b1, r, 2'b00}); recv_byte(d); deselect;
	end
endtask

task host_write(input [6:0] a, input [15:0] w);
	begin
		@(posedge clk); h_addr <= a; h_wdata <= w; h_we <= 1;
		@(posedge clk); h_we <= 0;
		repeat (3) @(posedge clk);
	end
endtask

task host_read(input [6:0] a, output [15:0] w);
	begin
		@(posedge clk); h_addr <= a;
		repeat (4) @(posedge clk);
		w = h_rdata;
	end
endtask

function [15:0] pat(input [6:0] i);
	pat = {i * 8'd13 + 8'd1, i * 8'd7 + 8'd3};
endfunction
function [7:0] pat_lo(input [6:0] i);
	pat_lo = i * 8'd7 + 8'd3;
endfunction
function [7:0] pat_hi(input [6:0] i);
	pat_hi = i * 8'd13 + 8'd1;
endfunction

task check8(input [255:0] what, input [7:0] got, input [7:0] exp);
	if (got !== exp) begin
		$display("FAIL: %0s: got %02x expected %02x", what, got, exp);
		errors = errors + 1;
	end
endtask

task check16(input [255:0] what, input [15:0] got, input [15:0] exp);
	if (got !== exp) begin
		$display("FAIL: %0s: got %04x expected %04x", what, got, exp);
		errors = errors + 1;
	end
endtask

task check_stb(input [255:0] what, input integer exp);
	if (stb_count !== exp) begin
		$display("FAIL: %0s: pram_wr_stb count %0d expected %0d", what, stb_count, exp);
		errors = errors + 1;
	end
endtask

reg  [7:0] b;
reg [15:0] w;
integer i;
reg [31:0] secs;

initial begin
	repeat (5) @(posedge clk);
	nreset = 1;
	timestamp = 33'd1_000_000;          // the wall clock seeds from this
	repeat (10) @(posedge clk);

	// 1. power-up zeros
	xp_read(8'h37, b); check8("power-up XPRAM $37", b, 8'h00);
	host_read(7'd5, w); check16("power-up host word 5", w, 16'h0000);
	check_stb("after reads", 0);

	// 2. a full host load, seen by the guest and by the host port
	for (i = 0; i < 128; i = i + 1) host_write(i[6:0], pat(i[6:0]));
	check_stb("after the host load", 0);
	for (i = 0; i < 128; i = i + 1) begin
		host_read(i[6:0], w); check16("host read after load", w, pat(i[6:0]));
	end
	xp_read(8'h00, b); check8("guest byte 0",   b, pat_lo(7'd0));
	xp_read(8'h01, b); check8("guest byte 1",   b, pat_hi(7'd0));
	xp_read(8'h44, b); check8("guest byte $44", b, pat_lo(7'h22));
	xp_read(8'h45, b); check8("guest byte $45", b, pat_hi(7'h22));
	xp_read(8'hFF, b); check8("guest byte $FF", b, pat_hi(7'h7F));
	check_stb("after guest reads", 0);

	// 3. a guest extended write: one strobe, visible both ways
	xp_write(8'h45, 8'hA5);
	check_stb("after one guest write", 1);
	xp_read(8'h45, b); check8("guest read back $45", b, 8'hA5);
	host_read(7'h22, w); check16("host word $22 after guest write", w, {8'hA5, pat_lo(7'h22)});

	// 4. a classic slot write (r = 21 is XPRAM byte 21)
	cl_write(5'd21, 8'h3C);
	check_stb("after the classic write", 2);
	cl_read(5'd21, b); check8("classic read back", b, 8'h3C);
	xp_read(8'd21, b); check8("extended read of byte 21", b, 8'h3C);
	host_read(7'd10, w); check16("host word 10 after classic write", w, {8'h3C, pat_lo(7'd10)});

	// 5. write protect: guest writes stop, host writes do not
	cl_write(5'd13, 8'h80);
	xp_write(8'h10, 8'h11);
	check_stb("guest write under write protect", 2);
	xp_read(8'h10, b); check8("byte $10 unchanged under write protect", b, pat_lo(7'h08));
	host_write(7'h08, 16'h2211);
	xp_read(8'h10, b); check8("host write under write protect, byte $10", b, 8'h11);
	xp_read(8'h11, b); check8("host write under write protect, byte $11", b, 8'h22);
	check_stb("host write is not a guest strobe", 2);
	cl_write(5'd13, 8'h00);
	xp_write(8'h10, 8'h5A);
	check_stb("guest write after write protect off", 3);
	xp_read(8'h10, b); check8("byte $10 after write protect off", b, 8'h5A);

	// 6. the host port follows a fresh address within a few clocks
	@(posedge clk); h_addr <= 7'h22;
	repeat (4) @(posedge clk);
	check16("host word $22 settles", h_rdata, {8'hA5, pat_lo(7'h22)});

	// 7. the wall clock is outside the image: still the seeded value (+ at
	//    most the seconds elapsed in this bench, which is far under one)
	cl_read(5'd0, secs[7:0]);  cl_read(5'd1, secs[15:8]);
	cl_read(5'd2, secs[23:16]); cl_read(5'd3, secs[31:24]);
	if (secs !== 32'd1_000_000 + 32'd2082844800) begin
		$display("FAIL: wall clock %0d expected %0d", secs, 32'd1_000_000 + 32'd2082844800);
		errors = errors + 1;
	end

	if (errors == 0) $display("tb_rtc_pram: ALL TESTS PASSED");
	else begin $display("tb_rtc_pram: TEST FAILED (%0d errors)", errors); $fatal(1); end
	$finish;
end

endmodule
