# CPU66 timing experiment 16: direct signed FMOVEM byte counts

Experiment14's worst path takes a late memory operand through the dynamic FMOVEM list count, multiplication by12, direction selection and forwarding. Each four-bit half of the list contributes only0,12,24,36 or48 bytes. This candidate maps each half directly to its signed contribution, then sums two seven-bit signed values into eight bits and sign-extends the result. This removes the serial count/multiply/wide-negation chain without adding any state.

Both static and dynamic LIST helpers use this calculation. The interface's unsigned byte count uses the same nibble mapping with a positive direction. A simulation-only independent arithmetic check exhausts **256 masks × eight addressing modes =2,048 cases**, comparing static, dynamic and unsigned results against12 times the original population count. A separate clocked observer compares the active list-byte output against the old arithmetic. The full FPU-result observer remains active.

All **185 CPU cases and four bus adapters pass**, with exact cycle counts matching experiment14. [Validation](perf/cpu66_20261022/timing16/validation.json). No new register, bank, cycle, queue entry or timing exception is added. Experiment15's combined AG change remains excluded.

66/33/99MHz, seed38 and stamp261022 remain fixed for the controlled comparison. The production recipe remains balanced. Separate pinned directories compare balanced synthesis with the [single-setting speed recipe](perf/cpu66_20261022/timing16/speed-recipe.patch), using the identical RTL. Results must include actual area, all setup/hold and related-clock checks before choosing either variant.

Both fits completed; neither closes timing. Balanced uses **33,153 ALMs**, CPU setup **−2.355 ns / TNS −435.502 ns**, SDRAM +0.952 ns, bus +1.000 ns, HDMI −0.101 ns, minimum hold +0.145 ns. Speed uses **33,238 ALMs**, CPU **−1.883 ns / TNS −356.189 ns**, SDRAM +0.573 ns, bus +0.850 ns, HDMI +0.458 ns, minimum hold +0.088 ns. Reports and artifact hashes: [balanced](perf/cpu66_20261022/timing16/fit/artifact.json), [speed](perf/cpu66_20261022/timing16/fit-speed/artifact.json). Neither was deployed.

The balanced worst path is instruction word queue → decoder consume → queue count arithmetic and shift/append selection → queue demand flag (11 logic levels). Speed's worst path is EX exception classification → FPU exception selection → branch decision → early redirect → return-stack restore valid (11 levels, 78% routing). The previously dominant FMOVEM result path is no longer the global worst. The working A/UX-qualified experiment12 remains the preserved hardware checkpoint.

Deferred follow-up agreed with the user: after completing the 66/33/99 MHz work, investigate DDR-backed VRAM for increased capacity. No VRAM, DDR, monitor or display-mode changes are part of this timing work.
