//============================================================================
//  rtc3430042 — Apple RTC/PRAM chip (343-0042-B flavor: 256-byte XPRAM),
//  bit-banged over VIA1 port B: PB0 data (bidir), PB1 clock, PB2 enable
//  (active low).  Protocol and command set per MAME macrtc.cpp: shift on
//  the clock's falling edge, MSB first; command byte selects clock
//  registers, classic 20-byte PRAM slots, the write-protect/test
//  registers, or the $38 extended-command path into full XPRAM.
//
//  PRAM powers up zeroed — the ROM sees an invalid checksum and writes
//  its defaults, exactly like a Mac with a dead battery — unless the
//  platform loads a saved image through the host port below before the
//  machine leaves reset (MacQuadra800.sv, the .nvr image on hps_io slot 2).
//============================================================================

module rtc3430042
#(
	parameter SEC_DIV = 33000000        // clk per wall second
)
(
	input        clk,
	input        nreset,

	// Unix seconds from the HPS (hps_io TIMESTAMP[31:0]); bit 32 is a
	// toggle we do not need. Seeded ONCE, the first cycle it is non-zero:
	// the ROM reads the clock long after that, and re-seeding later would
	// yank time out from under a running System. Same pattern MacLC_MiSTer
	// uses in rtl/egret_behavioral.sv:375.
	input [32:0] timestamp,

	input        ce_n,                  // PB2, low = selected
	input        clk_in,                // PB1
	input        data_in,               // PB0 as driven by the host
	output       data_out,              // PB0 read-back
	output       data_oe,               // chip is driving PB0 (send phase)

	// Host port into the XPRAM, for the platform's PRAM image (load at
	// core start, save when the guest has changed it).  One 16-bit word
	// per index i is the byte pair {byte 2i+1, byte 2i}, which is exactly
	// the hps_io WIDE sector layout.  h_we is a one-clock pulse writing
	// h_wdata at h_addr; pulses must be at least two clocks apart (the
	// odd byte lands in the clock after).  h_rdata is the word at h_addr,
	// valid three clocks after h_addr settles and refreshed continuously
	// while no write is in flight.  Host writes bypass the guest's
	// write-protect bit and do not count as guest writes.  The wall clock
	// (seconds[]) is not part of the image: it keeps seeding from the host
	// timestamp.
	input        h_we,
	input  [6:0] h_addr,
	input [15:0] h_wdata,
	output [15:0] h_rdata,
	output       pram_wr_stb            // a guest PRAM byte write landed this clock
);

localparam [31:0] MAC_UNIX_DELTA = 32'd2082844800;  // 1904-01-01 -> 1970-01-01

localparam ST_NORMAL = 2'd0, ST_WRITE = 2'd1, ST_XPCMD = 2'd2, ST_XPWRITE = 2'd3;

reg  [7:0] seconds [0:3];
reg  [1:0] state;
reg  [7:0] cmd;
reg  [7:0] data_byte;
reg  [3:0] bit_count;
reg        dir_out;                    // 1 = sending to host
reg        out_bit;
reg        wprot;
reg  [7:0] xpaddr;
reg        ce_d, clk_d;
reg        rtc_init;                   // clock has been seeded from the host

assign data_out = out_bit;
assign data_oe  = dir_out && !ce_n;

// wall-clock seconds
reg [$clog2(SEC_DIV)-1:0] secdiv;
wire sec_tick = (secdiv == SEC_DIV-1);
wire [31:0] sec_q = {seconds[3], seconds[2], seconds[1], seconds[0]};
wire [31:0] sec_n = sec_q + 32'd1;

// register index of a classic command
wire [4:0] regsel = cmd[6:2];

