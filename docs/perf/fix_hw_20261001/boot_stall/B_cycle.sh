#!/usr/bin/env bash
# Brief B: one boot cycle on the MiSTer, logged to scratch/hw_20261001/B_log.txt.
#   menu (fresh shot must come from the MENU core) -> serial stats -> load RBF
#   (box-side /tmp/B_bpoll.py: T0, Ticks every 5 s from T0+40, stall procedure)
#   + a screenshot every 15 s here (finder_probe: SPECIAL = Finder menu bar up)
#   -> low memory dump -> tmcheck -> mac_shutdown.sh -> fresh shot must be HALT
#   -> load menu.rbf -> fresh shot must come from the MENU core.
# Stops (exit != 0) and leaves the guest alone on anything unexpected.
# usage: bash scratch/hw_20261001/B_cycle.sh CYCLE_NO NAME      (NAME = REL | F33 | F21)
set -u
export MSYS_NO_PATHCONV=1
cd /c/Temp/mistercore/MacQuadra800_MiSTer || exit 1
. scripts/local.env
export MISTER_HOST MISTER_HTTP_PORT
N=$(printf %02d "$1"); NAME=$2
case $NAME in
    REL) RBF=/media/fat/_Computer/MacQuadra800_20261001.rbf; MD5=a4d4d00801f1c066fa99093ea8f35f6d ;;
    F33) RBF=/media/fat/_Unstable/MacQuadra800_F33.rbf;      MD5=faf2eacdec2c680b29e88ffc735d2fe3 ;;
    F21) RBF=/media/fat/_Unstable/MacQuadra800_F21.rbf;      MD5=476c10c5c5b55709775f88e438fcc242 ;;
    *) echo "unknown bitstream $NAME"; exit 2 ;;
esac
C=c${N}${NAME}
D=scratch/hw_20261001
LOG=$D/B_log.txt
P=$D/B_$C
POLL=${P}_poll.txt
SHOTS=${P}_shots.txt
SSH="ssh -n -o ConnectTimeout=15 -o ServerAliveInterval=20 -i $HOME/.ssh/mister_only root@$MISTER_HOST"
L()    { echo "$(date +%T) [$C] $*" | tee -a "$LOG"; }
Lpipe(){ while IFS= read -r l; do L "$1 $l"; done; }
grab() { bash scripts/grab_fresh.sh "$1" 2>&1 | tail -1; }
ms()   { date +%s%3N; }

L "=== cycle $N $NAME $RBF"

# ---- 0. the menu core must be on screen; configuration unchanged ----
g=$(grab "${P}_pre.png"); L "pre shot: $g"
case "$g" in FRESH*"<- MENU/"*) ;; *) L "ABORT: the fresh screenshot is not from the MiSTer menu core"; exit 3 ;; esac
cfg=$($SSH "md5sum $RBF | cut -c1-32; tr -d '\000' < /media/fat/config/MacQuadra800.s0; echo; tr -d '\000' < /media/fat/config/MacQuadra800.s4; echo; xxd -p -l 1 /media/fat/config/MacQuadra800.CFG" | tr '\n' '|')
L "config: $cfg"
want="$MD5|games/MacQuadra800/MacQuadra800_Problem_Games.hda|games/MacQuadra800/DRACULA.toast|50|"
[ "$cfg" = "$want" ] || { L "ABORT: configuration differs from $want"; exit 3; }

# ---- 1. serial statistics at the menu ----
$SSH 'cat /proc/tty/driver/serial' | Lpipe "serial-pre:"

# host/box clock offset (box_ms - host_ms), midpoint of one ssh round trip
h1=$(ms); b=$($SSH 'date +%s%N | cut -c1-13'); h2=$(ms)
OFF=$(( b - (h1 + h2) / 2 )); L "clock offset box-host ${OFF} ms (round trip $((h2 - h1)) ms)"

# ---- 2. load + box-side watcher ----
: > "$POLL"; : > "$SHOTS"
$SSH "python3 -u /tmp/B_bpoll.py $C $RBF" > "$POLL" 2>&1 &
SPID=$!
T0MS=""
for i in $(seq 1 60); do
    T0MS=$(sed -n 's/.*T0MS=\([0-9]*\).*/\1/p' "$POLL" | head -1)
    [ -n "$T0MS" ] && break
    sleep 0.5
done
[ -n "$T0MS" ] || { L "ABORT: the box-side watcher did not report T0 ($(head -3 "$POLL" | tr '\n' ' '))"; exit 6; }
L "loaded: $(grep T0MS "$POLL" | head -1)"

