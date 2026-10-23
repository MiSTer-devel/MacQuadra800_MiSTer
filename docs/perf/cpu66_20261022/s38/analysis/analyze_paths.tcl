project_open MacQuadra800
create_timing_netlist -model slow
read_sdc
update_timing_netlist
set cpu {emu|pll|pll_inst|altera_pll_i|general[2].gpll~PLL_OUTPUT_COUNTER|divclk}
set ram {emu|pll|pll_inst|altera_pll_i|general[1].gpll~PLL_OUTPUT_COUNTER|divclk}
report_timing -setup -npaths 20000 -pairs_only -less_than_slack 0 -detail summary -from_clock $cpu -to_clock $cpu -file scratch/cpu66_failing_pairs.txt
report_timing -setup -npaths 100 -pairs_only -detail full_path -from_clock $cpu -to_clock $cpu -file scratch/cpu66_top100.txt
report_timing -setup -npaths 10 -pairs_only -detail full_path -to_clock $ram -file scratch/cpu66_ram_paths.txt
report_clock_fmax_summary -file scratch/cpu66_fmax.txt
delete_timing_netlist
project_close
