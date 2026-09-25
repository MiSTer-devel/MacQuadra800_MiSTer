// cd_audio.sv - the CD-ROM target's audio front end.
//
// Since phase 2 of the SCSI offload (docs/scsi-hps-offload-plan.md) the
// AppleCD playhead lives on the ARM: the Main fork's mac_cdrom_play.cpp
// executes every transport CDB the target forwards through its command block
// ($7D000000), answers the status commands ($42 / $C2 / $CC) through the
// response window ($7E000000), and serves "the next frame at the playhead,
// volume applied" from the next-frame window ($7C000000).  What is left in
// the FPGA is the part that has to run at 44.1 kHz:
//
//   HOUSEKEEPING - after every mount pulse, block 0 of the MCDA blob
//                  ($7FFF0000): the magic, the version and the has-data flag
//                  the READ HEADER / audio-only CHECK logic needs; and after
//                  every forwarded transport command, one read of the $CC
//                  AUDIO STATUS response, which is how this engine learns
//                  whether the ARM is now playing, paused, at the end or idle.
//   FETCH        - while the ARM says "playing", fill the free half of the
//                  two-frame ping-pong from the next-frame window: one
//                  5-block (2560-byte) transaction = 2352 bytes of PCM and a
//                  pad {state, have, flush generation} at bytes 2352..2357.
//                  The ARM's playhead advances per fetch, so fetched ==
//                  played; a generation change (the position moved by a
//                  command) drops the stale half and restarts the cadence on
//                  the new frame.
//   SAMPLE       - the 44.1 kHz fractional cadence with linear interpolation
//                  between cadence targets, 16-bit LE stereo, one frame per
//                  588 stereo samples (unchanged: it is the "CD quality" fix
//                  of 2026-07-28).
//
// Gone with phase 2: the command decode and the playhead (SEARCH / PLAY /
// PAUSE / STOP / SCAN, the track and M:S:F bookkeeping and its dividers), the
// blob's track table and its RAM, the volume law and its two multipliers (the
// ARM scales the PCM from the page $0E ports it mirrors).
//
// Structure (strict single-driver: each always block owns its registers):
//   HOUSEKEEPING block: mst, hk_*, the header / status captures, toc_ready,
//                       disc_audio, st_pend, st_done
//   FETCH block:        fst, fr_*, ast, gen_r, the pad captures, hold, flush
//   SAMPLE block:       the cadence, fr_half_r, frame_ra
//   output stage:       snd_l / snd_r
//
// Channel sharing: ncr53c96 raises ch_grant only while the target has no
// transfer of its own in flight; housekeeping has priority over FETCH.

module cd_audio #(
	parameter CLK_HZ = 32'd32_500_000   // clk rate, for the 44.1 kHz cadence
)(
	input             clk,
	input             rst,       // SYSTEM reset only (survives SCSI bus resets)
	input             bus_rst,   // SCSI bus reset: stops playback

	input             mounted,
	input             img_mounted,      // mount pulse: (re)read the blob header

	// a transport CDB the target forwarded to the ARM has been acked: the
	// ARM has executed it, ask it what state it is in now
	input             fwd_stb,
	input             read_stb,         // data READ latched: stop playback
	input             eject_stb,

	// shared HPS io channel
	input             ch_grant,
	output            ca_io_active,     // owns the channel (request/ack window)
	output            ca_io_rd,
	output     [31:0] ca_io_lba,
	output      [5:0] ca_io_blk_cnt,    // hps_io sd_blk_cnt for the request: 4 for a frame, else 0
	input             io_ack,
	input       [7:0] sd_buff_addr,
	input       [4:0] sd_buff_addr_hi,  // hps_io addr[12:8]: whole-frame bursts
	input      [15:0] sd_buff_dout,
	input             sd_buff_wr,

	// the blob header has been parsed since the last mount pulse
	output reg        toc_ready,

	// 1 = the mounted disc has NO data track (blob v2 byte 12 bit 0 clear).
	// Data READs against such a disc must CHECK with ILLEGAL REQUEST/0x64
	// "illegal mode for this track" (BlueSCSI/Snow oracles) -- the Audio CD
	// Access extension RELIES on that failure to classify the disc; serving
	// audio bytes as data bombs the Finder (2026-07-20, system error 10
	// during the Audio CD desktop mount).
	output reg        disc_audio,

	output reg signed [15:0] snd_l,
	output reg signed [15:0] snd_r,

	// probe words (sim / JTAG): engine state, and the underrun forensics
	//   dbg_cda0: [0]=mounted [1]=toc_ready [3:2]=fr_valid [6:4]=mst
	//             [7]=playing [15:8]=ast [17:16]=fst [23:18]=0
	//             [31:24]=frame_fetch_cnt (wraps)
	//   dbg_cdur: [31:16]=starvation entries (wraps), [15:0]=starved clk/256
	output     [31:0] dbg_cda0,
	output     [31:0] dbg_cdur
);

