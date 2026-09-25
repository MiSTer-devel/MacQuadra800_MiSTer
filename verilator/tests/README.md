# Simulation control and profiling checks

These deterministic host-only tests were recovered from the profiling branch.
They require no ROM, disk, FPGA, or running guest:

```sh
g++ -std=c++17 -Wall -Wextra -Werror \
  verilator/tests/cpu_dispatch_observer_test.cpp -o /tmp/q800-dispatch-test
/tmp/q800-dispatch-test
g++ -std=c++17 -Wall -Wextra -Werror \
  verilator/tests/sim_control_test.cpp -o /tmp/q800-control-test
/tmp/q800-control-test
```

The full simulator integration test catches missing model wiring that parser
unit tests cannot see. After building `verilator/obj_dir/Vemu`, run:

```sh
python3 scripts/cpu/test_profile_integration.py
```

It boots a tiny synthetic ROM, injects real key down/up events, checks a
20,002-clock profile bracket, requests `quit` before the cycle limit, and
requires a flushed timing-observer summary. No guest disk is opened.

The dispatch test covers reset, stalls, consecutive opcode loads with identical
PC/state, disabled consumers, and profile start/stop boundaries. It tests
opcode-load observation; it does not claim every folded branch generates an
opcode event. The control test covers bounded parsing, clock-based pacing,
reset/screenshot pauses, FIFO reconnect, and append-only command files.

For the register-pipeline differential experiment, run
`python3 scripts/cpu/pipeline_prototype.py`. For immutable Speedometer wrapper
signatures and timer observations, see
`scripts/fixtures/speedometer_timing_observer/README.md`.