# ---- 3. screenshots every 15 s until the watcher ends ----
tb() { echo $(( ( $(ms) + OFF - T0MS ) / 1000 )); }
FINDER=""; k=1
while :; do
    grep -q ' END ' "$POLL" && break
    kill -0 "$SPID" 2>/dev/null || { L "the watcher's ssh exited without END"; break; }
    t=$(tb)
    if [ "$t" -lt $(( 15 * k )) ]; then sleep 1; continue; fi
    k=$(( t / 15 + 1 ))
    tt=$(printf %03d "$t")
    f=${P}_t${tt}.png
    g=$(grab "$f"); md=-; probe=-
    case "$g" in FRESH*) md=$(md5sum "$f" | cut -c1-10); probe=$(python scripts/finder_probe.py screen "$f" 181 | cut -d'#' -f1) ;; esac
    core=${g##*<- }; core=${core%%/*}
    echo "$(date +%T) t+${tt} shot $f md5 $md core $core probe $probe ${g%% *}" >> "$SHOTS"
    if [ -z "$FINDER" ] && [ "${probe%% *}" = SPECIAL ] && [ "$core" = MacQuadra800 ]; then
        FINDER=$t
        $SSH 'touch /tmp/B_finder'
        echo "$(date +%T) t+${tt} FINDER menu bar (Special at rest) first seen in $f" >> "$SHOTS"
    fi
done
wait "$SPID"
# merge the watcher's and the screenshots' lines into the main log, in time order
/usr/bin/sort -s -k1,1 "$POLL" "$SHOTS" | sed "s/^\([0-9:]*\) /\1 [$C] /" >> "$LOG"
STATUS=$(sed -n 's/.* END \([A-Z_]*\).*/\1/p' "$POLL" | tail -1)
SUMM=$(grep ' SUMMARY ' "$POLL" | tail -1 | sed 's/.* SUMMARY //')
L "boot watch ended: status=${STATUS:-none} finder_shot=t+${FINDER:-none}"
if $SSH "test -s /tmp/B_stall_$C.txt"; then
    $SSH "cat /tmp/B_stall_$C.txt" > "$D/B_stall_$C.txt"; L "stall capture saved to $D/B_stall_$C.txt"
fi
if [ "$STATUS" != BOOT_DONE ]; then
    L "STOP: the boot did not complete normally -- guest left as it is, no input sent, nothing loaded"
    L "SUMMARY $NAME $SUMM finder_shot=t+${FINDER:-none} RESULT=STOPPED"
    exit 10
fi

# ---- 4. low memory once the Finder is up, then the Time Manager check ----
$SSH 'python3 /tmp/gdump.py 100 200 /tmp/B_low.bin >/dev/null && xxd -o 0x100 /tmp/B_low.bin' > "$D/B_low_$C.txt"
L "low memory \$100-\$2FF -> $D/B_low_$C.txt ($(wc -l < "$D/B_low_$C.txt") lines; \$290 line: $(grep '^00000290' "$D/B_low_$C.txt"))"
tm=$($SSH 'sh /tmp/tmcheck.sh' 2>&1)
echo "$tm" | Lpipe "tmcheck:"
case "$tm" in *moving*) TM=moving ;; *FROZEN*) TM=FROZEN ;; *) TM=unknown ;; esac

# ---- 5. shut down (closed loop), confirm the halt screen ----
L "mac_shutdown.sh start"
bash scripts/mac_shutdown.sh > "${P}_sd.txt" 2>&1; rc=$?
sed 's/^/    /' "${P}_sd.txt" >> "$LOG"
L "mac_shutdown.sh exit $rc"
cp -f scratch/shutdown/00_pinned.png "${P}_sd_pinned.png" 2>/dev/null
[ -f scratch/shutdown/40_after.png ] && cp -f scratch/shutdown/40_after.png "${P}_sd_after.png"
if [ "$rc" != 0 ]; then
    L "STOP: shutdown walker exit $rc -- look at ${P}_sd_pinned.png and scratch/shutdown/ before anything else"
    L "SUMMARY $NAME $SUMM finder_shot=t+${FINDER:-none} tm=$TM RESULT=STOPPED_AT_SHUTDOWN"
    exit 11
fi
g=$(grab "${P}_halt.png"); h=$(python scripts/finder_probe.py halt "${P}_halt.png" 2>&1)
L "halt shot: $g -> $h"
case "$g" in FRESH*"<- MacQuadra800/"*) ;; *) h=NOT_FRESH ;; esac
if [ "$h" != HALT ]; then
    L "STOP: no fresh halt screen -- not loading the menu"
    L "SUMMARY $NAME $SUMM finder_shot=t+${FINDER:-none} tm=$TM RESULT=STOPPED_NO_HALT"
    exit 12
fi

# ---- 6. back to the menu ----
$SSH 'echo "load_core /media/fat/menu.rbf" > /dev/MiSTer_cmd'
L "load_core /media/fat/menu.rbf sent"
sleep 10
g=$(grab "${P}_menu.png"); L "menu shot: $g"
case "$g" in FRESH*"<- MENU/"*) M=menu ;; *) M=NOT_CONFIRMED ;; esac
L "SUMMARY $NAME $SUMM finder_shot=t+${FINDER:-none} tm=$TM menu=$M RESULT=OK"
[ "$M" = menu ] || exit 13
exit 0
