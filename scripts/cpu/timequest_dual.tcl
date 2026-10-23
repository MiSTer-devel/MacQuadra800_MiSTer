# Full Quadra dual-issue timing: CPU MHz argument is 33 or 66.
set mhz [lindex $quartus(args) 0]
if {$mhz ni {33 66}} {error "Pass 33 or 66"}
set cpu {emu|pll|pll_inst|altera_pll_i|general[0].gpll~PLL_OUTPUT_COUNTER|divclk}
if {$mhz == 66} {set cpu {emu|pll|pll_inst|altera_pll_i|general[2].gpll~PLL_OUTPUT_COUNTER|divclk}}
set ram {emu|pll|pll_inst|altera_pll_i|general[1].gpll~PLL_OUTPUT_COUNTER|divclk}
project_open MacQuadra800
create_timing_netlist
read_sdc
update_timing_netlist
file mkdir scratch
report_timing -setup -npaths 100 -pairs_only -detail full_path -from_clock $cpu -to_clock $cpu -file scratch/dual_cpu_top100.txt
report_timing -hold -npaths 10 -detail full_path -from_clock $cpu -to_clock $cpu -file scratch/dual_cpu_hold.txt
report_timing -setup -npaths 10 -pairs_only -detail full_path -to_clock $ram -file scratch/dual_ram_paths.txt
report_timing -setup -npaths 20 -detail full_path -file scratch/dual_all_setup.txt
report_timing -hold -npaths 20 -detail full_path -file scratch/dual_all_hold.txt
report_clock_fmax_summary -file scratch/dual_fmax.txt
project_close
