#!/usr/bin/env python3
"""Pure-python measurement helpers for authoring clean-room kits (no numpy): render a voice through lxr_render
and report level, decay, pitch and brightness. This is how kits are checked since nobody can listen in CI."""
import math, os, struct, subprocess, sys, tempfile, wave

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RENDER = os.path.join(ROOT, 'build-core', 'lxr_render')
FS = 44140

def render(lines, blocks=400, prefix=None):
    with tempfile.TemporaryDirectory() as t:
        sc = os.path.join(t, 's.lxr'); open(sc, 'w').write('seed 1\n' + '\n'.join(lines) + f'\nrender {blocks}\n')
        subprocess.run([RENDER, sc, '-o', os.path.join(t, 'o')], check=True, capture_output=True)
        out = []
        for bus in ('dac1', 'dac2'):
            w = wave.open(os.path.join(t, f'o.{bus}.wav')); d = w.readframes(w.getnframes())
            v = struct.unpack('<%dh' % (len(d) // 2), d); out.append(([x / 32768 for x in v[0::2]], [x / 32768 for x in v[1::2]]))
        return out          # [(L,R) dac1, (L,R) dac2]

def mono(r):
    l, rr = r[0]; l2, r2 = r[1]
    return [a + b + c + d for a, b, c, d in zip(l, rr, l2, r2)]

def peak(x): return max(abs(v) for v in x) if x else 0.0

def env(x, win=441):
    return [math.sqrt(sum(v * v for v in x[i:i + win]) / win) for i in range(0, len(x) - win, win)]     # 10 ms rms steps

def decay_ms(x, drop_db=40):
    e = env(x)
    if not e: return 0.0
    pk = max(e); ip = e.index(pk)
    thr = pk * 10 ** (-drop_db / 20)
    for i in range(ip, len(e)):
        if e[i] < thr: return (i - ip) * 10.0
    return (len(e) - ip) * 10.0

def fft(re):
    n = len(re); im = [0.0] * n; re = list(re)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit: j ^= bit; bit >>= 1
        j ^= bit
        if i < j: re[i], re[j] = re[j], re[i]
    k = 2
    while k <= n:
        ang = -2 * math.pi / k; wr, wi = math.cos(ang), math.sin(ang)
        for s in range(0, n, k):
            cr, ci = 1.0, 0.0
            for q in range(k // 2):
                a, b = s + q, s + q + k // 2
                tr, ti = re[b] * cr - im[b] * ci, re[b] * ci + im[b] * cr
                re[b], im[b] = re[a] - tr, im[a] - ti; re[a] += tr; im[a] += ti
                cr, ci = cr * wr - ci * wi, cr * wi + ci * wr
        k <<= 1
    return [math.hypot(a, b) for a, b in zip(re[:n // 2], im[:n // 2])]

def spectrum(x, start, n=8192):
    seg = x[start:start + n]; seg += [0.0] * (n - len(seg))
    win = [0.5 - 0.5 * math.cos(2 * math.pi * i / n) for i in range(n)]
    return fft([a * b for a, b in zip(seg, win)])

def dominant_hz(x, start=0, n=8192):
    s = spectrum(x, start, n)
    k = max(range(2, len(s)), key=lambda i: s[i]); return k * FS / n

def centroid_hz(x, start=0, n=8192):
    s = spectrum(x, start, n); tot = sum(s) or 1.0
    return sum(i * FS / n * v for i, v in enumerate(s)) / tot

def band_db(x, start, lo, hi, n=8192):
    s = spectrum(x, start, n); k0, k1 = int(lo * n / FS), int(hi * n / FS)
    return 10 * math.log10(sum(v * v for v in s[k0:k1]) + 1e-12)

def report(name, x):
    st = next((i for i, v in enumerate(x) if abs(v) > 0.01), 0)
    print(f'{name:14s} peak {peak(x):5.2f}  decay(-40dB) {decay_ms(x):5.0f} ms  dominant {dominant_hz(x, st):7.1f} Hz  centroid {centroid_hz(x, st):7.0f} Hz')

if __name__ == '__main__':
    print('usage: import measure; measure.report(...)')
