#!/usr/bin/env python3
"""Finish this task's disposable-disk baseline after its scripted prefix.

Requires the run directory's identities.json, control.txt and run.log.
Requests graceful simulator exit through this run's own control stream.
This is a simulation driver, not a hardware lifecycle script.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--timeout", type=int, default=10800)
    parser.add_argument("--profile-start-count", type=int, default=1)
    args = parser.parse_args()
    out = args.directory.resolve()
    identities = json.loads((out / "identities.json").read_text())
    if (out / "run.hda").resolve() == Path(identities["run.hda"]["source"]).resolve():
        parser.error("run disk must be a disposable copy")
    deadline = time.monotonic() + args.timeout

    def log_text():
        return (out / "run.log").read_text(errors="replace")

    def await_condition(condition):
        while not condition():
            if (out / "exit.status").exists():
                raise RuntimeError("Simulator exited before capture completed")
            if time.monotonic() >= deadline:
                raise TimeoutError("Baseline capture deadline expired")
            time.sleep(2)

    def send(*commands):
        subprocess.run(["python3", str(ROOT / "scripts/guest/sim_control_send.py"),
                        str(out / "control.txt"), *commands], check=True)

    def shot(*commands):
        before = set(out.glob("screenshot_f*.png"))
        send(*commands, "shot")
        await_condition(lambda: bool(set(out.glob("screenshot_f*.png")) - before))
        # The log is printed after stbi_write_png finishes writing the file.
        new = max(set(out.glob("screenshot_f*.png")) - before, key=lambda p: p.stat().st_mtime)
        await_condition(lambda: f"Saved {new.name}" in log_text())
        return new

    await_condition(lambda: log_text().count("[CPU-PROFILE] started") >= args.profile_start_count)
    print("Benchmark profile started", flush=True)
    for _ in range(400):
        picture = shot("wait 20000000")
        result = subprocess.run(["tesseract", str(picture), "stdout", "--psm", "11"],
                                check=True, capture_output=True, text=True)
        picture.with_suffix(".txt").write_text(result.stdout)
        if re.search(r"\btests?\s+(?:are|is)\s+done\b", result.stdout, re.I):
            (out / "completion_shot.txt").write_text(picture.name + "\n")
            send("profile stop")
            await_condition(lambda: log_text().count("[CPU-PROFILE] wrote") >= args.profile_start_count)
            final = shot("wait 3300000", "down 5a", "wait 330000", "up 5a", "wait 66000000")
            (out / "results_shot.txt").write_text(final.name + "\n")
            with (out / "report.md").open("w") as report:
                subprocess.run(["python3", str(ROOT / "scripts/cpu/report_pipeline_profile.py"),
                                str(out / "profile.tsv")], check=True, stdout=report)
            send("quit")
            await_condition(lambda: (out / "exit.status").exists())
            if (out / "exit.status").read_text().strip() != "0":
                raise RuntimeError("Simulator failed during graceful completion")
            (out / "capture.json").write_text(json.dumps({
                "status": "captured; screenshots require review", "completion": picture.name,
                "results": final.name, "profile": "profile.tsv",
                "boundary": "Run Set input through first completion-alert polling screenshot",
                "timer_log": "timer.log; inspect summary for missing identities or capture cap"
            }, indent=2) + "\n")
            print(f"Captured {out}; inspect {final.name}", flush=True)
            return
    raise RuntimeError("Completion alert not found within 400 guest-time polls")


if __name__ == "__main__":
    main()
