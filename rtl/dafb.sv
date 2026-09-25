//============================================================================
//  dafb — DAFB II video as integrated in djMEMC (MAME dafb.cpp DAFB_MEMC,
//  version 3), Quadra 800 flavor.
//
//  Register blocks at $F9800000 (32-bit registers, low 12 bits live):
//    +$000 DAFB:   fb base ($00 bits 20:9, $04 bits 8:5), stride ($08, in
//          longwords), timing ctrl ($0C), config ($10), monitor sense
//          ($1C — hardwired 13" 640x480: reads 1), test/version ($2C =
//          version 3 << 9)
//    +$100 Swatch: mode ($00), int enable ($04 bit0 VBL), int status
//          ($08), VBL clear ($14, read or write; $0C cursor), H/V CRTC
//          params ($24-$64, stored, not interpreted — scanout is a fixed
//          640x480 window)
//    +$200 RAMDAC (AC842a): palette address ($00), palette data ($10,
//          R,G,B write cycle), pixel bus control ($20 — bits 4:2 select
//          1/2/4/8/24 bpp)
//    +$300 clockgen (DP8534): writes stored, reads 0; the sim scanout
//          does not model the PLL
//
//  Scanout: 640x480 in an 800x525 frame, one pixel per clk, 8bpp (and
//  1/2/4bpp) from VRAM through the CLUT.  VRAM reads go out on vid_addr
//  and return registered on vid_rdata the next cycle.  VBL raises
//  int_status bit 0 (when enabled) at the start of the blank; the irq
//  output is simply |int_status (MAME recalc_ints).
//============================================================================

module dafb
(
	input         clk,
	input         nreset,
	input         ce,

	// Scanout clock. The register file, the CLUT writes and the VBL status
	// bit stay on clk (the machine's 33 MHz); everything from hcnt/vcnt down
	// runs on clk_vid, which is the real 25.175 MHz dot clock so the core
	// presents a standard VGA 640x480 @ 59.94 Hz mode. See rtl/pll_video.v
	// for why that matters to the HDMI scaler, and MacLC's maclc_v8_video.sv
	// for the same arrangement -- config 2FF-synced in, VBL toggled back.
	input         clk_vid,
	input         nreset_vid,
	// Monitor on the DA-15: 0 = 13" RGB 640x480 (sense code 6), 1 = 12" RGB
	// 512x384 (sense code 2).  Quasi-static: the platform latches it under
	// reset, because a real Quadra samples the sense lines only in the ROM's
	// boot probe and QuickDraw lays out for the boot geometry.  It picks
	// both the sense-register answer and the scanout timing (clk_vid is
	// retargeted to the matching dot clock by MacQuadra800.sv).
	input         mon_12in,

	// register beat slave ($F9800000 block, addr = offset bits [9:2])
	input         sel,
	input         write,
	input   [9:2] addr,
	input  [31:0] wdata,
	output reg [31:0] rdata,
	output reg    ack,

	output        vbl_irq,

	// video: VRAM word fetch (registered externally, 1-cycle latency)
	output [21:2] vid_addr,
	input  [31:0] vid_rdata,
	// the programmed row pitch, so the platform's VRAM mapper can compact
	// away the never-visible tail of each row (see MacQuadra800.sv)
	output [13:0] vid_stride,

	output  [7:0] vga_r,
	output  [7:0] vga_g,
	output  [7:0] vga_b,
	output reg    vga_hs,
	output reg    vga_vs,
	output        vga_hb,
	output        vga_vb,
	output        ce_pixel
);

//----------------------------------------------------------------------------
// registers
//----------------------------------------------------------------------------
reg [20:0] fb_base;
reg [13:0] stride;               // bytes
assign vid_stride = stride;
reg  [2:0] sense_drive;          // last value written to the sense register
reg [11:0] timing_ctrl, config_r, swatch_mode, test_r, swatch_test;
reg [11:0] hparam [0:9];
reg [11:0] vparam [0:6];
// MAME's DAFB has VBL on status bit 0 (clear at +$114); QEMU's macfb has
// it on bit 2 (clear at +$10C, irq masked by +$104).  The ROM boots on
// both, so serve both conventions: VBL raises bits {2,0} as enabled,
// either clear address drops them, irq = |(status & enable).
reg  [2:0] int_en;
reg  [2:0] int_status;
reg [11:0] cursor_line, anim_line;

