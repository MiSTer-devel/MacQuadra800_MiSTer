# CPU66 timing experiment 5: simplify the integer funnel

The normal fourth fit is 33,098 ALMs, with CPU slack −1.879 ns. Its worst path runs from EX operand B through the integer shift/rotate funnel into the registered slow result. The cache-tag and redirect control paths now pass.

This candidate uses a single arithmetic right funnel instead of selecting arithmetic versus logical shifted results. Logical-shift inputs have a zero sign bit. ROX can place X in that bit, but no consumed result or carry bit reaches beyond bit 65, so arithmetic fill cannot change an observed output. ASR, rotations and left shifts also use the unmasked operand when constructing the funnel input: ASR explicitly extends at the size, rotates construct their period, and left shifts cannot bring higher bits into the low operand size. LSR retains its pre-mask. Final size merging and flags remain unchanged.

No register or pipeline cycle is added. The [differential bench](perf/cpu66_20261022/timing5/funnel/README.md) passes **1,048,576 vectors** against the original ALU. The full 185 CPU cases and four adapter tests pass, and all 185 CPU cycle counts match experiment 2. [Validation](perf/cpu66_20261022/timing5/validation.json).

Clocks remain 66/33/99 MHz, seed 38 and the normal balanced synthesis recipe. The speed-synthesis comparison is not carried forward. Fitted area and timing are pending; this RBF is not hardware qualified.
