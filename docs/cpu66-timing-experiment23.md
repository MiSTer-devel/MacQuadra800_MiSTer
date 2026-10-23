# CPU66 timing experiment 23: separate word-index sign replication from long scaling

Experiment21 seed38's worst path remains the index register read through front/back selection, forwarding, word sign extension and variable scaling into AG. The last part starts at index bit15 and ends at AG bit31: a word index's sign bit crosses logic for the variable long-word shifter even though the high bits at every supported scale are simply the original sign.

This candidate computes the long shift and the four word-index concatenations separately, then selects word/long and masks a suppressed index. The mathematical result remains `(long ? v : sign_extend(v[15:0])) << scale`, or zero when suppressed. No register or cycle is added. Simulation checks zero, all32 single-bit basis vectors and all-ones across all16 valid/word/scale combinations (544 cases). For fixed metadata this is a bit-wiring transform; the basis patterns exercise each input bit's contribution. All185 CPU cases and four adapters pass for each variant with exact experiment22 cycles. The original consumed-operand observer still checks27,002 pairs in the FPU witness.

Two variants use balanced synthesis, seed38, stamp261023, physical duplication OFF and66/33/99MHz:

- **preread**: experiment22 plus [index-scale.patch](perf/cpu66_20261022/timing23/preread/index-scale.patch), retaining the extra RF read port (30 MLAB arrays). [Validation](perf/cpu66_20261022/timing23/preread/validation.json).
- **small**: experiment20 plus [index-scale.patch](perf/cpu66_20261022/timing23/small/index-scale.patch), which includes the experiment22 EARLY_RES-qualified bypass removal and the new scaling expression, with the original five RF read ports (25 MLAB arrays). [Validation](perf/cpu66_20261022/timing23/small/validation.json).

The comparison measures whether the added read-port copies are still necessary after the scaling simplification. Each composite source is byte-verified against its tested scratch tree; RAM guards require all register-file arrays to remain MLABs and all four tag memories to remain true-dual-port M10Ks. Main RTL remains frozen at experiment20 while these independent copies fit. No fitted benefit, hardware qualification or timing closure is claimed yet. No VRAM/DDR changes are included.
