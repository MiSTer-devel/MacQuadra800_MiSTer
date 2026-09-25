#!/usr/bin/env bash
# shutdown_finder.sh -- folded into scripts/mac_shutdown.sh on 2026-09-16; this
# name still works and takes the same arguments (--dry-run, --release).
#
# This walker was tuned for the System 7.1 Finder on the A/UX disk's
# MacPartition: SPECIAL_X=229 (behind a Label menu) and a black inverted row
# looked for at x 295..335. On the Mac OS 8.1 Finder x=229 is Help and x
# 295..335 is past the right edge of the Special panel (149..264), so it
# printed "no row highlighted" forever. Under A/UX itself the same walker
# would have released on Logout, the last item there. mac_shutdown.sh refuses
# both System 7 Finders; the old geometry is in this file's git history.
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/mac_shutdown.sh" "$@"
