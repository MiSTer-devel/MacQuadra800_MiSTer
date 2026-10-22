# Pipelined 040 shutdown testing (2026-10-22)

A continuous Finder Special → Shut Down mouse gesture reaches the safe-to-switch-off screen on both the minimal pipelined CPU and the performance/options build. The previously reported hardware hang is not reproduced with this input method. No shutdown RTL fix has been applied.

## Hardware evidence

MiSTer `10.0.2.192`, Mac OS 8.1, 32 MB. These are the existing bitstreams, without recompilation:

| Build | Area | Bitstream MD5 | Result |
|---|---:|---|---|
| Minimal (`pipelined-040-min`, `6e1b795`, seed 38), `MacQuadra800_fix2.rbf` | 33,200 ALMs | `11580e654e9fa77e391c933b668f43c5` | Finder shutdown reached halt screen within 12 s |
| Write buffer + FPU_PIPE/LOOP_PRED/EARLY_RES, seed 40, `MacQuadra800_opts.rbf` | 35,648 ALMs | `916b27a3190c22fb6ed62480f6237a68` | After Speedometer Mix/PR/Color/FPU runs, shutdown reached halt screen within 12 s |

Screenshots: [minimal selection](perf/shutdown_20261022/min-selected.png), [minimal halt](perf/shutdown_20261022/min-halted.png), [options selection](perf/shutdown_20261022/options-selected.png), [options halt](perf/shutdown_20261022/options-halted.png). Both CPUs also reached the shutdown ROM loop in the inherited full-machine simulations (`/Users/alans/dev2/q800_hang/NOTES.md`).

## Input method

The installed MiSTerKVMS CLI's `mouse down left` sends **both** `mouseBtn:left_down` and `mouseBtn:left_up` immediately; `/tmp/remote.log` on the MiSTer confirms it. Keeping its MCP subprocess alive does not change this behavior. A sequence of separate KVM mouse commands cannot be treated as a held-button drag. A still-inverted Special title alone does not prove a CPU hang.

Use the existing websocket helper with its interactive mode (Python 3.9+, POSIX, `websockets` installed):

```sh
python3 scripts/mister_ws.py --host 10.0.2.192 --delay 0.15 --interactive mousebtn:left_up
```

On this Mac, `/usr/bin/python3` has `websockets`; the Homebrew Python does not. In the helper's terminal, enter one command per line:

```text
mouse:3,0
mouse:0,3
mousebtn:left_down
mouse:0,3
mousebtn:left_up
```

Position the pointer over Special with the button up and verify a screenshot before pressing. Keep this helper running while taking screenshots with the KVM. After pressing, move down in paced steps, verify Shut Down is highlighted, and only then send `mousebtn:left_up`. The helper leaves the websocket open between commands and releases the left button on EOF, SIGINT, SIGTERM, or SIGHUP. It does not infer menu geometry or choose an item automatically.

The successful geometry on the 640×480 Mac desktop is Special near `(180, 7)` and Shut Down near `(180, 104)`. Relative motion depends on acceleration: use screenshots to confirm position instead of assuming a fixed scale.

Validation of the helper: existing batch tokens retain their wire format; interactive mode emits no premature mouse release; EOF and SIGTERM each emit an explicit left release. Hardware verification used the same websocket input path.

## Branch policy

`pipelined-040-min` keeps the AP68040 integration and correctness fixes. `pipelined-040` carries performance experiments, with speed, area, and timing measured for each. Test-tool corrections and their evidence belong on both branches and add no FPGA logic. The higher-area options build is a measured variant; its enabled parameters are not the defaults of the minimal branch.

A/UX 3.1 boot and shutdown remain unqualified on these bitstreams. The regression needs the installed guest image and the 32 MB setting.
