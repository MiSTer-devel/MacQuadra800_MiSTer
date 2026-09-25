# Development-only headroom profile, sourced from MacQuadra800.qsf.  Compile-time
# removals of framework the benchmark runs never use; nothing here touches the
# CPU, MMU, FPU, caches, SDRAM, SCSI disks, SCC, EASC, ADB, timers or Mac video.
# Not a release recipe: a release build must not source this file.
# Measured 2026-09-15 on the profile branch: OSDs ~1,080 ALMs, audio path ~850,
# IIR filter ~445, 512x384 retarget ~360, video measurement ~260, Y/C ~240,
# shadowmask ~135.
set_global_assignment -name VERILOG_MACRO "MISTER_DISABLE_YC=1"
set_global_assignment -name VERILOG_MACRO "MISTER_DISABLE_SHADOWMASK=1"
set_global_assignment -name VERILOG_MACRO "MISTER_BYPASS_AUDIO_FILTER=1"
set_global_assignment -name VERILOG_MACRO "MISTER_DISABLE_AUDIO_OUT=1"
set_global_assignment -name VERILOG_MACRO "MISTER_DISABLE_VIDEO_CALC=1"
set_global_assignment -name VERILOG_MACRO "MISTER_DISABLE_HDMI_OSD=1"
set_global_assignment -name VERILOG_MACRO "MISTER_DISABLE_VGA_OSD=1"
set_global_assignment -name VERILOG_MACRO "VIDEO_512_OFF=1"
set_global_assignment -name VERILOG_MACRO "SCSI_CACHE_OFF=1"