reg  [7:0] pal_addr;
reg  [1:0] pal_idx;
// The CLUT is a true dual-port, dual-clock RAM per plane: port A (clk) is
// the RAMDAC write and its readback, port B (clk_vid) is the scan-out.  As
// three plain arrays with a second read port on clk, synthesis kept the M10K
// for the scan-out and rebuilt the readback from logic — 6.7k LUTs and 3.5k
// registers for this module.  With explicit ports it is three M10Ks.
wire [7:0] pal_q_r, pal_q_g, pal_q_b;     // port A readback of pal_addr
wire [7:0] clut_r, clut_g, clut_b;        // port B scan-out
wire [7:0] clut_idx;
reg        pal_rd_pend;                   // readback: one cycle for the RAM
// RAMDAC data register ($200+$10): the write lands in the access cycle, at
// the address the RAMDAC currently points at (it auto-increments after B).
wire       pal_acc  = sel && !ack && (blk == 2'd2) && (rsel == 6'h04);
wire       pal_rd   = pal_acc && !write;
wire       pal_wr   = pal_acc &&  write && ce;
wire       pal_we_r = pal_wr && (pal_idx == 2'd0);
wire       pal_we_g = pal_wr && (pal_idx == 2'd1);
wire       pal_we_b = pal_wr && (pal_idx == 2'd2);
dafb_clut clut_r_i (.clka(clk), .aa(pal_addr), .da(wdata[7:0]), .wea(pal_we_r), .qa(pal_q_r),
                    .clkb(clk_vid), .ab(clut_idx), .qb(clut_r));
dafb_clut clut_g_i (.clka(clk), .aa(pal_addr), .da(wdata[7:0]), .wea(pal_we_g), .qa(pal_q_g),
                    .clkb(clk_vid), .ab(clut_idx), .qb(clut_g));
dafb_clut clut_b_i (.clka(clk), .aa(pal_addr), .da(wdata[7:0]), .wea(pal_we_b), .qa(pal_q_b),
                    .clkb(clk_vid), .ab(clut_idx), .qb(clut_b));
reg  [7:0] pbctrl;
reg  [2:0] mode;                 // 0=1bpp 1=2bpp 2=4bpp 3=8bpp 4=24bpp

assign vbl_irq = |(int_status & int_en);

wire [5:0] rsel = addr[7:2];     // register within a block
wire [1:0] blk  = addr[9:8];

// pulsed in the clk domain one clk_vid VBL later; see the CDC below
wire vbl_start;

always @(posedge clk) begin
	if (!nreset) begin
		ack <= 0; rdata <= 0;
		fb_base <= 0; stride <= 14'd1024; sense_drive <= 3'b111;
		timing_ctrl <= 0; config_r <= 0; swatch_mode <= 12'd1;
		test_r <= 0; swatch_test <= 0;
		int_en <= 0; int_status <= 0;
		cursor_line <= 0; anim_line <= 0;
		pal_addr <= 0; pal_idx <= 0; pbctrl <= 0; mode <= 3'd0;
		pal_rd_pend <= 0;
	end
	else if (ce) begin
		ack <= 0;

		// VBL: status rises at the blank unconditionally (QEMU macfb — the
		// ROM polls INTR_STAT with the mask off); the irq output is masked
		if (vbl_start) begin
			int_status[0] <= 1'b1;
			int_status[2] <= 1'b1;
		end

		// RAMDAC data readback: cycle 1 lets the RAM present pal_addr, cycle
		// 2 returns it.  Every other access still completes in one cycle.
		if (pal_rd && !pal_rd_pend) begin
			pal_rd_pend <= 1;
		end
		else if (sel && !ack) begin
			ack   <= 1;
			rdata <= 32'h0;
			pal_rd_pend <= 0;
			case (blk)
			2'd0: begin                                   // DAFB
				if (write) begin
`ifdef VERILATOR
					// bring-up tap: what the ROM/driver actually programs.
					// The 308 KB VRAM only covers 480 rows if stride <= 640.
					if (rsel <= 6'h04)
						$display("[DAFB] reg %02h <= %03h  (fb_base=%06h stride=%0d mode=%0d)",
						         {rsel, 2'b00}, wdata[11:0], fb_base, stride, mode);
`endif
					case (rsel)
					6'h00: fb_base[20:9] <= wdata[11:0];
					6'h01: fb_base[8:5]  <= wdata[3:0];
					6'h02: stride        <= {wdata[11:0], 2'b00};
					6'h03: timing_ctrl   <= wdata[11:0];
					6'h04: config_r      <= wdata[11:0];
					6'h07: sense_drive   <= wdata[2:0];
					6'h0B: test_r        <= wdata[11:0];
					default: ;                            // SCSI ctl etc
					endcase
				end
				else begin
					case (rsel)
					6'h00: rdata <= {20'd0, fb_base[20:9]};
					6'h01: rdata <= {28'd0, fb_base[8:5]};
					6'h02: rdata <= {20'd0, stride[13:2]};
					6'h03: rdata <= {20'd0, timing_ctrl};
					6'h04: rdata <= {20'd0, config_r};
					// QEMU macfb normal-sense formula (~code & 7) | (~driven & 7):
					// 13" 640x480 is code 6 (~6 = 001), 12" 512x384 is code 2
					// (~2 = 101) -- MAME dafb.cpp's table, Apple TN HW26.
					6'h07: rdata <= {29'd0, (mon_12in ? 3'b101 : 3'b001) | ~sense_drive};
					6'h0B: rdata <= {20'd0, 3'd3, test_r[8:0]};  // DAFB version 3
					default: ;
					endcase
				end
			end
			2'd1: begin                                   // Swatch
				if (write) begin
					case (rsel)
					6'h00: swatch_mode <= wdata[11:0];
					6'h01: begin
						int_en <= wdata[2:0];
						if (!wdata[0]) int_status[0] <= 0;
						if (!wdata[2]) int_status[2] <= 0;
					end
					6'h03: int_status <= 0;               // clear (macfb $10C)
					6'h05: int_status <= 0;               // clear (DAFB $114)
					6'h06: cursor_line <= wdata[11:0];
					6'h07: anim_line   <= wdata[11:0];
					6'h08: swatch_test <= wdata[11:0];
					default: begin
						if (rsel >= 6'h09 && rsel <= 6'h12)
							hparam[rsel - 6'h09] <= wdata[11:0];
						if (rsel >= 6'h13 && rsel <= 6'h19)
							vparam[rsel - 6'h13] <= wdata[11:0];
					end
					endcase
				end
				else begin
					case (rsel)
					6'h02: rdata <= {29'd0, int_status};
					6'h03: begin rdata <= 0; int_status <= 0; end
					6'h05: begin rdata <= 0; int_status <= 0; end
					6'h08: rdata <= {20'd0, swatch_test};
					default: begin
						if (rsel >= 6'h09 && rsel <= 6'h12)
							rdata <= {20'd0, hparam[rsel - 6'h09]};
						if (rsel >= 6'h13 && rsel <= 6'h19)
							rdata <= {20'd0, vparam[rsel - 6'h13]};
					end
					endcase
				end
			end
			2'd2: begin                                   // RAMDAC (AC842a)
				if (write) begin
					case (rsel)
					6'h00: begin pal_addr <= wdata[7:0]; pal_idx <= 0; end
					6'h04: begin
						// the plane write itself is pal_we_* above
						if (pal_idx == 2'd2) begin
							pal_idx  <= 0;
							pal_addr <= pal_addr + 1'b1;
						end
						else pal_idx <= pal_idx + 1'b1;
					end
					6'h08: begin
						pbctrl <= wdata[7:0];
						case (wdata[4:2])
						3'b000: mode <= 3'd0;             // 1bpp
						3'b010: mode <= 3'd1;             // 2bpp
						3'b100: mode <= 3'd2;             // 4bpp
						3'b110: mode <= 3'd3;             // 8bpp
						default: mode <= 3'd4;            // 24bpp
						endcase
					end
					default: ;
					endcase
				end
				else begin
					case (rsel)
					6'h00: begin rdata <= {24'd0, pal_addr}; pal_idx <= 0; end
					6'h04: begin
						rdata <= {24'd0, (pal_idx == 2'd0) ? pal_q_r :
						                 (pal_idx == 2'd1) ? pal_q_g :
						                                     pal_q_b};
						pal_idx <= (pal_idx == 2'd2) ? 2'd0 : pal_idx + 1'b1;
					end
					6'h08: rdata <= {24'd0, pbctrl};
					default: ;
					endcase
				end
			end
			default: ;                                    // clockgen: inert
			endcase
		end
	end
