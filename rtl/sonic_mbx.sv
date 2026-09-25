//============================================================================
//  sonic_mbx — the Quadra 800's built-in Ethernet (DP83932 SONIC), FPGA half.
//
//  The chip model (CAM, descriptor walks, CRC, the network bridge) runs on the
//  ARM inside the Main fork (support/mac/mac_sonic.cpp, mac_eth.cpp "Q8"
//  personality).  This block is the part that has to be in the machine:
//
//    * register writes -> a doorbell ring in a DDR3 window; the guest waits
//      only for the entry to be IN DDR3, never for host software;
//    * register reads <- one on-demand DDR3 read of the ARM's shadow block
//      (no 64-register shadow file in flip-flops);
//    * ISR and IMR live HERE.  A guest write-1-to-clear takes effect in its own
//      bus cycle and irq is exact.  The ARM raises bits through the sequenced
//      ISR_SET word, and every doorbell entry carries the last ISR_SET seq this
//      block had consumed, so the ARM clears its replica only for raises the
//      guest could have seen;
//    * CR command bits the guest wrote read back set until the ARM's
//      applied-index passes that doorbell (Apple's driver spin-polls CR.TXP);
//    * the MAC PROM, read on demand from the window;
//    * the guest-RAM DMA engine: the ARM posts an ordered list of up to eight
//      {dir, byte address, byte count} ops; the engine moves longword beats
//      between the XFER staging area and guest RAM through the machine's own
//      service FSM (quadra800.sv), first/last write beats under byte enables.
//
//  Guest map (MAME macquadra800.cpp / QEMU q800.c agree):
//    $5000A000-$5000A0FF  64 x 16-bit registers, 4-byte stride, data on D15-D0
//                         (bytes +2/+3 of each longword); register = A[7:2]
//    $50008000-$50008007  MAC PROM: 6 bit-reversed MAC bytes, 0, ~XOR
//    (both repeat every $40000; the ROM uses the $50Fxxxxx image)
//    INT -> VIA2 port A bit 0 (slot $9), active low -> IPL 2
//
//  DDR3 window v4, ARM physical 0x1FF00000 (Main's mac_eth.h is the twin of
//  this table); addresses here are 64-bit word indices into the window:
//    $000-$7FF  XFER      16 KiB; op k's bytes start at the next 8-byte
//                         boundary, guest byte (addr & ~3) + j at offset + j
//    $800       MAGIC     ARM->FPGA "McQ8ETH4": the service is up
//    $801       WPTR      FPGA->ARM doorbell write index, monotonic
//    $802-$811  SHAD      ARM->FPGA register 4n+k at bits [16k+15:16k] of word n
//    $812       ISR_SET   ARM->FPGA [15:0] seq | [30:16] bits to OR into ISR |
//                         [63:48] applied index at the time of the post
//    $813       ISR_ACK   FPGA->ARM [15:0] seq consumed
//    $814       MACPROM   ARM->FPGA byte k = PROM byte k
//    $816       PTRS      ARM->FPGA [31:0] ring read index | [63:32] applied index
//    $817       DMA_CMD   ARM->FPGA [7:0] seq | [11:8] op count
//    $818       DMA_STAT  FPGA->ARM [7:0] seq echo
//    $819       DEBUG     FPGA->ARM [14:0] ISR | [29:15] IMR | [30] present | [31] irq |
//                         [37:32] last register the guest read | [38] it was the PROM |
//                         [55:40] guest read count; rewritten whenever it changes (Main
//                         prints it: register READS never reach the ARM otherwise, so a
//                         guest spin-polling a register is invisible without this)
//    $81A       SAMPLE    FPGA->ARM [31:0] CPU PC | [47:32] SR, rewritten once per poll round:
//                         a statistical profiler for a guest that spins where nothing else
//                         can see it (Main prints the histogram)
//    $820-$827  OPS       ARM->FPGA [0] dir (1 = to guest) | [31:16] bytes | [63:32] address
//    $900-$9FF  RING      [0] valid | [3:1] tag (0 write, 1 reset) | [9:4] reg |
//                         [31:16] data | [47:32] ISR_SET seq seen
//
//  Everything is clk_sys; the top drives DDRAM_CLK from the same clock.  With
//  the OSD option off (ena = 0) the block never touches DDR3 or the bus.
//============================================================================

