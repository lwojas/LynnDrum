"""Audition and acceptance checks for library presets: nobody can listen in CI, so the audit renders every pattern through the real
engine + sequencer and reports what is measurable (level, clipping, density, per-track activity, and for demonstration presets
whether the technique is actually audible: locked hits must measurably differ from unlocked ones)."""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from library.core import *
from library.core import _tr
from lab import *            # after core: lab.render must win over measure.render

PEAK_TARGET = 0.8
SPEC_TARGET_PEAK = (0.30, 0.98)         # pattern peak at default Master (1.0); the plugin's Master goes to 2.0
SPEC_RMS_DB = (-27.0, -9.0)


def render_pattern(preset, idx, loops=2, bpm=None, solo=None, events=None, tail_ms=900):
    p = preset.patterns[idx]
    return render(preset.kit, p.to_json(0), bpm or preset.meta['bpm'], p.master_steps() * loops, solo=solo, events=events, tail_ms=tail_ms)


def level_db(x):
    r = math.sqrt(sum(v * v for v in x) / max(len(x), 1)); return 20 * math.log10(r + 1e-9)


def audit(preset, verbose=True, images=False):
    """-> list of problems (empty = pass). Prints a short report."""
    bad = []; peaks = []
    if verbose: print('== %s  [%s, level %d, %d bpm]' % (preset.name, preset.meta['category'], preset.meta['level'], preset.meta['bpm']))
    for i, p in enumerate(preset.patterns):
        ev = []
        lr = render_pattern(preset, i, events=ev)
        st = stats(lr); m = mono_of(lr)
        n = int(p.master_steps() * 2 * (60000 / preset.meta['bpm'] / 4) * FS / 1000)      # active part (two loops)
        db = level_db(m[:n])
        per = [sum(1 for e in ev if e[1] == t) for t in range(7)]
        flag = []
        dc = sum(m) / max(len(m), 1)
        if abs(dc) > 0.004: flag.append('DC offset %.4f (a constant level somewhere: an FX offset?)' % dc)
        if st['clipped'] > 0: flag.append('CLIPS %d' % st['clipped'])
        if not SPEC_TARGET_PEAK[0] <= st['peak'] <= SPEC_TARGET_PEAK[1]: flag.append('peak %.2f out of %s' % (st['peak'], SPEC_TARGET_PEAK))
        if not (preset.rms_floor if preset.rms_floor is not None else SPEC_RMS_DB[0]) <= db <= SPEC_RMS_DB[1]: flag.append('rms %.1f dB out of %s' % (db, SPEC_RMS_DB))
        if verbose: print('  pattern %s  peak %.2f  rms %5.1f dB  triggers/track(2 loops) %s %s' % ('ABCDEFGH'[i], st['peak'], db, per, ('  <-- ' + '; '.join(flag)) if flag else ''))
        if verbose and i == 0:
            solo = []
            for t in range(7):
                if per[t]:
                    x = mono_of(render_pattern(preset, 0, loops=1, solo=t, tail_ms=0))
                    solo.append('%s %+.0f/%+.0f' % (['K', 'D2', 'D3', 'S', 'C', 'H', 'O'][t], 20 * math.log10(max(abs(v) for v in x) + 1e-9), level_db(x)))
            print('  solo peak/rms (dBFS): ' + '  '.join(solo))
        bad += ['%s pattern %s: %s' % (preset.name, 'ABCDEFGH'[i], f) for f in flag]
        peaks.append(st['peak'])
    if verbose: print('  gain %.2f (stored by --balance)' % preset.gain)
    for desc, fn in preset.checks:
        ok = False
        try: ok = bool(fn(preset))
        except Exception as e: desc += '  (raised %r)' % e
        if verbose: print('  check: %-90s %s' % (desc, 'ok' if ok else 'FAILED'))
        if not ok: bad.append('%s check failed: %s' % (preset.name, desc))
    return bad


