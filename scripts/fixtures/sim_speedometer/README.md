# Simulator Speedometer capture tooling

**Current status:** P67 completed a visually reviewed full Mix in simulation
(see below). P89 is booting in an isolated snapshot with a fresh disposable
disk. Neither is a hardware acceptance result.

**Historical rejected attempt, 2026-09-19:** Frame5311
showed Prince of Persia, not Speedometer. No baseline number is accepted.
The historical keyboard replay is not reliable for this startup state; use
screenshot-driven navigation before enabling a future profile bracket.
The remainder documents the attempted run and tools, not a successful result.

`prefix_control.txt` is the historical keyboard sequence for the immutable
`MacQuadra800-Speedometer402-profile.hda` fixture: cold boot, open Speedometer
4.02, choose Benchmark Mix, start profiling, and press Run Set. Its waits
are simulated rising edges, so a full run takes substantial wall time.
It is specific to this disk's Finder layout; screenshots must confirm it.

The rejected attempt is in `scratch/pipeline_baseline_20260919c/`, launched
by `q800-pipeline-baseline-c-20260919.service`. Its original monitor was
`q800-pipeline-baseline-monitor-c-20260919.service`. Both are user systemd
units. `identities.json` records the copied simulator, selected development ROM, golden
disk and prefix hashes; `source_sha256.json` and `sources/` preserve source
identity. `run.hda` is disposable; never mount the golden disk directly.

The first cold-boot attempt reached MacAtrium but the host crashed on its
first key: `SimInput::ps2_key` had not been connected to the model port.
That connection is fixed and covered by `test_profile_integration.py`.
The `b` attempt was stopped during RAM testing after confirming that the
legacy `+warmstart` option does not skip this ROM's RAM test. See
`docs/quadra800-ram-test.md`: the low-memory cookie is not the RAM-test gate.
The `c` development attempt used `make -C verilator fastboot` and copies
`quadra800-fastboot.rom.hex`, with the initial wait reduced to 660,000,000
rising edges. Verification confirmed that this ROM differs only in the
RAM-test branch and corrected checksum. **This is development profiling,
not pristine-ROM acceptance.** Later simulator comparisons must use the
same recipe; release acceptance still uses the original ROM.

The simulator invocation, from that scratch directory, is:

```sh
./Vemu --headless --no-cpu-trace --disk run.hda +rom=rom.hex +ram=0 \
  --control control.txt --cpu-profile profile.tsv \
  --speedometer-observe timer.log --max-cycles 14000000000
```

For another run, create a new directory with fresh copies and identities;
do not reuse a mounted or previously interrupted writable image.

The monitor waits for the profile start, requests screenshots at 20-million
guest-clock intervals, and uses Tesseract to identify the completion alert.
It stops the profile, dismisses the alert, captures results, writes a state
and opcode report, then sends `quit` through that run's own control stream. The simulator
flushes its observer summary and exits; the monitor checks its exit status. It is intentionally a **disposable simulation** procedure, not
permission to interrupt a running hardware guest. The completion screenshot
and results still require inspection; a captured screen is not itself a
valid benchmark result.

```sh
python3 scripts/fixtures/sim_speedometer/monitor_baseline.py NEW_RUN_DIRECTORY
python3 scripts/cpu/report_pipeline_profile.py NEW_RUN_DIRECTORY/profile.tsv
```

The bracket includes launch overhead and polling, capture and host-processing delay
after the completion alert. Its state counts cover the complete
bracket, not just benchmark kernels. Dispatch counts are opcode-load events,
which include faulting instructions and may omit folded short branches.
Report them as clocks/opcode load, never retirement CPI. The P0 supported
opcode share is instruction coverage, not an estimate of saved cycles.

Check `timer.log` for a final summary, recognized identities and a capture
cap before interpreting it. Missing anomalies cannot establish timer
correctness. A crash/interrupted run can leave buffered records unwritten.


The `c` run's initial 20-second wait proved too short: frame1572 still showed
busy startup, and frame2231 remained in MacAtrium after the first navigation.
The original monitor was stopped before profiling. `recovery_control.txt`
replays the navigation after the first prefix drains and discards its first
bracket; `navigation_recovery.json` records why and hashes the amended stream.
The replacement monitor was `q800-pipeline-baseline-monitor-c2-20260919`, using
`--profile-start-count 2`. A final screenshot review is still required before
any number is accepted. Future automated launches should wait for a confirmed
MacAtrium screen instead of assuming a 20-second boot.

## P67 completed full-guest profile, 2026-09-20

The isolated snapshot in `scratch/p67_fullguest_20260920/tree` completed
all ten tests once. Root visually reviewed `screenshot_f6222.png`; the displayed
simulated Mix was1.187. `capture.json`, `workload.tsv` and `report.md` record
965772857 CPU clocks and257445279 opcode-load events. The bracket includes
launch/UI work and approximately two guest seconds after observed completion;
that delay was not subtracted. The simulator exited after queued profile-stop
and quit commands. Its completion monitor had timed out, so the screenshot and
processed profile-stop were reviewed directly rather than treating monitor exit
as proof of success.

This uses P67, the baseline divider, the development fastboot ROM and a
disposable fixture disk. P67 failed FPGA routing; this is not a hardware score,
an original-ROM release gate, or a controlled single-change P89 baseline.

Navigation was checked at each step: Escape from MacAtrium, two Tabs to
Exit to Finder, Return, then open Mac-7-5-5 → Applications → Speedometer
4.02 Folder → Speedometer 4.02. The live control stream and screenshots
are in that scratch directory; the old `prefix_control.txt` remains rejected.
Allow application loading to finish before interpreting a screenshot taken
immediately after Command-O.

The current profiler's `OPCODE` histogram samples the legacy `ir` register.
Pipeline dispatch can refer to a different opcode, so this histogram must
not be used for exact pipeline opcode attribution or instruction-coverage
claims. State-cycle and memory-path counters remain useful for locating
bottlenecks. The timer observer recognizes Queens and Sieve; it does not
establish validity of Whetstone or all ten benchmark timers. Any full Mix
profile must be labelled with its actual bracket, including UI overhead.


## Physical RAM inspection

New host builds accept `ramdump N` through the optional control stream, where
N is1..128MiB from physical address0. This writes guest-order bytes to
`ram_snapshot_<simulator-cycle>.bin` in the simulator working directory and
logs the cycle, PC, TC, URP and SRP. It reads RAM without advancing guest clocks
or injecting input; host wall time pauses while writing. This is physical RAM,
not an MMU-translated virtual view or an architectural checkpoint. Pending
writes/registers/cache state are not included. Do not treat it as a restartable
snapshot. A failed write is logged FAILED and may leave a partial file.

Example: `python3 scripts/guest/sim_control_send.py RUN/control.txt 'ramdump 8'`.
The current immutable P97 running executable predates this command; do not send
it there. Its full-queue profile counter also predates the queue-depth fix.
New host builds count buffer requests blocked by capacity while excluding the
registered acknowledgement guard, so both two- and four-entry queues work.

Validation: control parser rejects invalid sizes; RAM serialization unit checks
big-endian bytes, chunk boundaries and unchanged inputs. The real simulator
integration check requires a1MiB snapshot, normal key input/profile counts and
normal quit. All passed on the isolated P97-model host build in
scratch/whet_snapshot_host_20260920; production RTL is unchanged.