//----------------------------------------------------------------------------
// XPRAM storage: one 256 x 8 true-dual-port M10K (the project's dpram
// wrapper, an altsyncram in BIDIR_DUAL_PORT mode).  Port A is the chip's
// own access, port B the host port's.
//
// Port A: every guest access funnels through exec_cmd, which fires on a
// single falling-clock-edge cycle, so at most one access is live at a time
// and a read and a write never share a cycle (they come from different
// command states).  Reads launch in the exec cycle and land in data_byte
// one clock later via rd_pend -- the bit-banged VIA clock is thousands of
// core clocks per edge, so the host cannot observe the extra cycle.  The
// old bare array (one write port, one registered read port) inferred the
// same block; three read address expressions, three write sites and an
// initial clear had once kept it in logic: 1,137 ALUTs / 2,142 registers.
//
// Port B: a byte sequencer behind the 16-bit host word.  A write lands its
// even byte in the h_we clock and its odd byte in the next; otherwise the
// port reads the two bytes of h_addr alternately into h_rdata, so the word
// follows the address within three clocks.  hps_io strobes one word per
// SPI transfer (many clocks apart) and holds the address between strobes,
// which is all the timing this needs.
//
// M10K powers up zeroed on this device, and the sim's two-state arrays
// start zeroed too, so without a loaded image the ROM sees an invalid
// checksum and rewrites its defaults (the dead-battery path).
//----------------------------------------------------------------------------
reg  [7:0] pram_q;
reg        rd_pend;

