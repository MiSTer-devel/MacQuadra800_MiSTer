//---------------------------------------------------------------------------
// tb_corpus.v — run a wombat33 SingleStepTests bench payload against the
// AP68040 core (or any core with the TG68K-shaped ap040 port set).
//
// Lean derivative of AP68040's tb_ap040_program.v: flat 4 MB RAM,
// zero-wait-state 16-bit bus, no fault injection. The payload (built by
// the sim040 Makefile, linked at $40000 by the shared payload.ld) runs
// the corpus and writes JSONL into RAM at $100000 via jsonl_sim.c; a
// word write of $600D to the $F00000 doorbell ends the run and the
// results window is dumped to +results=<file>.
//
//   +prog=<hex>      $readmemh image (vectors @0, payload @word 20000)
//   +results=<file>  binary dump of RAM $100000..$163FFF at DONE
//   +maxcycles=<n>   timeout (default 800,000,000)
//---------------------------------------------------------------------------

`timescale 1ns/1ps

module tb_corpus;

reg clk = 0;
reg nreset = 0;
always #5 clk = ~clk;

wire [15:0] data_in;
wire [31:0] addr_out;
wire [15:0] data_write;
wire        nwr, nuds, nlds;
wire  [1:0] busstate;
wire        longword;
wire        nresetout;
wire  [2:0] fc;
wire [31:0] cacr_out, vbr_out;
wire        debug_busy, debug_fault, debug_halted;
wire [255:0] debug_status;
wire        walker_req, walker_we;
wire [31:0] walker_addr, walker_wdat;

reg         mem_ready;
wire        clkena_in = (busstate == 2'b01) | mem_ready;
reg         walker_ack_r;
reg  [31:0] walker_data_r;
reg         walker_armed;

ap040_tg68k_compat dut
(
    .clk(clk),
    .nreset(nreset),
    .cache_allow_all(1'b1),
    .cache_snoop_stb(1'b0), .cache_snoop_addr(32'd0),
    .cache_z2_ena(1'b0),
    .cache_z3_base0(5'd0),
    .cache_z3_ena0(1'b0),
    .cache_z3_base1(4'd0),
    .cache_z3_ena1(1'b0),
    .clkena_in(clkena_in),
    .data_in(data_in),
    .ipl(3'b111),                 // active low: no interrupt request
    .ipl_autovector(1'b1),
    .berr(1'b0),

    .addr_out(addr_out),
    .data_write(data_write),
    .nwr(nwr),
    .nuds(nuds),
    .nlds(nlds),
    .busstate(busstate),
    .longword(longword),
    .nresetout(nresetout),
    .fc(fc),

    .mmu_addr_log(),
    .mmu_addr_phys(),
    .mmu_cache_inhibit(),
    .walker_req(walker_req),
    .walker_we(walker_we),
    .walker_addr(walker_addr),
    .walker_wdat(walker_wdat),
    .walker_ack(walker_ack_r),
    .walker_data(walker_data_r),
    .walker_berr(1'b0),
    .cache_req(),
    .cache_addr(),
    .cache_data(16'd0),
    .cache_ack(1'b0),
    .cache_burst(),
    .cache_burst_len(),
    .cache_ramaddr(),

    .cacr_out(cacr_out),
    .vbr_out(vbr_out),
    .debug_busy(debug_busy),
    .debug_fault(debug_fault),
    .debug_halted(debug_halted),
    .debug_status(debug_status)
);

wire [31:0] dbg_pc = debug_status[31:0];
wire [15:0] dbg_ir = debug_status[63:48];

//---------------------------------------------------------------------------
// 4 MB flat RAM + doorbell
//---------------------------------------------------------------------------
localparam RAM_WORDS = 2097152;               // 4 MB as 16-bit words
localparam [31:0] DOORBELL  = 32'h00F00000;
localparam [31:0] RESULTS   = 32'h00100000;
localparam integer RES_LEN  = 409600;

reg [15:0] mem [0:RAM_WORDS-1];
wire ram_sel = (addr_out < 32'h00400000);
assign data_in = ram_sel ? mem[addr_out[21:1]] : 16'h0000;

integer result;      // 0 running, 1 done
longint cycles;
reg [1023:0] prog_file;
reg [1023:0] results_file;
longint maxcycles;

always @(posedge clk) begin
    mem_ready <= 0;
    if (nreset && busstate != 2'b01 && !mem_ready)
        mem_ready <= 1;
end

// Dedicated 32-bit table-walker memory port (the mmu suite's page tables
// live in payload .bss inside the same flat RAM). Zero wait states, one
// acknowledge per request edge — the shape of tb_ap040_program.v's model
// without its latency sweep or fault injection.
always @(posedge clk) begin
    walker_ack_r <= 0;
    if (!nreset) walker_armed <= 1;
    else begin
        if (!walker_req) walker_armed <= 1;
        else if (walker_armed) begin
            walker_armed <= 0;
            if (walker_addr < 32'h00400000) begin
                if (walker_we) begin
                    mem[walker_addr[21:1]]        = walker_wdat[31:16];
                    mem[walker_addr[21:1] + 1'b1] = walker_wdat[15:0];
                end
                else
                    walker_data_r <= {mem[walker_addr[21:1]],
                                      mem[walker_addr[21:1] + 1'b1]};
            end
            walker_ack_r <= 1;
            if ($test$plusargs("walkdbg"))
                $display("WALK %s addr=%08x data=%08x wdat=%08x pc=%h",
                         walker_we ? "wr" : "rd", walker_addr,
                         {mem[walker_addr[21:1]], mem[walker_addr[21:1]+1'b1]},
                         walker_wdat, dbg_pc);
        end
    end
end

always @(posedge clk) begin
    if (nreset && mem_ready && busstate == 2'b11) begin
        if (ram_sel) begin
            if (!nuds) mem[addr_out[21:1]][15:8] = data_write[15:8];
            if (!nlds) mem[addr_out[21:1]][7:0]  = data_write[7:0];
        end
        else if (addr_out == DOORBELL && data_write == 16'h600D)
            result = 1;
        else if (addr_out == DOORBELL) begin
            $display("FAIL: doorbell wrote %04x (not 600D), pc=%h",
                     data_write, dbg_pc);
            result = 2;
        end
    end
end

// A halted core is a failed run — dump state and stop.
always @(posedge clk) begin
    if (nreset && (debug_fault || debug_halted) && result == 0) begin
        $display("FAIL: core halted, fault=%b pc=%h ir=%h", debug_fault,
                 dbg_pc, dbg_ir);
        result = 2;
    end
end

// Heartbeat so a long corpus run is visibly alive.
always @(posedge clk) begin
    cycles = cycles + 1;
    if (cycles % 20000000 == 0)
        $display("HEARTBEAT %0d cycles, pc=%h", cycles, dbg_pc);
end

integer i, f;
initial begin
    result = 0;
    cycles = 0;
    if (!$value$plusargs("prog=%s", prog_file)) begin
        $display("FAIL: missing +prog=<hexfile>");
        $finish;
    end
    if (!$value$plusargs("maxcycles=%d", maxcycles))
        maxcycles = 64'd2500000000;
    for (i = 0; i < RAM_WORDS; i = i + 1) mem[i] = 16'h0000;
    $readmemh(prog_file, mem);

    // Identity translation world (68040 8K-page format) at the top of
    // RAM: root[0] -> pointer table -> 512 pages mapping 0..4MB 1:1.
    // The Quadra ROM hands the bench a machine with valid tables; the
    // corpus's safe MOVEC TC row enables translation assuming exactly
    // that, so the sim provides the same environment (finding 22/30).
    // payload_entry_sim (SIM_MMU_WORLD) points URP/SRP here.
    begin : ident_world
        integer k;
        mem[32'h3FE000 >> 1] = 16'h003F; mem[(32'h3FE000 >> 1)+1] = 16'hE203;
        for (k = 0; k < 16; k = k + 1) begin
            mem[(32'h3FE200 + 4*k) >> 1]       = (32'h3FE400 + 128*k) >> 16;
            mem[((32'h3FE200 + 4*k) >> 1) + 1] = ((32'h3FE400 + 128*k) | 3) & 16'hFFFF;
        end
        for (k = 0; k < 512; k = k + 1) begin
            mem[(32'h3FE400 + 4*k) >> 1]       = (k * 32'h2000) >> 16;
            mem[((32'h3FE400 + 4*k) >> 1) + 1] = ((k * 32'h2000) | 1) & 16'hFFFF;
        end
    end

    nreset = 0;
    repeat (10) @(posedge clk);
    nreset = 1;

    while (result == 0 && cycles < maxcycles) @(posedge clk);

    if (result == 0)
        $display("FAIL: timeout after %0d cycles, pc=%h ir=%h", cycles,
                 dbg_pc, dbg_ir);
    if (result != 1)
        $display("dumping partial results for post-mortem");
    begin
        if (result == 1)
            $display("CORPUS DONE in %0d cycles", cycles);
        if ($value$plusargs("results=%s", results_file)) begin
            f = $fopen(results_file, "wb");
            for (i = 0; i < RES_LEN; i = i + 1)
                $fwrite(f, "%c", (i & 1) ? mem[(RESULTS + i) >> 1][7:0]
                                         : mem[(RESULTS + i) >> 1][15:8]);
            $fclose(f);
            $display("results written to %0s", results_file);
        end
    end
    $finish;
end

endmodule
