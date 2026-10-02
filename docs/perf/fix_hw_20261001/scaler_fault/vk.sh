#!/usr/bin/env bash
# vk.sh <rbf path on the box> <tag> <loads> [only-failing] -- clean-boot loads, each
# followed by vk_probe.py (how many beats is the scaler's data displaced?)
set -u
cd /c/Temp/mistercore/MacQuadra800_MiSTer || exit 1
export MSYS_NO_PATHCONV=1
. scripts/local.env
RBF="$1"; TAG="$2"; L="${3:-6}"
S="ssh -o BatchMode=yes -o ConnectTimeout=8 -i $HOME/.ssh/mister_only root@$MISTER_HOST"
LOG=scratch/hw_20261001/vk.log
reboot_box() {
	$S -n 'sync; (sleep 1; reboot) >/dev/null 2>&1 &' 2>/dev/null
	sleep 25; n=0
	until $S -n 'test -e /tmp/CORENAME' 2>/dev/null || [ $n -ge 150 ]; do sleep 5; n=$((n+5)); done
	sleep 10
}
for i in $(seq 1 "$L"); do
	reboot_box
	$S 'cat > /tmp/vk_probe.py' < scratch/s1002/vk_probe.py
	out=$($S -n "echo 'load_core $RBF' > /dev/MiSTer_cmd; sleep 9; python3 /tmp/vk_probe.py" 2>&1)
	echo "$(date +%H:%M:%S) $TAG load $i:" >> $LOG
	echo "$out" | sed 's/^/    /' >> $LOG
done
reboot_box
echo "$(date +%H:%M:%S) $TAG done; box at $($S -n 'cat /tmp/CORENAME')" >> $LOG
