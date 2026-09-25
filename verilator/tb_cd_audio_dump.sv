// tb_cd_audio_dump -- feed cd_audio an MCDA blob and dump the three
// response tables it builds ($C1, $43 format 0, format 2 + session page),
// as the golden reference for Main's mac_cdrom_resp.cpp builders
// (scripts/cd_resp_golden.sh).
//
//   ./obj_dir_tb/tb_cd_audio_dump +blob=<name>.blob.hex +out=<name>.rtl.bin
//
// The blob file is 1024 bytes as two-digit hex tokens (what the host test's
// "gen" writes). The dump is 404 + 512 + 512 bytes; "<disc_audio>
// <toc43_len> <toc2_len>" goes to <out>.txt.

`timescale 1ns/1ps
module tb_cd_audio_dump;

reg clk = 0;
always #15 clk = ~clk;

reg         rst = 1;
reg         mounted = 0, img_mounted = 0;
reg  [31:0] img_blocks = 0;
wire        ca_io_active, ca_io_rd;
wire [31:0] ca_io_lba;
reg         io_ack = 0;
reg   [7:0] sd_buff_addr = 0;
reg  [15:0] sd_buff_dout = 0;
reg         sd_buff_wr = 0;
reg   [8:0] toc_base = 0, toc43_base = 0, toc2_base = 0;
wire  [7:0] toc_q0, toc43_q0, toc2_q0;
wire        toc_ready, disc_audio;
wire  [9:0] toc43_len, toc2_len;

reg [7:0] blob [0:1023];

cd_audio #(.CLK_HZ(32'd33_000_000)) dut (
	.clk(clk), .rst(rst), .bus_rst(1'b0),
	.mounted(mounted), .img_mounted(img_mounted), .img_blocks(img_blocks),
	.cmd_stb(1'b0), .cmd_op(8'd0),
	.cdb1(8'd0), .cdb2(8'd0), .cdb3(8'd0), .cdb4(8'd0), .cdb5(8'd0),
	.cdb6(8'd0), .cdb7(8'd0), .cdb8(8'd0), .cdb9(8'd0),
	.read_stb(1'b0), .eject_stb(1'b0),
	.ap_ch0(8'h01), .ap_vol0(8'hFF), .ap_ch1(8'h02), .ap_vol1(8'hFF),
	.ch_grant(1'b1),
	.ca_io_active(ca_io_active), .ca_io_rd(ca_io_rd), .ca_io_lba(ca_io_lba),
	.io_ack(io_ack),
	.sd_buff_addr(sd_buff_addr), .sd_buff_addr_hi(5'd0),
	.sd_buff_dout(sd_buff_dout), .sd_buff_wr(sd_buff_wr),
	.ast_code(), .cur_ctrl(), .cur_trk(),
	.abs_m(), .abs_s(), .abs_f(), .rel_m(), .rel_s(), .rel_f(),
	.toc_base(toc_base), .toc_q0(toc_q0), .toc_q1(), .toc_q2(), .toc_q3(),
	.toc_ready(toc_ready),
	.toc43_base(toc43_base), .toc43_q0(toc43_q0), .toc43_q1(), .toc43_q2(), .toc43_q3(),
	.toc43_len(toc43_len),
	.toc2_base(toc2_base), .toc2_q0(toc2_q0), .toc2_q1(), .toc2_q2(), .toc2_q3(),
	.toc2_len(toc2_len),
	.disc_audio(disc_audio),
	.snd_l(), .snd_r(),
	.dbg_cda0(), .dbg_cdur()
);

// HPS model for the TOC blob window: ack rises, the 256 words of block
// (lba - TOC_BLK) stream on sd_buff_wr in the FPGA's little-endian lane
// order (byte 2i in [7:0]), ack falls.
integer d_state = 0, d_i = 0, d_blk = 0;
always @(posedge clk) begin
	sd_buff_wr <= 0;
	case (d_state)
	0: if (ca_io_rd) begin
		d_blk = ca_io_lba - 32'h7FFF_0000;
		d_i = 0;
		io_ack <= 1;
		d_state = 1;
	end
	1: begin
		if (d_i < 256) begin
			sd_buff_addr <= d_i[7:0];
			sd_buff_dout <= {blob[d_blk*512 + d_i*2 + 1], blob[d_blk*512 + d_i*2]};
			sd_buff_wr   <= 1;
			d_i = d_i + 1;
		end
		else begin io_ack <= 0; d_state = 2; end
	end
	2: if (!ca_io_rd) d_state = 0;
	endcase
end

string blobfile, outfile;
integer fd, ft, a, guard;

initial begin
	if (!$value$plusargs("blob=%s", blobfile)) begin $display("need +blob="); $finish; end
	if (!$value$plusargs("out=%s", outfile))   begin $display("need +out=");  $finish; end
	$readmemh(blobfile, blob);

	repeat (10) @(posedge clk);
	rst <= 0;
	repeat (4) @(posedge clk);
	img_blocks <= {blob[11], blob[10], blob[9], blob[8]} << 2;   // lead-out in 512-byte blocks
	mounted <= 1;
	img_mounted <= 1;
	@(posedge clk);
	img_mounted <= 0;

	guard = 0;
	while (!toc_ready && guard < 20_000_000) begin @(posedge clk); guard = guard + 1; end
	if (!toc_ready) begin $display("FAIL: toc_ready never rose"); $finish; end
	$display("toc_ready after %0d cycles, toc_valid=%0d n_tracks=%0d disc_audio=%0d toc43_len=%0d toc2_len=%0d",
	         guard, dut.toc_valid, dut.n_tracks, disc_audio, toc43_len, toc2_len);

	fd = $fopen(outfile, "wb");
	for (a = 0; a < 404; a = a + 1) begin
		toc_base = a[8:0];
		repeat (3) @(posedge clk);
		$fwrite(fd, "%c", toc_q0);
	end
	for (a = 0; a < 512; a = a + 1) begin
		toc43_base = a[8:0];
		repeat (3) @(posedge clk);
		$fwrite(fd, "%c", toc43_q0);
	end
	for (a = 0; a < 512; a = a + 1) begin
		toc2_base = a[8:0];
		repeat (3) @(posedge clk);
		$fwrite(fd, "%c", toc2_q0);
	end
	$fclose(fd);
	ft = $fopen({outfile, ".txt"}, "w");
	$fwrite(ft, "%0d %0d %0d\n", disc_audio, toc43_len, toc2_len);
	$fclose(ft);
	$display("wrote %s", outfile);
	$finish;
end

endmodule
