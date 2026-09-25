#!/usr/bin/env bash
# type.sh — type an ASCII string into the guest through the MiSTer Remote
# websocket, one raw Linux keycode per character, Shift held where needed.
#
# Usage:
#   bash scripts/guest/type.sh 'shutdown -h now'        # text only
#   bash scripts/guest/type.sh -r 'uname -a'            # text, then Return
#   bash scripts/guest/type.sh -r ''                    # just Return
#
# The guest sees a US-layout ADB keyboard, so the mapping below is the US
# layout of the Linux keycodes mister_ws.py forwards. Pacing is 0.30 s per
# key to leave margin for ADB polling during interactive hardware validation.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)" || exit 1
. scripts/local.env

RET=0
if [ "${1:-}" = "-r" ]; then RET=1; shift; fi
TEXT="${1-}"

ARGS=$(python - "$TEXT" "$RET" <<'PY'
import sys
text, ret = sys.argv[1], sys.argv[2] == "1"
plain = {
 'a':30,'b':48,'c':46,'d':32,'e':18,'f':33,'g':34,'h':35,'i':23,'j':36,'k':37,
 'l':38,'m':50,'n':49,'o':24,'p':25,'q':16,'r':19,'s':31,'t':20,'u':22,'v':47,
 'w':17,'x':45,'y':21,'z':44,
 '1':2,'2':3,'3':4,'4':5,'5':6,'6':7,'7':8,'8':9,'9':10,'0':11,
 '-':12,'=':13,'[':26,']':27,';':39,"'":40,'`':41,'\\':43,',':51,'.':52,'/':53,
 ' ':57,'\t':15,'\n':28,
}
shifted = {
 '!':2,'@':3,'#':4,'$':5,'%':6,'^':7,'&':8,'*':9,'(':10,')':11,
 '_':12,'+':13,'{':26,'}':27,':':39,'"':40,'~':41,'|':43,'<':51,'>':52,'?':53,
}
out = []
for ch in text:
    if ch in plain:
        out.append(f"raw:{plain[ch]}")
    elif ch in shifted:
        out.append(f"down:42 raw:{shifted[ch]} up:42")
    elif ch.isalpha() and ch.lower() in plain:
        out.append(f"down:42 raw:{plain[ch.lower()]} up:42")
    else:
        sys.stderr.write(f"type.sh: no keycode for {ch!r}\n"); sys.exit(2)
if ret:
    out.append("raw:28")
print(" ".join(out))
PY
) || exit 2

[ -n "$ARGS" ] || exit 0
exec python scripts/mister_ws.py --host "$MISTER_HOST" --port "${MISTER_HTTP_PORT:-8182}" --delay 0.30 $ARGS
