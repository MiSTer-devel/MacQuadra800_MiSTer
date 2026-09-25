# Release-lite headroom: the four framework trims a Quadra 800 user never
# notices, kept off so the fast CPU has a chance to route.  Everything a
# user does see stays in: the HDMI/VGA OSDs, the audio output, composite
# Y/C.  Measured 2026-09-15 on the profile branch: IIR audio filter ~445
# ALMs, 512x384 retarget ~360, video measurement ~260, shadowmask ~135
# (1,200 together; the full development profile, configs/cpu_development.tcl,
# also drops the OSDs ~1,080, the audio path ~850 and Y/C ~240).
set_global_assignment -name VERILOG_MACRO "MISTER_DISABLE_SHADOWMASK=1"
set_global_assignment -name VERILOG_MACRO "MISTER_BYPASS_AUDIO_FILTER=1"
set_global_assignment -name VERILOG_MACRO "MISTER_DISABLE_VIDEO_CALC=1"
set_global_assignment -name VERILOG_MACRO "VIDEO_512_OFF=1"
