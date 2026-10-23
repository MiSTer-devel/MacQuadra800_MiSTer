# Completed experiments 21–23

| Candidate | ALMs | CPU setup (ns) | CPU TNS (ns) | Minimum hold (ns) |
|---|---:|---:|---:|---:|
| 21 seed38 | 34,098 | -1.399 | -256.139 | -0.073 |
| 21 seed19 | 34,095 | -1.556 | -167.011 | +0.215 |
| 22 seed38 | 33,599 | -1.793 | -382.444 | +0.188 |
| 22 seed19 | 33,645 | -1.712 | -164.944 | +0.242 |
| 23 pre-read seed38 | 34,116 | -2.030 | -333.730 | -0.107 |
| 23 small seed38 | 33,757 | -2.089 | -355.869 | +0.133 |

None closes timing; none was deployed. Experiment21 seed19 also misses HDMI setup by 0.009ns. All other non-CPU setup domains pass in these fits. The extra register-file read port costs 5,120 MLAB bits and did not yield a global timing win. Word-index scaling also did not improve global timing. Preserve these as experiments, not release changes.

Experiment22 both seeds and experiment23 pre-read are limited by FRESTORE frame-header decoding through the FPU exception vector into WB exception-address selection. Experiment23 small is limited by AG register forwarding into the scaled index, with WB exception-address paths close behind. Experiment24 tests removing the exception-vector dependency from the address selection without adding a stage.

Full original reports and bitstreams are preserved in local scratch and their isolated build directories. Committed reports include artifact hashes and source manifests. Hardware qualification remains on experiment12; no newer candidate has been tested on the MiSTer.
