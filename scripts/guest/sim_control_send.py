#!/usr/bin/env python3
"""Send runtime commands to an existing simulator control stream in place.

Atomic editor replacement disconnects an already-open regular-file reader.
This sender appends without replacing that inode. It never creates a path.
"""
import argparse
import os
import re
import stat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stream")
    parser.add_argument("commands", nargs="+")
    args = parser.parse_args()
    grammar = re.compile(r"(?:shot|quit|profile (?:start|stop)|wait [0-9]+|ramdump [0-9]+|(?:down|up) (?:0x)?[0-9a-fA-F]{1,2}(?: ext)?)")
    for command in args.commands:
        if not grammar.fullmatch(command) or (command.startswith("ramdump ") and not 1 <= int(command.split()[1]) <= 128):
            parser.error(f"invalid control command: {command!r}")
    payload = ("\n".join(args.commands) + "\n").encode("ascii")
    # O_NONBLOCK avoids hanging on a FIFO without a simulator reader.
    fd = os.open(args.stream, os.O_WRONLY | os.O_APPEND | os.O_NONBLOCK)
    try:
        mode = os.fstat(fd).st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISFIFO(mode)):
            parser.error("control stream must be an existing regular file or FIFO")
        while payload:
            count = os.write(fd, payload)
            if count <= 0:
                raise OSError("control stream made no write progress")
            payload = payload[count:]
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
