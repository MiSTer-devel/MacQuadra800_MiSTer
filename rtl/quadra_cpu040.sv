//============================================================================
//  quadra_cpu040 -- the pipelined AP68040 (rtl/ap68040_faster) behind
//  wombat_cpu's port list, so quadra800 can take either CPU (CPU_AP68040 in
//  the qsf selects this one).
//
//  The core drives the real MC68040 external bus (MC68040UM section 7).
//  It runs here on the machine clock with the bus at 1:1 (bclk_en high):
//  every bus output is a flip-flop, and address, size, kind and write data
//  hold from TS until the transfer's last TA.  So the transaction bus that
//  wombat_cpu exported is made straight from the pins:
//
//  - bus_req rises in the clock TS is on the bus and stays high, level-held,
//    until the transfer's last acknowledge.  A line transfer (SIZ 11) is four
//    aligned longword beats with bus_req held across them and bus_addr
//    counting A3:A2 up from the long word asked for, wrapping in the line --
//    the shape of the old cache's fills, which quadra800's retained-line and
//    first-miss fast paths expect.
//  - TA is bus_ack itself (quadra800's acknowledges are registered), with the
//    read data put on the byte lanes of MC68040UM table 7-1.  The core
//    ignores TA in the clock after TS (its S_C1), and no acknowledge can come
//    then: the request is one clock old at most.  On a write burst the core
//    loads the next beat's data on the edge it samples TA, so the next beat
//    is requested at once.
//  - TEA is the platform's berr pulse, or the stall watchdog's.
//  - TCI with every TA outside RAM ($0-$3FFFFFFF) and the ROM window
//    ($4xxxxxxx): wombat_cpu's cache_allow rule.
//  - Interrupt acknowledges (TT 11) are answered here with TA and AVEC;
//    every Quadra 800 interrupt is autovectored.
//
//  Not provided with this CPU: the MMU walker port (the core walks through
//  its own data cache and the bus), the retained-line sideband into the
//  cache, the store buffer (the core has its own push buffer and copyback),
//  and the SONIC D-cache snoop (the core snoops the 68040 way, which needs
//  bus arbitration quadra800 does not have) -- build with the Ethernet off.
//============================================================================

module quadra_cpu040
#(
	parameter AP040_HAS_FPU      = 1,   // (the core always has its FPU)
	parameter AP040_ENABLE_CACHE = 1,
	parameter AP040_STORE_BUFFER = 1
)
(
	input         clk,
	input         nreset,
	input         ce,

	input   [2:0] ipl,            // active low
	input         ipl_autovector,
	input         berr,
	input         stall_hold,
	output        dbg_stall_flt,

	input         cache_line_valid,
	input  [31:4] cache_line_tag,
	input [127:0] cache_line_data,
	input         store_buffer_ok,

	output        bus_req,
	output        bus_write,
	output        bus_instr,
	output  [1:0] bus_size,       // AP040_SZ_B/W/L
	output [31:0] bus_addr,
	output [31:0] bus_wdata,
	output  [2:0] bus_fc,
	input         bus_ack,
	input  [31:0] bus_rdata,

	output        walker_req,
	output        walker_we,
	output [31:0] walker_addr,
	output [31:0] walker_wdat,
	input         walker_ack,
	input  [31:0] walker_data,
	input         walker_berr,

	input         snoop_stb,
	input  [31:0] snoop_addr,

	output        nresetout,
	output        nmi_ack_toggle,
	output [31:0] cacr_out,
	output [31:0] vbr_out,
	output        debug_busy,
	output        debug_fault,
	output        debug_halted,
	output [255:0] debug_status,
	output [127:0] debug_status2
);

wire [31:0] c_a, c_do;
wire        c_a_oe, c_rw_n, c_ts_n, c_rsto_n, c_mi_n;
wire  [1:0] c_siz, c_tt;
wire  [2:0] c_tm;
wire [31:0] dbg_pc;
wire        dbg_halted;
wire [31:0] c_di;
wire        c_ta_n, c_tea_n, c_tci_n, c_avec_n;

