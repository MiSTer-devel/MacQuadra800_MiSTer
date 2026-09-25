# Amiga test floppies — debugging context (68040 port)

Everything learned bringing the 68030 originals up under FS-UAE
(2026-06-12) in the MacIIvi project, still current for this 68040 port
except where noted,
written down so the next wedge — on the Minimig DUT, a real Amiga, or
an emulator — starts from knowledge instead of archaeology.
(The design doc AMIGA_TESTBENCH.md lives in the MacIIvi repo.)

## 1. The boot chain, stage by stage

```
Kickstart strap                 validates bootblock 'DOS'+checksum, calls it
  └─ bootblock.s @ disk 0x0     entered at offset 12, A1=trackdisk IOStdReq,
       │                        A6=ExecBase; PC-relative code only
       ├─ AllocAbs($80000)      fail -> screen color-flash loop forever
       ├─ CMD_READ payload      disk 0x400 -> chip $80000 (PAYLLEN! slot)
       ├─ [marker slot 0]       writes its own header to disk 0xD8000
       └─ CacheClearU + jmp $80000
  └─ payload_entry_amiga.s
       ├─ stash A1/A6           g_amiga_ioreq / g_amiga_execbase
       ├─ [marker slot 1]       payload first 512 bytes -> disk 0xD8200
       ├─ SuperState()          supervisor on our task; SR=$2700
       ├─ custom-chip takeover  INTENA/INTREQ/DMACON cleared (INTENAR saved),
       │                        copper list + 1 hires bitplane, COLOR00/01
       └─ amiga_gate()
            ├─ install_vbr()    MUST be first bracketed-I/O prerequisite (§3)
            ├─ [slot 2 'GAT0']  proves the OS I/O bracket works
            ├─ [slot 4 'ATN'+AttnFlags]
            ├─ AttnFlags 68040? no -> painted refusal, halt (+FPU/MMU per disk)
            ├─ [slot 5 'VBRI']
            ├─ MOVEC TC probe   (mmu disks) under recovery; vec!=0 -> refusal
            ├─ [slot 6 'VEC'+vec]
            └─ [slot 3 'GATE']  gate passed
       └─ bench_main()          shared runner; first output = reloc header
                                committed to results @ 0x78000
```

## 2. Diagnostic marker slots (your first stop on any wedge)

512-byte sectors at the tail of the results region. Read them with:

```
python3 - <<'PY'
d = open('run.adf','rb').read()
for s,n in enumerate(['boot','entry','GAT0','GATE','ATTN','VBRI','VEC']):
    b = d[0xD8000+s*0x200:0xD8000+s*0x200+4]
    print(s, n, 'EMPTY' if b==bytes(4) else b.hex())
PY
```

