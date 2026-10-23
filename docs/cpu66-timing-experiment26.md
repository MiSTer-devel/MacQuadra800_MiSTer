# CPU66 timing experiment26: measure the cache-maintenance selector cost

This is25-small with only the experiment20 early maintenance set selection reverted. The D-cache engine again selects the write set only after the maintenance tag match. All real writes, way masks and invalidations keep their original behavior. No other file changes.

The earlier20 fit used446 more ALMs than18 for a0.101ns setup improvement and worse TNS; that comparison also included the pointer-mask change and a new date stamp, so it did not isolate the selector's cost. This controlled comparison holds25's entire source, stamp and configuration fixed and removes only that selector change.185 CPU cases and four adapters pass, with all185 cycle counts exactly matching25-small. No state, stage or timing exception is added. A fit is required before claiming any area saving or timing benefit. No VRAM change is included.

## Completed fit: not retained

33,816ALMs, CPU setup -1.712ns/TNS -453.866ns, SDRAM -0.663ns (fails), bus +0.660ns, HDMI +0.288ns and minimum hold +0.121ns. Compared with25-small it uses79 more ALMs, improves CPU WNS but fails SDRAM; it does not establish that reverting the selector saves area. The candidate inherits25's added FPU cycle and does not beat24-small globally. No hardware trial or main-source application. Full reports and RBF hashes are preserved.
