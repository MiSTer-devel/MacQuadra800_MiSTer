// tb_adb -- rtl/adb.sv: the ADB transceiver's devices, driven through the
// ST0/ST1 + shift-register byte interface the ROM uses (via iosb's shim).
//
//   make tb_adb
//
// Checks (docs/adb-joystick.md, "Verification" 1):
//   - joystick absent: the mouse alone at 3 behaves as before (Talk 3, the
//     0xFE move, Talk 0 with a mouse packet, and it rejects handler 0x23);
//   - MouseStick II: mouse + stick at 3 -> Talk 3 is the mouse's and marks the
//     stick collided, Listen 3 0xFE moves only the mouse, the next Talk 3 finds
//     the stick, the ROM's move-back works, the stick accepts 0x23 and the
//     mouse does not, Talk 1 = 03 00, Talk 0 = the 7-byte report, nothing
//     when unchanged, again when it changes;
//   - Firebird: 0x4E accepted, Talk 1 = 0A 01 30, the 8-byte report;
//   - pointer mode: handler 0x01 with the option set gives mouse deltas;
//   - the Reset command puts every device back at its default address.
`timescale 1ns/1ps
module tb_adb;

reg clk = 0;
always #15 clk = ~clk;

reg         reset = 1;
reg   [1:0] st = 2'b11;                   // {ST1, ST0}: idle
reg   [7:0] din = 0;
reg         din_stb = 0;
reg  [24:0] ps2_mouse = 0;
reg  [51:0] adb_joy = 0;
reg  [10:0] ps2_key = 0;
wire        int_n;
wire  [7:0] dout;
wire        dout_stb;
wire        resp_pending;

adb dut (
	.clk(clk), .clk_en(1'b1), .reset(reset),
	.st(st), ._int(int_n), .viaBusy(1'b0), .listen(),
	.adb_din(din), .adb_din_strobe(din_stb),
	.adb_dout(dout), .adb_dout_strobe(dout_stb),
	.capslock(),
	.ps2_mouse(ps2_mouse), .ps2_key(ps2_key),
	.adb_joy(adb_joy),
	.resp_pending(resp_pending), .dbg_adb(), .mouse_has_event_o()
);

localparam [1:0] S_CMD = 2'b00, S_D1 = 2'b01, S_D2 = 2'b10, S_IDLE = 2'b11;

integer errors = 0;
integer checks = 0;

task tick(input integer n);
	repeat (n) @(posedge clk);
endtask

task set_st(input [1:0] s);
	begin st = s; tick(4); end
endtask

task send(input [7:0] b);
	begin din = b; din_stb = 1; tick(1); din_stb = 0; tick(4); end
endtask

// a command byte in the Command state; a Listen's data bytes follow in the
// data states and the Listen is applied when the bus returns to Command
task command(input [7:0] c);
	begin set_st(S_IDLE); set_st(S_CMD); send(c); end
endtask

task listen3(input [3:0] a, input [7:0] b0, input [7:0] b1);
	begin
		command({a, 4'b1011});
		set_st(S_D1); send(b0);
		set_st(S_D2); send(b1);
		set_st(S_IDLE);
		set_st(S_CMD);                    // applies the Listen
		set_st(S_IDLE);
	end
endtask

// read the reply to a Talk: n bytes expected; the byte after the last one
// must come back as "no data"
reg [7:0] got [0:9];
integer   got_n;
task talk(input [3:0] a, input [1:0] r, input integer n);
	integer i;
	reg [1:0] s;
	begin
		command({a, 2'b11, r});
		got_n = 0;
		for (i = 0; i < n + 1; i = i + 1) begin
			s = (i % 2 == 0) ? S_D1 : S_D2;
			set_st(s);
			if (i < n) begin
				got[i] = dout;
				got_n = got_n + 1;
			end
		end
		set_st(S_IDLE);
	end
endtask

task expect_len(input [255:0] what, input integer n);
	begin
		checks = checks + 1;
		if (dut.resp_len != n) begin
			$display("FAIL %0s: reply length %0d, expected %0d", what, dut.resp_len, n);
			errors = errors + 1;
		end
	end
endtask

task expect_byte(input [255:0] what, input integer i, input [7:0] v);
	begin
		checks = checks + 1;
		if (got[i] !== v) begin
			$display("FAIL %0s: byte %0d = %02x, expected %02x", what, i, got[i], v);
			errors = errors + 1;
		end
	end
endtask

task expect_reg3(input [255:0] what, input [3:0] a, input [7:0] h);
	begin
		talk(a, 2'd3, 2);
		expect_len(what, 2);
		expect_byte(what, 0, {4'b0110, a});
		expect_byte(what, 1, h);
	end
endtask

task expect_none(input [255:0] what, input [3:0] a, input [1:0] r);
	begin
		command({a, 2'b11, r});
		checks = checks + 1;
		if (dut.resp_len != 0) begin
			$display("FAIL %0s: expected no reply at %0d, got %0d bytes", what, a, dut.resp_len);
			errors = errors + 1;
		end
		set_st(S_D1);
		checks = checks + 1;
		if (int_n !== 1'b0) begin
			$display("FAIL %0s: INT not asserted at Data1 for an empty reply", what);
			errors = errors + 1;
		end
		set_st(S_IDLE);
	end
endtask

task joy(input [2:0] mode, input ptr, input signed [7:0] x, input signed [7:0] y,
         input signed [7:0] t, input [7:0] btn);
	begin
		adb_joy = {ptr, mode, t, 8'd0, y, x, 4'd0, btn, 4'd0};
		tick(4);
	end
endtask

task joy_rx(input [2:0] mode, input signed [7:0] x, input signed [7:0] y,
            input signed [7:0] t, input signed [7:0] rx, input [7:0] btn, input [3:0] dpad);
	begin
		adb_joy = {1'b0, mode, t, rx, y, x, 4'd0, btn, dpad};
		tick(4);
	end
endtask

initial begin
	// ---------------- joystick absent ----------------
	joy(3'd0, 1'b0, 0, 0, 0, 0);
	tick(10); reset = 0; tick(10);
	command(8'h00); set_st(S_IDLE);               // ADB Reset
	expect_reg3("mouse alone", 4'd3, 8'h01);
	expect_reg3("keyboard alone", 4'd2, 8'h02);
	expect_none("nothing at 4", 4'd4, 2'd3);
	listen3(4'd3, 8'h09, 8'h23);                   // the mouse rejects 0x23
	expect_reg3("mouse rejects 0x23", 4'd3, 8'h01);
	listen3(4'd3, 8'h09, 8'hFE);                   // ... and moves on 0xFE
	expect_none("mouse moved away", 4'd3, 2'd3);
	command(8'h21); set_st(S_IDLE);              // Flush the keyboard
	command(8'h92); set_st(S_IDLE);              // reserved 0010 at the mouse
	expect_none("Flush leaves the mouse moved", 4'd3, 2'd3);
	expect_reg3("mouse at 9", 4'd9, 8'h01);
	ps2_mouse = {1'b1, 8'd0, 8'd5, 8'h01};         // +5 X, button down
	tick(20);
	talk(4'd9, 2'd0, 2);
	expect_len("mouse Talk 0", 2);
	expect_byte("mouse Talk 0", 0, 8'h00);         // button down, dy 0
	expect_byte("mouse Talk 0", 1, 8'h85);         // dx +5
	expect_none("no joystick at 3", 4'd3, 2'd0);

	// ---------------- MouseStick II ----------------
	reset = 1; tick(4);
	joy(3'd1, 1'b0, 0, 0, 0, 0);
	tick(4); reset = 0; tick(10);
	command(8'h00); set_st(S_IDLE);
	// ADBReInit at address 3: the mouse wins, the stick is marked
	expect_reg3("collision: mouse wins", 4'd3, 8'h01);
	checks = checks + 1;
	if (!dut.joy_col) begin $display("FAIL stick not marked collided"); errors = errors + 1; end
	listen3(4'd3, 8'h08, 8'hFE);                   // only the winner moves
	checks = checks + 1;
	if (dut.mouse_addr != 4'd8 || dut.joy_addr != 4'd3) begin
		$display("FAIL 0xFE move: mouse %0d stick %0d", dut.mouse_addr, dut.joy_addr);
		errors = errors + 1;
	end
	expect_reg3("stick found second", 4'd3, 8'h01);
	listen3(4'd3, 8'h09, 8'hFE);                   // the stick moves too ...
	expect_none("address 3 empty", 4'd3, 2'd3);
	listen3(4'd9, 8'h03, 8'hFE);                   // ... and is moved back
	expect_reg3("stick back at 3", 4'd3, 8'h01);
	expect_reg3("mouse at 8", 4'd8, 8'h01);
	// silent in handler 0x01 without the pointer option
	joy(3'd1, 1'b0, 8'sd100, 0, 0, 8'h01);
	expect_none("stick silent in 0x01", 4'd3, 2'd0);
	expect_none("no Talk 1 in 0x01", 4'd3, 2'd1);
	// the Gravis driver's probe: the mouse ignores 0x23, the stick takes it
	listen3(4'd8, 8'h08, 8'h23);
	expect_reg3("mouse keeps 0x01", 4'd8, 8'h01);
	listen3(4'd3, 8'h03, 8'h23);
	expect_reg3("stick takes 0x23", 4'd3, 8'h23);
	listen3(4'd3, 8'h03, 8'h4E);                   // not a Firebird
	expect_reg3("MouseStick rejects 0x4E", 4'd3, 8'h23);
	talk(4'd3, 2'd1, 2);
	expect_len("MouseStick Talk 1", 2);
	expect_byte("MouseStick Talk 1", 0, 8'h03);
	expect_byte("MouseStick Talk 1", 1, 8'h00);
	// full right, full up, trigger held: X = 127*75/16 = 595, Y = -595
	joy(3'd1, 1'b0, 8'sd127, -8'sd127, 0, 8'h01);
	talk(4'd3, 2'd0, 8);
	expect_len("MouseStick Talk 0", 8);
	expect_byte("MouseStick pad byte", 7, 8'h00);
	expect_byte("MouseStick Talk 0", 0, 8'h80);
	expect_byte("MouseStick Talk 0", 1, 8'h80);
	expect_byte("MouseStick Talk 0", 2, 8'h02);
	expect_byte("MouseStick Talk 0", 3, 8'h53);
	expect_byte("MouseStick Talk 0", 4, 8'hFD);
	expect_byte("MouseStick Talk 0", 5, 8'hAC);
	expect_byte("MouseStick Talk 0", 6, 8'hFB);  // trigger (bit 2) down
	expect_none("unchanged stick", 4'd3, 2'd0);
	joy(3'd1, 1'b0, 8'sd127, -8'sd127, 0, 8'h1E); // buttons 2-5, trigger up
	talk(4'd3, 2'd0, 7);
	expect_byte("MouseStick buttons", 6, 8'hE4);
	joy(3'd1, 1'b0, 0, 0, 0, 0);
	tick(4);
	// D-pad: full deflection left/down from a digital pad
	adb_joy = {1'b0, 3'd1, 8'd0, 8'd0, 8'd0, 8'd0, 4'd0, 8'd0, 4'b0110};
	tick(4);
	talk(4'd3, 2'd0, 7);
	expect_byte("D-pad X", 2, 8'hFD);
	expect_byte("D-pad X", 3, 8'hAC);
	expect_byte("D-pad Y", 4, 8'h02);
	expect_byte("D-pad Y", 5, 8'h53);
	// the Reset command puts both back at 3, handler 0x01
	command(8'h00); set_st(S_IDLE);
	checks = checks + 1;
	if (dut.mouse_addr != 4'd3 || dut.joy_addr != 4'd3 || dut.joy_handler != 8'h01) begin
		$display("FAIL Reset: mouse %0d stick %0d handler %02x", dut.mouse_addr, dut.joy_addr, dut.joy_handler);
		errors = errors + 1;
	end

	// ---------------- Firebird ----------------
	reset = 1; tick(4);
	joy(3'd2, 1'b0, 0, 0, 0, 0);
	tick(4); reset = 0; tick(10);
	command(8'h00); set_st(S_IDLE);
	expect_reg3("Firebird ReInit", 4'd3, 8'h01);
	listen3(4'd3, 8'h0A, 8'hFE);                   // mouse to 10
	listen3(4'd3, 8'h03, 8'h4E);
	expect_reg3("Firebird takes 0x4E", 4'd3, 8'h4E);
	talk(4'd3, 2'd1, 4);
	expect_len("Firebird Talk 1", 4);
	expect_byte("Firebird Talk 1 pad", 3, 8'h00);
	expect_byte("Firebird Talk 1", 0, 8'h0A);
	expect_byte("Firebird Talk 1", 1, 8'h01);
	expect_byte("Firebird Talk 1", 2, 8'h30);
	// full right, full up, throttle back (down), trigger + Thumb + Base 3
	joy(3'd2, 1'b0, 8'sd127, -8'sd127, 8'sd127, 8'h83);
	talk(4'd3, 2'd0, 8);
	expect_len("Firebird Talk 0", 8);
	expect_byte("Firebird Talk 0", 0, 8'hFF);
	expect_byte("Firebird Talk 0", 1, 8'hDF);     // base middle left (Base 3, bit 53)
	expect_byte("Firebird Talk 0", 2, 8'hBB);     // handle upper (Thumb) + trigger
	expect_byte("Firebird Talk 0", 3, 8'hFF);
	expect_byte("Firebird Talk 0", 4, 8'h01);
	expect_byte("Firebird Talk 0", 5, 8'hFF);
	expect_byte("Firebird Talk 0", 6, 8'h80);
	expect_byte("Firebird Talk 0", 7, 8'h80);
	listen3(4'd3, 8'h03, 8'h23);                   // the Firebird's MouseStick mode
	expect_reg3("Firebird takes 0x23", 4'd3, 8'h23);

	// ---------------- pointer mode ----------------
	reset = 1; tick(4);
	joy(3'd1, 1'b1, 0, 0, 0, 0);
	tick(4); reset = 0; tick(10);
	command(8'h00); set_st(S_IDLE);
	expect_reg3("pointer ReInit", 4'd3, 8'h01);
	listen3(4'd3, 8'h0B, 8'hFE);                   // mouse to 11
	expect_none("centred stick is quiet", 4'd3, 2'd0);
	joy(3'd1, 1'b1, 8'sd127, 0, 0, 0);
	talk(4'd3, 2'd0, 2);
	expect_len("pointer Talk 0", 2);
	expect_byte("pointer Talk 0", 0, 8'h80);      // button up, dy 0
	expect_byte("pointer Talk 0", 1, 8'h8C);      // dx +(127-24)/8 = 12
	joy(3'd1, 1'b1, 0, -8'sd128, 0, 8'h01);
	talk(4'd3, 2'd0, 2);
	expect_byte("pointer up + button", 0, 8'h73); // button down, dy -13
	expect_byte("pointer up + button", 1, 8'h80);
	// the option is live: off stops the deltas at once, on resumes them
	joy(3'd1, 1'b0, 8'sd127, 0, 0, 0);
	expect_none("pointer option off, live", 4'd3, 2'd0);
	joy(3'd1, 1'b1, 8'sd127, 0, 0, 0);
	talk(4'd3, 2'd0, 2);
	expect_byte("pointer option on again", 1, 8'h8C);

	// ---------------- Gravis GamePad (address 2, with the keyboard) ----------------
	reset = 1; tick(4);
	joy_rx(3'd3, 0, 0, 0, 0, 0, 4'd0);
	tick(4); reset = 0; tick(10);
	command(8'h00); set_st(S_IDLE);
	expect_reg3("GamePad: keyboard wins", 4'd2, 8'h02);
	begin : rom_scan                                // Talk 3 to 3..15 first
		integer a;
		for (a = 3; a < 16; a = a + 1) begin command({a[3:0], 4'b1111}); set_st(S_D1); set_st(S_D2); set_st(S_IDLE); end
	end
	checks = checks + 1;
	if (!dut.pad_col) begin $display("FAIL pad not marked collided"); errors = errors + 1; end
	listen3(4'd2, 8'h0A, 8'hFE);                   // the keyboard moves to 10
	checks = checks + 1;
	if (dut.kbd_addr != 4'd10 || dut.pad_addr != 4'd2) begin
		$display("FAIL GamePad 0xFE move: kbd %0d pad %0d", dut.kbd_addr, dut.pad_addr);
		errors = errors + 1;
	end
	expect_reg3("GamePad found second", 4'd2, 8'h02);
	listen3(4'd2, 8'h0B, 8'hFE);
	expect_none("address 2 empty", 4'd2, 2'd3);
	listen3(4'd11, 8'h02, 8'hFE);                  // moved back to 2
	expect_reg3("GamePad back at 2", 4'd2, 8'h02);
	expect_reg3("keyboard at 10", 4'd10, 8'h02);
	// the keyboard still types at its new address
	ps2_key = {~ps2_key[10], 1'b1, 1'b0, 8'h1C};   // 'A' down (set 2 code 1C)
	tick(40);
	talk(4'd10, 2'd0, 2);
	expect_len("keyboard Talk 0 at 10", 2);
	expect_byte("keyboard Talk 0 at 10", 0, 8'h00);   // ADB key code 0 = A
	// handler 0x02: the D-pad is the arrow keys, the buttons do nothing
	expect_none("pad quiet", 4'd2, 2'd0);
	joy_rx(3'd3, 0, 0, 0, 0, 8'h01, 4'b0001);      // right + button 1
	talk(4'd2, 2'd0, 2);
	expect_byte("right arrow down", 0, 8'h3C);
	expect_byte("right arrow down", 1, 8'hFF);
	joy_rx(3'd3, 0, 0, 0, 0, 0, 4'b1010);          // right up, left + up down
	talk(4'd2, 2'd0, 2);
	expect_byte("left down", 0, 8'h3B);
	expect_byte("right up", 1, 8'hBC);
	talk(4'd2, 2'd0, 2);
	expect_byte("up down", 0, 8'h3E);
	expect_byte("up down", 1, 8'hFF);
	expect_none("arrows settled", 4'd2, 2'd0);
	talk(4'd2, 2'd1, 2);
	expect_byte("GamePad Talk 1", 0, 8'h03);
	expect_byte("GamePad Talk 1", 1, 8'h00);
	talk(4'd2, 2'd2, 2);
	expect_byte("GamePad Talk 2", 0, 8'hFF);
	expect_byte("GamePad Talk 2", 1, 8'hFF);
	// the Gravis driver: the keyboard rejects 0x34, the pad takes it
	listen3(4'd10, 8'h0A, 8'h34);
	expect_reg3("keyboard keeps 0x02", 4'd10, 8'h02);
	listen3(4'd2, 8'h02, 8'h34);
	expect_reg3("GamePad takes 0x34", 4'd2, 8'h34);
	joy_rx(3'd3, 0, 0, 0, 0, 8'h01, 4'b1000);      // green + D-pad up
	talk(4'd2, 2'd0, 2);
	expect_byte("GamePad 0x34", 0, 8'hB7);
	expect_byte("GamePad 0x34", 1, 8'hFF);
	expect_none("GamePad unchanged", 4'd2, 2'd0);

	// ---------------- SideWinder 3D Pro (address 4 + a mouse half at 3) ----------------
	reset = 1; tick(4);
	joy_rx(3'd4, 0, 0, 0, 0, 0, 4'd0);
	tick(4); reset = 0; tick(10);
	command(8'h00); set_st(S_IDLE);
	expect_reg3("SideWinder stick at 4", 4'd4, 8'h5D);
	expect_reg3("SideWinder: mouse wins 3", 4'd3, 8'h01);
	listen3(4'd3, 8'h0C, 8'hFE);                   // mouse to 12, the mouse half stays
	expect_reg3("SideWinder mouse half", 4'd3, 8'h01);
	listen3(4'd3, 8'h03, 8'h23);                   // not a MouseStick
	expect_reg3("SideWinder rejects 0x23", 4'd3, 8'h01);
	listen3(4'd3, 8'h03, 8'h02);
	expect_reg3("SideWinder mouse half takes 0x02", 4'd3, 8'h02);
	listen3(4'd4, 8'h04, 8'h4E);
	expect_reg3("SideWinder stick keeps 0x5D", 4'd4, 8'h5D);
	// full right, full up, throttle and twist centred, trigger + base bottom left
	joy_rx(3'd4, 8'sd127, -8'sd127, 0, 0, 8'h41, 4'd0);
	talk(4'd4, 2'd0, 8);
	expect_len("SideWinder Talk 0", 8);
	expect_byte("SideWinder pad byte", 7, 8'h00);
	expect_byte("SideWinder Talk 0", 0, 8'h7F);
	expect_byte("SideWinder Talk 0", 1, 8'hFC);
	expect_byte("SideWinder Talk 0", 2, 8'h04);
	expect_byte("SideWinder Talk 0", 3, 8'h01);
	expect_byte("SideWinder Talk 0", 4, 8'h01);
	expect_byte("SideWinder Talk 0", 5, 8'hE2);
	expect_byte("SideWinder Talk 0", 6, 8'h02);
	expect_none("SideWinder unchanged", 4'd4, 2'd0);
	expect_none("SideWinder no Talk 1", 4'd4, 2'd1);

	$display("tb_adb: %0d checks, %0d errors", checks, errors);
	if (errors == 0) $display("PASS");
	$finish;
end

endmodule