// the byte completing on this clock (bit 7..1 shifted, bit 0 on the pin)
wire [7:0] bnow = {data_byte[6:0], data_in};
// the one cycle exec_cmd runs: selected, falling clock, 8th receive bit
wire       exec_now = !nreset ? 1'b0 :
                      (ce_n == ce_d) && !ce_n && clk_d && !clk_in &&
                      !dir_out && (bit_count == 4'd7);

wire [7:0] pram_raddr = (state == ST_XPCMD) ? {cmd[2:0], bnow[6:2]}
                                            : {3'b000, bnow[6:2]};
wire       pram_we    = exec_now &&
                        ((state == ST_XPWRITE && !wprot) ||
                         (state == ST_WRITE && !wprot &&
                          (cmd[6] || cmd[6:4] == 3'b010)));
wire [7:0] pram_waddr = (state == ST_XPWRITE) ? xpaddr : {3'b000, cmd[6:2]};
assign     pram_wr_stb = pram_we;

// host byte sequencer (port B)
reg        hb_odd_pend;                // the odd byte of a host write is owed
reg  [6:0] hb_odd_addr;
reg  [7:0] hb_odd_data;
reg        hb_ph;                      // which byte the idle read fetches
reg        hb_ph_d;                    // ... and which one q_b now holds
reg  [7:0] hb_lo, hb_hi;
wire       hb_we    = h_we || hb_odd_pend;
wire [7:0] hb_addr  = h_we        ? {h_addr, 1'b0} :
                      hb_odd_pend ? {hb_odd_addr, 1'b1} :
                                    {h_addr, hb_ph};
wire [7:0] hb_wdata = h_we ? h_wdata[7:0] : hb_odd_data;
wire [7:0] hb_q;
reg        hb_we_d;                    // port B wrote in the previous clock
assign h_rdata = {hb_hi, hb_lo};

dpram #(8, 8) pram_ram (
	.clock     (clk),
	.address_a (pram_we ? pram_waddr : pram_raddr),
	.data_a    (bnow),
	.wren_a    (pram_we),
	.q_a       (pram_q),
	.address_b (hb_addr),
	.data_b    (hb_wdata),
	.wren_b    (hb_we),
	.q_b       (hb_q)
);

always @(posedge clk) begin
	if (!nreset) begin
		hb_odd_pend <= 0; hb_odd_addr <= 0; hb_odd_data <= 0;
		hb_ph <= 0; hb_ph_d <= 0; hb_lo <= 0; hb_hi <= 0; hb_we_d <= 0;
	end
	else begin
		hb_odd_pend <= h_we;
		if (h_we) begin
			hb_odd_addr <= h_addr;
			hb_odd_data <= h_wdata[15:8];
		end
		// q_b holds the byte addressed in the previous clock; only an idle
		// read's byte is captured (a write cycle's read-back is not a word)
		hb_ph_d <= hb_ph;
		if (!hb_we) hb_ph <= !hb_ph;
		hb_we_d <= hb_we;
		if (!hb_we_d) begin
			if (hb_ph_d) hb_hi <= hb_q;
			else         hb_lo <= hb_q;
		end
	end
end

always @(posedge clk) begin
	if (!nreset) begin
		state <= ST_NORMAL; cmd <= 0; data_byte <= 0; bit_count <= 0;
		dir_out <= 0; out_bit <= 0; wprot <= 0; xpaddr <= 0;
		ce_d <= 1; clk_d <= 0; rd_pend <= 0;
		secdiv <= 0;
		seconds[0] <= 0; seconds[1] <= 0; seconds[2] <= 0; seconds[3] <= 0;
		rtc_init <= 0;
	end
	else begin
		// a PRAM read launched by exec_cmd lands one clock later; any
		// same-cycle abort or (impossible at VIA speeds) new edge below
		// simply overrides it
		if (rd_pend) begin
			data_byte <= pram_q;
			rd_pend   <= 0;
		end

		// Seed from the host clock before free-running. The Mac epoch is
		// 1904-01-01 and Unix is 1970-01-01, so the constant below is the
		// 2,082,844,800 seconds between them -- without it the Mac boots at
		// "Fri 12:00" every time (the 1904 zero).
		if (!rtc_init && timestamp[31:0] != 32'd0) begin
			{seconds[3], seconds[2], seconds[1], seconds[0]} <=
				timestamp[31:0] + MAC_UNIX_DELTA;
			rtc_init <= 1'b1;
		end
		else begin
			secdiv <= sec_tick ? '0 : secdiv + 1'b1;
			if (sec_tick) begin
				seconds[0] <= sec_n[7:0];   seconds[1] <= sec_n[15:8];
				seconds[2] <= sec_n[23:16]; seconds[3] <= sec_n[31:24];
			end
		end

		ce_d  <= ce_n;
		clk_d <= clk_in;

		if (ce_n != ce_d) begin
			// select/deselect aborts any transfer in flight
			data_byte <= 0; bit_count <= 0; dir_out <= 0; out_bit <= 0;
			state <= ST_NORMAL;
		end
		else if (!ce_n && clk_d && !clk_in) begin
			// falling clock edge with the chip selected
			if (dir_out) begin
				out_bit   <= data_byte[bit_count - 1'b1];
				bit_count <= bit_count - 1'b1;
			end
			else begin
				if (bit_count == 4'd7)
					exec_cmd({data_byte[6:0], data_in});
				else begin
					data_byte <= {data_byte[6:0], data_in};
					bit_count <= bit_count + 1'b1;
				end
			end
		end
	end
end

// One received byte: dispatch per state (MAME rtc_execute_cmd)
task exec_cmd;
	input [7:0] b;
	reg   [4:0] r;
	begin
		data_byte <= 0;
		bit_count <= 0;
		case (state)
		ST_XPCMD: begin
			xpaddr <= {cmd[2:0], b[6:2]};
			if (cmd[7]) begin
				dir_out   <= 1;
				rd_pend   <= 1;                // pram_raddr = {cmd[2:0], b[6:2]}
				bit_count <= 4'd8;
				state     <= ST_NORMAL;
			end
			else state <= ST_XPWRITE;
		end
		ST_XPWRITE: begin
			// the write itself runs through pram_we above
			state <= ST_NORMAL;
		end
		ST_WRITE: begin
			state <= ST_NORMAL;
			r = cmd[6:2];
			if (!wprot || r == 5'd13) begin
				casez (r)
				5'b00???: seconds[r[1:0]] <= b;            // 0-7 clock bytes
				5'b010??: ;                                // classic PRAM: pram_we
				5'd13:    wprot <= b[7];
				5'b1????: ;                                // PRAM slots: pram_we
				default: ;                                 // test register etc
				endcase
			end
		end
		default: begin
			cmd <= b;
			if (b[6:3] == 4'b0111) begin                   // $38: extended
				state <= ST_XPCMD;
			end
			else if (b[7]) begin                           // register read
				dir_out   <= 1;
				bit_count <= 4'd8;
				casez (b[6:2])
				5'b00???: data_byte <= seconds[b[3:2]];    // (cmd>>2)&3
				5'b010??: rd_pend <= 1;        // pram_raddr = {3'b000, b[6:2]}
				5'b1????: rd_pend <= 1;
				default:  data_byte <= 8'h00;
				endcase
			end
			else state <= ST_WRITE;                        // wait for data
		end
		endcase
	end
endtask

endmodule
