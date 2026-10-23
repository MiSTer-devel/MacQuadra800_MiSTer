# CPU66 timing experiment 15: combine the two zero-state bypass removals

This compares experiment 14 with the overwritten AG operand bypass removal from experiment 13. The earlier AG-only fit was smaller but regressed global timing. With the FPU result path shortened independently, this comparison measures whether the combined placement improves either timing or area. No single change is assumed to improve the combined fit.

To leave experiment 14's active inputs frozen, the isolated build uses its exact archived source, overlaid with only `ap68040_backend.sv` and the matching simulation observer from committed experiment 13. The [manifest](perf/cpu66_20261022/timing15/source-manifest.json) pins both full commits, both file hashes and the final archive hash. Every build input comes from those committed sources; no worktree or mutable input is used.

All **185 CPU cases and four adapters pass**, with exact cycle counts matching experiment 14. Both the full old FPU-result observer and the consumed AG-bypass observer run together. [Validation](perf/cpu66_20261022/timing15/validation.json). The combined change adds no registers, banks or cycles.

66/33/99 MHz, seed 38, balanced synthesis and the existing DBcc floor of four CPU clocks at 2× remain fixed. Fit complete: **33,496 ALMs**, CPU setup **-1.919 ns**, CPU TNS **-352.419 ns**. SDRAM +0.732 ns, bus +0.989 ns, HDMI +0.286 ns and minimum hold +0.217 ns pass. [Reports and RBF hashes](perf/cpu66_20261022/timing15/fit/artifact.json). CPU timing still fails; this variant has not been deployed.

The combined fit uses more area and has worse global setup and TNS than either standalone candidate. It is preserved as a measured comparison and is not retained in the active RTL.
