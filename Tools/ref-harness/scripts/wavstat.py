#!/usr/bin/env python3
"""Per-segment peak/RMS of the harness WAVs: wavstat.py file.wav [blocks_per_segment=50]"""
import sys, wave, struct, math
w = wave.open(sys.argv[1]); seg = int(sys.argv[2]) * 64 if len(sys.argv) > 2 else 3200
d = w.readframes(w.getnframes()); v = struct.unpack('<%dh' % (len(d)//2), d)
n = len(v)//2
for s in range(0, n, seg):
    l = v[2*s:2*min(n, s+seg):2]; r = v[2*s+1:2*min(n, s+seg):2]
    pk = max(max(map(abs, l)), max(map(abs, r)))
    rms = math.sqrt(sum(x*x for x in l+r)/max(1, len(l+r)))
    print(f"frames {s:7d}..{min(n,s+seg):7d}  peak {pk:6d}  rms {rms:9.1f}")
