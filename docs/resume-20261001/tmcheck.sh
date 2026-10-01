#!/bin/sh
# Classify a guest hang: is the Mac OS Time Manager stalled?
# Reads (via gdump.py, read-only) Ticks, the TimeVars record and the TM
# active queue, twice 3 s apart.  Stalled = Ticks advance, TM record frozen,
# queue head due (tmCount small) but never fired.
g() { python3 /tmp/gdump.py "$1" "$2" /tmp/tmc.bin >/dev/null && xxd -p /tmp/tmc.bin | tr -d '\n'; }
be32() { echo "$1" | cut -c"$2"-$(($2 + 7)); }
tv=$(g 00000B30 4)
t0=$(g 0000016A 4); r0=$(g $tv 20)
sleep 3
t1=$(g 0000016A 4); r1=$(g $tv 20)
echo "Ticks $t0 -> $t1   TimeVars=$tv"
echo "TM rec  $r0"
echo "TM rec  $r1  $( [ "$r0" = "$r1" ] && echo FROZEN || echo moving )"
a=$(be32 "$r1" 1); i=0
while [ "$a" != "00000000" ] && [ $i -lt 10 ]; do
  e=$(g $a 16)
  echo "  elem $a qType $(echo $e | cut -c9-12) tmAddr $(echo $e | cut -c13-20) tmCount $(echo $e | cut -c21-28)"
  a=$(be32 "$e" 1); i=$((i + 1))
done
