"""Authoring framework for the LynnDrum preset library.

A library preset is exactly what the plugin already stores (Source/Plugin/PresetManager.cpp, schema 1): a kit (sound parameters by
stable id), up to 64 patterns (steps with velocity / probability / note / flam / shift / two p-locks, per-track length, shuffle),
a song and mutes. The only addition is an optional `meta` object (documentation: category, level, what it demonstrates, ...) which
the loader ignores and the preset browser shows. There is no second representation: `Preset.to_json()` produces the .lynnpreset.

Pattern notation (one string per track; the string length IS the track length, 1..64):

    '.' '-' no trigger  ('|' and spaces are ignored: use them to group)     '1'..'9'  trigger, velocity 14, 28 ... 127 (9 = 127)       'X'  accent (127)

    pat(k='9...7...9...7...', h='..5...5...5...5.', swing=54)          # track names: k d2 d3 s c h o  (tracks 0..6)

Per-step extras are applied with methods that return the pattern, so variations read as diffs of the core pattern:

    b = a.copy().lock('s', [12], 'Snare', 'Filter Freq', 110).note('d3', {0: 55, 4: 60}).at('k', 15, flam=1)

Remember (measured, see docs/preset-library.md): step velocity changes the level only if the voice has `Velocity > Volume` on,
and a step carries at most two p-locks, which hold until that track's next trigger.
"""
import json, os, sys, math, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from kitlib import *

PRESET_DIR = os.path.join(ROOT, 'Presets', 'factory')
TRACKS = {'k': 0, 'd2': 1, 'd3': 2, 's': 3, 'c': 4, 'h': 5, 'o': 6}
TRACK_NAMES = ['Kick (Drum 1)', 'Drum 2', 'Drum 3', 'Snare', 'Cymbal', 'Hi-hat closed', 'Hi-hat open']
GROUPS = {'d1': 'Drum 1', 'd2': 'Drum 2', 'd3': 'Drum 3', 'sn': 'Snare', 'cy': 'Cymbal', 'hh': 'Hi-hat', 'fx': 'FX', 'gl': 'Global'}
D1, D2, D3, SN, CY, HH, FX, GL = (V(GROUPS[k]) for k in ('d1', 'd2', 'd3', 'sn', 'cy', 'hh', 'fx', 'gl'))
END, LOOP = 64, 65
BALANCE_FILE = os.path.join(os.path.dirname(__file__), 'balance.json')
try: BALANCE = json.load(open(BALANCE_FILE))
except FileNotFoundError: BALANCE = {}
VOLUME_IDS = ['vol1', 'vol2', 'vol3', 'vol4', 'vol5', 'vol6']


# ---- helpers on parameter names ---------------------------------------------------------------------------------------
def pid(group, name):
    """parameter id from its group + display name, e.g. pid('Snare', 'Filter Freq') -> 'filter_freq_4'"""
    return voice_id(group, name)


def tgt(label):
    """index into the modulation-target list (the value of a velocity / LFO target parameter) from its label, e.g. 'Hi-hat: Filter Freq'"""
    import json as _j
    for i, t in enumerate(_j.load(open(os.path.join(ROOT, 'Tools/params/params.json')))['targets']):
        if t['label'] == label: return i
    raise KeyError(label)


_TARGETS = None
def target_par(index):
    """PAR_* number a velocity / LFO target index points at (0 = none)"""
    global _TARGETS
    if _TARGETS is None: _TARGETS = json.load(open(os.path.join(ROOT, 'Tools/params/params.json')))['targets']
    return _TARGETS[index]['par'] if index else 0


def modulated_pars(kit):
    """PAR_* numbers that a velocity or LFO modulator of the kit writes every control tick"""
    out = set()
    for ident, v in kit.items():
        d = BY_ID[ident]
        if d['kind'] == 'target' and v: out.add(target_par(v))
    return out


def midi_name(n):
    return ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'][n % 12] + str(n // 12 - 1)


def hz(n): return 440.0 * 2 ** ((n - 69) / 12)


def shuffle_for(swing_pct):
    """pattern shuffle value for a swing percentage (50 = straight, 66.7 = triplet); measured: delay of odd steps = shuffle * 0.265 % of a step pair"""
    return int(round(max(0.0, swing_pct - 50.0) / 0.265))


def swing_of(shuffle): return 50 + 0.265 * shuffle


