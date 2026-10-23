# CPU66 timing experiment 13: remove an overwritten AG operand bypass

Experiment 11's worst path traverses full EX write qualification (including divide overflow, memory faults, raised exceptions and odd targets) into AG's operand mux, then into `dc1_a`. When AG advances, a later nonblocking assignment already forwards the EX value using `exw_fw`. Its condition includes every case accepted by `exw_v`. Thus the earlier full bypass can only contribute when the later assignment overwrites it.

This candidate removes that unused bypass from `opnd`, keeping the later forwarding and its assignment priority unchanged. The front-file write, EX operand capture, exception and retirement qualifications are unchanged. No register, pipeline cycle or timing exception is added. It includes experiment 12's A/UX DBcc setting.

A simulation observer reconstructs the old operands and compares the complete values consumed after the later forwarding assignment; it also checks `exw_v` always implies `exw_fw`. All **185 CPU cases and four adapters pass**, with all 185 CPU cycle counts exactly matching the prior floor-four regression. [Validation](perf/cpu66_20261022/timing13/validation.json).

66/33/99 MHz, seed 38 and balanced synthesis remain fixed. Fit complete: **33,063 ALMs**, CPU setup **-2.509 ns**, CPU TNS **-588.172 ns**. SDRAM +0.596 ns, bus +1.449 ns, HDMI +0.181 ns and minimum hold +0.151 ns pass. [Reports and RBF hashes](perf/cpu66_20261022/timing13/fit/artifact.json). CPU timing still fails.

This is the smallest measured fit (137 ALMs below the frozen minimal 33 MHz core), but its setup and TNS regress significantly. The new worst path is `ag_u.dyn[0]` → dynamic transfer/AG interlock → stall → `agx_q[24]`, 11 levels. The bypass change is not retained in the active RTL; experiment 12 is the current hardware candidate.
