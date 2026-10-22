# The pipelined AP68040 in MacQuadra800_MiSTer

`rtl/ap68040_faster/` is Adam Polkosnik's pipelined AP68040 ("faster"),
taken on 2026-10-21 from the NeXT core's `pipelined_040` branch
(`MiSTer-devel/NeXT_MiSTer` f8e9591, its `rtl/ap68040/`).  That tree is
`apolkosnik/AP68040` main 1247b45 plus the NeXT port's two local changes
(`UPSTREAM.md`, `docs/CPU_NEXT_PORT.md` there): the `dbcc_floor` input
(tied to 0 here) and the `ap68040_sdp_be` byte-enable RAM written in the
form Quartus 17.0 infers as one M10K per slice.  Upstream main is at
606c0eb now, which changes only the bench's timeout.

The Mac side is `rtl/quadra_cpu040.sv` (wombat_cpu's ports, the 68040 bus
at 1:1 on the machine clock); `CPU_AP68040` in the qsf selects it.
