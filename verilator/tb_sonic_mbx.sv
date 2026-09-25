//============================================================================
//  tb_sonic_mbx — directed bench for rtl/sonic_mbx.sv.
//
//  Plays the three parties around the block: the service FSM's device port
//  (the guest CPU), the service FSM's DMA grant + guest RAM, and the top's
//  DDR3 arbiter with the ARM behind the window.  The window layout and the
//  DMA op semantics are the ones Main's support/mac/test/mac_q8_test.cpp
//  models in C; a change to either side must keep both benches green.
//
//    make tb_sonic_mbx
//============================================================================
`timescale 1ns/1ps

module tb_sonic_mbx;

reg clk = 0;
always #15 clk = ~clk;

reg         nreset = 0, ena = 1;
wire        present, irq;
reg         sel = 0, write = 0, prom = 0;
reg   [7:2] addr = 0;
reg   [3:0] be = 0;
reg  [31:0] wdata = 0;
wire        ack;
wire [31:0] rdata;
wire        dma_req, dma_we;
wire [26:2] dma_addr;
wire  [3:0] dma_be;
wire [31:0] dma_wdata;
reg         dma_ack = 0;
reg  [31:0] dma_rdata = 0;
wire [11:0] mem_addr;
wire        mem_rd, mem_we;
wire [63:0] mem_wdata;
reg         mem_accept = 0, mem_rvalid = 0;
reg  [63:0] mem_rdata = 0;

wire [47:0] cpu_sample = 48'h2000_4080_1234;
sonic_mbx dut (.*);

//----------------------------------------------------------------------------
// DDR3 window + the top's arbiter: accept is registered, reads answer later,
// and the bridge is busy at random so every wait state gets exercised
//----------------------------------------------------------------------------
reg [63:0] win [0:4095];
reg        ddr_dead = 0;
integer    ddr_reqs = 0;
reg  [2:0] rd_wait = 0;
reg [11:0] rd_a;
reg        rd_busy = 0;
always @(posedge clk) begin
	mem_accept <= 0;
	mem_rvalid <= 0;
	if (rd_busy) begin
		if (rd_wait == 0) begin mem_rvalid <= 1; mem_rdata <= win[rd_a]; rd_busy <= 0; end
		else rd_wait <= rd_wait - 1'b1;
	end
	else if ((mem_rd || mem_we) && !mem_accept && !ddr_dead && ($urandom_range(0, 3) != 0)) begin
		mem_accept <= 1;
		ddr_reqs   <= ddr_reqs + 1;
		if (mem_we) win[mem_addr] <= mem_wdata;
		else begin rd_busy <= 1; rd_a <= mem_addr; rd_wait <= $urandom_range(1, 4); end
	end
end

//----------------------------------------------------------------------------
// guest RAM behind the service FSM's DMA arm
//----------------------------------------------------------------------------
reg [31:0] ram [0:65535];       // 256 KB, longword-indexed
integer    beats = 0;
reg  [2:0] gw = 0;
always @(posedge clk) begin
	dma_ack <= 0;
	if (dma_req && !dma_ack) begin
		if (gw == 0) begin
			dma_ack <= 1;
			beats   <= beats + 1;
			if (dma_we) begin
				if (dma_be[3]) ram[dma_addr[17:2]][31:24] <= dma_wdata[31:24];
				if (dma_be[2]) ram[dma_addr[17:2]][23:16] <= dma_wdata[23:16];
				if (dma_be[1]) ram[dma_addr[17:2]][15:8]  <= dma_wdata[15:8];
				if (dma_be[0]) ram[dma_addr[17:2]][7:0]   <= dma_wdata[7:0];
			end
			else dma_rdata <= ram[dma_addr[17:2]];
			gw <= $urandom_range(0, 3);
		end
		else gw <= gw - 1'b1;
	end
end

function [7:0] ram_byte(input [31:0] a);
	ram_byte = ram[a[17:2]][8 * (3 - a[1:0]) +: 8];
endfunction
task ram_set_byte(input [31:0] a, input [7:0] v);
	ram[a[17:2]][8 * (3 - a[1:0]) +: 8] = v;
endtask
function [7:0] xfer_byte(input integer off);
	xfer_byte = win[off / 8][8 * (off % 8) +: 8];
endfunction
task xfer_set_byte(input integer off, input [7:0] v);
	win[off / 8][8 * (off % 8) +: 8] = v;
endtask

//----------------------------------------------------------------------------
// the guest CPU
//----------------------------------------------------------------------------
integer fails = 0, checks = 0;
task check(input bit ok, input string what);
	begin
		checks = checks + 1;
		if (!ok) begin fails = fails + 1; $display("FAIL: %s", what); end
	end
endtask

reg [31:0] got;
task cpu(input bit wr, input bit pr, input [7:0] a, input [3:0] lanes, input [31:0] d);
	integer n;
	begin
		@(posedge clk); sel <= 1; write <= wr; prom <= pr; addr <= a[7:2]; be <= lanes; wdata <= d;
		n = 0;
		while (!ack) begin @(posedge clk); n = n + 1; if (n > 300000) begin check(0, "cpu cycle never acked"); break; end end
		got = rdata;
		sel <= 0;
		@(posedge clk);
	end
endtask
task reg_wr(input [5:0] r, input [15:0] v); cpu(1, 0, {r, 2'b00}, 4'b0011, {16'h0, v}); endtask
task reg_rd(input [5:0] r);                 cpu(0, 0, {r, 2'b00}, 4'b0011, 0);           endtask

localparam MAGIC = 12'h800, WPTR = 12'h801, SHAD = 12'h802, ISRSET = 12'h812, ISRACK = 12'h813,
           PROMW = 12'h814, PTRS = 12'h816, DMACMD = 12'h817, DMASTAT = 12'h818, OPS = 12'h820,
           RING = 12'h900;

task wait_clk(input integer n); repeat (n) @(posedge clk); endtask
task wait_stat(input [7:0] s);
	integer n;
	begin
		n = 0;
		while (win[DMASTAT][7:0] !== s) begin @(posedge clk); n = n + 1; if (n > 400000) begin check(0, "DMA never finished"); break; end end
	end
endtask

integer i, base;
reg [63:0] e;
initial begin
	for (i = 0; i < 4096; i = i + 1) win[i] = 0;
	for (i = 0; i < 65536; i = i + 1) ram[i] = 32'hEEEEEEEE;
	// a command and a post left over from a previous session must never replay
	win[DMACMD] = 64'h0000_0000_0000_0155; win[OPS] = {32'h0000_1000, 16'd8, 16'd1};
	win[ISRSET] = {33'd0, 15'h7FFF, 16'h0042};

	wait_clk(4); nreset = 1;
	wait_clk(400000);
	check(!present, "absent until the service writes MAGIC");
	check(ddr_reqs > 0 && ddr_reqs < 40, "idle: a MAGIC read every ~2 ms, nothing else");

	win[MAGIC] = 64'h4D635138_45544834;
	wait_clk(150000);
	check(present, "present once MAGIC is seen");
	check(win[WPTR] == 1 && win[RING][3:0] == 4'b0011, "guest reset announced: tag 1 at ring[0]");
	check(beats == 0, "a DMA command staged before the reset did not replay");
	check(win[ISRACK][15:0] == 16'h0042 && !irq, "a stale ISR post is adopted, not raised");
	reg_rd(5); check(got == 0, "ISR clear after reset");

	// register write -> doorbell
	reg_wr(6'h01, 16'h0020);
	e = win[RING + 1];
	check(win[WPTR] == 2 && e[0] && e[3:1] == 0 && e[9:4] == 6'h01 && e[31:16] == 16'h0020 && e[47:32] == 16'h0042,
	      "DCR write is ring[1] with the ISR_SET seq seen");
	cpu(1, 0, 8'h04, 4'b1100, 32'hBEEF0000);
	e = win[RING + 2];
	check(e[9:4] == 6'h01 && e[31:16] == 16'hBEEF, "a word write on the upper lanes is taken too");

	// register read <- shadow block, on demand
	win[SHAD + 1] = 64'h4444_3333_2222_1111;      // regs 4..7
	win[SHAD + 5] = 64'hDDDD_CCCC_BBBB_AAAA;      // regs 20..23
	reg_rd(6'd22); check(got == 32'h0000CCCC, "REA from the shadow, low half");
	cpu(0, 0, {6'd23, 2'b00}, 4'b1100, 0); check(got[31:16] == 16'hDDDD, "upper-lane read");
	reg_rd(6'd6);  check(got == 32'h00003333, "UTDA from the shadow");
	reg_rd(6'd4);  check(got == 0, "IMR is local, not the shadow's $1111");

	// MAC PROM
	win[PROMW] = 64'h8877_6655_4433_2211;
	cpu(0, 1, 8'h00, 4'b1111, 0); check(got == 32'h11223344, "PROM bytes 0-3");
	cpu(0, 1, 8'h04, 4'b1111, 0); check(got == 32'h55667788, "PROM bytes 4-7");

	// ISR ownership
	reg_wr(6'd4, 16'h0400);
	win[ISRSET] = {33'd0, 15'h0400, 16'h0043};
	wait_clk(1500);   // one idle poll round is 4 x 256 clocks
	check(irq, "posted PKTRX raises irq");
	check(win[ISRACK][15:0] == 16'h0043, "post acknowledged");
	reg_rd(5); check(got == 32'h00000400, "ISR reads the posted bit");
	reg_wr(6'd5, 16'h0400);
	check(!irq, "write-1-to-clear drops irq in the same cycle");
	reg_rd(5); check(got == 0, "and reads back clear at once");
	e = win[RING + win[WPTR][7:0] - 1];
	check(e[9:4] == 6'd5 && e[31:16] == 16'h0400 && e[47:32] == 16'h0043, "the ack's doorbell names post $43");
	win[ISRSET] = {33'd0, 15'h0200, 16'h0044};
	wait_clk(1500);   // one idle poll round is 4 x 256 clocks
	check(!irq, "a masked bit raises nothing");
	reg_rd(5); check(got == 32'h00000200, "but it is there");

	// CR command overlay
	win[SHAD] = 64'h0000_0000_0000_0094;          // reg 0 = CR, the model has not seen TXP yet
	reg_wr(6'd0, 16'h0002);
	reg_rd(6'd0); check(got == 32'h00000096, "TXP reads back set before the ARM applied it");
	win[PTRS] = {win[WPTR][31:0], win[WPTR][31:0]};
	wait_clk(800);
	reg_rd(6'd0); check(got == 32'h00000094, "and follows the shadow once the applied index passes");
	// the interrupt post carries the applied index too: TXP must be gone when TXDN shows
	reg_wr(6'd5, 16'h0200);                                    // the masked TXDN from above
	reg_wr(6'd4, 16'h0600);
	reg_wr(6'd0, 16'h0002);
	reg_rd(6'd0); check(got == 32'h00000096, "TXP overlay up again");
	win[PTRS] = 64'd0;                                         // PTRS deliberately stale
	win[ISRSET] = {win[WPTR][15:0], 16'd0, 1'b0, 15'h0200, 16'h0045};
	while (!irq) @(posedge clk);
	reg_rd(6'd0); check(got == 32'h00000094, "TXP reads clear in the TXDN handler's first CR read");
	reg_wr(6'd5, 16'h0200);
	win[PTRS] = {win[WPTR][31:0], win[WPTR][31:0]};

	// DMA: three ops in one list
	for (i = 0; i < 7; i = i + 1) xfer_set_byte(3 + i, 8'h10 + i);           // op0: 7 bytes -> $1003
	win[OPS + 0] = {32'h0000_1003, 16'd7, 16'd1};
	ram[16'h0800] = 32'hA1A2A3A4; ram[16'h0801] = 32'hB1B2B3B4; ram[16'h0802] = 32'hC1C2C3C4;
	win[OPS + 1] = {32'h0000_2001, 16'd9, 16'd0};                           // op1: 9 bytes <- $2001
	for (i = 0; i < 1514; i = i + 1) xfer_set_byte(16 + 16 + 2 + i, i[7:0] ^ 8'h5A);
	win[OPS + 2] = {32'h0000_3002, 16'd1514, 16'd1};                        // op2: a full frame -> $3002
	beats = 0;
	win[DMACMD] = 64'h0000_0000_0000_0301;
	wait_stat(8'h01);
	check(beats == 3 + 3 + 379, $sformatf("beat count %0d", beats));
	check(ram_byte(32'h1002) == 8'hEE && ram_byte(32'h1003) == 8'h10 && ram_byte(32'h1009) == 8'h16 &&
	      ram_byte(32'h100A) == 8'hEE, "op0: byte enables keep the neighbours");
	check(xfer_byte(16 + 1) == 8'hA2 && xfer_byte(16 + 4) == 8'hB1 && xfer_byte(16 + 9) == 8'hC2,
	      "op1: guest bytes land 8-aligned after op0, at offset + (addr & 3)");
	base = 0;
	for (i = 0; i < 1514; i = i + 1) if (ram_byte(32'h3002 + i) != (i[7:0] ^ 8'h5A)) base = base + 1;
	check(base == 0, $sformatf("op2: %0d frame bytes wrong", base));
	check(ram_byte(32'h3001) == 8'hEE && ram_byte(32'h3002 + 1514) == 8'hEE, "op2: frame edges");

	// read it back through a second list, registers moving meanwhile
	win[OPS + 0] = {32'h0000_3002, 16'd1514, 16'd0};
	win[DMACMD] = 64'h0000_0000_0000_0102;
	fork
		wait_stat(8'h02);
		begin reg_wr(6'h11, 16'h1234); reg_rd(6'd22); reg_wr(6'h12, 16'h5678); end
	join
	base = 0;
	for (i = 0; i < 1514; i = i + 1) if (xfer_byte(2 + i) != (i[7:0] ^ 8'h5A)) base = base + 1;
	check(base == 0, $sformatf("readback: %0d bytes wrong", base));
	check(got == 32'h0000CCCC, "a register read during the DMA still answers");

	// a guest reset mid-session: index restarts, the model is told, nothing replays
	nreset = 0; wait_clk(4); nreset = 1;
	beats = 0;
	wait_clk(3000);
	check(win[WPTR] == 1 && win[RING][3:1] == 3'd1, "reset: wptr restarts and announces tag 1");
	check(beats == 0 && !irq, "reset: no replay, no interrupt");

	// a dead window must not hold the CPU
	ddr_dead = 1;
	reg_rd(6'd22);
	check(got == 0, "watchdog retires a read with zeros");
	ddr_dead = 0;
	wait_clk(200);
	reg_rd(6'd22); check(got == 32'h0000CCCC, "and the next read is its own");

	// OSD off: provably inert
	ena = 0; wait_clk(10);
	i = ddr_reqs;
	wait_clk(200000);
	check(ddr_reqs == i && !present && !dma_req && !irq, "Ethernet off: no DDR3 traffic, no bus, no irq");

	$display("%0d checks, %0d failed", checks, fails);
	if (fails) $fatal(1, "tb_sonic_mbx FAILED");
	$finish;
end

endmodule
