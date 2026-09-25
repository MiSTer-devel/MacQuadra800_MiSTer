# Run only after the complete build wrapper ends and before another build
# overwrites db. Optional output directory keeps each fit's evidence separate:
# quartus_sta -t scripts/cpu/timequest_worst_paths.tcl scratch/<fit>/cpu_timing
set out_dir [expr {[llength $quartus(args)] > 0 ? [lindex $quartus(args) 0] : "scratch/cpu_timing"}]
file mkdir $out_dir
project_open MacQuadra800
create_timing_netlist
read_sdc
update_timing_netlist
report_timing -setup -npaths 12 -detail summary -to_clock {emu|pll|pll_inst|altera_pll_i|general[0].gpll~PLL_OUTPUT_COUNTER|divclk} -file [file join $out_dir worst_paths.txt]
report_timing -setup -npaths 3 -detail path_only -to_clock {emu|pll|pll_inst|altera_pll_i|general[0].gpll~PLL_OUTPUT_COUNTER|divclk} -file [file join $out_dir worst_detail.txt]
project_close