| last marker present | the failure is in |
|---|---|
| none | bootblock never ran (checksum? strap?) or AllocAbs failed (screen flashes colors) or ADF writes diverted (FS-UAE overlay — see §5) |
| `boot` (slot 0) | payload entry: bad PAYLLEN read, cache not cleared, entry crash |
| `entry` (slot 1) | SuperState/takeover/display init, or `install_vbr` ordering (§3) |
| `GAT0` (2) | AttnFlags read — non-68040 machine refusal paints on screen |
| `ATTN` (4) | between flags check and probe: `install_vbr` internals |
| `VBRI` (5) | the MOVEC TC probe wedged harder than recovery could catch |
| `VEC` (6) with vec≠0 | gate refused: no working MMU (68EC040, or an RTL core without the MMU register file; vec is in the marker's low byte) |
| `GATE` (3), no results | bench startup: mmu_save / jw header commit |
| results header only | first test wedged — the on-screen test index names it |

Tags: `ATN`+AttnFlags word (e.g. `4154ce37` → flags `0xCE37`), `VEC`+
vector byte (`56454300` → vec 0 = probe ok).

## 3. The two AmigaOS landmines (both cost hours; both are fixed in code)

1. **exec reaches supervisor mode by deliberately faulting.**
   `Supervisor()` / `SuperState()` execute a privileged op from user
   mode and let the exception happen. Consequence: while OUR vector
   table is live, ANY exec call that crosses the user/supervisor
   boundary lands in a recovery stub → longjmp through a stale resume
   context → **zombie execution** (see §4 for its signature). Fix
   (recovery.s): the OS bracket swaps the **entire VBR** to the OS
   original around every `DoIO` — `use_os_vbr()` / `use_recovery_vbr()`.
   Restoring only the TRAP vectors (first attempt) is NOT enough.
2. **VBR lifecycle ordering.** `use_recovery_vbr()` must never engage
   before `install_vbr()` populated the table (1 KB of zero vectors =
   jump-to-0 on the next interrupt), and `install_vbr()` must be
   idempotent — a second call would snapshot our own stubbed table as
   the "OS original" and poison the bracket. Both enforced via
   `g_vbr_ready`; `amiga_gate()` calls `install_vbr()` before any
   bracketed I/O. If you reorder gate/entry code, preserve that.

## 4. Recognizing zombie execution

Symptoms we observed when a stale longjmp let the machine "continue":
PC free-running linearly through empty space (executing open-bus/
pattern bytes), SSP either stable-garbage or descending fast (fault
spiral), and — nastiest — **garbage written into the results region**
(hundreds of KB of spaces/junk) because the zombie re-entered the
writer with corrupted state. If the results region contains big junk
instead of JSONL: suspect a stale-context longjmp first; check which
vector got stolen vs what the OS needed.

## 5. FS-UAE specifics

- `--writable_floppy_images=1` or all writes silently go to an overlay
  (`~/Documents/FS-UAE/Save States/.../*.sdf`) and the ADF stays clean.
  If markers are EMPTY but the run "worked", look for an `.sdf`.
- Headless works (`--stdout`, no X needed; Mesa offscreen GL).
  Terminate with SIGINT (`timeout --signal=INT N fs-uae ...`).
- Use `--amiga-model=A4000/040` + `kicka4000.rom`; the mmu disks also
  need `--uae_mmu_model=68040` (FS-UAE does not enable 040 MMU
  emulation by default). Kickstarts: raw files accepted (`~/kickstarts/`).
- **Always work on a copy of the ADF** — the run mutates it.
- `--floppy_drive_speed=0` (turbo floppy) cuts run time drastically —
  the writes dominate (one commit per result row).

## 6. Cross-oracle divergences from the 68030 campaign (historic; the
68040 suite's equivalents are the score_vs_oracle.py classes)

FS-UAE (WinUAE core) vs MAME, both KS-independent CPU-model issues;
real silicon (A3000 / LC II) is the referee:

| Row class | MAME | FS-UAE | PRM says |
|---|---|---|---|
| PTEST full walk, 3 levels | PSR `N=3` | `I\|N=2`, desc-addr = level-B | walk completes |
| PTEST WP / invalid descriptor | `W\|N` / `I\|N` | `I\|N=2` both | per-flag |
| PTEST root-limit violation | `I\|N=1` (no L) | limit ignored (`0x1`) | L set |
| PTEST through enabled TT0 | `T` | no T bit | T set |
| PMOVE TC bad geometry (E=1) | vector 56 (MMU config) | **vector 11 (F-line)** | vector 56 |
| MOVEC CACR all-ones readback | `$FF13` | `$3313` | `$3313` expected (bits 14-15 absent; CD/CED self-clear) |
| RTM | silent no-op (decode-table bug) | vector 4 | vector 4 |

For the 68040 suite, score any Amiga run against the Quadra 800
hardware captures with `gen/score_vs_oracle.py` — its classified
divergence classes are the current version of this table.

## 7. Layout constants (single source of truth)

| What | Value | Where defined |
|---|---|---|
| payload load address | chip `$80000` | `payload_amiga.ld`, `bootblock.s` |
| payload on disk | `0x400` | `bootblock.s` PAYLOAD_DOFF |
| results region | `0x78000`, 409600 bytes | `payload_entry_amiga.s` g_results_* |
| marker slots | `0xD8000 + slot*0x200` | `jsonl_trackdisk.c` amiga_diag_marker |
| framebuffer | payload .bss, 480×80 B | `payload_entry_amiga.s` |
| MMU identity window | 256 KB from `$80000` (`MMU_PAYLOAD_WINDOW_BASE`) | `mmu_bench_main.c` |

Keep payload+bss inside the 256 KB identity window from `$80000`.
