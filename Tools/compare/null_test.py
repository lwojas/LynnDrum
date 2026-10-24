#!/usr/bin/env python3
"""Null test: lxr_core (lxr_render) vs the unmodified-upstream harness (lxr_ref_render).
usage: null_test.py <lxr_ref_render> <lxr_render> <scenario_dir> [name-filter]
Compares the rendered DAC buses sample by sample (T0: max|diff| == 0). On a mismatch prints the
first differing frame (block, channel), both values and the last parameter write / trigger
before that block from the reference trace."""
import os, subprocess, sys, tempfile, struct

ref, core, sdir = sys.argv[1:4]
flt = sys.argv[4] if len(sys.argv) > 4 else ''

def pcm(path):
    d = open(path, 'rb').read()[44:]
    return struct.unpack('<%dh' % (len(d) // 2), d)

def run(exe, script, prefix, trace=False):
    cmd = [exe, script, '-o', prefix] + (['--trace'] if trace else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr.strip()[:200])

bad = 0; n = 0
with tempfile.TemporaryDirectory() as t:
    for f in sorted(os.listdir(sdir)):
        if not f.endswith('.lxr') or flt not in f: continue
        n += 1; sc = os.path.join(sdir, f)
        try:
            run(ref, sc, t + '/r', True); run(core, sc, t + '/c')
        except RuntimeError as e:
            print('ERROR', f, e); bad += 1; continue
        for bus in ('dac1', 'dac2'):
            a, b = pcm(f'{t}/r.{bus}.wav'), pcm(f'{t}/c.{bus}.wav')
            if len(a) != len(b):
                print('FAIL', f, bus, 'length', len(a), len(b)); bad += 1; break
            if a != b:
                i = next(k for k in range(len(a)) if a[k] != b[k])
                frame, ch = divmod(i, 2); blk = frame // 64
                last = ''
                for line in open(t + '/r.trace.txt'):
                    if int(line.split()[0]) <= blk: last = line.strip()
                print(f'FAIL {f} {bus}: first diff frame {frame} (block {blk}) ch{"LR"[ch]} ref={a[i]} core={b[i]}; '
                      f'max|diff|={max(abs(x - y) for x, y in zip(a, b))}; last event: {last}')
                bad += 1; break
print(f'{n - bad}/{n} scenarios bit-identical')
sys.exit(1 if bad else 0)
