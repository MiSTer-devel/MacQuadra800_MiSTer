#!/usr/bin/env bash
# Unattended boot-repeat loop: alternate REL and F33 with the operator's B_cycle.sh
# (it refuses to load unless a fresh screenshot shows the menu core, and to return
# to the menu unless a fresh screenshot shows the halt screen).  Stops at the first
# cycle that does not end RESULT=OK, leaving the guest alone.
#   usage: B_loop.sh FIRST LAST
cd /c/Temp/mistercore/MacQuadra800_MiSTer || exit 1
for n in $(seq "$1" "$2"); do
    if [ $((n % 2)) = 1 ]; then name=REL; else name=F33; fi
    bash scratch/hw_20261001/B_cycle.sh "$n" "$name" > "scratch/hw_20261001/B_run_c$(printf %02d "$n").txt" 2>&1
    rc=$?
    echo "$(date +%T) cycle $n $name rc=$rc $(grep SUMMARY "scratch/hw_20261001/B_run_c$(printf %02d "$n").txt" | tail -1 | sed 's/.*SUMMARY //' | cut -c1-200)" >> scratch/hw_20261001/B_loop.log
    [ "$rc" = 0 ] || { echo "$(date +%T) STOP at cycle $n (rc=$rc)" >> scratch/hw_20261001/B_loop.log; exit "$rc"; }
done
echo "$(date +%T) loop $1..$2 complete" >> scratch/hw_20261001/B_loop.log