end

//----------------------------------------------------------------------------
// clk -> clk_vid config crossing.  fb_base/stride/mode are quasi-static: the
// guest programs them once per mode set and then redraws the whole screen, so
// a 2FF sync per bit is enough and the worst case on a change is one torn
// frame.  MacLC does exactly this (maclc_v8_video.sv *_meta stages); the meta
// stages are false-pathed in MacQuadra800.sdc.
//----------------------------------------------------------------------------
reg [20:0] fb_base_meta, fb_base_v;
reg [13:0] stride_meta,  stride_v;
reg  [2:0] mode_meta,    mode_v;
reg        mon_meta,     mon_v;
always @(posedge clk_vid) begin
	fb_base_meta <= fb_base; fb_base_v <= fb_base_meta;
	stride_meta  <= stride;  stride_v  <= stride_meta;
	mode_meta    <= mode;    mode_v    <= mode_meta;
	mon_meta     <= mon_12in; mon_v    <= mon_meta;
end

//----------------------------------------------------------------------------
// scanout: one pixel per clk_vid.
//   13" RGB: 640x480 active in 800x525 at 25.175 MHz -> 59.94 Hz (VGA)
//   12" RGB: 512x384 active in 640x407 at 15.664 MHz -> 60.14 Hz (the real
//            Quadra drives 15.6672 MHz; sync 528-576 / 385-388 as MacLC's
//            12" table, which is MAME's 512-active shape)
// The platform swaps the dot clock with the monitor, so the counters simply
// follow mon_v; a change holds the scanout in reset anyway (pix_quiet).
//----------------------------------------------------------------------------
wire [9:0] H_ACT  = mon_v ? 10'd512 : 10'd640;
wire [9:0] H_FP   = 10'd16;
wire [9:0] H_SYNC = mon_v ? 10'd48  : 10'd96;
wire [9:0] H_TOT  = mon_v ? 10'd640 : 10'd800;
wire [9:0] V_ACT  = mon_v ? 10'd384 : 10'd480;
wire [9:0] V_FP   = mon_v ? 10'd1   : 10'd10;
wire [9:0] V_SYNC = mon_v ? 10'd3   : 10'd2;
wire [9:0] V_TOT  = mon_v ? 10'd407 : 10'd525;

