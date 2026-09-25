# The clk_sys <-> clk_ram crossing report every fitted tree gets BEFORE its db
# is overwritten (the SDRAM bridge's half-cycle handoffs, docs/sdram-open-row-crossing.md).
# Run from the project directory that holds the fitted db:
#   quartus_sta -t scripts/cpu/timequest_cross_domain.tcl [tag]
# Writes scratch/cross_sys2ram_<tag>.txt (watch sdram_beat32 req_tgl -> req_handoff)
# and scratch/cross_ram2sys_<tag>.txt (line_done_handoff -> line_data).
set tag [expr {[llength $quartus(args)] > 0 ? [lindex $quartus(args) 0] : "fit"}]
set sys {emu|pll|pll_inst|altera_pll_i|general[0].gpll~PLL_OUTPUT_COUNTER|divclk}
set ram {emu|pll|pll_inst|altera_pll_i|general[1].gpll~PLL_OUTPUT_COUNTER|divclk}
project_open MacQuadra800
create_timing_netlist
read_sdc
update_timing_netlist
file mkdir scratch
report_timing -setup -npaths 6 -detail summary -from_clock $sys -to_clock $ram -file scratch/cross_sys2ram_$tag.txt
report_timing -setup -npaths 6 -detail summary -from_clock $ram -to_clock $sys -file scratch/cross_ram2sys_$tag.txt
project_close
