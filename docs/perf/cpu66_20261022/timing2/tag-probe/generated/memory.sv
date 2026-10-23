module ap68040_tdp #(
	parameter int AW = 6,
	parameter int DW = 22,
	parameter bit WRITE_A = 1
)(
	input  logic          clk,
	input  logic [AW-1:0] addr_a,
	input  logic          we_a,
	input  logic [DW-1:0] wd_a,
	output logic [DW-1:0] q_a,
	output logic [DW-1:0] qa_raw,    // ... the RAM's word, and the write laid
	output logic          qa_bv,     // over it (qa_bv: q_a is qa_bd), for a
	output logic [DW-1:0] qa_bd,     // caller comparing both in parallel
	input  logic [AW-1:0] addr_b,
	input  logic          we_b,
	input  logic [DW-1:0] wd_b,
	output logic [DW-1:0] q_b
);
	// A read returns the word as written at the edge that registered its
	// address (a write to the same word at that edge included).  The RAM
	// itself reads the old word; the write is laid over it by a compare of
	// registered addresses and one multiplexer (Quartus's inferred bypass
	// put three logic levels in front of the users' compares; a compare of
	// the incoming address would put it behind the address's own logic).
	(* ramstyle = "M10K, no_rw_check" *) logic [DW-1:0] mem [0:(1<<AW)-1];
	logic [DW-1:0] qa_r, qb_r, wa_d, wb_d;
	logic [AW-1:0] ra, rb, wa_q, wb_q;
	logic          wa_v, wb_v;
	generate
		if (WRITE_A) begin : g_write_a
			always_ff @(posedge clk) begin
				if (we_a) mem[addr_a] <= wd_a;
				if (we_b) mem[addr_b] <= wd_b;
				qa_r <= mem[addr_a];
				qb_r <= mem[addr_b];
			end
		end
		else begin : g_read_a
			// Quartus 17 drops the M10K attribute on the two-write
			// template even when we_a is tied low at the instance. An
			// elaborated single-write template infers one true-dual-port
			// M10K, with the same read latency and external bypass.
			always_ff @(posedge clk) begin
				if (we_b) mem[addr_b] <= wd_b;
				qa_r <= mem[addr_a];
				qb_r <= mem[addr_b];
			end
		end
	endgenerate
	always_ff @(posedge clk) begin
		ra   <= addr_a;
		rb   <= addr_b;
		wa_v <= WRITE_A && we_a; wa_q <= addr_a; wa_d <= wd_a;
		wb_v <= we_b; wb_q <= addr_b; wb_d <= wd_b;
	end
	// synthesis translate_off
	always_ff @(posedge clk)
		if (!WRITE_A && we_a) $fatal(1, "FAIL: write to read-only tag RAM port A");
	// synthesis translate_on
	// (port B's write wins a same-word collision, as in the old order)
	assign q_a    = (wb_v && wb_q == ra) ? wb_d : (wa_v && wa_q == ra) ? wa_d : qa_r;
	assign qa_raw = qa_r;
	assign qa_bv  = (wb_v && wb_q == ra) || (wa_v && wa_q == ra);
	assign qa_bd  = (wb_v && wb_q == ra) ? wb_d : wa_d;
	assign q_b = (wb_v && wb_q == rb) ? wb_d : (wa_v && wa_q == rb) ? wa_d : qb_r;
endmodule
