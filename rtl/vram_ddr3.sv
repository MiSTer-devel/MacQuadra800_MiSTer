//============================================================================
//  vram_ddr3.sv — 1 MB / 2 MB DDR3-backed VRAM Controller with Ping-Pong
//  Scanline Cache for Mac Quadra 800.
//
//  Replaces ~260 M10K blocks of on-chip BRAM with a 1 MB DDR3 framebuffer
//  and an 8-block M10K ping-pong scanline cache.
//============================================================================

`timescale 1ns/1ps

module vram_ddr3 #(
	parameter [28:0] DDR_VRAM_BASE   = 29'h0500_0000, // 64-bit word address (byte 0x2800_0000 >> 3)
	parameter        VRAM_1MB        = 1              // 1 = 1 MB wrap (ROM probe advertises 1 MB)
)(
	input             clk_sys,         // 33.33 MHz system clock
	input             reset,           // synchronous reset on clk_sys

	//---------------------------------------------------------
	// CPU / quadra800 bus interface (clk_sys)
	//---------------------------------------------------------
	input             mem_req,
	input             mem_is_vram,
	input             mem_write,
	input      [31:2] mem_addr,
	input       [3:0] mem_be,
	input      [31:0] mem_wdata,
	input             mem_vram_wp,     // 1-cycle direct write strobe from store buffer
	output reg        vram_ack,
	output reg [31:0] vram_rdata,
	output            vram_wq_room,    // write queue has room

	//---------------------------------------------------------
	// Video Scanout interface (clk_vid)
	//---------------------------------------------------------
	input             clk_vid,         // 25.175 MHz pixel dot clock
	input             reset_vid,
	input       [9:0] vid_col_word,    // word index (0..1023) within the scanline
	input      [13:0] vid_stride,      // row stride in bytes (e.g. 1024)
	input             vid_line_req,    // pulse at hcnt==0: fetch upcoming scanline
	input      [20:0] vid_line_addr,   // byte address of upcoming scanline
	input             vid_line_swap,   // pulse at hcnt==H_TOT-3: swap ping-pong buffers
	output     [31:0] vid_rdata,       // pixel data to DAFB (1-cycle registered latency)

	//---------------------------------------------------------
	// DDR3 Arbiter client interface (clk_sys)
	//---------------------------------------------------------
	output reg        vram_ddr_req,
	output reg        vram_ddr_we,
	output reg [28:0] vram_ddr_addr,
	output reg  [7:0] vram_ddr_burstcnt,
	output reg [63:0] vram_ddr_din,
	output reg  [7:0] vram_ddr_be,
	input             vram_ddr_busy,
	input             vram_ddr_ack,
	input      [63:0] vram_ddr_dout,
	input             vram_ddr_rvalid
);

//----------------------------------------------------------------------------
// Address mapping: relative 64-bit word address within VRAM
//----------------------------------------------------------------------------
wire [16:0] cpu_w64_addr = VRAM_1MB ? {1'b0, mem_addr[18:3]} : mem_addr[19:3];
wire [63:0] cpu_w64_din  = mem_addr[2] ? {mem_wdata, 32'd0} : {32'd0, mem_wdata};
wire  [7:0] cpu_w64_be   = mem_addr[2] ? {mem_be, 4'b0000}  : {4'b0000, mem_be};

//----------------------------------------------------------------------------
// Ping-Pong Scanline Cache (8 M10K blocks total: 2 banks of 1024 x 32-bit)
// Bank Even: holds words with col[0] == 0 (DDR3 bits [31:0])
// Bank Odd:  holds words with col[0] == 1 (DDR3 bits [63:32])
// Each bank has 1024 entries: [9] is buffer select (0 or 1), [8:0] is word64 index
//----------------------------------------------------------------------------
(* ramstyle = "M10K, no_rw_check" *) reg [7:0] line_even_b0 [0:1023];
(* ramstyle = "M10K, no_rw_check" *) reg [7:0] line_even_b1 [0:1023];
(* ramstyle = "M10K, no_rw_check" *) reg [7:0] line_even_b2 [0:1023];
(* ramstyle = "M10K, no_rw_check" *) reg [7:0] line_even_b3 [0:1023];

(* ramstyle = "M10K, no_rw_check" *) reg [7:0] line_odd_b0  [0:1023];
(* ramstyle = "M10K, no_rw_check" *) reg [7:0] line_odd_b1  [0:1023];
(* ramstyle = "M10K, no_rw_check" *) reg [7:0] line_odd_b2  [0:1023];
(* ramstyle = "M10K, no_rw_check" *) reg [7:0] line_odd_b3  [0:1023];

reg        buf_display_vid = 1'b1;
reg        buf_prefetch_sys = 1'b0;
reg        buf_display_sys = 1'b1;

// Read side on clk_vid
reg  [9:0] vid_col_word_d;
reg [31:0] vid_rdata_even, vid_rdata_odd;

wire [9:0] line_rd_addr = {buf_display_vid, vid_col_word[9:1]};

always @(posedge clk_vid) begin
	vid_col_word_d <= vid_col_word;
	vid_rdata_even <= {line_even_b3[line_rd_addr], line_even_b2[line_rd_addr],
	                   line_even_b1[line_rd_addr], line_even_b0[line_rd_addr]};
	vid_rdata_odd  <= {line_odd_b3[line_rd_addr],  line_odd_b2[line_rd_addr],
	                   line_odd_b1[line_rd_addr],  line_odd_b0[line_rd_addr]};
end

assign vid_rdata = vid_col_word_d[0] ? vid_rdata_odd : vid_rdata_even;

// Buffer swap on clk_vid
reg swap_tog_vid = 1'b0;
always @(posedge clk_vid) begin
	if (reset_vid) begin
		buf_display_vid <= 1'b1;
		swap_tog_vid    <= 1'b0;
	end
	else if (vid_line_swap) begin
		buf_display_vid <= ~buf_display_vid;
		swap_tog_vid    <= ~swap_tog_vid;
	end
end

// Synchronize swap to clk_sys
reg swap_meta, swap_s1, swap_s2;
always @(posedge clk_sys) begin
	swap_meta <= swap_tog_vid;
	swap_s1   <= swap_meta;
	swap_s2   <= swap_s1;
	if (reset) begin
		buf_prefetch_sys <= 1'b0;
		buf_display_sys  <= 1'b1;
	end
	else if (swap_s1 ^ swap_s2) begin
		buf_prefetch_sys <= ~buf_prefetch_sys;
		buf_display_sys  <= ~buf_display_sys;
	end
end

// Synchronize line_fetch_req from clk_vid to clk_sys
reg fetch_tog_vid = 1'b0;
always @(posedge clk_vid) begin
	if (reset_vid) fetch_tog_vid <= 1'b0;
	else if (vid_line_req) fetch_tog_vid <= ~fetch_tog_vid;
end

reg fetch_meta, fetch_s1, fetch_s2;
always @(posedge clk_sys) begin
	fetch_meta <= fetch_tog_vid;
	fetch_s1   <= fetch_meta;
	fetch_s2   <= fetch_s1;
end
wire line_req_sys = fetch_s1 ^ fetch_s2;

// Track active line base addresses for DMA & snoop
reg [16:0] cur_display_line_word64;
reg [16:0] cur_prefetch_line_word64;
reg [13:0] vid_stride_sys;

always @(posedge clk_sys) begin
	if (reset) begin
		cur_display_line_word64  <= 17'd0;
		cur_prefetch_line_word64 <= 17'd0;
		vid_stride_sys           <= 14'd1024;
	end
	else begin
		vid_stride_sys <= vid_stride;
		if (swap_s1 ^ swap_s2) begin
			cur_display_line_word64 <= cur_prefetch_line_word64;
		end
		if (line_req_sys) begin
			cur_prefetch_line_word64 <= vid_line_addr[19:3];
		end
	end
end

//----------------------------------------------------------------------------
// CPU Write FIFO (32 entries deep, 64-bit wide)
//----------------------------------------------------------------------------
localparam FIFO_DEPTH = 32;
reg  [16:0] fifo_addr [0:FIFO_DEPTH-1];
reg  [63:0] fifo_din  [0:FIFO_DEPTH-1];
reg   [7:0] fifo_be   [0:FIFO_DEPTH-1];
reg   [5:0] fifo_count = 6'd0;
reg   [4:0] fifo_wptr  = 5'd0;
reg   [4:0] fifo_rptr  = 5'd0;
reg         fifo_pop;

wire  [5:0] fifo_count_eff = fifo_pop ? (fifo_count - 1'b1) : fifo_count;

assign vram_wq_room = (fifo_count_eff < (FIFO_DEPTH - 4));

// Detect CPU write condition
reg vram_wr_ph = 1'b0;
wire cpu_vram_write = mem_vram_wp || (mem_req && mem_is_vram && mem_write && !vram_wr_ph);

// Write FIFO push logic
always @(posedge clk_sys) begin
	if (reset) begin
		fifo_count <= 6'd0;
		fifo_wptr  <= 5'd0;
	end
	else begin
		if (cpu_vram_write && (fifo_count < FIFO_DEPTH)) begin
			fifo_addr[fifo_wptr] <= cpu_w64_addr;
			fifo_din[fifo_wptr]  <= cpu_w64_din;
			fifo_be[fifo_wptr]   <= cpu_w64_be;
			fifo_wptr            <= fifo_wptr + 1'b1;
			if (!fifo_pop) fifo_count <= fifo_count + 1'b1;
		end
		else if (fifo_pop) begin
			fifo_count <= fifo_count - 1'b1;
		end
	end
end

always @(posedge clk_sys) begin
	if (reset) fifo_rptr <= 5'd0;
	else if (fifo_pop) fifo_rptr <= fifo_rptr + 1'b1;
end

//----------------------------------------------------------------------------
// CPU Write Snoop into Ping-Pong Line Buffer
// Updates visible scanline immediately so CPU writes never tear or drop
//----------------------------------------------------------------------------
wire [16:0] snoop_disp_diff = cpu_w64_addr - cur_display_line_word64;
wire        snoop_disp_hit  = (snoop_disp_diff < {6'd0, vid_stride_sys[13:3]});
wire  [9:0] snoop_disp_addr = {buf_display_sys, snoop_disp_diff[8:0]};

wire [16:0] snoop_pref_diff = cpu_w64_addr - cur_prefetch_line_word64;
wire        snoop_pref_hit  = (snoop_pref_diff < {6'd0, vid_stride_sys[13:3]});
wire  [9:0] snoop_pref_addr = {buf_prefetch_sys, snoop_pref_diff[8:0]};

//----------------------------------------------------------------------------
// DDR3 DMA Burst Engine for Line Pre-fetch
//----------------------------------------------------------------------------
localparam DMA_IDLE       = 3'd0;
localparam DMA_BURST_REQ  = 3'd1;
localparam DMA_BURST_DATA = 3'd2;
localparam DMA_BURST_DONE = 3'd3;

reg [2:0] dma_state = DMA_IDLE;
reg [8:0] dma_word64_idx;
reg [7:0] dma_total_bursts;
reg [7:0] dma_burst_idx;
reg [4:0] dma_beats_left;
reg [16:0] dma_cur_addr;

wire dma_writing = (dma_state == DMA_BURST_DATA) && vram_ddr_rvalid;
wire [9:0] dma_wr_addr = {buf_prefetch_sys, dma_word64_idx};

// Single multiplexed Write Port on clk_sys for M10K BRAM inference
wire        line_wr_dma = dma_writing;
wire        line_wr_cpu = cpu_vram_write && (snoop_disp_hit || snoop_pref_hit);
wire        line_wr_en  = line_wr_dma || line_wr_cpu;

wire  [9:0] line_wr_addr = line_wr_dma ? dma_wr_addr :
                           snoop_disp_hit ? snoop_disp_addr : snoop_pref_addr;

wire [63:0] line_wr_din  = line_wr_dma ? vram_ddr_dout : cpu_w64_din;
wire  [7:0] line_wr_be   = line_wr_dma ? 8'hFF : cpu_w64_be;

always @(posedge clk_sys) begin
	if (line_wr_en) begin
		if (line_wr_be[0]) line_even_b0[line_wr_addr] <= line_wr_din[7:0];
		if (line_wr_be[1]) line_even_b1[line_wr_addr] <= line_wr_din[15:8];
		if (line_wr_be[2]) line_even_b2[line_wr_addr] <= line_wr_din[23:16];
		if (line_wr_be[3]) line_even_b3[line_wr_addr] <= line_wr_din[31:24];

		if (line_wr_be[4]) line_odd_b0[line_wr_addr]  <= line_wr_din[39:32];
		if (line_wr_be[5]) line_odd_b1[line_wr_addr]  <= line_wr_din[47:40];
		if (line_wr_be[6]) line_odd_b2[line_wr_addr]  <= line_wr_din[55:48];
		if (line_wr_be[7]) line_odd_b3[line_wr_addr]  <= line_wr_din[63:56];
	end
end

//----------------------------------------------------------------------------
// DDR3 Request & Arbitration FSM
// Priority:
//   1. CPU Read (on-demand probe / CopyBits read, flushes write queue first)
//   2. Line DMA Burst (pre-fetches next scanline during horizontal period)
//   3. CPU Write Drain (drains FIFO to DDR3 between DMA bursts)
//----------------------------------------------------------------------------
localparam S_IDLE      = 3'd0;
localparam S_CPU_READ  = 3'd1;
localparam S_DMA_BURST = 3'd2;
localparam S_CPU_WRITE = 3'd3;

reg [2:0] state = S_IDLE;
reg       cpu_rd_pend = 1'b0;

always @(posedge clk_sys) begin
	vram_ack     <= 1'b0;
	fifo_pop     <= 1'b0;
	vram_ddr_req <= 1'b0;

	if (reset) begin
		state           <= S_IDLE;
		dma_state       <= DMA_IDLE;
		cpu_rd_pend     <= 1'b0;
		vram_wr_ph      <= 1'b0;
		dma_word64_idx  <= 9'd0;
	end
	else begin
		// Normal write handshake with quadra800 bus
		if (mem_req && mem_is_vram && mem_write) begin
			vram_wr_ph <= !vram_wr_ph;
			if (vram_wr_ph) vram_ack <= 1'b1;
		end
		else begin
			vram_wr_ph <= 1'b0;
		end

		// DMA trigger: start prefetch on line_req_sys
		if (line_req_sys) begin
			dma_cur_addr      <= vid_line_addr[19:3];
			dma_total_bursts  <= {1'b0, vid_stride_sys[13:7]} + (vid_stride_sys[6:0] != 7'd0 ? 8'd1 : 8'd0);
			dma_burst_idx     <= 8'd0;
			dma_word64_idx    <= 9'd0;
			dma_state         <= DMA_BURST_REQ;
		end

		// CPU Read detection
		if (mem_req && mem_is_vram && !mem_write && !vram_ack) begin
			cpu_rd_pend <= 1'b1;
		end

		// DMA beat counter
		if (dma_state == DMA_BURST_DATA) begin
			if (vram_ddr_rvalid) begin
				dma_word64_idx  <= dma_word64_idx + 1'b1;
				dma_cur_addr    <= dma_cur_addr + 1'b1;
				dma_beats_left  <= dma_beats_left - 1'b1;
				if (dma_beats_left == 5'd1) begin
					dma_burst_idx <= dma_burst_idx + 1'b1;
					if (dma_burst_idx + 1'b1 >= dma_total_bursts) begin
						dma_state <= DMA_IDLE;
					end
					else begin
						dma_state <= DMA_BURST_REQ;
					end
				end
			end
		end

		// DDR3 bus state machine
		case (state)
		S_IDLE: begin
			// 1. CPU Read (if write queue empty)
			if (cpu_rd_pend && (fifo_count_eff == 0)) begin
				vram_ddr_req      <= 1'b1;
				vram_ddr_we       <= 1'b0;
				vram_ddr_addr     <= DDR_VRAM_BASE + {12'd0, cpu_w64_addr};
				vram_ddr_burstcnt <= 8'd1;
				state             <= S_CPU_READ;
			end
			// 2. CPU Write drain (top priority if CPU read waiting on non-empty queue, or if queue getting full)
			else if ((fifo_count_eff > 0) && (cpu_rd_pend || (fifo_count_eff >= 16) || (dma_state == DMA_IDLE))) begin
				vram_ddr_req      <= 1'b1;
				vram_ddr_we       <= 1'b1;
				vram_ddr_addr     <= DDR_VRAM_BASE + {12'd0, fifo_addr[fifo_rptr]};
				vram_ddr_din      <= fifo_din[fifo_rptr];
				vram_ddr_be       <= fifo_be[fifo_rptr];
				vram_ddr_burstcnt <= 8'd1;
				state             <= S_CPU_WRITE;
			end
			// 3. Line DMA burst read
			else if (dma_state == DMA_BURST_REQ) begin
				vram_ddr_req      <= 1'b1;
				vram_ddr_we       <= 1'b0;
				vram_ddr_addr     <= DDR_VRAM_BASE + {12'd0, dma_cur_addr};
				vram_ddr_burstcnt <= 8'd16;
				state             <= S_DMA_BURST;
			end
			// 4. Opportunistic write drain when idle
			else if (fifo_count_eff > 0) begin
				vram_ddr_req      <= 1'b1;
				vram_ddr_we       <= 1'b1;
				vram_ddr_addr     <= DDR_VRAM_BASE + {12'd0, fifo_addr[fifo_rptr]};
				vram_ddr_din      <= fifo_din[fifo_rptr];
				vram_ddr_be       <= fifo_be[fifo_rptr];
				vram_ddr_burstcnt <= 8'd1;
				state             <= S_CPU_WRITE;
			end
		end

		S_CPU_READ: begin
			vram_ddr_req <= 1'b1;
			if (vram_ddr_ack) begin
				vram_ddr_req <= 1'b0;
			end
			if (vram_ddr_rvalid) begin
				vram_rdata  <= mem_addr[2] ? vram_ddr_dout[63:32] : vram_ddr_dout[31:0];
				vram_ack    <= 1'b1;
				cpu_rd_pend <= 1'b0;
				state       <= S_IDLE;
			end
		end

		S_DMA_BURST: begin
			vram_ddr_req <= 1'b1;
			if (vram_ddr_ack) begin
				vram_ddr_req   <= 1'b0;
				dma_beats_left <= 5'd16;
				dma_state      <= DMA_BURST_DATA;
				state          <= S_IDLE; // returns to IDLE to interleave writes or next burst
			end
		end

		S_CPU_WRITE: begin
			vram_ddr_req <= 1'b1;
			if (vram_ddr_ack) begin
				vram_ddr_req <= 1'b0;
				fifo_pop     <= 1'b1;
				state        <= S_IDLE;
			end
		end

		default: state <= S_IDLE;
		endcase
	end
end

endmodule
