# CPU66 timing experiment 16: direct signed FMOVEM byte counts

Experiment14's worst path takes a late memory operand through the dynamic FMOVEM list count, multiplication by12, direction selection and forwarding. Each four-bit half of the list contributes only0,12,24,36 or48 bytes. This candidate maps each half directly to its signed contribution, then sums two seven-bit signed values into eight bits and sign-extends the result. This removes the serial count/multiply/wide-negation chain without adding any state.

Both static and dynamic LIST helpers use this calculation. The interface's unsigned byte count uses the same nibble mapping with a positive direction. A simulation-only independent arithmetic check exhausts **256 masks × eight addressing modes =2,048 cases**, comparing static, dynamic and unsigned results against12 times the original population count. A separate clocked observer compares the active list-byte output against the old arithmetic. The full FPU-result observer remains active.

All **185 CPU cases and four bus adapters pass**, with exact cycle counts matching experiment14. [Validation](perf/cpu66_20261022/timing16/validation.json). No new register, bank, cycle, queue entry or timing exception is added. Experiment15's combined AG change remains excluded.

66/33/99MHz, seed38 and stamp261022 remain fixed for the controlled comparison. The production recipe remains balanced. Separate pinned directories compare balanced synthesis with the [single-setting speed recipe](perf/cpu66_20261022/timing16/speed-recipe.patch), using the identical RTL. Results must include actual area, all setup/hold and related-clock checks before choosing either variant.
