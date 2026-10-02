#!/usr/bin/env bash
# autoscreen.sh <walkdir> <loads> -- wait for the next fit the seed walk archives
# (seedN/MacQuadra800_seedN.rbf with its rbf.md5), push it to the MiSTer as
# _Unstable/MacQuadra800_W<N>.rbf and run the clean-boot scaler screen on it.
set -u
cd /c/Temp/mistercore/MacQuadra800_MiSTer || exit 1
export MSYS_NO_PATHCONV=1
. scripts/local.env
W="$1"; L="${2:-16}"; DONE=scratch/hw_20261001/autoscreen.done; touch $DONE
while :; do
	for f in "$W"/seed*/rbf.md5; do
		[ -f "$f" ] || continue
		d=$(dirname "$f"); n=${d##*seed}
		[ -s "$d/MacQuadra800_seed$n.rbf" ] || continue
		grep -qx "$W/$n" $DONE && continue
		echo "$W/$n" >> $DONE
		sleep 20   # let the walk finish copying its reports
		scp -q -i ~/.ssh/mister_only "$d/MacQuadra800_seed$n.rbf" root@$MISTER_HOST:/media/fat/_Unstable/MacQuadra800_W$n.rbf || exit 1
		echo "$(date +%H:%M:%S) seed $n ($(cut -c1-8 "$f")): $(grep -A1 "Type  : Setup" "$d/MacQuadra800.sta.summary" | grep Slack | head -3 | tr '\n' ' ')" >> scratch/hw_20261001/autoscreen.log
		bash scratch/s1002/vscreen.sh MacQuadra800_W$n.rbf W$n "$L" >> scratch/hw_20261001/autoscreen.log 2>&1
		exit 0
	done
	grep -q 'walk over' "$W/walk.log" 2>/dev/null && { echo "$(date +%H:%M:%S) walk over, nothing new" >> scratch/hw_20261001/autoscreen.log; exit 2; }
	sleep 30
done
