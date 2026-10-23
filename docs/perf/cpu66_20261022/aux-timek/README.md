# A/UX 66 MHz calibration overflow

The live retirement PCs from the original 66 MHz failed boot identify `/unix`'s `SetUpTimeK`, specifically the first delay-loop calibration at `0x55d14`–`0x55d64`. The kernel came from the user's new 1 GB A/UX archive. Its `pstart` section is mapped at `0x54000`, so these are exact symbol addresses, not a guessed relocation.

The routine doubles a **16-bit** trial count from `0x1000` until a bare `dbra d0,*` takes at least `0x492` VIA ticks. Its largest nonzero doubled count is `0x8000`; the next doubling wraps to zero. The pipelined CPU currently executes a warm bare DBcc about every two CPU clocks. At 33 MHz, that maximum exceeds the required interval. At 66 MHz it falls short, wraps to zero, and keeps retrying tiny loops forever. The branch predictor is not required for this failure (`LOOP_PRED=0`).

A focused simulation runs the **exact extracted guest bytes**, through `quadra_cpu040` and the production `via6522` with the machine's E-clock ratio of 42 bus clocks per timer tick. No approximate timer or rewritten calibration algorithm is used. Only the CPU's existing `dbcc_floor` input is exposed as a test control in a generated wrapper copy.

| CPU/bus | DBcc minimum | Result |
|---|---:|---|
| 33/33 MHz | 0 (existing) | Returns; calibration values 16415 / 781 |
| 66/33 MHz | 0 (existing) | Counter wraps to zero; still at `0x55d14` after 1,000,000 bus clocks |
| 66/33 MHz | 4 CPU clocks | Returns; calibration values 16415 / 781 |

The four-clock minimum is already implemented and covered by `t_dbccfloor` in the CPU. It applies only to DBcc following a taken DBcc; it does not throttle other instruction classes. Applying that existing input to the 2× integration is the proposed compatibility fix. A further [185 CPU cases and four adapter tests](floor4-regression/validation.json) pass with the proposed setting (the 1× adapter remains at floor zero). Full A/UX hardware boot/shutdown and the resulting fit remain required; this isolated reproduction does not qualify the whole guest or prove that every hardware problem is resolved.

Reproduce from an unmounted raw copy of the user's image:

```sh
python3 docs/perf/cpu66_20261022/aux-timek/reproduce.py \
  --image /path/to/AUX_3_1_1GB.dsk \
  --out scratch/aux-timek-repro
```

The image is opened read-only. The script searches valid UFS superblocks rather than mistaking the preceding Eschatology slice for the root. It verifies the extracted routine's hash, writes generated binaries only under `--out`, and checks all three outcomes. Vasm and Verilator must be on PATH. The kernel and extracted guest binary remain local artifacts and are not included here. [Source hashes](source.json) and the three logs record this run.