module sonic_mbx
(
	input             clk,
	input             nreset,
	input             ena,           // OSD "Ethernet", latched under reset by the top
	output reg        present,       // registers and PROM decode here, else inert in iosb

	// device port from the service FSM: sel level-held until the 1-cycle ack
	input             sel,
	input             write,
	input             prom,          // 1 = PROM window, 0 = registers
	input       [7:2] addr,
	input       [3:0] be,
	input      [31:0] wdata,
	output reg        ack,
	output reg [31:0] rdata,
	output            irq,
	input      [47:0] cpu_sample,    // {SR, PC} of the CPU, for the SAMPLE word

	// guest-RAM master port into the service FSM: req level-held until the 1-cycle ack
	output reg        dma_req,
	output reg        dma_we,
	output reg [26:2] dma_addr,
	output reg  [3:0] dma_be,
	output     [31:0] dma_wdata,
	input             dma_ack,
	input      [31:0] dma_rdata,

	// DDR3 window port: rd/we level-held until the 1-cycle accept; read data with rvalid
	output reg [11:0] mem_addr,
	output reg        mem_rd,
	output reg        mem_we,
	output     [63:0] mem_wdata,
	input             mem_accept,
	input             mem_rvalid,
	input      [63:0] mem_rdata
);

localparam [11:0] AV_MAGIC = 12'h800, AV_WPTR = 12'h801, AV_SHAD = 12'h802,
                  AV_ISRSET = 12'h812, AV_ISRACK = 12'h813, AV_PROM = 12'h814,
                  AV_PTRS = 12'h816, AV_DMACMD = 12'h817, AV_DMASTAT = 12'h818,
                  AV_DEBUG = 12'h819, AV_SAMPLE = 12'h81A, AV_OPS = 12'h820, AV_RING = 12'h900;
localparam [63:0] MAGIC_V = 64'h4D635138_45544834;   // "McQ8ETH4"

//----------------------------------------------------------------------------
// guest-visible state
//----------------------------------------------------------------------------
reg  [14:0] isr, imr;
reg  [15:0] isr_seq;        // last ISR_SET post consumed
reg         isr_first;      // first sighting after reset adopts the staged seq
reg         isr_ack_pend;
reg  [15:0] cr_ovl;         // command bits written, not yet applied by the ARM
reg  [15:0] cr_idx;         // doorbell index past the last CR write
reg         magic_ok;

assign irq = present && |(isr & imr);

// CPU cycle
localparam H_IDLE = 2'd0, H_RUN = 2'd1, H_DONE = 2'd2;
reg   [1:0] hstate;
reg         h_read_ddr;     // this cycle completes on a DDR3 read
reg         h_wait_cmd;     // this cycle completes when its doorbell is published
reg         h_abort;        // watchdog retired it: a late DDR3 answer is dropped
reg         h_prom;
reg   [5:0] h_reg;
reg         h_hi;           // the access touches only the upper half of the longword
reg         h_a2;
reg  [17:0] h_wd;           // 2^17 clk ~ 4 ms: a dead window can never hold the CPU

