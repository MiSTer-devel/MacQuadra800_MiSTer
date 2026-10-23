# Report all fields, not just displacement, of each two-entry uop bank.
set tag [expr {[llength $quartus(args)] ? [lindex $quartus(args) 0] : "cpu66"}]
project_open MacQuadra800
create_timing_netlist -model slow
read_sdc
update_timing_netlist
set cpu {emu|pll|pll_inst|altera_pll_i|general[2].gpll~PLL_OUTPUT_COUNTER|divclk}
file mkdir scratch
foreach {label pattern bank} {
 fifo_first_all {*|useq|uq0.*} 0
 fifo_second_all {*|useq|uq1.*} 1
} {
 set regs [get_registers $pattern]
 if {[get_collection_size $regs] == 0} {
  set regs [get_registers "*|useq|uq_bank${bank}.*"]
 }
 if {[get_collection_size $regs] == 0} {error "No registers found for $label"}
 report_timing -setup -from_clock $cpu -to $regs -npaths 10 -detail full_path -file scratch/target_${label}_${tag}.txt
}
delete_timing_netlist
project_close
