# CPU66 timing experiment27: select FP odd-target addresses with the BSUN predicate

Experiment24-small's worst path still runs from FPU dispatch go through vector selection, the backend exception record and its zero test into WB exception-address selection (-1.539ns,11 levels). FP branches only have BSUN to prioritize ahead of their odd-target address error. Their target is the decoded target; the microcode only emits conditional FP branches.

The FPU interface exposes the existing BSUN predicate directly (signaling predicate, unordered CC, BSUN enabled). After the original vector/SSW priority chain, the backend independently overrides the FP address using that predicate and its existing odd-target check. Instruction-fetch and operand faults retain their higher priority. The exception-vector, frame, commit and side-effect logic is unchanged. The existing FPU xaddr still supplies every other FP address.

This is24-small plus the preserved backend/interface patch. No register, stage, cycle or timing exception is added. The original full WB-address model still matches on every initialized clock. Additional assertions verify that every advancing odd FP branch has the original zero-vector/BSUN relation and uses the decoded target.

All185 CPU cases and four adapters pass with exact24-small cycles. Five signaling-true odd-target BSUN runs retain BSUN priority. A second extended exception test checks taken FBT and FDBF odd targets (format2 address and PC, suppressed FDBcc counter write), plus untaken FBF/FDBT odd targets. All five bus configurations pass on both24-small and27 with exact cycle counts. [Validation and sources](perf/cpu66_20261022/timing27/validation.json).

The fit retains five RF ports,66/33/99MHz, balanced seed38, duplication OFF and stamp261023. Source will be byte-verified and all tag/RF RAM inference guarded before fitting. No fitted benefit, timing closure or hardware qualification is claimed before measurement. No VRAM change is included.

## Completed fit: not retained

33,510ALMs, CPU setup -1.814ns/TNS -350.927ns, SDRAM -0.122ns (fails), bus +0.774ns, HDMI +0.548ns and minimum hold +0.193ns. Worst CPU path now runs fromEX load data into fe_flush (-1.814ns), followed by the slow ALU result (-1.794ns), FIFO head/index input (-1.569ns) and WB exception address (-1.493ns). The targeted address path moves out of the worst slot but global timing and area regress relative to24-small. No hardware trial or main-source application.