ap68040 #(
	.FPU_REVISION(8'h41),
	.FPU_PIPE(0), .LOOP_PRED(0), .EARLY_RES(0), .DC1_ATC(0), .SKID(0), .DIV_STEPS(2),
	// only RAM ($0-$3FFFFFFF) and the ROM window ($4xxxxxxx) are cacheable:
	// everything else is a device, never read speculatively
	.PA_IO_SERIAL(1),
	.PA_C0_MASK(32'hC000_0000), .PA_C0_MATCH(32'h0000_0000),
	.PA_C1_MASK(32'hF000_0000), .PA_C1_MATCH(32'h4000_0000)
) cpu (
	.clk(clk),
	.bclk_en(1'b1),
	.rsti_n(nreset),
	.dbcc_floor(4'd0),

	.a_o(c_a), .a_oe(c_a_oe), .d_o(c_do), .d_oe(),
	.rw_n(c_rw_n), .siz(c_siz), .tt(c_tt), .tm(c_tm), .tln(), .upa(),
	.ciout_n(), .lock_n(), .locke_n(), .ts_n(c_ts_n), .tip_n(),
	.d_i(c_di), .ta_n(c_ta_n), .tea_n(c_tea_n), .tci_n(c_tci_n), .tbi_n(1'b1),
	.ipl_n(ipl), .avec_n(c_avec_n), .ipend_n(),
	// the only master: the bus is granted for good
	.br_n(), .bg_n(1'b0), .bb_n_i(1'b1), .bb_n_o(), .bb_oe(),
	// nothing else drives the bus, so nothing is snooped
	.a_i(32'd0), .ts_n_i(1'b1), .rw_n_i(1'b1), .siz_i(2'd0), .tt_i(2'd0), .sc(2'b00),
	.mi_n(c_mi_n), .ta_n_o(), .ta_oe(),
	.rsto_n(c_rsto_n), .cdis_n(1'b1), .mdis_n(1'b1), .pst(),
	.dbg_pc(dbg_pc), .dbg_retire(), .dbg_halted(dbg_halted)
);

//----------------------------------------------------------------------------
// the transfer on the bus
//----------------------------------------------------------------------------
wire        ts      = c_a_oe && !c_ts_n;
wire        is_ack  = (c_tt == 2'b11);       // interrupt / breakpoint acknowledge
wire        is_line = (c_siz == 2'b11);

reg         xfer;        // a transfer past its TS clock, waiting for its last TA
reg   [1:0] beat;        // beats of a line done
reg         iack;        // an acknowledge cycle: TA (and AVEC) in this clock

wire        stall_flt;
wire        req     = (ts && !is_ack) || xfer;
wire        last    = !is_line || (beat == 2'd3);

always @(posedge clk) begin
	if (!nreset) begin
		xfer <= 0;
		beat <= 0;
		iack <= 0;
	end
	else begin
		iack <= ts && is_ack;
		if (req && (berr || stall_flt)) begin
			xfer <= 0;
			beat <= 0;
		end
		else if (req && bus_ack) begin
			xfer <= !last;
			beat <= last ? 2'd0 : beat + 2'd1;
		end
		else if (ts && !is_ack)
			xfer <= 1;
	end
end

assign bus_req   = req;
assign bus_write = !c_rw_n;
assign bus_instr = (c_tm == 3'd2) || (c_tm == 3'd6);
assign bus_fc    = c_tm;
assign bus_size  = (c_siz == 2'b01) ? 2'd0 :          // byte
                   (c_siz == 2'b10) ? 2'd1 : 2'd2;     // word; long, line beat
assign bus_addr  = is_line ? {c_a[31:4], c_a[3:2] + beat, 2'b00} : c_a;
// wdata right-aligned by size, from the byte lanes the core drives
assign bus_wdata = (c_siz == 2'b01) ? (c_do >> {~c_a[1:0], 3'd0}) :
                   (c_siz == 2'b10) ? (c_a[1] ? {16'd0, c_do[15:0]} : {16'd0, c_do[31:16]}) :
                                      c_do;

// read data right-aligned by size: replicated onto every lane the size covers
assign c_di      = (c_siz == 2'b01) ? {4{bus_rdata[7:0]}} :
                   (c_siz == 2'b10) ? {2{bus_rdata[15:0]}} : bus_rdata;

wire cacheable   = (c_a[31:30] == 2'b00) || (c_a[31:28] == 4'h4);

assign c_ta_n    = !((req && bus_ack) || iack);
assign c_tea_n   = !((req && berr) || stall_flt);
assign c_tci_n   = cacheable;
assign c_avec_n  = !iack;

//----------------------------------------------------------------------------
// stall watchdog (wombat_cpu's: 2^24 clocks, 0.5 s, held while the platform
// has a block transfer outstanding)
//----------------------------------------------------------------------------
reg  [23:0] stall_cnt;
reg         stall_r;
always @(posedge clk) begin
	stall_r <= 0;
	if (!nreset || !((ts && !is_ack) || xfer) || bus_ack || stall_hold)
		stall_cnt <= 0;
	else if (&stall_cnt)
		stall_r <= 1;
	else
		stall_cnt <= stall_cnt + 1'd1;
end
assign stall_flt     = stall_r;
assign dbg_stall_flt = stall_r;

//----------------------------------------------------------------------------
// the rest of wombat_cpu's ports
//----------------------------------------------------------------------------
assign walker_req     = 1'b0;
assign walker_we      = 1'b0;
assign walker_addr    = 32'd0;
assign walker_wdat    = 32'd0;
assign nresetout      = c_rsto_n;
assign nmi_ack_toggle = 1'b0;
assign cacr_out       = 32'd0;
assign vbr_out        = 32'd0;
assign debug_busy     = xfer;
assign debug_fault    = 1'b0;
assign debug_halted   = dbg_halted;
assign debug_status   = {224'd0, dbg_pc};
assign debug_status2  = 128'd0;

endmodule