def make_kit(*parts, base=None):
    k = dict(base or defaults())
    for p in parts: k.update(p)
    for key, v in k.items():
        d = BY_ID[key]
        if key in VOLUME_IDS: assert 1 <= v <= 1000, key        # design volumes are only a balance (see Preset.kit)
        else: assert d['min'] <= v <= d['max'], (key, v, d['min'], d['max'])
    return k


# ---- patterns -------------------------------------------------------------------------------------------------------------
VEL = {str(i): min(127, 14 * i + (1 if i == 9 else 0)) for i in range(1, 10)}; VEL['9'] = 127; VEL['X'] = 127


def _tr(t): return TRACKS[t] if isinstance(t, str) else t


class Pat:
    def __init__(self, rows, shuffle=0):
        self.shuffle = shuffle
        self.length = [16] * 7
        self.steps = [dict() for _ in range(7)]
        for name, row in rows.items():
            row = row.replace('|', '').replace(' ', ''); t = _tr(name); assert 1 <= len(row) <= 64, (name, len(row))
            self.length[t] = len(row)
            for i, ch in enumerate(row):
                if ch in VEL: self.steps[t][i] = dict(vol=VEL[ch])
                else: assert ch in '.-', (name, i, ch)

    def copy(self): return copy.deepcopy(self)

    def _step(self, track, step):
        t = _tr(track)
        if step not in self.steps[t]: raise KeyError('no trigger on track %s step %d (triggers are on %s)' % (track, step, sorted(self.steps[t])))
        return self.steps[t][step]

    def at(self, track, step, **kw):
        """modify a step: vol prob note flam shift (flam 0..5 = off,x2,x3,x4,x6,x8; shift 0..14 = -7..+7 of 24 per 16th)"""
        s = self._step(track, step)
        for k, v in kw.items():
            assert k in ('vol', 'prob', 'note', 'flam', 'shift'), k
            s[k] = v
        return self

    def set_length(self, track, n):
        assert 1 <= n <= 64; self.length[_tr(track)] = n; return self

    def add(self, track, step, vol=100, **kw):
        t = _tr(track); assert 0 <= step < self.length[t], 'step %d is outside the length (%d) of track %s: set_length() first' % (step, self.length[t], track)
        self.steps[t][step] = dict(vol=vol); return self.at(track, step, **kw)

    def remove(self, track, steps):
        for st in ([steps] if isinstance(steps, int) else steps): self.steps[_tr(track)].pop(st, None)
        return self

    def note(self, track, notes):
        """per-step note (60 = no change; each semitone = +1 semitone of every oscillator of the voice): {step: note} or {step: offset} via rel"""
        for st, n in notes.items(): self._step(track, st)['note'] = n
        return self

    def rel(self, track, offsets):
        """like note() but as semitone offsets from the unlocked pitch"""
        return self.note(track, {st: 60 + o for st, o in offsets.items()})

    def tune(self, track, offsets):
        """semitone offsets for the triggers of a track, in order (as many offsets as triggers): the melody of a pitched voice"""
        idx = sorted(self.steps[_tr(track)]); assert len(idx) == len(offsets), (track, len(idx), len(offsets), idx)
        return self.rel(track, dict(zip(idx, offsets)))

    def lock_seq(self, track, group, name, values):
        """p-lock values for the triggers of a track, in order; None leaves a trigger unlocked"""
        idx = sorted(self.steps[_tr(track)]); assert len(idx) == len(values), (track, len(idx), len(values), idx)
        return self.lock(track, None, group, name, {i: v for i, v in zip(idx, values) if v is not None})

    def lock(self, track, steps, group, name, value):
        """p-lock `name` of `group` to `value` (or per-step values: dict {step: value}) on those steps; uses the first free of the two slots"""
        ident = pid(group, name); d = BY_ID[ident]
        assert d['kind'] in ('int', 'choice', 'bool'), ident
        vals = value if isinstance(value, dict) else {s: value for s in steps}
        for st, v in vals.items():
            assert d['min'] <= v <= d['max'], (ident, v)
            s = self._step(track, st)
            slot = 'lock1' if 'lock1' not in s else 'lock2'
            assert slot == 'lock1' or 'lock2' not in s, 'step %s/%d already has two locks' % (track, st)
            assert all(s[x][0] != d['par'] for x in ('lock1', 'lock2') if x in s), 'duplicate lock'
            s[slot] = [d['par'], v]
        return self

    def rotate(self, track, n):
        """move every trigger of a track n steps later (negative = earlier), wrapping inside the track length: rhythmic displacement"""
        t = _tr(track); L = self.length[t]
        self.steps[t] = {(i + n) % L: s for i, s in self.steps[t].items()}
        return self

    def strip_locks(self):
        for tr in self.steps:
            for s in tr.values(): s.pop('lock1', None); s.pop('lock2', None)
        return self

    def to_json(self, index):
        tracks = []
        for t in range(7):
            steps = []
            for i in sorted(self.steps[t]):
                s = dict(i=i); s.update(self.steps[t][i]); steps.append(s)
            tracks.append(dict(length=self.length[t], steps=steps))
        return dict(index=index, shuffle=self.shuffle, tracks=tracks)

    def grid(self):
        """text rendering for docs / the console: one row per track (digit = velocity), then the per-step extras (identical extras are grouped)"""
        out = []; extras = []
        names = ['K', 'D2', 'D3', 'S', 'C', 'H', 'O']
        inv = lambda v: str(max(1, min(9, int(round(v / 14.1)))))
        for t in range(7):
            if not self.steps[t]: continue
            row = ''.join(inv(self.steps[t][i]['vol']) if i in self.steps[t] else '.' for i in range(self.length[t]))
            row = '|'.join(row[i:i + 4] for i in range(0, len(row), 4))
            out.append('%-4s %s' % (names[t], row))
            groups = {}                                            # description -> steps (1-based), in order of first appearance
            for i in sorted(self.steps[t]):
                s = self.steps[t][i]
                if s.get('note', 60) != 60: groups.setdefault('note %+d' % (s['note'] - 60), []).append(i + 1)
                if s.get('prob', 100) != 100: groups.setdefault('probability %d%%' % s['prob'], []).append(i + 1)
                if s.get('flam', 0): groups.setdefault('flam x%s' % [0, 2, 3, 4, 6, 8][s['flam']], []).append(i + 1)
                if s.get('shift', 7) != 7: groups.setdefault('shift %+d' % (s['shift'] - 7), []).append(i + 1)
                for k in ('lock1', 'lock2'):
                    if k in s:
                        d = next(p for p in PARAMS if p['par'] == s[k][0]); groups.setdefault('lock %s %s = %d' % (d['group'], d['name'], s[k][1]), []).append(i + 1)
            # locks of one parameter with many different values: show "lock X = a, b, c" in step order instead of one line per value
            by_param = {}
            for desc in list(groups):
                if desc.startswith('lock '):
                    param, val = desc[5:].rsplit(' = ', 1); by_param.setdefault(param, []).append((groups.pop(desc), val))
            for desc, steps in groups.items(): extras.append('%s step%s %s: %s' % (names[t], 's' if len(steps) > 1 else '', ','.join(map(str, steps)), desc))
            for param, lst in by_param.items():
                pairs = sorted((st, v) for steps, v in lst for st in steps)
                if len(pairs) == 1: extras.append('%s step %d: lock %s = %s' % (names[t], pairs[0][0], param, pairs[0][1]))
                elif len({v for _s, v in pairs}) == 1: extras.append('%s steps %s: lock %s = %s' % (names[t], ','.join(str(s) for s, _v in pairs), param, pairs[0][1]))
                else: extras.append('%s lock %s: %s' % (names[t], param, ', '.join('%d=%s' % (s, v) for s, v in pairs)))
        return out, extras

    def master_steps(self):
        return max(self.length)


