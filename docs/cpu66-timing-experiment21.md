# CPU66 timing experiment 21: read both incoming index registers before head selection

Experiment18 balanced's worst path starts at the micro-op FIFO read pointer (fanout323), selects the incoming index register, reads the front/back files and live-value table, then scales the index into AG. This prototype exposes the two FIFO banks' index addresses and the read pointer as internal CPU wires. It reads both candidate addresses in parallel, selecting the returned value after the register files. A held skid uop still uses its original index address on port1.

The register files grow from five to six physical read ports. Their write ports, live-value tables and all forwarding/selection priority remain unchanged. One extra read per front/back file replicates five32×32 MLAB arrays (5,120 bits total); actual ALM cost must be fitted. No pipeline stage, explicit register bank or timing exception is added. The three internal CPU module interfaces change; the platform CPU bus interface does not.

All185 CPU cases and four adapters pass with exact experiment20 cycle counts. Two independent simulation-only copies of the original five-port files receive the same writes and the original selected-head address; every active incoming index read is compared against their value. The normal FPU witness checks120,770 reads, including62,167 from queue bank1. An additional35 cases with SKID=1 pass (integer/MMU/cache/MOVEM/early-redirect/BTB/FPU under five bus configurations), checking the held-skid selection too. [Validation](perf/cpu66_20261022/timing21/validation.json).

The candidate remains in scratch while experiment20 fits. Source is experiment20 plus [index-read.patch](perf/cpu66_20261022/timing21/index-read.patch), applied with `git apply --unidiff-zero`. Pinned composite archives identify every replaced file and are byte-checked against the tested tree. Balanced fits compare seeds38 and19 at66/33/99MHz, stamp261023, physical register duplication OFF. The alternate seed tests placement sensitivity; retention requires measured area and global timing. No hardware or closure result is claimed yet. No DDR/VRAM changes are included.

## Completed fit results

Both fits completed: seed38 uses34,098 ALMs with CPU setup -1.399ns/TNS -256.139ns and minimum hold -0.073ns; seed19 uses34,095 ALMs with CPU setup -1.556ns/TNS -167.011ns, minimum hold +0.215ns and HDMI setup -0.009ns. Neither closes timing. The added read port has not demonstrated a release-worthy global improvement. Neither was deployed. [Comparison and preserved reports](perf/cpu66_20261022/timing23/results.md).
