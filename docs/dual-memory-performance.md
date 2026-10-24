# Dual issue memory-performance experiment

Branch `pipelined-040-dual-memory` starts at checkpoint `43a5280`, tagged
`pipelined-040-dual-checkpoint-20261023`. The tagged source, both tested RBFs,
Mac results and real-Quadra comparison remain preserved. This experiment
keeps CPU/bus/SDRAM at 33/33/99 MHz for the first fit. No DDR/VRAM storage,
resolution, CPU issue-class, FPU-option or cache-size change is included.

## First port: non-faulting VRAM stores

The earlier CPU could acknowledge a safe VRAM store before it completed
downstream. The new CPU instead routes every cache-inhibited store through
its general memory engine and waits for bus completion before retirement.
The platform itself already retains the fast RAM/VRAM write paths.

An external write queue was tried first. It passes the extended adapter
workload, but with the platform's next-clock write response its 32-store
loop takes the same 343 bus clocks as the unbuffered control (and the
whole workload takes three more clocks). It adds queue registers without
a demonstrated gain in that model. It is therefore removed from the
active RTL. The [prototype snapshot](perf/dual_memory_20261023/comparison-prototypes.patch)
can reproduce both prototypes from checkpoint43a5280; select
STORE_BUFFER=1,VRAM_POST=0 for the rejected external queue. Its logs and
unbuffered control are under queue-prototype.

The retained candidate ports the retirement policy into the new DMU.
PA_VRAM_POST defaults off in the CPU and is enabled by the Quadra wrapper.
An ordinary store can complete at WB after its translation and protection
checks pass, provided it targets the on-chip physical VRAM window, is
cache-inhibited, has no active cache hit requiring writeback/invalidation,
is not locked/RMW or MOVE16, and fits in one 32-bit bus word. The existing
bus-engine registers capture its address/data. No new write FIFO or wide
data register is added. The engine remains occupied until bus completion;
subsequent uncached reads, device accesses and cache maintenance wait.
Cached independent computation can proceed. The physical-I/O serialization
rule remains enabled. This policy depends on the current non-faulting
on-chip VRAM implementation and must be reconsidered for a DDR-VRAM port.

## Validation

The extended adapter workload checks RAM/cache fills, byte/word VRAM
writes and readback, a device write observing prior pixel stores, locked
CAS, accesses crossing bus words, an interrupt storm during VRAM writes,
and CPUSHA immediately after a posted store. Each enabled run witnesses
69 fast VRAM stores and a real locked write. Both CPU clock ratios run
with delayed, mixed-fast and next-clock-platform write responses.
Unmodified behavior is compared with CPU040_VRAM_POST=0.

Commands, from verilator/:

```sh
make tb_quadra_cpu040 CPU040_TAG=_vram_post
make tb_quadra_cpu040_2x CPU040_TAG=_vram_post
make tb_quadra_cpu040 CPU040_VRAM_POST=0 CPU040_TAG=_control
make tb_quadra_cpu040_2x CPU040_VRAM_POST=0 CPU040_TAG=_control
make tb_store_buffer
```

The older queue unit test assumed two slots although its RTL already had
four. That fixture fails with nine errors on the unchanged checkpoint too.
It now fills all four slots and backpressures the fifth; both the old and
current module pass the corrected fixture. Failures/timeouts now return a
nonzero status. This does not change the queue's RTL or put it in the new
CPU's hardware path.

The general 225-case CPU regression runs from an isolated copy so its
generator cannot modify the pinned FPGA build inputs. Its default
PA_VRAM_POST=0 covers unchanged upstream behavior; the adapter cases
exercise the newly enabled platform feature. FPGA area/timing and hardware
performance are still pending; synthetic loop gains are not Speedometer
results or a release qualification.
