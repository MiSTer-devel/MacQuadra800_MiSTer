# CPU66 timing experiment29: select memory operands as DC2 enters EX

The measured EX paths include the memory/register operand mux ahead of FDBcc zero tests, the ALU and FPU format checks. The existing EX A/B registers and EX load register capture on the same DC2 advance. Selecting memory data at that edge can place the final operand directly in A/B, removing the mux from the later computation without adding a stage.

This candidate loads dm_ldata into an operand register when its DC2 source is OS_MEM; otherwise it keeps the exact existing register-forwarding/raw-value priority. EX consumes A/B directly, with the same word sign extension. The old ex_ld declaration and assignment remain for the independent simulation reference; with no synthesis-visible consumer they can be pruned. No register, cycle or array is added. Fitted area must confirm the actual saving.

Two simulation-only models retain the complete original A/B capture rules. Every valid EX cycle, including held cycles, compares the new operands against the original raw-register-or-ex_ld expressions. The other raw consumers are also checked: shift count from A, and FPU CHK instruction words from A/B. These consumers use register/immediate operands rather than memory. The slow FPU witness checks90,723 operand pairs. Existing FPU-result, branch and WB-address references remain.

Both variants pass185 CPU cases, four adapters and ten targeted FP odd-target/BSUN cases, with exact parent cycles. Small is24-small plus this backend patch; combined is28 plus the same operand change, retaining the direct FP address priority and FDBcc counter simplification. Both retain five physical RF read ports,66/33/99MHz, balanced seed38, duplication OFF and stamp261023. The combination is measured separately because27 had no global win. No timing exception is added, and no area or timing gain is claimed before fitting. No VRAM change is included.

## Completed fits: not retained

Small: 33,698 ALMs, CPU setup -1.816 ns/TNS -212.891 ns, SDRAM +0.541 ns, bus +1.024 ns, HDMI +0.411 ns and minimum hold +0.203 ns. Combined: 33,921 ALMs, CPU setup -1.929 ns/TNS -495.152 ns, SDRAM +0.494 ns, bus +1.034 ns, HDMI +0.170 ns and minimum hold +0.158 ns.

Synthesis did remove state: small mapped registers fell from24-small's28,430 to28,395, with ALUTs48,565→48,543 and unchanged block memory. But the routed fit grew370 ALMs and regressed timing. Combined also regressed. Neither is retained or deployed. Fitter logs show active physical register retiming, including replicated retimed FPU output registers; synthesis savings alone do not establish a fitted saving.