// HPS window contract (docs/scsi-hps-offload-plan.md section 4; the Main
// fork's support/mac/mac_cdrom.h)
localparam [31:0] TOC_BLK   = 32'h7FFF_0000;                    // MCDA blob, block 0 = the header
localparam [31:0] FRAME_BLK = 32'h7C00_0000;                    // next frame at the playhead, 5 blocks
localparam [31:0] STAT_BLK  = 32'h7E00_0000 | 32'h00CC_0000;    // $CC AUDIO STATUS type 0: byte 0 = the state
localparam [23:0] HOLD_CLKS = CLK_HZ / 32'd75;                  // one frame time

// The platform word with the EVEN byte in [7:0].  The real MiSTer HPS packs
// wide words little-endian (disk byte 0 in sd_buff_dout[7:0]); the
// simulation block-device models (sim_blkdevice.cpp, the tb_ncr53c96 device)
// pack them big-endian, and ncr53c96 swaps at the same boundary.  A 16-bit
// PCM sample is then the word itself.
`ifdef VERILATOR
wire [15:0] pw = {sd_buff_dout[7:0], sd_buff_dout[15:8]};
`else
wire [15:0] pw = sd_buff_dout;
`endif
wire [10:0] pword = {sd_buff_addr_hi[2:0], sd_buff_addr};      // word index within the transaction

// ============================================================================
// frame ping-pong: 2 x 2048 x 16 (1176 words = one 2352 B frame per half;
// the pad words 1176..1178 land there too and are read on the fly below).
// Each half is filled by ONE 5-block transaction: a single sd_ack window
// with sd_buff_addr streaming 0..1279 continuously -- the wide address bits
// come in via sd_buff_addr_hi.  (The old 5x512 view cost five ~2.8 ms round
// trips per 13.3 ms frame = chronic ~4.5% starvation, CDUR-measured
// 2026-07-28.)
// ============================================================================
reg         fr_cap;
reg         fr_half_w;
reg [11:0]  frame_ra;
wire [15:0] frame_q;
cd_sdp #(.DW(16), .AW(12)) frame_ram (
	.clock(clk),
	.waddr({fr_half_w, pword}), .wdata(pw),
	.wr(fr_cap && sd_buff_wr),
	.raddr(frame_ra), .q(frame_q)
);

// ============================================================================
// io-channel request mux (each FSM owns its own request registers)
// ============================================================================
reg         hk_rd, hk_act;             // housekeeping: the blob header, the status poke
reg  [31:0] hk_lba;
reg         fr_rd, fr_act;             // a frame
assign ca_io_rd      = hk_rd | fr_rd;
assign ca_io_lba     = hk_act ? hk_lba : FRAME_BLK;
assign ca_io_active  = hk_act | fr_act;
assign ca_io_blk_cnt = fr_act ? 6'd4 : 6'd0;

reg old_ack;
always @(posedge clk) old_ack <= io_ack;
wire ack_fall = old_ack & ~io_ack;

// ============================================================================
// playback state, as the ARM last reported it (owned by the FETCH block)
// ============================================================================
reg  [7:0] ast;                        // 0 play, 1 paused, 3 end, 5 idle (the $CC code)
wire       playing = (ast == 8'd0);
reg  [1:0] fr_valid;
// the cadence keeps running through the buffered frames after the ARM
// reached the end of the range, so the last 26 ms of a track are not cut
wire       run = playing || ((ast == 8'd3) && (|fr_valid));
wire       frame_done;                 // sample engine finished a frame
reg        frame_done_half_r;          // ...which half (captured pre-flip)

// ============================================================================
// HOUSEKEEPING FSM
// ============================================================================
localparam [2:0] M_IDLE = 3'd0, M_HDR_REQ = 3'd1, M_HDR_WAIT = 3'd2,
                 M_ST_REQ = 3'd3, M_ST_WAIT = 3'd4;
reg  [2:0] mst;
reg        hdr_cap, st_cap;
reg        hdr_m0, hdr_m1;             // "MC" "DA"
reg  [7:0] hdr_ver, hdr_flags;         // blob byte 4, byte 12 (v2: bit 0 = the disc has a data track)
reg  [7:0] st_new;                     // $CC byte 0 as it streamed past
reg        st_pend;                    // a status read is owed
reg        st_done;                    // 1-clk: st_new is the ARM's answer

always @(posedge clk) begin
	if (rst) begin
		mst <= M_IDLE;
		hk_rd <= 0; hk_act <= 0; hk_lba <= 0;
		hdr_cap <= 0; st_cap <= 0;
		hdr_m0 <= 0; hdr_m1 <= 0; hdr_ver <= 0; hdr_flags <= 0; st_new <= 8'd5;
		toc_ready <= 0; disc_audio <= 0;
		st_pend <= 0; st_done <= 0;
	end else begin
		st_done <= 0;
		if (fwd_stb) st_pend <= 1'b1;

		// on-the-fly captures: the blocks stream past, nothing is stored
		if (hdr_cap && sd_buff_wr && sd_buff_addr_hi == 5'd0) begin
			case (sd_buff_addr)
			8'd0: hdr_m0    <= (pw == {"C", "M"});
			8'd1: hdr_m1    <= (pw == {"A", "D"});
			8'd2: hdr_ver   <= pw[7:0];
			8'd6: hdr_flags <= pw[7:0];
			default: ;
			endcase
		end
		if (st_cap && sd_buff_wr && sd_buff_addr_hi == 5'd0 && sd_buff_addr == 8'd0)
			st_new <= pw[7:0];

		case (mst)
		M_IDLE: begin
			hdr_cap <= 1'b0; st_cap <= 1'b0;
			if (img_mounted && mounted) begin
				toc_ready <= 1'b0;
				mst <= M_HDR_REQ;
			end
			else if (mounted && !toc_ready)
				// need-driven (re)acquisition -- HW root cause 2026-07-17: the
				// PRAM late-load AUTO-RESTART resets this FSM mid-acquisition;
				// the mounted latch survives the restart but the img_mounted
				// PULSE never repeats.  Terminates: acquisition always ends in
				// toc_ready=1.
				mst <= M_HDR_REQ;
			else if (st_pend) begin
				st_pend <= 1'b0;
				if (mounted) mst <= M_ST_REQ;   // nothing to ask about an empty drive
			end
		end

		M_HDR_REQ:
			// unmount escape: ch_grant requires mounted, so an eject here would
			// park the engine forever (HW 2026-07-17: guest 0xC0 mid-session)
			if (!mounted) mst <= M_IDLE;
			else if (ch_grant && !fr_act && !fr_rd) begin
				hk_lba  <= TOC_BLK;
				hk_rd   <= 1'b1; hk_act <= 1'b1; hdr_cap <= 1'b1;
				hdr_m0  <= 1'b0; hdr_m1 <= 1'b0;
				mst <= M_HDR_WAIT;
			end
		M_HDR_WAIT: begin
			if (!mounted && !hk_act) begin hk_rd <= 1'b0; hdr_cap <= 1'b0; mst <= M_IDLE; end
			if (io_ack) hk_rd <= 1'b0;
			if (ack_fall && hk_act) begin
				hk_act  <= 1'b0; hdr_cap <= 1'b0;
				// a v1 blob (no flag) can only come from a Main the ncr53c96
				// probe has already refused; without the magic: a data disc
				disc_audio <= hdr_m0 && hdr_m1 && (hdr_ver >= 8'd2) && !hdr_flags[0];
				toc_ready  <= 1'b1;
				mst <= M_IDLE;
			end
		end

		M_ST_REQ:
			if (!mounted) mst <= M_IDLE;
			else if (ch_grant && !fr_act && !fr_rd) begin
				hk_lba <= STAT_BLK;
				hk_rd  <= 1'b1; hk_act <= 1'b1; st_cap <= 1'b1;
				mst <= M_ST_WAIT;
			end
		M_ST_WAIT: begin
			if (io_ack) hk_rd <= 1'b0;
			if (ack_fall && hk_act) begin
				hk_act <= 1'b0; st_cap <= 1'b0;
				st_done <= 1'b1;
				mst <= M_IDLE;
			end
		end
		default: mst <= M_IDLE;
		endcase
	end
end

// ============================================================================
// FETCH FSM: fill the free frame half while the ARM is playing
// ============================================================================
localparam [1:0] F_IDLE = 2'd0, F_REQ = 2'd1, F_WAIT = 2'd2;
reg  [1:0] fst;
reg  [7:0] pad_ast;                    // byte 2352: the state after this frame
reg        pad_have;                   // byte 2353: 1 = the 2352 bytes are a frame
reg [31:0] pad_gen, gen_r;             // bytes 2354..2357: the flush generation
reg [23:0] hold;                       // no frame although "playing": ask again in a frame's time
reg        flush;                      // 1-clk: drop every buffered frame, restart the cadence
reg        flush_half;                 // ...reading this half (when one holds the new frame)
reg  [7:0] dbg_fr_fetch_cnt = 8'd0;

always @(posedge clk) begin
	if (rst) begin
		fst <= F_IDLE; fr_cap <= 0; fr_valid <= 2'b00; fr_half_w <= 0;
		fr_rd <= 0; fr_act <= 0;
		ast <= 8'd5; gen_r <= 0; pad_ast <= 8'd5; pad_have <= 0; pad_gen <= 0;
		hold <= 0; flush <= 0; flush_half <= 0;
	end else begin
		flush <= 1'b0;
		if (hold != 0) hold <= hold - 1'b1;

		// the pad as it streams past: words 1176..1178
		if (fr_cap && sd_buff_wr) begin
			case (pword)
			11'd1176: begin pad_ast <= pw[7:0]; pad_have <= pw[8]; end
			11'd1177: pad_gen[15:0]  <= pw;
			11'd1178: pad_gen[31:16] <= pw;
			default: ;
			endcase
		end

		// Free the half that FINISHED (frame_done_half_r is captured pre-flip;
		// indexing by the live half freed the one that had just STARTED and
		// degenerated the ping-pong into fetch-on-demand, 2026-07-28).
		if (frame_done) fr_valid[frame_done_half_r] <= 1'b0;

		case (fst)
		F_IDLE: begin
			fr_cap <= 1'b0;
			if (playing && mounted && toc_ready && !(&fr_valid) && hold == 0) begin
				fr_half_w <= fr_valid[0] ? 1'b1 : 1'b0;
				fst <= F_REQ;
			end
		end
		F_REQ:
			if (!playing || !mounted) fst <= F_IDLE;
			else if (ch_grant && !hk_act && !hk_rd && (mst == M_IDLE)) begin
				fr_rd  <= 1'b1;
				fr_act <= 1'b1;
				fr_cap <= 1'b1;
				dbg_fr_fetch_cnt <= dbg_fr_fetch_cnt + 8'd1;
				fst <= F_WAIT;
			end
		F_WAIT: begin
			if (io_ack) fr_rd <= 1'b0;
			if (ack_fall && fr_act) begin
				fr_act <= 1'b0;
				fr_cap <= 1'b0;
				ast <= pad_ast;
				if (pad_have) begin
					if (pad_gen != gen_r) begin
						// the position moved (a command): only this frame is current
						gen_r      <= pad_gen;
						fr_valid   <= fr_half_w ? 2'b10 : 2'b01;
						flush      <= 1'b1;
						flush_half <= fr_half_w;
					end
					else fr_valid[fr_half_w] <= 1'b1;
				end
				else hold <= HOLD_CLKS;
				fst <= F_IDLE;
			end
		end
		default: fst <= F_IDLE;
		endcase

		// the ARM's answer to a forwarded transport command.  Anything but
		// "playing" drops what is buffered: the ARM's playhead is where the
		// command left it, and a later PLAY starts from there, not from
		// frames fetched before the command (a PAUSE/RESUME pair costs the
		// two buffered frames, 26 ms; a SEARCH-then-PLAY starts clean).
		if (st_done) begin
			ast  <= st_new;
			hold <= 0;
			if (st_new != 8'd0) begin
				fr_valid <= 2'b00;
				flush <= 1'b1; flush_half <= 1'b0;
			end
		end

		// this engine's own stops (the ARM sees the same events forwarded:
		// a data READ, an eject, a bus reset, an unmount)
		if (read_stb || eject_stb || bus_rst || !mounted) begin
			if (ast != 8'd5 || (|fr_valid)) begin
				ast <= 8'd5; fr_valid <= 2'b00;
				flush <= 1'b1; flush_half <= 1'b0;
			end
		end
	end
end

assign dbg_cda0 = { dbg_fr_fetch_cnt, 6'd0, fst, ast, playing, mst, fr_valid, toc_ready, mounted };

// ============================================================================
// SAMPLE engine: 44.1 kHz cadence; a frame = 588 stereo samples = 1176 words
// ============================================================================
reg [31:0] acc;
reg [10:0] widx;
reg  [1:0] sph;
reg        frame_done_r;
reg        fr_half_r;                  // half being played
assign frame_done = frame_done_r;

// The 44.1 kHz targets are linearly interpolated on the way out (below):
// sys/audio_out.sv picks AUDIO_L/R up with a free-running 48 kHz zero-order
// hold, and feeding it the raw stair-step adds audible imaging ("not CD
// quality" report, 07-28). Interpolating continuously in the 32.5 MHz domain
// means whatever instant the framework samples, it sees a point on the
// segment between the previous and current cadence targets -- no knowledge of
// the 48 kHz phase needed. frac16 is a Q16 approximation of the segment
// phase (increment 89 ~= 65536*44100/32.5MHz per clk, saturating; reset at
// each pair commit). Interpolation never leaves the [prev,target] range, so
// the 16-bit output cannot overflow.
reg signed [15:0] snd_l_t, snd_r_t;   // cadence-tick targets
reg signed [15:0] snd_l_p, snd_r_p;   // previous targets (segment start)
reg        [16:0] frac16;             // Q16 segment phase, saturating at 1.0

always @(posedge clk) begin
	if (rst) begin
		acc <= 0; widx <= 0; sph <= 0; frame_done_r <= 0; frame_done_half_r <= 0;
		snd_l_t <= 0; snd_r_t <= 0; snd_l_p <= 0; snd_r_p <= 0;
		frac16 <= 0; fr_half_r <= 0; frame_ra <= 0;
	end else begin
		frame_done_r <= 1'b0;
		if (!frac16[16]) frac16 <= frac16 + 17'd89;
		if (flush) begin
			widx <= 0; acc <= 0; sph <= 0; fr_half_r <= flush_half;
		end
		else if (run && fr_valid[fr_half_r]) begin
			if (sph == 2'd0) begin
				acc <= acc + 32'd44_100;
				if (acc >= (CLK_HZ - 32'd44_100)) begin
					acc <= acc + 32'd44_100 - CLK_HZ;
					frame_ra <= {fr_half_r, widx};      // 1 + 11 = 12 bits
					sph <= 2'd1;
				end
			end else begin
				sph <= sph + 2'd1;
				case (sph)
				2'd1: frame_ra <= {fr_half_r, widx + 11'd1};
				2'd2: begin snd_l_p <= snd_l_t; snd_l_t <= frame_q; end
				default: begin
					snd_r_p <= snd_r_t; snd_r_t <= frame_q;
					frac16 <= 0; sph <= 2'd0;
					if (widx == 11'd1174) begin
						widx <= 0;
						fr_half_r <= ~fr_half_r;
						frame_done_r <= 1'b1;
						// nonblocking: captures the PRE-flip half -- the one
						// that just finished playing
						frame_done_half_r <= fr_half_r;
					end else widx <= widx + 11'd2;
				end
				endcase
			end
		end
		else begin
			if (!run) begin
				snd_l_t <= 0; snd_r_t <= 0; snd_l_p <= 0; snd_r_p <= 0;
				acc <= 0;
			end
			// underrun (half not ready): hold position, emit silence
		end
	end
end

// Interpolated output stage -- the only driver of snd_l/snd_r.
// The output register commits only every 8th clk (246 ns hold, ~92 points
// per 44.1 kHz sample): sys/audio_out.sv's clk_audio pickup is a STABILITY
// FILTER -- two consecutive 24.576 MHz captures must be EQUAL before a value
// is accepted (audio_out.sv "if(cl2 == cl1)") -- so a bus that moves every
// clk_sys is rejected outright: the framework freezes through any fast
// segment and jumps where the ramp flattens (= the "scratchy, sometimes
// muffled" report on the every-clk version of this stage, 07-28 evening).
// The 8-clk hold spans ~6 clk_audio captures, so every step is accepted,
// while the stair-step imaging the interpolation exists to kill stays gone.
// The volume law (the measured (vol/255)^5 of docs/cd_volume_law_2026-07-30.md)
// is applied by the ARM before the frame is served.
wire        [15:0] seg_f  = frac16[16] ? 16'hFFFF : frac16[15:0];
wire signed [16:0] seg_dl = {snd_l_t[15], snd_l_t} - {snd_l_p[15], snd_l_p};
wire signed [16:0] seg_dr = {snd_r_t[15], snd_r_t} - {snd_r_p[15], snd_r_p};
wire signed [33:0] seg_ml = seg_dl * $signed({1'b0, seg_f});
wire signed [33:0] seg_mr = seg_dr * $signed({1'b0, seg_f});
wire signed [16:0] sum_l  = {snd_l_p[15], snd_l_p} + $signed(seg_ml[32:16]);
wire signed [16:0] sum_r  = {snd_r_p[15], snd_r_p} + $signed(seg_mr[32:16]);
reg  [2:0] odiv;
always @(posedge clk) begin
	if (rst || !run) begin
		snd_l <= 0; snd_r <= 0; odiv <= 0;
	end else begin
		odiv <= odiv + 3'd1;
		if (odiv == 3'd0) begin
			snd_l <= sum_l[15:0];
			snd_r <= sum_r[15:0];
		end
	end
end

// Starvation forensics (CDUR): playing, but the half-frame the sample engine
// needs has not been delivered, so the output freezes at its last value.
// HDMI-capture forensics of the 07-20 build measured ~5% of music time in
// 0.4-4 ms freezes -- exactly this condition (the 2-half ping-pong affords
// 13.3 ms of slack and HPS serving intermittently exceeds it).  Counters
// wrap; readers diff two snapshots over a known interval.
reg [15:0] ur_cnt  = 16'd0;
reg [23:0] ur_clks = 24'd0;
reg        ur_d    = 1'b0;
wire       ur_now  = playing && !fr_valid[fr_half_r];
always @(posedge clk) begin
	ur_d <= ur_now;
	if (ur_now && !ur_d) ur_cnt  <= ur_cnt  + 16'd1;
	if (ur_now)          ur_clks <= ur_clks + 24'd1;
end
assign dbg_cdur = {ur_cnt, ur_clks[23:8]};

endmodule

// Minimal simple-dual-port RAM (one write, one registered read) for the
// frame buffer above -- scsi_dpram would burn two unused mirror arrays per
// instance (the map.rpt M10K check applies here; see the 2026-07-07
// BRAM-inference lesson: exactly one write statement per array).
module cd_sdp #(parameter DW = 16, AW = 12)
(
	input           clock,
	input  [AW-1:0] waddr,
	input  [DW-1:0] wdata,
	input           wr,
	input  [AW-1:0] raddr,
	output reg [DW-1:0] q
);
// vram_bram's hardware-proven inference recipe (see rtl/vram_bram.sv):
// forced "M10K" (overrides the small-RAM heuristic that silently turned the
// 2 Kbit response planes into ~2000 registers each -- fit attempts #1-#3 of
// this file) + no_rw_check, with write and read in SEPARATE always blocks.
(* ramstyle = "M10K,no_rw_check" *) reg [DW-1:0] ram [0:(1<<AW)-1];
always @(posedge clock) if (wr) ram[waddr] <= wdata;
always @(posedge clock) q <= ram[raddr];
endmodule
