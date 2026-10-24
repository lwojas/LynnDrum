#!/usr/bin/env python3
"""Audition lab for preset authoring: render a kit + pattern through the real engine and sequencer
(lxr_render_seq: the same lxr_core / lxr_seq the plugin runs), then look at it.

Nobody can listen in CI and the author of a preset cannot always listen either, so the lab makes sound inspectable:
  - render()      -> stereo float lists, the two output buses summed exactly as the plugin does
  - write_wav()   -> a 16 bit WAV you can open in any player (44 140 Hz, the engine's native rate)
  - spectrogram() -> a PNG: log-frequency spectrogram with a waveform strip, step grid and bar lines
  - hits()        -> per-trigger features (level, dominant Hz, centroid Hz, decay) of one track, soloed
                     (this is how "the technique is audible" is checked: locked hits must differ from unlocked hits)

Kits are written as raw parameter bytes (index = PAR_* number) and loaded with the script command `kit`, which is the only
path that also applies the LFO / velocity modulation targets (a plain `par` line does not).
"""
import math, os, struct, subprocess, sys, tempfile, wave
sys.path.insert(0, os.path.dirname(__file__))
from kitlib import *

RENDER_SEQ = os.path.join(ROOT, 'build-core', 'lxr_render_seq')
OUT_DIR = os.path.join(ROOT, 'build-previews')
KIT_BYTES = 247                      # END_OF_SOUND_PARAMETERS (upstream constant, see docs/building-lynndrum.md)


def kit_file(kit, path):
    b = bytearray(KIT_BYTES)
    for ident, v in kit.items(): b[BY_ID[ident]['par']] = v
    open(path, 'wb').write(bytes(b))



