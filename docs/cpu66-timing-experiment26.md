# CPU66 timing experiment26: measure the cache-maintenance selector cost

This is25-small with only the experiment20 early maintenance set selection reverted. The D-cache engine again selects the write set only after the maintenance tag match. All real writes, way masks and invalidations keep their original behavior. No other file changes.

The earlier20 fit used446 more ALMs than18 for a0.101ns setup improvement and worse TNS; that comparison also included the pointer-mask change and a new date stamp, so it did not isolate the selector's cost. This controlled comparison holds25's entire source, stamp and configuration fixed and removes only that selector change.185 CPU cases and four adapters pass, with all185 cycle counts exactly matching25-small. No state, stage or timing exception is added. A fit is required before claiming any area saving or timing benefit. No VRAM change is included.