wire [15:0] w16 = (be[1:0] == 2'b00) ? wdata[31:16] : wdata[15:0];
// a register write commits in exactly one cycle: the one that queues its doorbell
wire        reg_commit = (hstate == H_RUN) && !h_prom && write && !h_wait_cmd && !cmd_queued;

// doorbell
reg  [31:0] wptr;
reg         wptr_init;
reg         reset_pend;     // tell the ARM's model about this guest reset, once
reg         cmd_queued;
reg         cmd_tag;
reg   [5:0] cmd_reg;
reg  [15:0] cmd_data, cmd_seq;
reg  [15:0] rptr_sh;
reg  [15:0] cmd_wait;
wire [15:0] ring_used = wptr[15:0] - rptr_sh;
wire        ring_full = ring_used >= 16'd200;

//----------------------------------------------------------------------------
// DMA engine
//----------------------------------------------------------------------------
reg         dma_active, dma_first;
reg   [7:0] dma_seq, dma_done_seq;
reg   [3:0] dma_nops, dma_k;
reg         dma_dir;
reg   [1:0] dma_lead, dma_end;
reg  [12:0] dma_beats;      // beats left in this op, this one included
reg         dma_firstbeat;
reg  [11:0] dma_xp;         // XFER longword index: word = [11:1], half = [0]
reg  [63:0] acc;
reg  [12:0] dma_hot;        // ~250 us of fast polling after a completion
localparam P_OP = 3'd0, P_XRD = 3'd1, P_BEAT = 3'd2, P_XWR = 3'd3, P_ADV = 3'd4,
           P_NEXT = 3'd5, P_STAT = 3'd6;
reg   [2:0] dma_ph;

wire        dma_last  = (dma_beats == 13'd1);
wire  [3:0] be_first  = 4'hF >> dma_lead;
wire  [3:0] be_last   = (dma_end == 2'd0) ? 4'hF : (4'hF << (3'd4 - {1'b0, dma_end}));
wire [31:0] acc_half  = dma_xp[0] ? acc[63:32] : acc[31:0];
// XFER byte j is ARM byte j = window bits [8j+7:8j]; the beat is big-endian
assign dma_wdata = {acc_half[7:0], acc_half[15:8], acc_half[23:16], acc_half[31:24]};
wire [31:0] rd_swap  = {dma_rdata[7:0], dma_rdata[15:8], dma_rdata[23:16], dma_rdata[31:24]};

//----------------------------------------------------------------------------
// DDR3 sequencer
//----------------------------------------------------------------------------
localparam S_IDLE = 4'd0, S_WPTR0 = 4'd1, S_CMD = 4'd2, S_WPTR = 4'd3, S_CPURD = 4'd4,
           S_ISRACK = 4'd5, S_POLL = 4'd6, S_OP = 4'd7, S_XRD = 4'd8, S_XWR = 4'd9,
           S_STAT = 4'd10, S_DEBUG = 4'd11, S_SAMPLE = 4'd12;
reg   [3:0] st;
reg   [2:0] wsel;
localparam W_ENTRY = 3'd0, W_WPTR = 3'd1, W_ISRACK = 3'd2, W_ACC = 3'd3, W_STAT = 3'd4,
           W_DEBUG = 3'd5, W_SAMPLE = 3'd6;
reg  [47:0] sample;
reg         sample_pend;
// what the guest sees, for the ARM's stats: a frozen guest with irq high and no ISR write is an
// interrupt that is not being delivered; with irq low it is the model that stopped raising
reg  [15:0] rd_cnt;
reg   [5:0] rd_last;
reg         rd_prom;
reg  [55:0] dbg_sent;
wire [55:0] dbg_now = {rd_cnt, 1'b0, rd_prom, rd_last, irq, present, imr, isr};
assign mem_wdata = (wsel == W_ENTRY)  ? {16'd0, cmd_seq, cmd_data, 6'd0, cmd_reg, 2'b00, cmd_tag, 1'b1} :
                   (wsel == W_WPTR)   ? {32'd0, wptr} :
                   (wsel == W_ISRACK) ? {48'd0, isr_seq} :
                   (wsel == W_ACC)    ? acc :
                   (wsel == W_DEBUG)  ? {8'd0, dbg_sent} :
                   (wsel == W_SAMPLE) ? {16'd0, sample} :
                                        {56'd0, dma_seq};

reg  [15:0] poll_div;
reg         poll_pend;
reg   [1:0] poll_step, poll_q;
wire        hot      = dma_active || (dma_hot != 0) || (cmd_queued && ring_full) || (cr_ovl != 0);
wire        poll_due = hot      ? (poll_div[4:0] == 5'h1F) :
                       magic_ok ? (poll_div[7:0] == 8'hFF) :
                                  (poll_div == 16'hFFFF);

wire [15:0] shad16   = mem_rdata[{h_reg[1:0], 4'b0000} +: 16];
wire [31:0] prom32   = h_a2 ? {mem_rdata[39:32], mem_rdata[47:40], mem_rdata[55:48], mem_rdata[63:56]}
                            : {mem_rdata[7:0],   mem_rdata[15:8],  mem_rdata[23:16], mem_rdata[31:24]};

task start_rd(input [11:0] a, input [3:0] next);
	begin mem_addr <= a; mem_rd <= 1; st <= next; end
endtask
task start_wr(input [11:0] a, input [2:0] w, input [3:0] next);
	begin mem_addr <= a; wsel <= w; mem_we <= 1; st <= next; end
endtask

// ISR has one writer: the guest's clear and the ARM's post may land in the same clock, and then
// the post wins (the doorbell entry carries the OLD seq, so the ARM keeps its replica bit too).
wire        post_now = (st == S_POLL) && mem_rvalid && (poll_q == 2'd1) && !isr_first &&
                       (mem_rdata[15:0] != isr_seq);
wire [14:0] isr_clr  = (reg_commit && h_reg == 6'd5) ? w16[14:0] : 15'd0;
wire [14:0] isr_set  = post_now ? mem_rdata[30:16] : 15'd0;
// same for the CR overlay: a clear decided on the old index never eats a new write.
// The applied index rides in the ISR post as well as in PTRS: on the chip TXP clears in the
// instant TXDN sets, and Apple's driver reads CR inside its TXDN handler -- with the index only
// in PTRS the interrupt could be raised one poll step before the overlay dropped, the handler
// saw the transmitter still busy and parked its pending CAM load for good (first hardware day:
// DHCP completed, then no ARP, no multicast, a livelocked Finder; QEMU's trace shows the
// driver reading CR=$0028 there).
wire [15:0] aptr_d   = mem_rdata[47:32] - cr_idx;
wire [15:0] aptr_p   = mem_rdata[63:48] - cr_idx;
wire        ovl_clr  = (st == S_POLL) && mem_rvalid &&
                       ((poll_q == 2'd2 && !aptr_d[15]) || (post_now && !aptr_p[15]));
wire [15:0] ovl_set  = (reg_commit && h_reg == 6'd0) ? (w16 & 16'h03BF) : 16'd0;

// a write is finished when it is accepted; a read when its data arrives
wire wr_done = mem_accept;
wire rd_done = mem_rvalid;

always @(posedge clk) begin
	if (!nreset || !ena) begin
		present <= 0;       magic_ok <= 0;
		isr <= 0;           imr <= 0;          isr_seq <= 0;   isr_first <= 1;  isr_ack_pend <= 0;
		cr_ovl <= 0;        cr_idx <= 0;
		hstate <= H_IDLE;   ack <= 0;          rdata <= 0;     h_wd <= 0;       h_abort <= 0;
		h_read_ddr <= 0;    h_wait_cmd <= 0;   h_prom <= 0;    h_reg <= 0;      h_hi <= 0;   h_a2 <= 0;
		wptr <= 0;          wptr_init <= 0;    reset_pend <= 1;
		cmd_queued <= 0;    cmd_tag <= 0;      cmd_reg <= 0;   cmd_data <= 0;   cmd_seq <= 0;
		rptr_sh <= 0;       cmd_wait <= 0;
		dma_active <= 0;    dma_first <= 1;    dma_seq <= 0;   dma_done_seq <= 0;
		dma_nops <= 0;      dma_k <= 0;        dma_dir <= 0;   dma_lead <= 0;   dma_end <= 0;
		dma_beats <= 0;     dma_firstbeat <= 0; dma_xp <= 0;   acc <= 0;        dma_hot <= 0;
		dma_ph <= P_OP;     dma_req <= 0;      dma_we <= 0;    dma_addr <= 0;   dma_be <= 0;
		st <= S_IDLE;       wsel <= W_ENTRY;
		mem_addr <= 0;      mem_rd <= 0;       mem_we <= 0;
		poll_div <= 0;      poll_pend <= 1;    poll_step <= 0;    poll_q <= 0;
		dbg_sent <= 0;      rd_cnt <= 0;       rd_last <= 0;      rd_prom <= 0;
		sample <= 0;        sample_pend <= 0;
	end
	else begin
		ack <= 0;
		poll_div <= poll_div + 1'b1;
		if (dma_hot != 0) dma_hot <= dma_hot - 1'b1;
		if (poll_due) poll_pend <= 1;
		if (mem_accept) begin mem_rd <= 0; mem_we <= 0; end
		isr    <= (isr & ~isr_clr) | isr_set;
		cr_ovl <= (ovl_clr ? 16'd0 : cr_ovl) | ovl_set;

		// the service is up: from here to the next reset the chip is there
		if (magic_ok) present <= 1;

		// the guest reset that just ended resets the ARM's model too
		if (reset_pend && magic_ok && !cmd_queued) begin
			reset_pend <= 0;
			cmd_queued <= 1; cmd_tag <= 1; cmd_reg <= 0; cmd_data <= 0; cmd_seq <= isr_seq;
		end

		if (cmd_queued && ring_full && st == S_IDLE) begin
			if (!(&cmd_wait)) cmd_wait <= cmd_wait + 1'b1;   // ~2 ms, then publish anyway
		end
		else if (!cmd_queued) cmd_wait <= 0;

		//--------------------------------------------------------------------
		// CPU cycle
		//--------------------------------------------------------------------
		case (hstate)
		// not while an abandoned read is still in flight: its answer must not retire this one
		H_IDLE: if (sel && !ack && present && st != S_CPURD) begin
			h_prom <= prom; h_reg <= addr[7:2]; h_a2 <= addr[2];
			h_hi   <= (be[1:0] == 2'b00);
			h_read_ddr <= 0; h_wait_cmd <= 0; h_abort <= 0;
			if (!write) begin rd_cnt <= rd_cnt + 16'd1; rd_last <= addr[7:2]; rd_prom <= prom; end
			hstate <= H_RUN;
		end
		H_RUN: begin
			if (h_prom) begin
				if (write) hstate <= H_DONE;
				else h_read_ddr <= 1;
			end
			else if (!write) begin
				if (h_reg == 6'd5)      begin rdata <= {h_hi ? {1'b0, isr} : 16'd0, 1'b0, isr}; hstate <= H_DONE; end
				else if (h_reg == 6'd4) begin rdata <= {h_hi ? {1'b0, imr} : 16'd0, 1'b0, imr}; hstate <= H_DONE; end
				else h_read_ddr <= 1;
			end
			else if (reg_commit) begin
				// the local copy moves in the guest's own bus cycle; the ARM's follows the ring
				if (h_reg == 6'd4) imr <= w16[14:0];
				if (h_reg == 6'd0) cr_idx <= wptr[15:0] + 16'd1;
				cmd_queued <= 1; cmd_tag <= 0; cmd_reg <= h_reg; cmd_data <= w16; cmd_seq <= isr_seq;
				h_wait_cmd <= 1;
			end
		end
		H_DONE: begin
			ack <= 1;
			hstate <= H_IDLE;
		end
		default: hstate <= H_IDLE;
		endcase

		//--------------------------------------------------------------------
		// DMA beat handshake (the DDR3 sequencer below runs beside it)
		//--------------------------------------------------------------------
		if (dma_active && dma_ph == P_BEAT) begin
			if (!dma_req && !dma_ack) begin
				dma_req <= 1;
				dma_we  <= dma_dir;
				dma_be  <= !dma_dir ? 4'hF :
				           (dma_firstbeat ? be_first : 4'hF) & (dma_last ? be_last : 4'hF);
			end
			else if (dma_ack) begin
				dma_req <= 0;
				if (!dma_dir) begin
					if (dma_xp[0]) acc[63:32] <= rd_swap;
					else           acc[31:0]  <= rd_swap;
				end
				dma_ph <= (!dma_dir && (dma_xp[0] || dma_last)) ? P_XWR : P_ADV;
			end
		end
		if (dma_active && dma_ph == P_ADV) begin
			dma_addr      <= dma_addr + 25'd1;
			dma_xp        <= dma_xp + 12'd1;
			dma_beats     <= dma_beats - 13'd1;
			dma_firstbeat <= 0;
			dma_ph        <= dma_last ? P_NEXT : (dma_dir && dma_xp[0]) ? P_XRD : P_BEAT;
		end
		if (dma_active && dma_ph == P_NEXT) begin
			dma_xp <= dma_xp + {11'd0, dma_xp[0]};          // next op starts 8-aligned
			dma_k  <= dma_k + 4'd1;
			dma_ph <= (dma_k + 4'd1 == dma_nops) ? P_STAT : P_OP;
		end

		//--------------------------------------------------------------------
		// DDR3 sequencer: one transaction at a time, the CPU's first
		//--------------------------------------------------------------------
		case (st)
		S_IDLE: begin
			if (!wptr_init)
				start_wr(AV_WPTR, W_WPTR, S_WPTR0);
			else if (cmd_queued && (!ring_full || (&cmd_wait)))
				start_wr(AV_RING + {4'd0, wptr[7:0]}, W_ENTRY, S_CMD);
			else if (hstate == H_RUN && h_read_ddr && !h_abort)
				start_rd(h_prom ? AV_PROM : AV_SHAD + {8'd0, h_reg[5:2]}, S_CPURD);
			else if (isr_ack_pend)
				start_wr(AV_ISRACK, W_ISRACK, S_ISRACK);
			else if (dma_active && hstate != H_RUN && dma_ph == P_OP)
				start_rd(AV_OPS + {8'd0, dma_k}, S_OP);
			else if (dma_active && hstate != H_RUN && dma_ph == P_XRD)
				start_rd({1'b0, dma_xp[11:1]}, S_XRD);
			else if (dma_active && hstate != H_RUN && dma_ph == P_XWR)
				start_wr({1'b0, dma_xp[11:1]}, W_ACC, S_XWR);
			else if (dma_active && hstate != H_RUN && dma_ph == P_STAT)
				start_wr(AV_DMASTAT, W_STAT, S_STAT);
			else if (poll_pend) begin
				poll_pend <= 0;
				poll_q <= poll_step;
				start_rd((poll_step == 2'd0) ? AV_MAGIC  :
				         (poll_step == 2'd1) ? AV_ISRSET :
				         (poll_step == 2'd2) ? AV_PTRS   : AV_DMACMD, S_POLL);
			end
			// last: a guest spin-reading a register dirties this every cycle, and the
			// polls above are what the machine lives on
			else if (magic_ok && dbg_now != dbg_sent) begin
				dbg_sent <= dbg_now;
				start_wr(AV_DEBUG, W_DEBUG, S_DEBUG);
			end
			else if (sample_pend) begin
				sample_pend <= 0;
				sample <= cpu_sample;
				start_wr(AV_SAMPLE, W_SAMPLE, S_SAMPLE);
			end
		end

		S_WPTR0: if (wr_done) begin wptr_init <= 1; st <= S_IDLE; end

		// the entry first, then the index that publishes it (mem_wdata follows wptr)
		S_CMD: if (wr_done) begin
			wptr <= wptr + 32'd1;
			start_wr(AV_WPTR, W_WPTR, S_WPTR);
		end
		S_WPTR: if (wr_done) begin
			cmd_queued <= 0;
			if (h_wait_cmd) begin h_wait_cmd <= 0; hstate <= H_DONE; end
			st <= S_IDLE;
		end

		S_CPURD: if (rd_done) begin
			if (!h_abort) begin
				rdata  <= h_prom ? prom32 :
				          {h_hi ? (shad16 | (h_reg == 6'd0 ? cr_ovl : 16'd0)) : 16'd0,
				           shad16 | (h_reg == 6'd0 ? cr_ovl : 16'd0)};
				h_read_ddr <= 0;
				hstate <= H_DONE;
			end
			st <= S_IDLE;
		end

		S_ISRACK: if (wr_done) begin isr_ack_pend <= 0; st <= S_IDLE; end

		S_DEBUG: if (wr_done) st <= S_IDLE;

		S_SAMPLE: if (wr_done) st <= S_IDLE;

		S_POLL: if (rd_done) begin
			case (poll_q)
			2'd0: magic_ok <= (mem_rdata == MAGIC_V);
			2'd1: if (mem_rdata[15:0] != isr_seq || isr_first) begin
				// isr_set above took the bits; a post staged before this reset is no event
				isr_first    <= 0;
				isr_seq      <= mem_rdata[15:0];
				isr_ack_pend <= 1;
			end
			2'd2: rptr_sh <= mem_rdata[15:0];   // the applied index is taken by ovl_clr above
			2'd3: begin
				if (dma_first) begin
					// DDR3 outlives a reset: a command staged before it must never replay
					dma_first    <= 0;
					dma_done_seq <= mem_rdata[7:0];
				end
				else if (!dma_active && mem_rdata[7:0] != dma_done_seq) begin
					dma_seq    <= mem_rdata[7:0];
					dma_nops   <= mem_rdata[11:8];
					dma_k      <= 0;
					dma_xp     <= 0;
					dma_active <= 1;
					dma_ph     <= (mem_rdata[11:8] == 4'd0) ? P_STAT : P_OP;
				end
			end
			endcase
			if (poll_q == 2'd3) sample_pend <= 1;
			// until the service shows up only MAGIC is worth a read
			poll_step <= (magic_ok || poll_q != 2'd0) ? poll_q + 2'd1 : 2'd0;
			st <= S_IDLE;
		end

		S_OP: if (rd_done) begin
			dma_dir       <= mem_rdata[0];
			dma_addr      <= mem_rdata[58:34];
			dma_lead      <= mem_rdata[33:32];
			dma_end       <= mem_rdata[33:32] + mem_rdata[17:16];
			// beats = (lead + bytes + 3) / 4
			dma_beats     <= ({1'b0, mem_rdata[31:16]} + {15'd0, mem_rdata[33:32]} + 17'd3) >> 2;
			dma_firstbeat <= 1;
			dma_ph        <= (mem_rdata[31:16] == 16'd0) ? P_NEXT : mem_rdata[0] ? P_XRD : P_BEAT;
			st <= S_IDLE;
		end

		S_XRD: if (rd_done) begin
			acc    <= mem_rdata;
			dma_ph <= P_BEAT;
			st     <= S_IDLE;
		end

		S_XWR: if (wr_done) begin
			dma_ph <= P_ADV;
			st     <= S_IDLE;
		end

		S_STAT: if (wr_done) begin
			dma_active   <= 0;
			dma_done_seq <= dma_seq;
			dma_hot      <= 13'h1FFF;
			st <= S_IDLE;
		end

		default: st <= S_IDLE;
		endcase

		//--------------------------------------------------------------------
		// bus watchdog: last, so it wins over both machines above
		//--------------------------------------------------------------------
		if (hstate == H_RUN) begin
			if (h_wd[17]) begin
				hstate     <= H_DONE;
				rdata      <= 32'd0;
				h_wait_cmd <= 0;      // must not retire a LATER access
				h_abort    <= 1;
				h_wd       <= 0;
			end
			else h_wd <= h_wd + 1'b1;
		end
		else h_wd <= 0;
	end
end

endmodule
