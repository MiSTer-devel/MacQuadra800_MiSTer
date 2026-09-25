#!/usr/bin/env python3
"""Build ToneTest.cue/.bin (python scripts/make_tonedisc.py <out_dir>): an AUDIBLE
4-track CD-DA image with the same
track layout as the silent AudioTest.cue (1:30 / 1:30 / 2:00 / 2:02, 31653
frames), so the p2c/p2d positions still compare.

  track 1  0:00-1:30  440 Hz (A4) both channels, plus a short 2 kHz click on
                      every second -- continuity + pitch by ear
  track 2  1:30-3:00  alternating 1 s LEFT only 660 Hz / 1 s RIGHT only 880 Hz
                      -- channel order; byte-swapped samples sound like noise
  track 3  3:00-5:00  1 kHz pip: 100 ms on, 900 ms off, once per second --
                      cadence; an underrun shows as an irregular pip
  track 4  5:00-7:02  200 Hz -> 2 kHz sweep every 10 s -- sample-rate check

Frames are 2352 bytes = 588 stereo 16-bit little-endian samples at 44.1 kHz.
Amplitude 0.25 FS (~ -12 dBFS).
"""
import sys, os, struct, math

try:
    import numpy as np
except ImportError:
    np = None

FRAMES = 31653
SPF = 588
SR = 44100
AMP = 0.25
T1, T2, T3 = 6750, 13500, 22500   # frame starts of tracks 2, 3, 4

out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
bin_path = os.path.join(out_dir, "ToneTest.bin")
cue_path = os.path.join(out_dir, "ToneTest.cue")

if np is None:
    sys.exit("numpy needed (pip install numpy)")

n = FRAMES * SPF
t = np.arange(n, dtype=np.float64) / SR          # seconds
frame = np.arange(n) // SPF
sec = np.floor(t).astype(np.int64)
frac = t - sec                                    # position inside the second

left = np.zeros(n, dtype=np.float64)
right = np.zeros(n, dtype=np.float64)

# track 1: 440 Hz + a 10 ms 2 kHz click at each second boundary
m = frame < T1
tone = np.sin(2 * math.pi * 440.0 * t[m])
click = np.where(frac[m] < 0.010, np.sin(2 * math.pi * 2000.0 * t[m]), 0.0)
left[m] = tone + click
right[m] = tone + click

# track 2: even seconds LEFT 660 Hz, odd seconds RIGHT 880 Hz
m = (frame >= T1) & (frame < T2)
even = (sec[m] % 2) == 0
left[m] = np.where(even, np.sin(2 * math.pi * 660.0 * t[m]), 0.0)
right[m] = np.where(even, 0.0, np.sin(2 * math.pi * 880.0 * t[m]))

# track 3: 1 kHz pip, 100 ms per second
m = (frame >= T2) & (frame < T3)
pip = np.where(frac[m] < 0.100, np.sin(2 * math.pi * 1000.0 * t[m]), 0.0)
left[m] = pip
right[m] = pip

# track 4: exponential sweep 200 Hz -> 2 kHz over 10 s, repeating
m = frame >= T3
tt = t[m] - t[m][0]
ph = tt % 10.0
f0, f1 = 200.0, 2000.0
k = math.log(f1 / f0) / 10.0
phase = 2 * math.pi * f0 * (np.exp(k * ph) - 1.0) / k
sw = np.sin(phase)
left[m] = sw
right[m] = sw

pcm = np.empty(2 * n, dtype=np.int16)
pcm[0::2] = np.clip(left * AMP * 32767, -32768, 32767).astype(np.int16)
pcm[1::2] = np.clip(right * AMP * 32767, -32768, 32767).astype(np.int16)
pcm.astype("<i2").tofile(bin_path)

with open(cue_path, "w", newline="\r\n") as f:
    f.write('FILE "ToneTest.bin" BINARY\n')
    f.write('  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n')
    f.write('  TRACK 02 AUDIO\n    INDEX 01 01:30:00\n')
    f.write('  TRACK 03 AUDIO\n    INDEX 01 03:00:00\n')
    f.write('  TRACK 04 AUDIO\n    INDEX 01 05:00:00\n')

print(bin_path, os.path.getsize(bin_path), "bytes;", FRAMES, "frames")
