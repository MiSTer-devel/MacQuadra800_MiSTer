#!/usr/bin/env bash
# vtiming.sh <rbf on box> <tag> <pairs>
# Does the scaler fault depend on how long Main takes between configuring the FPGA
# and releasing the core's reset?  Alternates two kinds of load on an idle, warm box:
#   A  plain load_core
#   B  load_core right after writing 24 MB of dirty pages to the SD card, so that
#      Main's sync() in app_restart (after the FPGA is configured, before the new
#      Main releases reset) takes seconds
# Each load is probed 5 s later (scratch/s1002/vbuf_probe.py) and the menu core is
# loaded again while the Mac is still in its RAM test.  A failed load breaks the
# HPS port until a reboot: the box is then rebooted and left to settle for 60 s.
set -u
cd /c/Temp/mistercore/MacQuadra800_MiSTer || exit 1
export MSYS_NO_PATHCONV=1
. scripts/local.env
RBF="$1"; TAG="$2"; N="${3:-8}"
S="ssh -o BatchMode=yes -o ConnectTimeout=8 -i $HOME/.ssh/mister_only root@$MISTER_HOST"
LOG=scratch/hw_20261001/vtiming.log
reboot_box() {
	$S -n 'sync; (sleep 1; reboot) >/dev/null 2>&1 &' 2>/dev/null
	sleep 25; n=0
	until $S -n 'test -e /tmp/CORENAME' 2>/dev/null || [ $n -ge 150 ]; do sleep 5; n=$((n+5)); done
	sleep 60
	$S 'cat > /tmp/vbuf_probe.py' < scratch/s1002/vbuf_probe.py
	$S -n 'sync'
}
$S 'cat > /tmp/vbuf_probe.py' < scratch/s1002/vbuf_probe.py
for i in $(seq 1 "$N"); do
	for mode in A B; do
		menu=$($S -n 'cat /tmp/CORENAME; python3 /tmp/vbuf_probe.py 1 | tail -1' 2>&1 | tr '\n' ' ')
		case "$menu" in *"hdr type=01 fmt=01"*) ;; *) echo "$(date +%H:%M:%S) $TAG menu header invalid before load ($menu): rebooting" >> $LOG; reboot_box ;; esac
		if [ "$mode" = B ]; then
			pre="dd if=/dev/zero of=/media/fat/vtiming_dirty.bin bs=1M count=24 2>/dev/null;"
		else
			pre="sync;"
		fi
		out=$($S -n "$pre echo 'load_core $RBF' > /dev/MiSTer_cmd; sleep 9; cat /tmp/CORENAME; echo; python3 /tmp/vbuf_probe.py 5" 2>&1)
		ok=$(echo "$out" | grep -c "hdr type=01 fmt=01 .* w=640 h=480")
		echo "$(date +%H:%M:%S) $TAG pair $i mode $mode: valid $ok/5  last: $(echo "$out" | tail -1 | sed 's/.*markers/markers/')" >> $LOG
		$S -n "rm -f /media/fat/vtiming_dirty.bin; echo 'load_core /media/fat/menu.rbf' > /dev/MiSTer_cmd; sleep 9; sync"
		if [ "$ok" -lt 4 ]; then reboot_box; fi
	done
done
echo "$(date +%H:%M:%S) $TAG done: A $(grep "$TAG pair" $LOG | grep 'mode A' | grep -c 'valid [45]/5')/$(grep "$TAG pair" $LOG | grep -c 'mode A') good, B $(grep "$TAG pair" $LOG | grep 'mode B' | grep -c 'valid [45]/5')/$(grep "$TAG pair" $LOG | grep -c 'mode B') good" | tee -a $LOG