def pat(swing=None, shuffle=None, **rows):
    """pat(k='9...', h='.5.5', swing=54): swing in percent (50 straight, 66.7 triplet) or the raw shuffle 0..127"""
    sh = shuffle if shuffle is not None else (shuffle_for(swing) if swing else 0)
    return Pat(rows, sh)


# ---- presets --------------------------------------------------------------------------------------------------------------
class Preset:
    def __init__(self, name, kit, patterns, meta, song=None, mutes=(), checks=(), gain=None, volumes=None, targets=None, rms_floor=None):
        self.name, self.patterns, self.meta, self.song, self.mutes, self.checks = name, list(patterns), dict(meta), song, mutes, list(checks)
        stored = BALANCE.get(name, {})
        self.gain = gain if gain is not None else stored.get('gain', 1.0)
        self.design_kit = dict(kit)
        self.targets = targets or {}
        self.rms_floor = rms_floor                     # audit: lowest acceptable pattern RMS (dB) for presets made of transients
        self.fixed_volumes = bool(volumes)
        volumes = volumes or stored.get('volumes')
        if volumes:                                  # (kick, drum2, drum3, snare, cymbal, hat): the balance found by `make_library.py --balance --write`
            assert len(volumes) == 6
            for ident, v in zip(VOLUME_IDS, volumes): self.design_kit[ident] = v
        assert 1 <= len(name) <= 40
        for key in ('category', 'level', 'character', 'technique', 'voices', 'key', 'bpm', 'demonstrates', 'patterns'):
            assert key in self.meta, (name, 'meta needs', key)
        assert self.meta['level'] in (1, 2, 3)
        assert len(self.meta['patterns']) == len(self.patterns), (name, 'one description per pattern')
        for q in self.patterns: validate(q)
        # ENGINE RULE (found while authoring, docs/preset-library.md): every control tick the engine rewrites the stored value of every parameter that a velocity or LFO
        # modulator targets, so a p-lock on such a parameter is undone within 1.5 ms. Refuse to build a preset that does this.
        dead = modulated_pars(self.design_kit)
        for pi, p in enumerate(self.patterns):
            for t in range(7):
                for i, s in p.steps[t].items():
                    for k in ('lock1', 'lock2'):
                        if k in s and s[k][0] in dead:
                            d = next(q for q in PARAMS if q['par'] == s[k][0])
                            raise ValueError('%s pattern %d: p-lock of "%s %s" is dead because a velocity/LFO target of the kit modulates that parameter' % (name, pi, d['group'], d['name']))

    @property
    def kit(self):
        """the kit as stored. The six voice Volumes of the design are only a balance between voices: they are scaled so the loudest is 127
        (the engine has no headroom beyond that: one sine voice at Volume 127 peaks near 0.25) and then by `gain` <= 1, one number per
        preset that the audit tunes so every preset peaks in the same range."""
        assert 0 < self.gain <= 1.0, self.name
        k = dict(self.design_kit)
        top = max(k[i] for i in VOLUME_IDS)
        for ident in VOLUME_IDS: k[ident] = max(1, int(round(k[ident] * 127.0 / top * self.gain)))
        return k

    def to_json(self, order=0):
        doc = dict(schema=1, name=self.name, kit=self.kit)
        doc['patterns'] = [p.to_json(i) for i, p in enumerate(self.patterns)]
        if self.song: doc['song'] = dict(enabled=False, entries=list(self.song) + [END] * (64 - len(self.song)))
        if any(self.mutes): doc['mutes'] = [1 if i in self.mutes else 0 for i in range(7)]
        m = dict(self.meta)
        m.setdefault('swing', ', '.join(sorted({'%d%%' % round(swing_of(p.shuffle)) for p in self.patterns})))
        m.setdefault('length', length_text(self.patterns))
        m['order'] = order
        doc['meta'] = m
        return doc

    def filename(self):
        return ''.join(c if c.isalnum() else '_' for c in self.name.lower()).strip('_').replace('__', '_') + '.lynnpreset'


def length_text(patterns):
    ls = sorted({l for p in patterns for l in p.length if l != 16} | {16}, key=lambda x: x)
    return '16' if ls == [16] else '16 (tracks of %s)' % ', '.join(str(x) for x in ls if x != 16)


def validate(p):
    for t in range(7):
        assert 1 <= p.length[t] <= 64
        for i, s in p.steps[t].items():
            assert 0 <= i < p.length[t], ('step outside track length', t, i)
            assert 1 <= s['vol'] <= 127 and 1 <= s.get('prob', 100) <= 100 and 0 <= s.get('flam', 0) <= 5 and 0 <= s.get('shift', 7) <= 14 and 0 <= s.get('note', 60) <= 127


def write_presets(presets, out_dir=PRESET_DIR):
    os.makedirs(out_dir, exist_ok=True)
    names = [p.name for p in presets]; assert len(set(names)) == len(names), 'duplicate preset names'
    files = []
    for n, p in enumerate(presets):
        for q in p.patterns: validate(q)
        fn = os.path.join(out_dir, p.filename()); files.append(fn)
        json.dump(p.to_json(order=100 + n), open(fn, 'w'), indent=1); open(fn, 'a').write('\n')
    return files
