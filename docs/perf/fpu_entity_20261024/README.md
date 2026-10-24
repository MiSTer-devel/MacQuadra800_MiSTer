# FPU and CPU entity sizes at synthesis, 2026-10-24

Two Analysis & Synthesis-only runs (`bash scripts/build_only.sh --check`,
Quartus 17.0 on misterubuntu, isolated copies `~/mister/q800_check_dual_20261024`
and `~/mister/q800_check_master_20261024`), to answer whether porting the
shipping core's area-compacted FPU into the dual-issue core would save area.

- `dual-entities.txt`: branch `pipelined-040-dual-memory` at `236b8c5` (RTL identical to
  checkpoint `6bfd9c0`): the dual-issue core with VRAM retirement, FPU_PIPE=0.
- `master-entities.txt`: `master` at `011f7d9`: the shipping core (ap040 + the 2026-09 stack).

Synthesis ALUTs are not fitted ALMs (the fitted whole cores are 34,554 and
~39,030 ALMs); compare entities within one run, or the two runs' same entity.

| Entity | Shipping core | Dual-issue core |
|---|---:|---:|
| whole `emu` | 49,587 ALUTs / 16,051 regs / 3.03 Mbit / 21 DSP | 41,556 / 20,261 / 3.36 Mbit / 23 DSP |
| CPU wrapper (`wombat_cpu` / `quadra_cpu040`) | 37,826 / 8,296 / 297 kbit / 13 DSP | 29,778 / 12,562 / 626 kbit / 15 DSP |
| **`ap040_fpu`** | **6,800 ALUTs / 1,387 regs / 9 DSP** | **6,336 ALUTs / 2,249 regs / 12 DSP** (+617 ALUTs / 464 regs in the `ap68040_fpif` wrapper) |
| integer mul/div | 630 / 301 / 3 DSP | 588 / 301 / 3 DSP |
| data/cache side (`ap040_cache`+`ap040_mmu` / `ap68040_dmu`) | 3,418 + 1,585 ALUTs, 297 kbit | 5,253 ALUTs, 76 kbit |
| backend (`ap040_core` own / `ap68040_backend` own) | 22,211 own | 6,592 own |

Conclusion: the dual core's FPU is already 464 ALUTs smaller than the shipping
FPU (it carries 862 more registers and 3 more DSPs); there is no area to gain by
porting the compacted shipping FPU, and a 2 -> 3 steps-per-clock FDIV/FSQRT port
adds a subtract/compare stage, i.e. costs area rather than saving it.
