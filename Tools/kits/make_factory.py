#!/usr/bin/env python3
"""Author the factory presets (clean-room: written for LynnDrum, no values copied from any LXR kit) and write
Presets/factory/*.lynnpreset. Each preset = a kit (sound parameters, by stable id) + an optional pattern.
Numbers were chosen with the formulas in docs/lxr-dsp.md and checked by measurement (measure.py): nobody can listen in CI,
so the report printed at the end (level, decay, pitch/brightness per voice) is the acceptance check; ears decide the rest.

usage: make_factory.py [--measure]     (the render binary build-core/lxr_render must exist for --measure)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from kitlib import *

OUT = os.path.join(ROOT, 'Presets/factory')
D1, D2, D3, SN, CY, HH, FX = V('Drum 1'), V('Drum 2'), V('Drum 3'), V('Snare'), V('Cymbal'), V('Hi-hat'), V('FX')

def kit(*parts, base=None):
    k = dict(base or {})
    for p in parts: k.update(p)
    for key, v in k.items():
        d = BY_ID[key]; assert d['min'] <= v <= d['max'], (key, v, d['min'], d['max'])
    return k

# ---- the Init kit: one plain voice each ----------------------------------------------------------------------------
INIT = kit(
    D1(Waveform=0, Coarse=31, Fine=63, Decay=32, Pitch_Mod=48, Pitch_Decay=34, Pitch_Slope=64, Volume=100),
    D2(Waveform=0, Coarse=45, Fine=63, Decay=28, Pitch_Mod=50, Pitch_Decay=28, Pitch_Slope=64, Volume=88),
    D3(Waveform=0, Coarse=55, Fine=63, Decay=24, Pitch_Mod=50, Pitch_Decay=26, Pitch_Slope=64, Volume=88),
    SN(Waveform=1, Coarse=57, Noise_Freq=127, Noise_Osc_Mix=70, Decay=17, Pitch_Mod=30, Pitch_Decay=20, Filter_Type=1, Filter_Freq=25, Volume=88),
    CY(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=100, Mod_Osc_1_Gain=110, Mod_Osc_2_Gain=110, Decay=58, Filter_Type=1, Filter_Freq=50, Volume=72),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=63, Mod_Osc_1_Gain=100, Mod_Osc_2_Gain=100, Filter_Type=1, Filter_Freq=90,
       Decay_closed=5, Decay_open=30, Volume=80),
    base=defaults())

def variant(name, **tweaks): return tweaks

# Velocity > Volume is OFF in the engine by default, and then a step's velocity changes nothing (found 2026-10-25 while building the demo library): the ghost notes and
# accents of the three patterned kits would play at full level. Switch it on for the kits whose patterns use velocity.
VEL = {}
for _v in (D1, D2, D3, SN, CY, HH): VEL.update(_v(Velocity_Volume=1))

TIGHT = kit(INIT, VEL,
    D1(Coarse=33, Decay=24, Pitch_Mod=58, Pitch_Decay=30), D2(Coarse=50, Decay=22), D3(Coarse=60, Decay=20),
    SN(Decay=14, Noise_Osc_Mix=85, Filter_Freq=40), CY(Decay=50, Coarse=105), HH(Decay_closed=3, Decay_open=22, Filter_Freq=100))
DEEP = kit(INIT, VEL,
    D1(Coarse=27, Decay=40, Pitch_Mod=40, Pitch_Decay=40), D2(Coarse=38, Decay=34), D3(Coarse=48, Decay=30),
    SN(Coarse=50, Decay=21, Noise_Osc_Mix=60, Filter_Freq=15), CY(Decay=66, Coarse=88, Mod_Osc_1_Freq=50), HH(Decay_closed=7, Decay_open=36, Filter_Freq=75))
METAL = kit(INIT, VEL,
    D1(FM_Amount=50, FM_Freq=70, Coarse=30, Decay=30, Pitch_Mod=45), D2(FM_Amount=70, FM_Freq=75, Coarse=48, Decay=24), D3(FM_Amount=80, FM_Freq=40, Coarse=66, Decay=22),
    SN(Waveform=3, Coarse=64, Noise_Osc_Mix=50, Decay=15, Pitch_Mod=0), CY(Wave_1=3, Wave_2=2, Wave_3=3, Coarse=85, Mod_Osc_1_Gain=127, Mod_Osc_1_Freq=80, Mod_Osc_2_Freq=40, Decay=64, Filter_Freq=70),
    HH(Wave_1=2, Wave_2=3, Wave_3=3, Coarse=75, Mod_Osc_1_Gain=127, Mod_Osc_2_Gain=127, Filter_Freq=100, Decay_closed=4, Decay_open=28))

# ---- patterns -------------------------------------------------------------------------------------------------------------
def pat(tracks, shuffle=0, lengths=None):
    out = []
    for t in range(7):
        steps = []
        for s in tracks.get(t, []):
            if isinstance(s, int): s = (s, 100)
            i, vol, *rest = s; o = dict(i=i, vol=vol)
            for k, v in zip(('prob', 'note', 'flam', 'shift'), rest): o[k] = v
            steps.append(o)
        out.append(dict(length=(lengths or {}).get(t, 16), steps=steps))
    return dict(shuffle=shuffle, tracks=out)

FOUR = pat({0: [(0, 118), (4, 112), (8, 118), (12, 112)], 3: [(4, 108), (12, 108)], 5: [(2, 80), (6, 80), (10, 80), (14, 80)], 6: [(14, 85)], 1: [(15, 60, 40)]})
BACK = pat({0: [(0, 118), (6, 100), (10, 112)], 3: [(4, 110), (12, 110), (7, 50, 45), (15, 55, 35)],
            5: [(i, 95 if i % 4 == 0 else 70) for i in range(0, 16, 2)], 6: [(11, 85)]}, shuffle=24)
BROKEN = pat({0: [(0, 118), (3, 100), (7, 105), (10, 118), (13, 95)], 3: [(4, 108, 100, 60, 1), (12, 108), (9, 55, 40), (14, 60, 50, 60, 0, 9)],
              5: [(i, 90 if i % 4 == 0 else 65, 85) for i in range(16)], 6: [(6, 80), (15, 80, 60)], 2: [(11, 80, 50), (13, 70, 50)],
              4: [(0, 85)]}, shuffle=40, lengths={4: 32, 2: 12})

def lock(p, track, step, slot, ident, value):
    """attach a p-lock (parameter id from the generated table) to an existing step of a pattern"""
    d = BY_ID[ident]; assert d['kind'] in ('int', 'choice', 'bool') and d['min'] <= value <= d['max'], ident
    for st in p['tracks'][track]['steps']:
        if st['i'] == step: st['lock%d' % slot] = [d['par'], value]; return p
    raise KeyError((track, step))

# variations (pattern 2 of each preset) and a song that uses them
FOUR_FILL = pat({0: [(0, 118), (4, 112), (8, 118), (12, 112)], 3: [(4, 108), (12, 108), (13, 80), (14, 90), (15, 100)], 5: [(i, 80) for i in range(0, 16, 2)],
                 2: [(12, 95), (14, 100)], 4: [(0, 85)]})
BACK_B = pat({0: [(0, 118), (6, 100), (8, 105), (10, 112)], 3: [(4, 110), (12, 110), (11, 55, 45)], 5: [(i, 90 if i % 4 == 0 else 65) for i in range(0, 16, 2)],
              6: [(6, 85), (14, 85)], 1: [(15, 80)]}, shuffle=24)
BROKEN_B = pat({0: [(0, 118), (10, 105)], 3: [(8, 108), (15, 70, 70, 60, 2)], 5: [(i, 85) for i in range(0, 16, 4)], 6: [(2, 80), (10, 80)],
                1: [(4, 85, 60), (6, 80, 60)], 4: [(0, 90)]}, shuffle=40, lengths={4: 32, 2: 12})
lock(BROKEN, 0, 10, 1, 'fmamnt1', 110)                      # the second kick hit gets a metallic FM bite
lock(BROKEN, 3, 12, 1, 'filter_freq_4', 60); lock(BROKEN, 3, 12, 2, 'reso_4', 70)   # and the backbeat snare a resonant filter sweep
END, LOOP = 64, 65
PRESETS = [('Init', INIT, [], None), ('Tight 4/4', TIGHT, [FOUR, FOUR_FILL], [0, 0, 0, 1, LOOP]),
           ('Deep Backbeat', DEEP, [BACK, BACK_B], [0, 0, 1, 0, LOOP]), ('Metal Broken', METAL, [BROKEN, BROKEN_B], [0, 1, LOOP])]

def validate_pattern(p):
    for t in p['tracks']:
        assert 1 <= t['length'] <= 64
        for s in t['steps']: assert 0 <= s['i'] < 64 and 1 <= s['vol'] <= 127 and 1 <= s.get('prob', 100) <= 100 and 0 <= s.get('flam', 0) <= 5 and 0 <= s.get('shift', 7) <= 14

def write():
    os.makedirs(OUT, exist_ok=True)
    for name, k, pats, song in PRESETS:
        for q in pats: validate_pattern(q)
        doc = dict(schema=1, name=name, kit=k)
        if pats: doc['patterns'] = [dict(index=i, **q) for i, q in enumerate(pats)]
        if song: doc['song'] = dict(enabled=False, entries=song + [END] * (64 - len(song)))
        fn = os.path.join(OUT, name.lower().replace(' ', '_').replace('/', '') + '.lynnpreset')
        if name == 'Init': fn = os.path.join(OUT, 'init.lynnpreset')
        json.dump(doc, open(fn, 'w'), indent=1, sort_keys=False); open(fn, 'a').write('\n')
        print('wrote', os.path.relpath(fn, ROOT))

def pattern_script(p):
    L = ['shuf 0 %d' % p['shuffle']]
    for t, tr in enumerate(p['tracks']):
        L.append('len 0 %d %d' % (t, tr['length']))
        for s_ in tr['steps']:
            L += ['ms 0 %d %d 1' % (t, s_['i']), 'sd 0 %d %d %d %d %d' % (t, s_['i'], s_['vol'], s_.get('prob', 100), s_.get('note', 60)),
                  'st 0 %d %d %d %d' % (t, s_['i'], s_.get('flam', 0), s_.get('shift', 7))]
    return L

def render_seq(lines, blocks):
    import tempfile, wave, struct, subprocess
    exe = os.path.join(ROOT, 'build-core', 'lxr_render_seq')
    with tempfile.TemporaryDirectory() as t:
        sc = os.path.join(t, 's.lxr'); open(sc, 'w').write('seed 1\nbpm 120\n' + '\n'.join(lines) + f'\nrun 1\nplay {blocks}\n')
        subprocess.run([exe, sc, '-o', os.path.join(t, 'o')], check=True, capture_output=True)
        outs = []
        for bus in ('dac1', 'dac2'):
            w = wave.open(os.path.join(t, f'o.{bus}.wav')); d = w.readframes(w.getnframes()); outs.append(struct.unpack('<%dh' % (len(d) // 2), d))
        return [max(abs(a), abs(b)) / 32768 for a, b in zip(outs[0], outs[1])]

def measure():
    VOICES = [('Kick (D1)', 0, 36), ('Tom (D2)', 1, 41), ('Tom (D3)', 2, 43), ('Snare', 3, 38), ('Cymbal', 4, 49), ('CH', 5, 42), ('OH', 6, 46)]
    bad = 0
    for name, k, pats, _song in PRESETS:
        print('==', name)
        for vn, voice, _n in VOICES:
            x = mono(render(par_lines(k) + [f'trig {voice} 60 115'], 900))
            st = next((i for i, v in enumerate(x) if abs(v) > 0.01), 0)
            pk, dec = peak(x), decay_ms(x)
            print(f'  {vn:10s} peak {pk:4.2f} decay(-40dB) {dec:5.0f} ms dominant {dominant_hz(x, st):6.0f} Hz centroid {centroid_hz(x, st):6.0f} Hz')
            if not (0.05 < pk < 1.9): print('   ^ LEVEL OUT OF RANGE'); bad += 1
        # all voices together must not clip hard
        for pi, p in enumerate(pats):
            pk = render_seq(par_lines(k) + pattern_script(p), 2750)       # 2 bars at 120 bpm (5.5 s)
            clipped = sum(1 for v in pk if v >= 0.999)
            print(f'  pattern {pi + 1}, 2 bars: peak {max(pk):.2f}, clipped samples {clipped}'); bad += clipped > 20
    return bad

if __name__ == '__main__':
    write()
    if '--measure' in sys.argv: sys.exit(1 if measure() else 0)
