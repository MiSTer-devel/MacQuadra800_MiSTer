#!/usr/bin/env python3
"""Virtual mouse for the MiSTer via /dev/uinput -- runs ON the MiSTer.

For boxes whose mrext remote has no mouseMove/mouseBtn (it answers "invalid").
Main hot-plugs uinput devices, so the mouse exists for the life of this
process and the button is always released before it goes away.

Usage (copy to /tmp on the MiSTer, run with its python3):
    vmouse.py [--step N] [--pace S] token ...

Tokens:
    m:DX,DY   relative move, sent as unit steps of at most --step counts per
              event, --pace seconds apart (slow, small steps keep Mac OS's
              pointer acceleration out of it: about 1 px per count)
    home      pin the pointer into the top-left corner
    down / up press / release the left button
    click     down, 0.15 s, up
    dclick    two clicks 0.12 s apart
    0.5       any bare float: sleep that long
"""
import fcntl, struct, sys, time

UI_SET_EVBIT  = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_SET_RELBIT = 0x40045566
UI_DEV_CREATE  = 0x00005501
UI_DEV_DESTROY = 0x00005502
EV_SYN, EV_KEY, EV_REL = 0, 1, 2
REL_X, REL_Y = 0, 1
BTN_LEFT, BTN_RIGHT, BTN_MIDDLE = 0x110, 0x111, 0x112


def emit(f, etype, code, value):
    f.write(struct.pack('llHHi', 0, 0, etype, code, value))
    f.flush()


def move(f, dx, dy, step, pace):
    while dx or dy:
        sx = max(-step, min(step, dx))
        sy = max(-step, min(step, dy))
        if sx:
            emit(f, EV_REL, REL_X, sx)
        if sy:
            emit(f, EV_REL, REL_Y, sy)
        emit(f, EV_SYN, 0, 0)
        dx -= sx
        dy -= sy
        time.sleep(pace)


def button(f, value):
    emit(f, EV_KEY, BTN_LEFT, value)
    emit(f, EV_SYN, 0, 0)


def main():
    args = sys.argv[1:]
    step, pace = 1, 0.03
    tokens = []
    i = 0
    while i < len(args):
        if args[i] == '--step':
            step = int(args[i + 1]); i += 2
        elif args[i] == '--pace':
            pace = float(args[i + 1]); i += 2
        else:
            tokens.append(args[i]); i += 1

    f = open('/dev/uinput', 'wb')
    fd = f.fileno()
    fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
    fcntl.ioctl(fd, UI_SET_EVBIT, EV_REL)
    for code in (BTN_LEFT, BTN_RIGHT, BTN_MIDDLE):
        fcntl.ioctl(fd, UI_SET_KEYBIT, code)
    for code in (REL_X, REL_Y):
        fcntl.ioctl(fd, UI_SET_RELBIT, code)
    dev = struct.pack('80sHHHHi', b'vmouse (Claude)', 0x0003, 0x1d6b, 0x0104, 1, 0)
    dev += struct.pack('64i', *([0] * 64)) * 4
    f.write(dev)
    f.flush()
    fcntl.ioctl(fd, UI_DEV_CREATE)
    time.sleep(2.0)                    # let Main pick the device up

    held = False
    try:
        for t in tokens:
            if t.startswith('m:'):
                dx, dy = (int(v) for v in t[2:].split(','))
                move(f, dx, dy, step, pace)
            elif t == 'home':
                move(f, -900, -700, 8, 0.01)
            elif t == 'down':
                button(f, 1); held = True
            elif t == 'up':
                button(f, 0); held = False
            elif t == 'click':
                button(f, 1); time.sleep(0.15); button(f, 0)
            elif t == 'dclick':
                for _ in range(2):
                    button(f, 1); time.sleep(0.06); button(f, 0); time.sleep(0.12)
            else:
                time.sleep(float(t))
    finally:
        if held:
            button(f, 0)               # never leave the guest in a menu track
        time.sleep(0.3)
        fcntl.ioctl(fd, UI_DEV_DESTROY)
        f.close()


if __name__ == '__main__':
    main()
