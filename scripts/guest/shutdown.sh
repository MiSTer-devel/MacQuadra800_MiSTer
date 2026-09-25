#!/usr/bin/env bash
# shutdown.sh -- folded into scripts/mac_shutdown.sh on 2026-09-16; this name
# still works and takes the same arguments (--dry-run, --release).
#
# This walker positioned with click.sh's damped loop and released when the lit
# row covered a hardcoded y=104, which is right for one Special menu layout
# only. See mac_shutdown.sh's header for the method that replaced it.
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/mac_shutdown.sh" "$@"
