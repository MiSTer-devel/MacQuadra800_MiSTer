#!/usr/bin/env bash
# vscreen.sh <rbf name in _Unstable or full path on the box> <tag> <loads>
# The scaler-port screen from the 2026-09-30 sessions: for each load, reboot the
# MiSTer (clean HPS port), wait for the menu, load the core, and sample the scaler
# header at DDR3 0x20000000 five times (scratch/s1002/vbuf_probe.py).  A load is
# good when at least 4 of 5 samples show a valid 640x480 header.  The core is
# loaded over only during the Mac's RAM test (the first 50 s at 128 MB), before
# any disk access, and the run ends with one more reboot back to the menu.
set -u
cd /c/Temp/mistercore/MacQuadra800_MiSTer || exit 1
export MSYS_NO_PATHCONV=1
. scripts/local.env
RBF="$1"; TAG="$2"; L="${3:-8}"
case "$RBF" in /*) ;; *) RBF=/media/fat/_Unstable/$RBF ;; esac
S="ssh -o BatchMode=yes -o ConnectTimeout=8 -i $HOME/.ssh/mister_only root@$MISTER_HOST"
LOG=scratch/hw_20261001/vscreen.log
reboot_box() {
	$S -n 'sync; (sleep 1; reboot) >/dev/null 2>&1 &' 2>/dev/null
	sleep 25; n=0
	until $S -n 'test -e /tmp/CORENAME' 2>/dev/null || [ $n -ge 150 ]; do sleep 5; n=$((n+5)); done
	sleep 10
}
good=0
for i in $(seq 1 "$L"); do
	reboot_box
	core=$($S -n 'cat /tmp/CORENAME' 2>/dev/null)
	$S 'cat > /tmp/vbuf_probe.py' < scratch/s1002/vbuf_probe.py
	menu=$($S -n 'python3 /tmp/vbuf_probe.py 2' 2>&1 | tail -1)
	out=$($S -n "echo 'load_core $RBF' > /dev/MiSTer_cmd; sleep 5; cat /tmp/CORENAME; echo; python3 /tmp/vbuf_probe.py 5" 2>&1)
	ok=$(echo "$out" | grep -c "hdr type=01 fmt=01 .* w=640 h=480")
	[ "$ok" -ge 4 ] && good=$((good+1))
	echo "$(date +%H:%M:%S) $TAG load $i: valid $ok/5 (menu before: core=$core ${menu#*hdr }) last: $(echo "$out" | tail -1 | sed 's/.*markers/markers/')" >> $LOG
done
reboot_box
echo "$(date +%H:%M:%S) $TAG $($S -n "md5sum $RBF" | cut -c1-8): $good/$L loads with video; box back at $($S -n 'cat /tmp/CORENAME')" | tee -a $LOG