reg [9:0] hcnt;
reg [9:0] vcnt;

wire hactive = (hcnt < H_ACT);
wire vactive = (vcnt < V_ACT);
assign ce_pixel = 1'b1;
wire vbl_start_v = (vcnt == V_ACT) && (hcnt == 0);

// VBL back the other way: toggle in the scanout domain, 2FF into clk, edge
// detect there. A level would be one clk_vid cycle wide (40 ns) against a
// 30 ns clk and could be missed or double-counted.
reg vbl_tog = 1'b0;
always @(posedge clk_vid) if (vbl_start_v) vbl_tog <= ~vbl_tog;

reg vbl_meta, vbl_s, vbl_s_d;
always @(posedge clk) begin
	vbl_meta <= vbl_tog;
	vbl_s    <= vbl_meta;
	vbl_s_d  <= vbl_s;
end
assign vbl_start = vbl_s ^ vbl_s_d;

// pixels per 32-bit word by depth: 32/16/8/4 for 1/2/4/8bpp
wire [5:0] pix_per_word = (mode_v == 3'd0) ? 6'd32 :
                          (mode_v == 3'd1) ? 6'd16 :
                          (mode_v == 3'd2) ? 6'd8  : 6'd4;

// Fetch pipeline: a trigger at cycle T presents vid_addr during T+1, the
// platform registers the VRAM read at the T+1 edge, and fetch_word
// captures it at the T+2 edge — so a refill triggered at shcnt==0 is
// ready 4 pixels later (every depth refills no more often than that),
// and the line prime at hcnt==H_TOT-3 is ready for pixel 0.
reg [31:0] shreg;
reg  [5:0] shcnt;
reg [21:0] fetch_addr;            // byte address in VRAM space
reg [31:0] fetch_word;
reg  [1:0] fpipe;

assign vid_addr = fetch_addr[21:2];

// current word: the freshly fetched one on a refill boundary
wire [31:0] cur = (shcnt == 0) ? fetch_word : shreg;
assign clut_idx = (mode_v == 3'd3) ? cur[31:24] :
                      (mode_v == 3'd0) ? {7'd0, cur[31]} :
                      (mode_v == 3'd1) ? {6'd0, cur[31:30]} :
                                         {4'd0, cur[31:28]};

reg       act_q;                  // active-video, aligned with the CLUT read
reg       hb_r, vb_r;
assign vga_r = act_q ? clut_r : 8'd0;
assign vga_g = act_q ? clut_g : 8'd0;
assign vga_b = act_q ? clut_b : 8'd0;
assign vga_hb = hb_r;
assign vga_vb = vb_r;

// next line's base offset: (vcnt+1) * stride, tracked incrementally
reg [21:0] line_base_next;

always @(posedge clk_vid) begin
	if (!nreset_vid) begin
		hcnt <= 0; vcnt <= 0;
		vga_hs <= 1; vga_vs <= 1;
		hb_r <= 1; vb_r <= 1;
		shreg <= 0; shcnt <= 0;
		fetch_addr <= 0; fetch_word <= 0; fpipe <= 0;
		act_q <= 0;
		line_base_next <= 0;
	end
	else begin
		if (hcnt == H_TOT-1) begin
			hcnt <= 0;
			vcnt <= (vcnt == V_TOT-1) ? 10'd0 : vcnt + 1'b1;
		end
		else hcnt <= hcnt + 1'b1;

		// outputs registered once, so blanks/syncs stay pixel-aligned
		vga_hs <= ~((hcnt >= H_ACT+H_FP) && (hcnt < H_ACT+H_FP+H_SYNC));
		vga_vs <= ~((vcnt >= V_ACT+V_FP) && (vcnt < V_ACT+V_FP+V_SYNC));
		hb_r   <= ~hactive;
		vb_r   <= ~vactive;

		fpipe <= {fpipe[0], 1'b0};
		if (fpipe[1]) fetch_word <= vid_rdata;

		if (hcnt == H_TOT-3) begin
			// prime the next line (or frame) while still in the blank
			if ((vcnt < V_ACT-1) || (vcnt == V_TOT-1)) begin
				fetch_addr <= (vcnt == V_TOT-1) ? {1'b0, fb_base_v}
				            : {1'b0, fb_base_v} + line_base_next;
				fpipe <= 2'b01;
				shcnt <= 0;
			end
		end
		else if (hcnt == H_TOT-1) begin
			if (vcnt == V_TOT-1) line_base_next <= {8'd0, stride_v};
			else if (vcnt < V_ACT) line_base_next <= line_base_next + {8'd0, stride_v};
		end
		else if (hactive && vactive) begin
			if (shcnt == 0) begin
				shreg <= (mode_v == 3'd0) ? {cur[30:0], 1'b0} :
				         (mode_v == 3'd1) ? {cur[29:0], 2'b0} :
				         (mode_v == 3'd2) ? {cur[27:0], 4'b0} :
				                            {cur[23:0], 8'b0};
				shcnt <= pix_per_word - 1'b1;
				fetch_addr <= fetch_addr + 22'd4;
				fpipe <= 2'b01;
			end
			else begin
				shcnt <= shcnt - 1'b1;
				shreg <= (mode_v == 3'd0) ? {shreg[30:0], 1'b0} :
				         (mode_v == 3'd1) ? {shreg[29:0], 2'b0} :
				         (mode_v == 3'd2) ? {shreg[27:0], 4'b0} :
				                            {shreg[23:0], 8'b0};
			end
		end

		act_q <= hactive && vactive;
	end
end

endmodule

//============================================================================
//  dafb_clut — one 256 x 8 CLUT plane as a true dual-port, dual-clock RAM.
//  Port A (clka): write and registered readback of the same address.
//  Port B (clkb): registered read for the scan-out.  Read-during-write on
//  the same address never happens on hardware (the RAMDAC readback follows
//  a write by at least a bus turnaround), so no bypass logic is asked for.
//============================================================================
module dafb_clut
(
	input        clka,
	input  [7:0] aa,
	input  [7:0] da,
	input        wea,
	output reg [7:0] qa,
	input        clkb,
	input  [7:0] ab,
	output reg [7:0] qb
);
(* ramstyle = "M10K, no_rw_check" *) reg [7:0] mem [0:255];
always @(posedge clka) begin
	if (wea) mem[aa] <= da;
	qa <= mem[aa];
end
always @(posedge clkb) qb <= mem[ab];
endmodule
