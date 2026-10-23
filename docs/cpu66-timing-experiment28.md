# CPU66 timing experiment28: read the FDBcc counter from its register word

Experiment27's worst path is EX load data through the memory-operand mux, counter zero test and FPU conditional branch into early redirect/fe_flush (-1.814ns). FDBcc always takes its counter from a data register. The FPU interface already receives that raw register word as bw, independent of the memory selection.

This candidate changes only the FDBcc taken test from bv[15:0]!=0 to bw!=0. The generated microcode contains one FPU DBCC uop with source DY. A new simulation assertion checks both words match on every valid FDBcc cycle, including held cycles. The original gated branch decision and full WB exception-address checks remain. No register, stage, cycle, interface or timing exception is added relative to27; the original five RF read ports remain.

All185 CPU cases and four adapters pass with exact parent cycles. Taken/untaken odd FBT/FDBcc and signaling-true odd-target BSUN tests pass under all five bus configurations with exact parent cycles. The parent27 address-priority change remains to keep the preceding24 WB-address bottleneck covered. Both27 and the other staged-FPU candidates failed globally; this new measured path provides the specific reason for trying another combination, not evidence that they were wins.

Balanced seed38, stamp261023, duplication OFF and66/33/99MHz remain fixed. All26 source/data files will be byte-verified against the tested scratch tree; tag/RF RAM guards precede fitting. Area and all setup/hold/crossing results must decide retention. No hardware qualification or timing improvement is claimed before measurement. A/UX24's failure is being compared separately with the12 reference on a fresh control image. No VRAM change is included.

## Completed fit: not retained

33,445ALMs, CPU setup -1.758ns/TNS -314.670ns, SDRAM +0.334ns, bus +0.950ns, HDMI +0.621ns and minimum hold +0.137ns. The result improves slightly on27's CPU WNS and area, but remains larger and globally worse than24-small. No hardware deployment or main-source application. Full reports and RBF hashes are preserved.
