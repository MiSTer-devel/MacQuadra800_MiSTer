#!/usr/bin/env python3
"""Exercise headless key injection, profiling, and graceful quit in the real simulator."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulator", type=Path, default=ROOT / "verilator/obj_dir/Vemu")
    args = parser.parse_args()
    out = Path(tempfile.mkdtemp(prefix="q800-profile-integration-"))
    image = bytearray(1024 * 1024)
    image[:8] = bytes.fromhex("0000340040800400")
    # MOVEQ #0,D0; ADDQ.L #1,D0 x3; BRA back to first ADDQ.
    image[0x400:0x40a] = bytes.fromhex("700052805280528060f8")
    (out / "rom.hex").write_text("\n".join(image[i:i+4].hex() for i in range(0, len(image), 4)) + "\n")
    (out / "control.txt").write_text(
        "wait 1000\ndown 1c\nwait 1000\nup 1c\nwait 1000\n"
        "ramdump 1\nprofile start\nwait 20000\nprofile stop\nquit\n")
    command = [str(args.simulator.resolve()), "--headless", "--no-cpu-trace", "+rom=rom.hex",
               "--control", "control.txt", "--cpu-profile", "profile.tsv",
               "--speedometer-observe", "timer.log", "--max-cycles", "500000"]
    with (out / "run.log").open("w") as log:
        subprocess.run(command, cwd=out, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
    log = (out / "run.log").read_text()
    snapshots = list(out.glob("ram_snapshot_*.bin"))
    assert len(snapshots) == 1 and snapshots[0].stat().st_size == 1048576
    assert "[RAM-SNAPSHOT] wrote" in log

    assert "[SIM-CONTROL] down 1C" in log and "[SIM-CONTROL] up 1C" in log
    assert "Reached 500000 cycles" not in log, "quit failed; only cycle limit stopped simulation"
    assert "[CPU-PROFILE] started" in log and "[CPU-PROFILE] wrote" in log
    rows = [line.split("\t") for line in (out / "profile.tsv").read_text().splitlines()]
    summary = next(r for r in rows if r[0] == "SUMMARY" and r[1].isdigit())
    assert int(summary[1]) == 20002, summary
    # Phase alignment may shift the boundary by one opcode event.
    assert 15000 <= int(summary[2]) <= 15002, summary
    assert "SUMMARY records=" in (out / "timer.log").read_text(), "observer did not flush on quit"
    print(f"PASS headless key down/up, profile bracket, graceful quit, timer summary: {out}")


if __name__ == "__main__":
    main()
