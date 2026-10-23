# CPU66 timing experiment30: measure compiler retiming cost

The retained24-small source is now checked into the working branch and byte-verified against the exact hardware-tested RBF. Experiment29 removed35 mapped registers, yet its final placement grew370 ALMs and regressed CPU timing. Fitter reports classify1,901 nodes as physical retimed registers in24-small and3,027 in29-small;207/208 are in the FPU's dout output family. These are counts of transformed nodes, not net extra flip-flops.

Two compiler-only comparisons start from the same retained24-small CPU:

- **global-off:** only PHYSICAL_SYNTHESIS_REGISTER_RETIMING changes from ON to OFF. All26 CPU source/data files remain byte-identical.
- **dout:** the global recipe stays unchanged and only the existing96-bit FPU dout register gets the dont_retime attribute. Removing that attribute restores the exact original source text; no behavior, state or cycle changes. The fit report must establish whether this directive also prevents the observed physical retiming on the installed17.0 flow. An ignored or ineffective directive is not a successful comparison.

The attribute syntax and synthesis scope are documented in the [Standard Edition compilation guide](https://www.intel.com/programmable/technical-pdfs/683283.pdf), section3.4.20, and the older [Quartus13.1 handbook](https://cdrdv2-public.intel.com/653796/quartusii_handbook_archive_131.pdf), section16, page16–46. The newer Pro/Hyper-Retimer behavior is not assumed to describe CycloneV/17.0. Final reports must measure what this installed compiler actually did.

The prior185 CPU cases, four adapters and Mac/AUX checks apply to the unchanged executable logic. Repeating those simulations would not test a compiler-only mapping change. Analysis/synthesis, RAM inference, final area, all setup/hold/crossing paths and actual retimed-node counts are the relevant first checks; any useful RBF still needs hardware qualification. Both fits retain66/33/99MHz, balanced seed38, duplication OFF, stamp261023 and five RF ports. No timing exception is added and no VRAM change is included. Main RTL and recipe remain unchanged while the isolated variants are measured.
