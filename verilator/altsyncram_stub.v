// Lint-only stub for the Altera altsyncram primitive; never synthesised.
// Quartus provides the real one. Present so `verilator --lint-only` can
// elaborate blocks that instantiate it (rtl/easc.sv).
module altsyncram #(
  parameter operation_mode = "", parameter width_a = 8, parameter widthad_a = 8,
  parameter numwords_a = 256, parameter width_b = 8, parameter widthad_b = 8,
  parameter numwords_b = 256, parameter outdata_reg_a = "", parameter outdata_reg_b = "",
  parameter lpm_type = "", parameter intended_device_family = "",
  parameter address_reg_b = "", parameter clock_enable_input_a = "",
  parameter clock_enable_input_b = "", parameter clock_enable_output_a = "",
  parameter clock_enable_output_b = "", parameter indata_reg_b = "",
  parameter power_up_uninitialized = "", parameter read_during_write_mode_port_a = "",
  parameter read_during_write_mode_port_b = "", parameter read_during_write_mode_mixed_ports = "",
  parameter width_byteena_a = 1, parameter width_byteena_b = 1,
  parameter byte_size = 8, parameter init_file = "", parameter ram_block_type = "",
  parameter outdata_aclr_a = "", parameter outdata_aclr_b = "",
  parameter address_aclr_a = "", parameter address_aclr_b = "",
  parameter indata_aclr_a = "", parameter indata_aclr_b = "",
  parameter wrcontrol_aclr_a = "", parameter wrcontrol_aclr_b = "",
  parameter byteena_aclr_a = "", parameter byteena_aclr_b = "",
  parameter clock_enable_core_a = "", parameter clock_enable_core_b = "",
  parameter wrcontrol_wraddress_reg_b = "", parameter rdcontrol_reg_b = "",
  parameter byteena_reg_b = "", parameter maximum_depth = 0,
  parameter enable_ecc = "", parameter width_eccstatus = 3
)(
  input clock0, input clock1, input clock2, input clock3,
  input clocken0, input clocken1, input clocken2, input clocken3,
  input aclr0, input aclr1,
  input addressstall_a, input addressstall_b,
  input [widthad_a-1:0] address_a, input [widthad_b-1:0] address_b,
  input [width_a-1:0] data_a, input [width_b-1:0] data_b,
  input wren_a, input wren_b, input rden_a, input rden_b,
  input [width_byteena_a-1:0] byteena_a, input [width_byteena_b-1:0] byteena_b,
  output [width_a-1:0] q_a, output [width_b-1:0] q_b,
  output [width_eccstatus-1:0] eccstatus
);
  assign q_a = {width_a{1'b0}};
  assign q_b = {width_b{1'b0}};
  assign eccstatus = {width_eccstatus{1'b0}};
endmodule