_TW = {}
def fft_fast(x):
    """radix-2 FFT magnitude (first half) with cached twiddles / bit-reversal; ~3x faster than measure.fft, same result"""
    n = len(x)
    if n not in _TW:
        rev = [0] * n; bits = n.bit_length() - 1
        for i in range(n): rev[i] = int(format(i, '0%db' % bits)[::-1], 2)
        tw = [(math.cos(-2 * math.pi * k / n), math.sin(-2 * math.pi * k / n)) for k in range(n // 2)]
        _TW[n] = (rev, tw)
    rev, tw = _TW[n]
    re = [x[i] for i in rev]; im = [0.0] * n
    k = 2
    while k <= n:
        half = k // 2; step = n // k
        for s0 in range(0, n, k):
            for q in range(half):
                wr, wi = tw[q * step]; a = s0 + q; b = a + half
                tr = re[b] * wr - im[b] * wi; ti = re[b] * wi + im[b] * wr
                re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] += tr; im[a] += ti
        k <<= 1
    return [math.hypot(re[i], im[i]) for i in range(n // 2)]


def pattern_lines(p, pat=0):
    """sequencer script lines for one pattern dict (steps, lengths, shuffle, notes, flam, shift, probability, p-locks)"""
    L = ['shuf %d %d' % (pat, p.get('shuffle', 0))]
    for t, tr in enumerate(p['tracks']):
        L.append('len %d %d %d' % (pat, t, tr['length']))
        for s in tr['steps']:
            i = s['i']
            L += ['ms %d %d %d 1' % (pat, t, i), 'sd %d %d %d %d %d %d' % (pat, t, i, s['vol'], s.get('prob', 100), s.get('note', 60)),
                  'st %d %d %d %d %d' % (pat, t, i, s.get('flam', 0), s.get('shift', 7))]
            for slot in (1, 2):
                lk = s.get('lock%d' % slot)
                if lk: L.append('pl %d %d %d %d %s %d' % (pat, t, i, slot, par_enum(lk[0]), lk[1]))
    return L

_ENUM = None
def par_enum(par):
    global _ENUM
    if _ENUM is None: _ENUM = {p['par']: p['enum'] for p in PARAMS}
    return _ENUM[par]


def _wav_in(path):
    w = wave.open(path); d = w.readframes(w.getnframes()); v = struct.unpack('<%dh' % (len(d) // 2), d)
    return [x / 32768 for x in v[0::2]], [x / 32768 for x in v[1::2]]


def render(kit, pattern=None, bpm=120, steps=32, mutes=(), solo=None, seed=1, pat=0, tail_ms=1500, events=None):
    """-> (L, R) lists. `steps` 16th notes are played; `tail_ms` of decay is rendered after the last step.
    The sequencer is started after the kit is loaded; one step at 120 bpm = 125 ms."""
    beat_ms = int(60000 / bpm)                                 # ms per beat; firmware tempo is integer-divided (docs/lxr-sequencer.md)
    blocks = int((steps * beat_ms / 4 + tail_ms) / (64 / 44140 * 1000))
    with tempfile.TemporaryDirectory() as t:
        kf = os.path.join(t, 'k.bin'); kit_file(kit, kf)
        lines = ['seed %d' % seed, 'bpm %d' % bpm, 'kit %s' % kf]
        if pattern: lines += pattern_lines(pattern, pat)
        for tr in range(7):
            if (solo is not None and tr != solo) or tr in mutes: lines.append('mute %d 1' % tr)
        lines += ['pattern %d' % pat, 'run 1', 'play %d' % blocks]
        sc = os.path.join(t, 's.lxr'); open(sc, 'w').write('\n'.join(lines) + '\n')
        evf = os.path.join(t, 'ev')
        r = subprocess.run([RENDER_SEQ, sc, '-o', os.path.join(t, 'o'), '--events', evf], capture_output=True, text=True)
        if r.returncode: raise RuntimeError(r.stderr)
        if events is not None:
            for ln in open(evf):
                f = ln.split()
                if len(f) >= 6 and f[2] == 'trig': events.append((int(f[0]) * 0.25, int(f[3]), int(f[4]), int(f[5])))   # (ms, track, note, vel)
        a, b = _wav_in(os.path.join(t, 'o.dac1.wav')), _wav_in(os.path.join(t, 'o.dac2.wav'))
        n = min(len(a[0]), len(b[0]))
        return [a[0][i] + b[0][i] for i in range(n)], [a[1][i] + b[1][i] for i in range(n)]


def write_wav(path, lr, gain=1.0, rate=44140):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    w = wave.open(path, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate)
    L, R = lr; out = bytearray()
    for a, b in zip(L, R): out += struct.pack('<hh', max(-32768, min(32767, int(a * gain * 32767))), max(-32768, min(32767, int(b * gain * 32767))))
    w.writeframes(bytes(out)); w.close()


def mono_of(lr): return [(a + b) * 0.5 for a, b in zip(*lr)]


def stats(lr):
    m = mono_of(lr)
    pk = max(max(abs(a), abs(b)) for a, b in zip(*lr)) if m else 0
    rms = math.sqrt(sum(v * v for v in m) / max(len(m), 1))
    return dict(peak=pk, rms=rms, clipped=sum(1 for a, b in zip(*lr) if abs(a) >= 0.999 or abs(b) >= 0.999))


def hits(kit, pattern, track, bpm=120, steps=16, seed=1, pat=0, window_ms=110):
    """per-trigger features of one track rendered alone (trigger times come from the sequencer's own event log):
    [(time_ms, step, note, vel, peak, dominant_hz, centroid_hz, brightness_db, decay_ms)]"""
    ev = []
    x = mono_of(render(kit, pattern, bpm, steps, solo=track, seed=seed, pat=pat, tail_ms=600, events=ev))
    step_ms = int(60000 / bpm) / 4
    tr = [e for e in ev if e[1] == track]
    res = []
    for k, (t, _tk, note, vel) in enumerate(tr):
        nxt = tr[k + 1][0] if k + 1 < len(tr) else t + 600
        a = int(t * FS / 1000); seg = x[a:a + int(min(window_ms, nxt - t) * FS / 1000)]
        if len(seg) < 256: continue
        full = x[a:a + int(min(600, nxt - t) * FS / 1000)]
        pk = max(abs(v) for v in seg)
        n = 1024
        while n * 2 <= len(seg) and n < 4096: n *= 2
        s_ = spectrum(seg, 0, n)
        kk = max(range(2, len(s_)), key=lambda i: s_[i]); tot = sum(s_) or 1
        cen = sum(i * FS / n * v for i, v in enumerate(s_)) / tot
        hi = sum(v * v for v in s_[int(4000 * n / FS):]) + 1e-12; lo = sum(v * v for v in s_[:int(4000 * n / FS)]) + 1e-12
        res.append((t, round(t / step_ms) % pattern['tracks'][track]['length'], note, vel, pk, kk * FS / n, cen, 10 * math.log10(hi / lo), decay_ms(full) if len(full) > 882 else 0))
    return res


def show_hits(label, rows):
    print('  ' + label)
    for t, st, note, vel, pk, dom, cen, br, dec in rows:
        print('    step %2d  t %6.0f ms  n%3d v%3d  peak %.2f  dom %6.0f Hz  centroid %6.0f Hz  hi/lo %+5.1f dB  decay %4.0f ms' % (st, t, note, vel, pk, dom, cen, br, dec))


def spectrogram(lr, path, bpm=120, steps=None, width=1400, fmin=30, fmax=18000, title='', labels=None, grid=True):
    """PNG: top = log-frequency spectrogram (dB), bottom = waveform envelope; grid lines on steps (faint) and beats/bars (strong)"""
    from PIL import Image, ImageDraw
    x = mono_of(lr); N = 2048; hop = max(128, len(x) // width)
    cols = (len(x) - N) // hop
    H, WF = 360, 70
    img = Image.new('RGB', (cols, H + WF + 14), (12, 12, 16)); px = img.load()
    win = [0.5 - 0.5 * math.cos(2 * math.pi * i / N) for i in range(N)]
    ys = [int(H - 1 - H * math.log(f / fmin) / math.log(fmax / fmin)) for f in range(1, 1)]
    binmap = []
    for y in range(H):
        f = fmin * (fmax / fmin) ** ((H - 1 - y) / (H - 1)); binmap.append(min(N // 2 - 1, max(1, int(f * N / FS))))
    for c in range(cols):
        seg = x[c * hop:c * hop + N]
        s = fft_fast([a * b for a, b in zip(seg, win)])
        for y in range(H):
            v = 20 * math.log10(s[binmap[y]] / (N / 4) + 1e-9)          # dBFS-ish
            u = max(0.0, min(1.0, (v + 90) / 80))
            r = int(255 * min(1, max(0, (u - 0.5) * 3))); g = int(255 * min(1, max(0, (u - 0.25) * 2.5) ** 1.2)); b = int(255 * (0.15 + 0.85 * (u ** 0.6)) * (1 - 0.6 * u))
            px[c, y] = (r, g, b)
        e = max(abs(v) for v in x[c * hop:(c + 1) * hop])
        h = int(min(1, e) * WF / 2)
        for yy in range(H + 7 + WF // 2 - h, H + 7 + WF // 2 + h + 1): px[c, yy] = (120, 200, 160)
    d = ImageDraw.Draw(img)
    for f in (50, 100, 200, 500, 1000, 2000, 5000, 10000):
        y = int(H - 1 - H * math.log(f / fmin) / math.log(fmax / fmin)); d.line([(0, y), (cols, y)], fill=(70, 70, 90)); d.text((2, y - 10), str(f), fill=(160, 160, 200))
    step_px = (int(60000 / bpm) / 4) * FS / 1000 / hop
    k = 0
    for sec, txt in (labels or []):
        xx = int(sec * FS / hop); d.line([(xx, 0), (xx, H + 12)], fill=(255, 120, 120)); d.text((xx + 3, H + WF + 2), txt, fill=(255, 200, 200))
    while grid and k * step_px < cols:
        xx = int(k * step_px)
        d.line([(xx, H), (xx, H + 5)], fill=(255, 255, 255) if k % 16 == 0 else (200, 200, 90) if k % 4 == 0 else (90, 90, 60))
        if k % 4 == 0: d.line([(xx, 0), (xx, H)], fill=(255, 255, 255, 40) if k % 16 == 0 else (45, 45, 60))
        k += 1
    if title: d.text((cols - 8 * len(title) - 6, 4), title, fill=(255, 255, 255))
    if cols < 1000:
        f = max(1, 1100 // cols); img = img.resize((cols * f, img.size[1]), Image.NEAREST)
    os.makedirs(os.path.dirname(path), exist_ok=True); img.save(path)
    return path


if __name__ == '__main__':
    print(__doc__)


def one_shot(kit, track, note=60, vel=110, ms=600, pattern_extra=None):
    """a single hit of `track` (pattern with one step, rendered with a tail)"""
    p = dict(shuffle=0, tracks=[dict(length=16, steps=[dict(i=0, vol=vel, note=note)] if t == track else []) for t in range(7)])
    return render(kit, p, 120, 1, tail_ms=ms)


def sheet(items, path, ms=600, gap_ms=120, width=1500):
    """items: [(label, kit, track, note, vel)] -> one spectrogram with every hit side by side, labelled; also prints hit features"""
    L, R, labels = [], [], []
    for label, kit, track, note, vel in items:
        l, r = one_shot(kit, track, note, vel, ms)
        n = int((ms + 120) * FS / 1000); l, r = l[:n], r[:n]
        l += [0.0] * (n - len(l)); r += [0.0] * (n - len(r))
        labels.append((len(L) / FS, label)); L += l; R += r
        x = mono_of((l, r)); st = next((i for i, v in enumerate(x) if abs(v) > 0.005), 0)
        print('%-34s peak %.2f  decay %4d ms  dom %6.0f Hz  centroid %6.0f Hz  hi/lo %+5.1f dB' % (label, max(abs(v) for v in x), decay_ms(x[st:]),
              dominant_hz(x, st), centroid_hz(x, st), band_db(x, st, 4000, 20000) - band_db(x, st, 40, 4000)))
    spectrogram((L, R), path, width=width, labels=labels, grid=False)
    write_wav(path.replace('.png', '.wav'), (L, R))
    return path
