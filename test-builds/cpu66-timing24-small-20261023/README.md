# Experimental CPU66 timing24 small checkpoint

CPU/bus/SDRAM66/33/99MHz, balanced seed38, stamp261023, original five register-file read ports.33,328ALMs (79.52%), CPU setup -1.539ns/TNS -147.124ns. SDRAM +0.339ns, bus +0.672ns, HDMI +0.347ns and minimum hold +0.165ns pass. **CPU timing remains violated; this is not a release.**

The exact source is base `a6cb17af25003b26d15433fa10a86bdeaff1e70e` plus `cpu-source.patch` (`git apply --unidiff-zero`). All26 CPU source/data files were compared; the backend is the only changed file. The patch combines the overwritten-bypass removal, separate word-index scaling and exception-address selection changes. No extra RF port, register, cycle or timing exception is added. The 2× DBcc minimum remains four clocks for A/UX.

The source archive, its parent chain and RBF hashes are pinned in `artifact.json`. Full fit reports and simulation evidence are under `docs/perf/cpu66_20261022/timing24/small/`.185 CPU cases and four adapters pass with unchanged cycles; signaling-true odd-target BSUN cases also pass. Mac OS8.1 passes Finder, input, advancing clock, Mix3.159, fullPR2.420 and clean shutdown. A/UX qualification is in progress; CD audio has not been qualified on this RBF. Original images and the previously shared ZIP are preserved.