def preview(preset, out_dir=None, image=True):
    """WAV of every pattern played twice in order (and the song if any) + one spectrogram per pattern, into build-previews/<preset>/"""
    d = os.path.join(out_dir or OUT_DIR, preset.filename().replace('.lynnpreset', ''))
    L, R = [], []
    for i in range(len(preset.patterns)):
        lr = render_pattern(preset, i, loops=2)
        gap = int(0.25 * FS)
        L += lr[0] + [0.0] * gap; R += lr[1] + [0.0] * gap
        if image:
            p = preset.patterns[i]; lr1 = render_pattern(preset, i, loops=1, tail_ms=600)
            spectrogram(lr1, os.path.join(d, 'pattern_%s.png' % 'ABCDEFGH'[i]), bpm=preset.meta['bpm'], title='%s %s' % (preset.name, 'ABCDEFGH'[i]))
    write_wav(os.path.join(d, 'all_patterns.wav'), (L, R))
    return d


# ---- checks for "the technique is audible" -------------------------------------------------------------------------------
FEATURES = dict(peak=4, dominant=5, centroid=6, bright=7, decay=8)


def feature(preset, pattern, track, steps, feat, bpm=None):
    """mean of a measured feature over the triggers of `track` that sit on `steps` (first loop), from the soloed render"""
    p = preset.patterns[pattern]
    rows = hits(preset.kit, p.to_json(0), track, bpm or preset.meta['bpm'], p.master_steps(), window_ms=110)
    vals = [r[FEATURES[feat]] for r in rows if r[1] in steps]
    if not vals: raise ValueError('no hits of track %s on steps %s' % (track, steps))
    return sum(vals) / len(vals)


def differs(pattern, track, steps_a, steps_b, feat, ratio=None, delta=None):
    """check factory: the feature on steps_b differs from steps_a by at least `ratio` (x) or `delta` (absolute)"""
    t = _tr(track)

    def fn(preset):
        a = feature(preset, pattern, t, steps_a, feat); b = feature(preset, pattern, t, steps_b, feat)
        if ratio is not None: return max(a, b) / max(min(a, b), 1e-9) >= ratio
        return abs(a - b) >= delta
    return fn


def spread(pattern, track, feat, ratio):
    """check factory: over all triggers of the track the feature varies by at least `ratio` (max / min)"""
    t = _tr(track)

    def fn(preset):
        p = preset.patterns[pattern]
        rows = hits(preset.kit, p.to_json(0), t, preset.meta['bpm'], p.master_steps(), window_ms=110)
        v = [r[FEATURES[feat]] for r in rows if r[FEATURES[feat]] > 0]
        return len(v) > 1 and max(v) / min(v) >= ratio
    return fn


# ---- mix balance ----------------------------------------------------------------------------------------------------------
# loudness of each track relative to the kick (dB, RMS of the first 60 ms after each trigger at the pattern's own velocities):
# in a drum mix the kick sustains, so hats sit about 19 dB under it in this measure (about 6-9 dB under it in peak). Centre we aim for:
BALANCE_TARGET = {'k': 0.0, 'd2': -11.0, 'd3': -4.0, 's': -4.0, 'c': -13.0, 'h': -19.0, 'o': -17.0}
BAL_VOICE = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 5}


def solo_peaks(preset, window_ms=60):
    """loudness of every track at the pattern's own velocities: RMS over the first `window_ms` after each trigger (power-averaged over the
    triggers, max over the patterns). Peak alone misjudges noise voices: a hat's peak is an isolated spike, its energy is tiny."""
    out = {}
    for i, p in enumerate(preset.patterns):
        for t in range(7):
            if not p.steps[t]: continue
            ev = []
            x = mono_of(render_pattern(preset, i, loops=1, solo=t, tail_ms=0, events=ev))
            n = int(window_ms * FS / 1000); acc = []
            for e in ev:
                if e[1] != t: continue
                a0 = int(e[0] * FS / 1000); seg = x[a0:a0 + n]
                if len(seg) == n: acc.append(sum(v * v for v in seg) / n)
            if acc: out[t] = max(out.get(t, 0), math.sqrt(sum(acc) / len(acc)))
    return out


