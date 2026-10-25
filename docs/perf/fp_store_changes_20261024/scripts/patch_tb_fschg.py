#!/usr/bin/env python3
# fp_store_changes 2026-10-24: the bench probes for the FP store changes, on a
# SCRATCH copy of rtl/ap68040_faster/tb/tb_ap68040.sv (never the checkout's):
#   - the per-cycle FP store trace of docs/perf/fp_store_trace_20261024
#     (+fstag=<n> +fslen=<cycles>; STAMP lines carry at=<cycle>), applied by
#     that directory's patch_tb_fstrace.py;
#   - +memdump=<file> [+dumpfrom=<hex> +dumpto=<hex>]: at the end of the run
#     the bench memory from dumpfrom (default 40000) to dumpto (default 7E000)
#     is written as "<address> <long word>" lines -- the differential test's
#     image (the program flushes its copyback data with CPUSHA first).
# usage: patch_tb_fschg.py <fp_store_trace scripts dir> <tb_ap68040.sv.orig> <tb_ap68040.sv>
import importlib.util, subprocess, sys, os
fsdir, src_path, dst_path = sys.argv[1:4]
tmp = dst_path + ".fstrace"
subprocess.check_call([sys.executable, os.path.join(fsdir, "patch_tb_fstrace.py"), src_path, tmp])
src = open(tmp).read()
os.unlink(tmp)

anchor = "// exception entries\n"
assert src.count(anchor) == 1, "anchor not found"
block = r'''// fp_store_changes 2026-10-24: +memdump=<file> +dumpfrom=<hex> +dumpto=<hex>:
// the bench memory at the end of the run, one long word a line
string fs_dump;
int    fs_d0, fs_d1;
initial begin
	if (!$value$plusargs("memdump=%s", fs_dump)) fs_dump = "";
	if (!$value$plusargs("dumpfrom=%h", fs_d0)) fs_d0 = 32'h40000;
	if (!$value$plusargs("dumpto=%h", fs_d1)) fs_d1 = 32'h7E000;
end
task automatic fs_memdump();
	int fd;
	fd = $fopen(fs_dump, "w");
	for (int a = fs_d0; a < fs_d1; a += 4)
		$fdisplay(fd, "%08x %08x", a, mem.mem[a >> 2]);
	$fclose(fd);
	$display("MEMDUMP %s %08x-%08x", fs_dump, fs_d0, fs_d1);
endtask

'''
src = src.replace(anchor, block + anchor)
old_end = "\tif (prof) prof_report();\n\tif (pcprof) pcprof_dump();\n"
assert src.count(old_end) == 1, "end of run not found"
src = src.replace(old_end, old_end + "\tif (fs_dump != \"\") fs_memdump();\n")
open(dst_path, "w").write(src)
print("patched", dst_path)
