# Run against each preserved fitted database; accepts a filename tag.
set tag [expr {[llength $quartus(args)] ? [lindex $quartus(args) 0] : "cpu66"}]
project_open MacQuadra800
create_timing_netlist -model slow
read_sdc
update_timing_netlist
set cpu {emu|pll|pll_inst|altera_pll_i|general[2].gpll~PLL_OUTPUT_COUNTER|divclk}
file mkdir scratch
foreach {label pattern} {
 fifo_second {*|useq|uq1.disp*}
 fifo_first {*|useq|uq0.disp*}
 redirect {*|be|redir_pc*}
 cache_tag {*|dmu|*tag|qa_r*}
 alu_forward {*|be|exq_val*}
 cache_way {*|dmu|f_way*}
} {
 set regs [get_registers $pattern]
 set count [get_collection_size $regs]
 if {$count == 0 && $label eq "cache_tag"} {
  # Dedicated M10Ks pack the old qa_r output into address registers.
  set pattern {*|dmu|*tag|*address_reg*}
  set regs [get_registers $pattern]
  set count [get_collection_size $regs]
 }
 puts "CPU66_TARGET $label registers=$count pattern=$pattern"
 if {$count == 0} {error "No registers found for $label"}
 report_timing -setup -from_clock $cpu -to $regs -npaths 3 -detail full_path -file scratch/target_${label}_${tag}.txt
}
delete_timing_netlist
project_close