def balance(preset, passes=3, verbose=True):
    """suggest design volumes (kick, d2, d3, snare, cymbal, hat) that put every voice at its target level relative to the kick"""
    names = {v: n for n, v in TRACKS.items()}
    tgt_db = dict(BALANCE_TARGET); tgt_db.update(preset.targets)
    import copy
    q = copy.copy(preset); q.design_kit = dict(preset.design_kit); q.gain = 1.0
    vol = [float(q.design_kit[i]) for i in VOLUME_IDS]
    for _ in range(0 if preset.fixed_volumes else passes):
        for ident, v in zip(VOLUME_IDS, vol): q.design_kit[ident] = max(1, min(1000, int(round(v))))
        pk = solo_peaks(q)
        ref = pk.get(0) or max(pk.values())
        want = {}
        for t, v in pk.items():
            db_now = 20 * math.log10(v / ref); db_want = tgt_db[names[t]]
            want.setdefault(BAL_VOICE[t], []).append(db_want - db_now)
        for voice, diffs in want.items():
            if voice == 0 and 0 in pk: continue                                  # the kick is the reference
            vol[voice] *= 10 ** ((sum(diffs) / len(diffs)) / 20)
    top = max(vol[v] for v in range(6)); res = tuple(max(1, int(round(x / top * 127))) for x in vol)
    q.design_kit = dict(preset.design_kit)
    for ident, v in zip(VOLUME_IDS, res): q.design_kit[ident] = v
    def pk_at(g):
        q.gain = g; return max(stats(render_pattern(q, i, loops=2))['peak'] for i in range(len(q.patterns)))
    peak = pk_at(1.0); gain = min(1.0, round(PEAK_TARGET / peak, 2)) if peak < 0.999 else 0.5
    for _ in range(6):                                                      # a clipped peak under-reports: re-measure until it is clean
        p2 = pk_at(gain)
        if p2 <= 0.9 and (p2 >= 0.7 or gain >= 1.0): break
        gain = min(1.0, round(gain * PEAK_TARGET / max(p2, 0.01), 2))
    if verbose: print('  balance %-22s volumes=%s  peak at gain 1: %.2f  -> gain %.2f%s' % (preset.name, res, peak, gain, '   QUIET: needs more drive/level in the design' if peak < 0.45 else ''))
    return dict(volumes=list(res), gain=gain)


# ---- structural checks (timing, probability, flams) -------------------------------------------------------------------------
def events_of(preset, pattern, track, loops=1, seed=1):
    ev = []; p = preset.patterns[pattern]
    render(preset.kit, p.to_json(0), preset.meta['bpm'], p.master_steps() * loops, solo=_tr(track), seed=seed, tail_ms=200, events=ev)
    return [e for e in ev if e[1] == _tr(track)]


def swing_delay(pattern, track, lo, hi):
    """check factory: odd steps are delayed by between lo and hi milliseconds relative to even steps"""
    def fn(preset):
        step_ms = int(60000 / preset.meta['bpm']) / 4
        ev = events_of(preset, pattern, track)
        pos = [e[0] / step_ms for e in ev]
        odd = [(x - round(x)) * step_ms for x in pos if round(x) % 2 == 1]
        even = [(x - round(x)) * step_ms for x in pos if round(x) % 2 == 0]
        if not odd or not even: return False
        d = sum(odd) / len(odd) - sum(even) / len(even)
        return lo <= d <= hi
    return fn


def varies_with_seed(pattern, track):
    """check factory: with different random seeds the probabilistic track plays different hits"""
    def fn(preset):
        a = [round(e[0]) for e in events_of(preset, pattern, track, loops=2, seed=1)]
        b = [round(e[0]) for e in events_of(preset, pattern, track, loops=2, seed=7)]
        return a != b
    return fn


def max_triggers_per_step(pattern, track, at_least):
    """check factory: some step of the track fires `at_least` triggers (a flam)"""
    def fn(preset):
        step_ms = int(60000 / preset.meta['bpm']) / 4
        ev = events_of(preset, pattern, track); from collections import Counter
        return max(Counter(int(e[0] // step_ms) for e in ev).values()) >= at_least
    return fn
