# Related-clock CPU/bus timing for CPU_AP68040_2X. Run on the fitted tree.
set tag [expr {[llength $quartus(args)] ? [lindex $quartus(args) 0] : "cpu66"}]
project_open MacQuadra800
create_timing_netlist
read_sdc
update_timing_netlist
set bus {emu|pll|pll_inst|altera_pll_i|general[0].gpll~PLL_OUTPUT_COUNTER|divclk}
set cpu {emu|pll|pll_inst|altera_pll_i|general[2].gpll~PLL_OUTPUT_COUNTER|divclk}
if {[get_collection_size [get_clocks $cpu]] != 1} {error "66 MHz CPU clock not found"}
file mkdir scratch
report_timing -setup -npaths 10 -detail full_path -from_clock $cpu -to_clock $cpu -file scratch/cpu_internal_$tag.txt
report_timing -setup -npaths 10 -detail full_path -from_clock $cpu -to_clock $bus -file scratch/cpu_to_bus_$tag.txt
report_timing -setup -npaths 10 -detail full_path -from_clock $bus -to_clock $cpu -file scratch/bus_to_cpu_$tag.txt
report_timing -setup -npaths 4 -detail full_path -to [get_registers {*cpu_bclk_en}] -file scratch/bus_phase_$tag.txt
project_close
