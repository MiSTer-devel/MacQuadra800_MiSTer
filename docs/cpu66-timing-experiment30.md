# CPU66 timing experiment30: measure compiler retiming cost

The retained24-small source is now checked into the working branch and byte-verified against the exact hardware-tested RBF. Experiment29 removed35 mapped registers, yet its final placement grew370 ALMs and regressed CPU timing. Fitter reports classify1,901 nodes as physical retimed registers in24-small and3,027 in29-small;207/208 are in the FPU's dout output family. These are counts of transformed nodes, not net extra flip-flops.

Two compiler-only comparisons start from the same retained24-small CPU:

- **global-off:** only PHYSICAL_SYNTHESIS_REGISTER_RETIMING changes from ON to OFF. All26 CPU source/data files remain byte-identical.
- **dout:** the global recipe stays unchanged and only the existing96-bit FPU dout register gets the dont_retime attribute. Removing that attribute restores the exact original source text; no behavior, state or cycle changes. The fit report must establish whether this directive also prevents the observed physical retiming on the installed17.0 flow. An ignored or ineffective directive is not a successful comparison.

The attribute syntax and synthesis scope are documented in the [Standard Edition compilation guide](https://www.intel.com/programmable/technical-pdfs/683283.pdf), section3.4.20, and the older [Quartus13.1 handbook](https://cdrdv2-public.intel.com/653796/quartusii_handbook_archive_131.pdf), section16, page16–46. The newer Pro/Hyper-Retimer behavior is not assumed to describe CycloneV/17.0. Final reports must measure what this installed compiler actually did.

The prior185 CPU cases, four adapters and Mac/AUX checks apply to the unchanged executable logic. Repeating those simulations would not test a compiler-only mapping change. Analysis/synthesis, RAM inference, final area, all setup/hold/crossing paths and actual retimed-node counts are the relevant first checks; any useful RBF still needs hardware qualification. Both fits retain66/33/99MHz, balanced seed38, duplication OFF, stamp261023 and five RF ports. No timing exception is added and no VRAM change is included. Main RTL and recipe remain unchanged while the isolated variants are measured.

## Completed comparisons

Both compiler controls took effect, but neither improves the retained checkpoint. All four D-cache tag M10Ks and all 25 register-file MLAB banks passed inference checks; all 18 additional path reports are preserved per fit.

| Configuration | ALMs | Registers | CPU setup / TNS ns | SDRAM setup ns | HDMI setup ns | Minimum hold ns |
|---|---:|---:|---:|---:|---:|---:|
| Retained24-small | 33,328 | 29,992 | -1.539 / -147.124 | +0.339 | +0.347 | +0.165 |
| Global retiming OFF | 33,079 | 29,008 | -1.793 / -341.996 | +0.399 | +0.033 | +0.172 |
| FPU dout dont_retime | 33,351 | 29,916 | -1.696 / -299.476 | -0.052 | +0.331 | +0.113 |

Global OFF produced zero physical-retimed register nodes. The dout directive reduced that output family's retimed-node count from 207 to zero, with 1,696 physical-retimed nodes overall. Thus the directive was effective on this installed flow, but the complete placement regressed. Both builds produced RBFs; their nonzero wrapper exits report timing violations, not synthesis/fit crashes. Neither variant is applied to the working source or tested on hardware.
