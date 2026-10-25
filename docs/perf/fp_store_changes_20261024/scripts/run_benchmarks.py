import subprocess, os

B = os.path.expanduser("~/mister/q800_fpchg_20261024")
BASE = os.path.join(B, "base/obj_fs/obj_prog/tb_ap68040")
NEW = os.path.join(B, "stageA/obj_fs/obj_prog/tb_ap68040")
HEXDIR = os.path.expanduser("~/mister/q800_fpattr_20261024/rtl/ap68040_faster/tb/build")

benchmarks = [
    ("Whetstone", "whet_2.hex", "whet_4.hex", 2),
    ("MatMul 20x20", "fpmm_20_r2.hex", "fpmm_20_r4.hex", 2),
    ("FFT 256-pt", "fft_256_r2.hex", "fft_256_r4.hex", 2),
]

def run_bench(bin_path, hex_file):
    cmd = [bin_path, f"+prog={os.path.join(HEXDIR, hex_file)}", "+timeout=40000000"]
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
    for line in out.splitlines():
        if line.startswith("PASS"):
            for part in line.split():
                if part.startswith("cycles="):
                    return int(part.split("=")[1])
    raise RuntimeError(f"Failed to find cycles in {hex_file}: {out[-200:]}")

print("%-16s %-18s %-20s %-16s %s" % ("Benchmark", "Base (cyc/iter)", "StageA (cyc/iter)", "Delta", "Speedup"))
print("-" * 80)

for name, r2_hex, r4_hex, n_iter in benchmarks:
    c_b2 = run_bench(BASE, r2_hex)
    c_b4 = run_bench(BASE, r4_hex)
    base_iter = (c_b4 - c_b2) / n_iter

    c_n2 = run_bench(NEW, r2_hex)
    c_n4 = run_bench(NEW, r4_hex)
    new_iter = (c_n4 - c_n2) / n_iter

    delta = new_iter - base_iter
    pct = (delta / base_iter) * 100
    print("%-16s %14.0f     %14.0f       %+10.0f (%+.2f%%)   %.3fx" % (name, base_iter, new_iter, delta, pct, base_iter/new_iter))
