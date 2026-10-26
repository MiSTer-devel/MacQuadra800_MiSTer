//============================================================================
//  tb_vram_ddr3.sv — Unit testbench for vram_ddr3 module
//============================================================================

`timescale 1ns/1ps

module tb_vram_ddr3;

reg clk_sys = 0;
always #15 clk_sys = ~clk_sys; // ~33.33 MHz

reg clk_vid = 0;
always #19.86 clk_vid = ~clk_vid; // ~25.175 MHz

reg reset = 1;
reg reset_vid = 1;

// CPU interface
reg         mem_req = 0;
reg         mem_is_vram = 0;
reg         mem_write = 0;
reg  [31:2] mem_addr = 0;
reg   [3:0] mem_be = 0;
reg  [31:0] mem_wdata = 0;
reg         mem_vram_wp = 0;
wire        vram_ack;
wire [31:0] vram_rdata;
wire        vram_wq_room;

// Video interface
reg   [9:0] vid_col_word = 0;
reg  [13:0] vid_stride = 14'd1024;
reg         vid_line_req = 0;
reg  [20:0] vid_line_addr = 0;
reg         vid_line_swap = 0;
wire [31:0] vid_rdata;

// DDR3 interface
wire        vram_ddr_req;
wire        vram_ddr_we;
wire [28:0] vram_ddr_addr;
wire  [7:0] vram_ddr_burstcnt;
wire [63:0] vram_ddr_din;
wire  [7:0] vram_ddr_be;
reg         vram_ddr_busy = 0;
reg         vram_ddr_ack = 0;
reg  [63:0] vram_ddr_dout = 0;
reg         vram_ddr_rvalid = 0;

// DDR3 Memory Model (64K words x 64-bit = 512 KB)
reg [63:0] ddr_mem [0:65535];
integer i;
initial begin
	for (i = 0; i < 65536; i = i + 1) ddr_mem[i] = 64'h0;
end

vram_ddr3 #(
	.DDR_VRAM_BASE(29'h0500_0000),
	.VRAM_1MB(1)
) dut (
	.clk_sys(clk_sys),
	.reset(reset),

	.mem_req(mem_req),
	.mem_is_vram(mem_is_vram),
	.mem_write(mem_write),
	.mem_addr(mem_addr),
	.mem_be(mem_be),
	.mem_wdata(mem_wdata),
	.mem_vram_wp(mem_vram_wp),
	.vram_ack(vram_ack),
	.vram_rdata(vram_rdata),
	.vram_wq_room(vram_wq_room),

	.clk_vid(clk_vid),
	.reset_vid(reset_vid),
	.vid_col_word(vid_col_word),
	.vid_stride(vid_stride),
	.vid_line_req(vid_line_req),
	.vid_line_addr(vid_line_addr),
	.vid_line_swap(vid_line_swap),
	.vid_rdata(vid_rdata),

	.vram_ddr_req(vram_ddr_req),
	.vram_ddr_we(vram_ddr_we),
	.vram_ddr_addr(vram_ddr_addr),
	.vram_ddr_burstcnt(vram_ddr_burstcnt),
	.vram_ddr_din(vram_ddr_din),
	.vram_ddr_be(vram_ddr_be),
	.vram_ddr_busy(vram_ddr_busy),
	.vram_ddr_ack(vram_ddr_ack),
	.vram_ddr_dout(vram_ddr_dout),
	.vram_ddr_rvalid(vram_ddr_rvalid)
);

// DDR3 Responder Model
reg [7:0] burst_rem = 0;
reg [28:0] resp_addr = 0;
always @(posedge clk_sys) begin
	vram_ddr_rvalid <= 0;
	if (vram_ddr_ack) vram_ddr_ack <= 0;

	if (burst_rem > 0) begin
		vram_ddr_dout <= ddr_mem[resp_addr[15:0]];
		vram_ddr_rvalid <= 1;
		resp_addr <= resp_addr + 1'b1;
		burst_rem <= burst_rem - 1'b1;
	end
	else if (vram_ddr_req && !vram_ddr_ack) begin
		vram_ddr_ack <= 1;
		if (vram_ddr_we) begin
			// Write to memory
			if (vram_ddr_be[0]) ddr_mem[vram_ddr_addr[15:0]][7:0]   <= vram_ddr_din[7:0];
			if (vram_ddr_be[1]) ddr_mem[vram_ddr_addr[15:0]][15:8]  <= vram_ddr_din[15:8];
			if (vram_ddr_be[2]) ddr_mem[vram_ddr_addr[15:0]][23:16] <= vram_ddr_din[23:16];
			if (vram_ddr_be[3]) ddr_mem[vram_ddr_addr[15:0]][31:24] <= vram_ddr_din[31:24];
			if (vram_ddr_be[4]) ddr_mem[vram_ddr_addr[15:0]][39:32] <= vram_ddr_din[39:32];
			if (vram_ddr_be[5]) ddr_mem[vram_ddr_addr[15:0]][47:40] <= vram_ddr_din[47:40];
			if (vram_ddr_be[6]) ddr_mem[vram_ddr_addr[15:0]][55:48] <= vram_ddr_din[55:48];
			if (vram_ddr_be[7]) ddr_mem[vram_ddr_addr[15:0]][63:56] <= vram_ddr_din[63:56];
		end
		else begin
			// Read from memory
			resp_addr <= vram_ddr_addr;
			burst_rem <= vram_ddr_burstcnt;
		end
	end
end

initial begin
	$display("Starting tb_vram_ddr3...");
	repeat (10) @(posedge clk_sys);
	reset <= 0;
	reset_vid <= 0;
	repeat (5) @(posedge clk_sys);

	// 1. Test direct CPU VRAM write (mem_vram_wp)
	$display("Test 1: Direct CPU write via mem_vram_wp");
	@(posedge clk_sys);
	mem_vram_wp <= 1;
	mem_addr    <= 30'h3E40_0000; // $F9000000 in word address
	mem_be      <= 4'b1111;
	mem_wdata   <= 32'hDEADBEEF;
	@(posedge clk_sys);
	mem_vram_wp <= 0;

	// Wait for write to drain to DDR3
	repeat (10) @(posedge clk_sys);
	if (ddr_mem[0][31:0] !== 32'hDEADBEEF) begin
		$fatal(1, "Mismatch: ddr_mem[0][31:0] = %08x, expected DEADBEEF", ddr_mem[0][31:0]);
	end
	$display("  -> ddr_mem[0][31:0] successfully written with %08x", ddr_mem[0][31:0]);

	// 2. Test CPU VRAM write to high half of 64-bit word (addr[2] == 1)
	$display("Test 2: CPU write with addr[2] == 1");
	@(posedge clk_sys);
	mem_vram_wp <= 1;
	mem_addr    <= 30'h3E40_0001; // $F9000004
	mem_be      <= 4'b1111;
	mem_wdata   <= 32'hCAFE1234;
	@(posedge clk_sys);
	mem_vram_wp <= 0;

	repeat (10) @(posedge clk_sys);
	if (ddr_mem[0][63:32] !== 32'hCAFE1234) begin
		$fatal(1, "Mismatch: ddr_mem[0][63:32] = %08x, expected CAFE1234", ddr_mem[0][63:32]);
	end
	$display("  -> ddr_mem[0][63:32] successfully written with %08x", ddr_mem[0][63:32]);

	// 3. Test CPU VRAM read
	$display("Test 3: CPU readback via mem_req");
	@(posedge clk_sys);
	mem_req     <= 1;
	mem_is_vram <= 1;
	mem_write   <= 0;
	mem_addr    <= 30'h3E40_0000;
	mem_be      <= 4'b1111;

	wait (vram_ack);
	if (vram_rdata !== 32'hDEADBEEF) begin
		$fatal(1, "Read mismatch: vram_rdata = %08x, expected DEADBEEF", vram_rdata);
	end
	$display("  -> CPU read 0x%08x matched DEADBEEF!", vram_rdata);
	@(posedge clk_sys);
	mem_req <= 0;
	mem_is_vram <= 0;
	repeat (5) @(posedge clk_sys);

	// 4. Test Scanline DMA Pre-fetch
	$display("Test 4: Scanline DMA burst prefetch");
	// Preload scanline 0 in ddr_mem
	for (i = 0; i < 128; i = i + 1) begin
		ddr_mem[i] = {32'hA000_0000 + i*2 + 1, 32'hA000_0000 + i*2};
	end

	@(posedge clk_vid);
	vid_line_addr <= 21'h000000;
	vid_line_req  <= 1;
	@(posedge clk_vid);
	vid_line_req  <= 0;

	// Wait for DMA fetch to complete (8 bursts of 16 beats = 128 beats)
	repeat (250) @(posedge clk_sys);

	// Swap ping-pong buffer
	@(posedge clk_vid);
	vid_line_swap <= 1;
	vid_col_word  <= 10'd0;
	@(posedge clk_vid);
	vid_line_swap <= 0;

	// Read out words on clk_vid
	@(posedge clk_vid);
	#0.01;
	$display("  Word 0: vid_rdata = %08x (expected A0000000)", vid_rdata);
	if (vid_rdata !== 32'hA000_0000) $fatal(1, "Word 0 mismatch!");

	@(posedge clk_vid);
	vid_col_word <= 10'd1;
	@(posedge clk_vid);
	#0.01;
	$display("  Word 1: vid_rdata = %08x (expected A0000001)", vid_rdata);
	if (vid_rdata !== 32'hA000_0001) $fatal(1, "Word 1 mismatch!");

	@(posedge clk_vid);
	vid_col_word <= 10'd2;
	@(posedge clk_vid);
	#0.01;
	$display("  Word 2: vid_rdata = %08x (expected A0000002)", vid_rdata);
	if (vid_rdata !== 32'hA000_0002) $fatal(1, "Word 2 mismatch!");

	// 5. Test CPU write-through snoop into active display line
	$display("Test 5: CPU write-through snoop to active line buffer");
	@(posedge clk_sys);
	mem_vram_wp <= 1;
	mem_addr    <= 30'h3E40_0002; // Word 2
	mem_be      <= 4'b1111;
	mem_wdata   <= 32'h5555_AAAA;
	@(posedge clk_sys);
	mem_vram_wp <= 0;

	repeat (2) @(posedge clk_vid);
	#0.01;
	$display("  Snoop Word 2: vid_rdata = %08x (expected 5555AAAA)", vid_rdata);
	if (vid_rdata !== 32'h5555_AAAA) $fatal(1, "Snoop update mismatch!");

	// 6. Test Concurrent CPU writes during DMA prefetch
	$display("Test 6: Concurrent CPU writes while DMA is in-flight");
	for (i = 0; i < 128; i = i + 1) begin
		ddr_mem[256 + i] = {32'hB000_0000 + i*2 + 1, 32'hB000_0000 + i*2};
	end

	@(posedge clk_vid);
	vid_line_addr <= 21'h000800; // Offset 2048 bytes (256 64-bit words)
	vid_line_req  <= 1;
	@(posedge clk_vid);
	vid_line_req  <= 0;

	// While DMA is actively executing bursts, pump in 8 CPU writes
	repeat (10) @(posedge clk_sys);
	for (i = 0; i < 8; i = i + 1) begin
		@(posedge clk_sys);
		mem_vram_wp <= 1;
		mem_addr    <= 30'h3E40_0400 + i[29:0]; // Writing to words at offset 0x400
		mem_be      <= 4'b1111;
		mem_wdata   <= 32'hC000_0000 + i;
		@(posedge clk_sys);
		mem_vram_wp <= 0;
	end

	// Wait for DMA and FIFO drain
	repeat (300) @(posedge clk_sys);

	// Verify all 8 CPU writes reached DDR3 memory
	for (i = 0; i < 8; i = i + 1) begin
		if (i % 2 == 0) begin
			if (ddr_mem[512 + (i/2)][31:0] !== (32'hC000_0000 + i)) begin
				$fatal(1, "Concurrent CPU write %0d failed: got %08x", i, ddr_mem[512 + (i/2)][31:0]);
			end
		end else begin
			if (ddr_mem[512 + (i/2)][63:32] !== (32'hC000_0000 + i)) begin
				$fatal(1, "Concurrent CPU write %0d failed: got %08x", i, ddr_mem[512 + (i/2)][63:32]);
			end
		end
	end
	$display("  -> All 8 concurrent CPU writes cleanly reached DDR3!");

	// Swap ping-pong buffer and verify prefetched line was not corrupted by the CPU writes
	@(posedge clk_vid);
	vid_line_swap <= 1;
	vid_col_word  <= 10'd0;
	@(posedge clk_vid);
	vid_line_swap <= 0;

	@(posedge clk_vid);
	#0.01;
	$display("  Prefetch Line Word 0: vid_rdata = %08x (expected B0000000)", vid_rdata);
	if (vid_rdata !== 32'hB000_0000) $fatal(1, "Prefetch Line Word 0 mismatch!");

	@(posedge clk_vid);
	vid_col_word <= 10'd1;
	@(posedge clk_vid);
	#0.01;
	$display("  Prefetch Line Word 1: vid_rdata = %08x (expected B0000001)", vid_rdata);
	if (vid_rdata !== 32'hB000_0001) $fatal(1, "Prefetch Line Word 1 mismatch!");

	@(posedge clk_vid);
	vid_col_word <= 10'd127;
	@(posedge clk_vid);
	#0.01;
	$display("  Prefetch Line Word 127: vid_rdata = %08x (expected B000007F)", vid_rdata);
	if (vid_rdata !== 32'hB000_007F) $fatal(1, "Prefetch Line Word 127 mismatch!");

	$display("ALL TESTS PASSED! vram_ddr3 verified successfully!");
	$finish;
end

endmodule
