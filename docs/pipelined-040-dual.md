# Ranzbak dual issue Quadra experiment

The new `pipelined-040-dual` branch preserves the saved CPU66 checkpoint
and replaces its CPU RTL with apolkosnik's current `faster` branch,
`eed15a0c7553d4bf220d2f9c164077d76ea69cb6`. This includes Ranzbak's
[faster-dual](https://github.com/ranzbak/AP68040/tree/fcb326be1d60d400ba4873fb68446a985429ec51)
work and newer [Minimig fixes](https://github.com/apolkosnik/AP68040/tree/eed15a0c7553d4bf220d2f9c164077d76ea69cb6).
The NeXT branch is still the older source we previously imported.

The measured baseline uses upstream's register/address-register dual
issue and BTB target-word cache, with 8 KB instruction and data caches.
Second-slot loads are disabled, matching upstream's latest hardware
default: intermittent bad load data corrupted Minimig disk contents with
that class enabled despite passing simulations. No original disk images
will be used as writable test media.

[Integration provenance](../rtl/ap68040_faster/UPSTREAM_QUADRA.md) lists
the local patches and retained bug fixes. In particular, the new faster
branch lacks two fixes already present in our old port; both are reapplied.
No old CPU66 timing optimization or DDR-VRAM change is included.

The working branch defaults to CPU/bus 33 MHz, SDRAM 99 MHz. The existing
CPU_AP68040_2X adapter selects the separate 66/33/99 MHz comparison. Each
fit pins its inputs and keeps a separate Quartus database. Mac hardware
qualification and Speedometer were run at 33 MHz first, then 66 MHz.

Initial tag-RAM checks pass (8,192 cycles, 4,065 writes and 1,064
same-address collisions). All four Quadra adapter cases pass: 1x normal
34,851 cycles / 2,392 beats, 1x fast 33,707 / 2,389; 2x normal 28,311 /
2,357, 2x fast 27,320 / 2,355. These directed workload cycle counts are
not Speedometer performance measurements. The expanded CPU regression passes 225 cases: 45 programs under five bus
configurations. The original new PIO diagnostic failed test 2 in all five
configurations; an unmodified upstream control reproduced the same failure.
Its claimed noncacheable device mapping was absent. The corrected fixture
identity-maps RAM and marks only page F serialized/noncacheable, retaining a
cacheable destination buffer; all five cases pass. The original failure,
control, corrected results and exact upstream/local RTL patch are preserved
under [measurements](perf/dual_20261023).

Removing only the Quadra load-capture fix makes adapter test 11 fail again;
the retained fix passes. The t_ld1 event report also confirms actual paired
retirements with the chosen hardware parameters. Final fitting and
hardware results follow below.

## What changes in the CPU

The companion slot handles independent one-word integer operations (move,
add/subtract, compare, bitwise operations, clear/negate, extend and swap),
plus supported address-register moves and quick arithmetic. Pairing checks
register dependencies; both slots move through the backend together and
the younger slot commits only when the older instruction commits without
a redirect. Trace mode issues instructions individually. Complex
microcoded and floating-point operations still run alone. This is a
limited second integer slot, rather than a second complete memory/FPU
pipeline. Its sixth RF read port and third backend write port increase
the replicated MLAB bank count from 25 to 36.

BTIC caches two words at a predicted branch target, allowing fetch to
supply them while the instruction-cache lookup catches up. Its valid
state and target tags must survive neither invalidation nor discarded
refetches; the newer D1 hold fix addresses a stale-BTB livelock. The cache
set count grows from 64 to 128, yielding 8 KB per I/D cache. The byte
enable and tag templates remain explicit for Quartus 17 inference. Both
final fits use 497 of 553 M10Ks; area and timing are recorded below.

The upstream README's published out-of-context numbers describe the
earlier scalar core, and the dual-issue design notes report Xilinx LUTs
and slices. Neither establishes the quoted approximately26k ALM result
for a complete Quadra build. The comparison here keeps our peripherals,
VRAM, bus adapter and default feature selection, and reports whole-core
ALMs as well as actual Mac benchmark results.

## Initial synthesis rejection

Both first analysis/synthesis runs stopped at the RF inference guard:
30 MLAB banks were present instead of the required 36. The backend's
third write bank disappeared and Quartus reports uq0s.v, uq1s.v, ex_s.v
and wb_s.v tied low. This would silently remove actual paired issue on
hardware despite passing RTL simulations. No fit or hardware test used
these netlists.

Separately, synthesis reported 102,891/102,895 total registers and an
estimated78,207 ALMs: the two framework OSD buffers (32,768 data bits
each) and MT32 LCD buffer (8,192 data bits) mapped into registers. CPU
cache slices, tag RAMs, predecoder ROM and BTIC word RAMs did infer as
block RAM. The compiler probe and mapping investigation precede any
replacement fit.

The isolated [compiler reproduction](perf/dual_20261023/compiler-probe)
shows s0_ok's registered output stuck at zero when it reads first/last
through its structure argument, while a direct first/last expression
remains dynamic. Passing those same two bits as explicit scalar arguments
retains a dynamic predicate. The integration applies this representation
change to the pairing function and its diagnostic caller. Separately,
explicit M10K attributes on the two OSD buffers and MT32 LCD buffer replace
automatic resource selection. The next A&S must verify those memories,
36 RF MLAB banks, and nonconstant companion-valid state before fitting.
No VRAM storage or guest-visible pipeline behavior is changed.

All225 CPU cases pass again after the predicate representation change,
with identical cycle counts in every case. Both1x and2x adapter variants
also retain identical cycles and beat counts under normal and fast
acknowledgements. The exact R2 inputs and mapping checks are pinned before
restarting full synthesis.

## Compiler RAM-budget comparison

After the pairing fix, R2 preserves all36 RF banks and nonconstant
companion-valid state. Its forced OSD/LCD memories infer correctly, but
the automatic RAM-budget heuristic instead puts both scaler polyphase
coefficient memories (10,240 bits each) into registers. The 33 MHz fitter
reports needing4,429 LABs where the device provides4,191.

R3 keeps every RTL file identical and disables
SYNTH_RESOURCE_AWARE_INFERENCE_FOR_BLOCK_RAM in its isolated QSF. This
setting name was obtained from the installed17.0 project API. The
[Standard Edition guide](https://docs.altera.com/r/docs/683283/18.1/design-compilation-user-guide-quartus-prime-standard-edition/resource-aware-ram-rom-and-shift-register-inference?contentId=qyeeXMpVNhjBnX13_IsAxQ)
describes this budget-driven RAM-to-logic fallback; the actual fit still
must verify physical RAM availability.

The 33 MHz R3 synthesis has29,315 registers and3,722,339 block-memory bits,
compared with49,811 registers and3,701,859 bits in R2. The20,496-register reduction closely matches the20,480 coefficient
memory bits restored to RAM. This is a compiler mapping comparison;
CPU behavior, clocks and video architecture are unchanged. A matching
66 MHz R3 build is pinned separately. Main's recipe is frozen while the
isolated flows run.

## First timing-passing33 MHz result

R3 seed38 fits successfully at34,643ALMs (82.66%),29,927registers,
497/553M10Ks and38DSPs. All setup and hold checks pass: CPU/bus+1.374ns,
SDRAM+0.099ns,HDMI+0.407ns andminimumhold+0.167ns. All8 additional path
reports are preserved under33mhz/r3/fit-s38. The exact experimental RBF
is preserved under test-builds/pipelined-040-dual-20261023/33mhz before
hardware qualification; MD5467a90ca4793e68cf39981a7fea9f8ea.

The whole-core area exceeds the minimal33MHz checkpoint by1,443ALMs
(4.35% relative). The quoted26kALM context was not established by this
measurement. The matching 66 MHz result is recorded in the final comparison below.

## 33 MHz hardware qualification

The exact timing-passing RBF boots Mac OS8.1 on`.192` with32 MB and
Ethernet Off using the separately copied and readback-verified Mac image.
Finder, keyboard/mouse input and the menu-bar clock pass. Speedometer4.02
finishes Mix **1.800** and full Performance Rating **1.569**: CPU1.806,
graphics0.937,disk2.269,math13.309,all one iteration. Compared with the
minimal branch's Mix1.611, this single-run result is11.7% higher for4.35%
more whole-core ALMs. Disk results remain sensitive to host/storage load.

After the tests, Speedometer was quit without saving, Finder Shut Down
was selected with a verified continuous mouse gesture, and the safe-to-
switch-off screen was observed. The source recipe now matches this exact
candidate at19d9fc3; all190 build-source files were checked, with identical
active QSF assignments. [Evidence](perf/dual_20261023/33mhz/mac/result.json).
A/UX and CD audio are not qualified on this new CPU.

## 66 MHz result and comparison

R3 seed 38 fits at **35,346 ALMs (84.34%)**, 31,088 registers,
497/553 M10Ks and 38 DSPs. CPU setup fails at **−3.308 ns** with
TNS −2114.552 ns; CPU Fmax is 54.17 MHz. SDRAM +0.335 ns,
machine bus +1.040 ns, HDMI +0.269 ns and minimum hold +0.180 ns pass.
This is **1.769 ns worse** than the previously tested timing24-small
CPU slack of −1.539 ns, while using 2,018 more ALMs (6.1%).

The exact 66 MHz RBF (MD5 `45308760ed233a198ecdcbcd613836ef`) boots Mac OS 8.1
with the same disposable image and baseline PRAM as 33 MHz. Finder,
keyboard/mouse and clock advance pass. Speedometer completes Mix **3.614**
and full PR **2.667**: CPU 3.637, graphics 1.579, disk 2.807, math 26.824,
all one iteration. The Mix gain over timing24-small is **14.4%**;
overall PR gains 10.2%. [Full comparison, including the real Quadra and
previous runs](dual-speedometer-comparison.md).

The [path analysis](perf/dual_20261023/66mhz/r3/path-analysis.json)
identifies a different bottleneck from the previous scalar timing stack:
76 of the worst 100 paths end in the D1 attribute-ROM address; six involve
MMU translation/cache-hit logic. The worst path has 14 levels and 18.416 ns
data delay, 57% routing. These are the next optimization targets; no new
CPU optimization is included in this checkpoint. A/UX and CD audio remain
unqualified, and 66 MHz is not timing-closed.

Speedometer was quit without saving, Finder Shut Down was selected with
a verified continuous gesture, and the explicit safe-to-switch-off screen
was visually confirmed. [66 MHz hardware evidence](perf/dual_20261023/66mhz/mac/result.json).
The board was then returned to Menu, clean test settings saved, and the
original S0/PRAM restored with S2/CFG absences preserved.
