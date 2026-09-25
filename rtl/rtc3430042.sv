//============================================================================
//  rtc3430042 — Apple RTC/PRAM chip (343-0042-B flavor: 256-byte XPRAM),
//  bit-banged over VIA1 port B: PB0 data (bidir), PB1 clock, PB2 enable
//  (active low).  Protocol and command set per MAME macrtc.cpp: shift on
//  the clock's falling edge, MSB first; command byte selects clock
//  registers, classic 20-byte PRAM slots, the write-protect/test
//  registers, or the $38 extended-command path into full XPRAM.
//
//  PRAM powers up zeroed — the ROM sees an invalid checksum and writes
//  its defaults, exactly like a Mac with a dead battery.
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
	output       data_oe                // chip is driving PB0 (send phase)
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
// XPRAM storage.  One write port and one registered read port, so the
// array infers as block RAM (three read address expressions, three write
// sites and an initial clear kept the old bare array in logic: 1,137
// ALUTs / 2,142 registers).  All accesses funnel through exec_cmd, which
// fires on a single falling-clock-edge cycle, so at most one access is
// live at a time.  Reads launch in the exec cycle and land in data_byte
// one clock later via rd_pend — the bit-banged VIA clock is thousands of
// core clocks per edge, so the host cannot observe the extra cycle.
//
// The initial clear is gone: M10K powers up zeroed on this device, and
// the sim's two-state arrays start zeroed too — the ROM still sees an
// invalid checksum and rewrites its defaults (dead-battery path).
//----------------------------------------------------------------------------
(* ramstyle = "M10K, no_rw_check" *) reg [7:0] pram [0:255];
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

always @(posedge clk) begin
	if (pram_we) pram[pram_waddr] <= bnow;
	pram_q <= pram[pram_raddr];
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
