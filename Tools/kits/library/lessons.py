"""Level 3: one technique per preset, as obvious as it can be made while staying musical. Pattern A is always the plain version; the next patterns
add the technique to the same rhythm, so A/B comparison is the lesson."""
from library.core import *
from library.audit import differs, spread, swing_delay, varies_with_seed, max_triggers_per_step

PRESETS = []

# shared context sounds (a clean kick, a clap, a hat) so a lesson is about one thing and the beat around it is just a beat
def ctx_kick(**kw): return D1(Waveform=0, Coarse=30, Decay=18, Pitch_Mod=60, Pitch_Decay=24, Drive=55, Velocity_Volume=1, **kw)
def ctx_clap(**kw): return SN(Waveform=4, Coarse=57, Noise_Osc_Mix=127, Decay=19, Pitch_Mod=0, Filter_Type=2, Filter_Freq=62, Resonance=15, Click_Type=9, Click_Level=85, Drive=30,
                              Velocity_Volume=1, **kw)
def ctx_hat(**kw):
    base = dict(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=64, Mod_Osc_1_Gain=100, Mod_Osc_2_Gain=100, Filter_Type=1, Filter_Freq=72, Decay_closed=3, Decay_open=20, Drive=85, Velocity_Volume=1)
    base.update(kw); return HH(**base)
def silent(*groups): return [g(Volume=1) for g in groups]


# =====================================================================================================================
# Filter Motion
# =====================================================================================================================
FM_KIT = make_kit(
    ctx_kick(), ctx_clap(),
    # two identical saw bass voices with a resonant low-pass. Drum 3 is moved by p-locks; Drum 2 by a tempo-synced triangle LFO (amount 0 until a pattern locks it on).
    # (A parameter can not be both locked and LFO-targeted: the engine rewrites an LFO target every control tick, which undoes a lock.)
    D3(Waveform=2, Coarse=31, Decay=12, Pitch_Mod=0, Filter_Type=0, Filter_Freq=40, Resonance=40, Drive=45, Velocity_Volume=1),
    D2(Waveform=2, Coarse=31, Decay=12, Pitch_Mod=0, Filter_Type=0, Filter_Freq=40, Resonance=40, Drive=45, Velocity_Volume=1,
       LFO_Wave=1, LFO_Sync=3, LFO_Amount=0, LFO_Target=tgt('Drum 2: Filter Freq')),
    ctx_hat(LFO_Wave=1, LFO_Sync=4, LFO_Amount=0, LFO_Target=tgt('Hi-hat: Filter Freq')),
    *silent(CY))
_fm_base = dict(k='9...9...9...9...' * 2, s='....8.......8...' * 2, h='6.4.6.4.6.4.6.4.' * 2)
_bass = '.55..55..55..55.' * 2
FM_A = pat(swing=50, d3=_bass, **_fm_base)                                                 # static: every cutoff constant
FM_B = FM_A.copy()
_ramp = [30 + int(round(i * 80 / 7)) for i in range(8)]
FM_B.lock_seq('d3', 'Drum 3', 'Filter Freq', _ramp + _ramp[::-1])                          # a stepped sweep up, then down, over two bars
FM_C = pat(swing=50, d2=_bass, **_fm_base)                                                 # the same bass line on the LFO voice
FM_C.lock('d2', sorted(FM_C.steps[1]), 'Drum 2', 'LFO Amount', 80).lock('h', sorted(FM_C.steps[5]), 'Hi-hat', 'LFO Amount', 70)   # the LFOs are switched on, per hit
FM_D = FM_B.copy()
PRESETS.append(Preset('Filter Motion', FM_KIT, [FM_A, FM_B, FM_C], dict(
    category='Technique', level=3, character='simple 4/4 with a moving filter',
    technique='filter cutoff as the only thing that changes: stepped sweeps by p-lock and smooth sweeps by LFO',
    secondary=['LFO amount used as a per-hit switch', 'tempo-synced triangle LFOs (1/1 on the bass, 1/2 on the hat)', 'a locked parameter must not also be an LFO target'],
    voices='Kick, clap: plain. Drum 3 and Drum 2: the same saw bass with resonant low-pass (Drum 3 locked, Drum 2 LFO). Hat: driven, high-pass, LFO amount 0 in the kit.',
    key='G (bass G1)', bpm=124,
    demonstrates='Filter modulation makes movement without changing the rhythm: A is static, B moves the bass cutoff by a p-lock on every step (up, then down over two bars), '
                 'C plays the same bass line on a twin voice whose cutoff an LFO sweeps smoothly, and the hats\' high-pass is swept too (the locks only switch the LFOs on).',
    patterns=['A: static (every cutoff constant)', 'B: bass cutoff locked step by step (stepped sweep)', 'C: same line on the LFO twin voice, LFO switched on per hit']),
    song=[0, 0, 1, 1, 2, 2, LOOP], volumes=(84, 127, 127, 94, 1, 31),
    checks=[('A: bass is static (same brightness every hit)', lambda p: not spread(0, 'd3', 'centroid', 1.15)(p)),
            ('B: the stepped sweep changes the bass brightness a lot', spread(1, 'd3', 'centroid', 2.0)),
            ('C: the LFO changes the bass brightness', spread(2, 'd2', 'centroid', 1.6))]))

# =====================================================================================================================
# Pitch Percussion
# =====================================================================================================================
PP_KIT = make_kit(
    ctx_kick(), ctx_clap(),
    # drum 2: a marimba-like tom (sine, a little FM, short click); drum 3: a low tom
    D2(Waveform=0, FM_Waveform=0, Coarse=60, FM_Amount=20, FM_Freq=80, Decay=13, Pitch_Mod=12, Pitch_Decay=10, Click_Type=12, Click_Level=25, Drive=25, Velocity_Volume=1),
    D3(Waveform=0, Coarse=48, Decay=22, Pitch_Mod=40, Pitch_Decay=22, Drive=35, Velocity_Volume=1),
    ctx_hat(), *silent(CY))
PP_A = pat(swing=52, k='9...9...9...9...' * 2, s='........8.......' * 2, h='.4.4.4.4.4.4.4.4' * 2, d2='9..7..8.9..7.8..' * 2, d3='...9.......9....' * 2)
PP_B = PP_A.copy().tune('d2', [0, 7, 4, 12, 9, 7, 14, 12, 9, 7, 4, 2]).tune('d3', [0, -5, -3, -7])     # same rhythm: a pentatonic line over a low answer
PP_C = PP_A.copy().tune('d2', [12, 16, 9, 19, 14, 7, 21, 19, 16, 14, 9, 7]).tune('d3', [-7, -12, -10, -14])   # an octave and a fifth higher; the answer lower
PRESETS.append(Preset('Pitch Percussion', PP_KIT, [PP_A, PP_B, PP_C], dict(
    category='Technique', level=3, character='tuned toms playing a tune',
    technique='per-step note on a drum voice: one tom becomes a melodic instrument',
    secondary=['two-voice answer (drum 2 / drum 3)', 'range of two and a half octaves from one voice'],
    voices='Kick, clap, hat: plain. Drum 2: marimba-like tom. Drum 3: low tom.',
    key='C major pentatonic (C D E G A)', bpm=118,
    demonstrates='A drum voice has a pitch, and the step note moves it by semitones from the kit tuning. A plays the toms on one pitch; B plays the same rhythm as a melody; '
                 'C stretches it to two and a half octaves.',
    patterns=['A: plain: the toms on a single pitch', 'B: the same rhythm as a pentatonic melody', 'C: the melody an octave and a fifth higher, the answer lower']),
    song=[0, 0, 1, 1, 2, 2, LOOP],
    checks=[('A: tom hits are all the same pitch', lambda p: not spread(0, 'd2', 'dominant', 1.15)(p)),
            ('B: tom hits cover a wide pitch range', spread(1, 'd2', 'dominant', 1.8)),
            ('C: even wider', spread(2, 'd2', 'dominant', 2.0))]))

# =====================================================================================================================
# One Voice, Six Drums
# =====================================================================================================================
OV_KIT = make_kit(
    D3(Waveform=0, Coarse=43, Decay=18, Pitch_Mod=60, Pitch_Decay=24, Drive=40, Filter_Type=1, Filter_Freq=8, Velocity_Volume=1),
    *silent(D1, D2, SN, CY, HH))
RECIPES = {   # name: (note offset, [(group, param, value), ...]): at most two locks per step
    'kick': (-17, [('Drum 3', 'Decay', 22)]),
    'snare': (5, [('Drum 3', 'Waveform', 4), ('Drum 3', 'Decay', 14)]),
    'hat': (24, [('Drum 3', 'Waveform', 4), ('Drum 3', 'Decay', 3)]),
    'tom': (7, [('Drum 3', 'Decay', 16)]),
    'bell': (24, [('Drum 3', 'FM Amount', 100), ('Drum 3', 'Decay', 26)]),
    'bass': (-12, [('Drum 3', 'Pitch Mod', 0), ('Drum 3', 'Decay', 30)]),
}
OV_ROW = '9.7.9.8.9.7.9.8.'
OV_A = pat(swing=50, d3=OV_ROW)
OV_B = pat(swing=50, d3=OV_ROW)
_names = ['kick', 'hat', 'snare', 'hat', 'kick', 'tom', 'snare', 'bell']
for step, nm in zip(sorted(OV_B.steps[2]), _names):
    n, locks = RECIPES[nm]; OV_B.at('d3', step, note=60 + n)
    for g, p_, v in locks: OV_B.lock('d3', [step], g, p_, v)
OV_C = pat(swing=50, d3='9.7.9.8.9.7.9.8.9.7.9.8.9.7.9.8.')
_names_c = ['kick', 'hat', 'snare', 'hat', 'kick', 'hat', 'snare', 'tom', 'kick', 'bass', 'snare', 'hat', 'bell', 'hat', 'snare', 'tom']
for step, nm in zip(sorted(OV_C.steps[2]), _names_c):
    n, locks = RECIPES[nm]; OV_C.at('d3', step, note=60 + n)
    for g, p_, v in locks: OV_C.lock('d3', [step], g, p_, v)
PRESETS.append(Preset('One Voice, Six Drums', OV_KIT, [OV_A, OV_B, OV_C], dict(
    category='Technique', level=3, character='a whole kit from one voice',
    technique='parameter locks + step note turn Drum 3 into a kick, snare, hat, tom, bell and bass',
    secondary=['waveform lock (sine -> noise)', 'decay locks from 3 to 30', 'FM amount lock for the bell, pitch-mod lock for the bass'],
    voices='Only Drum 3 plays (every other voice is silent). Kit: sine with pitch envelope, drive, light high-pass.',
    key='no tuned key; the note offsets are per drum (kick -17, hat +24, bell +24, bass -12)', bpm=100,
    demonstrates='Each step carries at most two locks and a note: a note offset and a decay lock make kick, tom and bass; a waveform lock to noise makes snare and hat; an FM lock makes the bell. '
                 'A is the voice unlocked: all eight hits identical.',
    patterns=['A: the voice unlocked (eight identical hits)', 'B: the same eight hits as kick, hat, snare, hat, kick, tom, snare, bell', 'C: two bars, six different drums']),
    song=[0, 0, 1, 1, 2, 2, LOOP], volumes=(1, 1, 127, 1, 1, 1),
    checks=[('A: the eight hits are identical', lambda p: not spread(0, 'd3', 'centroid', 1.1)(p)),
            ('B: the hits are very different from each other (centroid spread > 10x)', spread(1, 'd3', 'centroid', 10.0)),
            ('C: also', spread(2, 'd3', 'centroid', 10.0))]))

# =====================================================================================================================
# Locked Kick
# =====================================================================================================================
LK_KIT = make_kit(
    D1(Waveform=0, Coarse=30, Decay=18, Pitch_Mod=55, Pitch_Decay=24, Drive=50, Click_Type=2, Click_Level=0, Velocity_Volume=1),
    ctx_clap(), ctx_hat(), *silent(D2, D3, CY))
_lk = dict(s='....8.......8...' * 4, h='..5...5...5...5.' * 4, o='.4.4.4.4.4.4.4.4' * 4)
LK_A = pat(swing=50, k='9...9...9...9...' * 4, **_lk)
LK_B = LK_A.copy()
# sixteen kick hits, four bars: (note offset, [(param, value), ...]); the rhythm never changes
_states = [
    (0, []), (0, []), (0, []), (3, [('Decay', 11)]),                                              # bar 1: a plain bar that ends higher and shorter (a phrase ending)
    (0, [('Pitch Mod', 100)]), (0, [('Drive', 110), ('Decay', 24)]), (0, [('Click Level', 100)]), (-5, [('Decay', 38)]),   # bar 2: snappy, crunchy, clicky, boom
    (0, [('FM Amount', 70), ('FM Freq', 50)]), (0, [('Waveform', 3), ('Filter Freq', 45)]), (0, [('Pitch Decay', 60)]), (0, [('Decay', 10), ('Pitch Mod', 100)]),  # bar 3: metal, square, zap, tick
    (0, [('Decay', 14)]), (-3, [('Decay', 20)]), (-6, [('Decay', 28)]), (-9, [('Decay', 40)])]  # bar 4: a falling, lengthening scale
for step, (n, locks) in zip(sorted(LK_B.steps[0]), _states):
    if n: LK_B.at('k', step, note=60 + n)
    for name, v in locks: LK_B.lock('k', [step], 'Drum 1', name, {step: v})
PRESETS.append(Preset('Locked Kick', LK_KIT, [LK_A, LK_B], dict(
    category='Technique', level=3, character='four on the floor, sixteen different kicks',
    technique='per-step locks on one drum voice: the rhythm is identical, the timbre is not',
    secondary=['phrase-ending pitch/decay lock', 'drive, click, FM, waveform and pitch-envelope locks', 'a falling scale by note and decay'],
    voices='Kick: sine with pitch envelope and drive. Clap, hat: plain (the beat that stays the same).',
    key='G (kick 49 Hz)', bpm=126,
    demonstrates='Four bars of four-on-the-floor in which no kick is like its neighbour: bar 1 ends higher and shorter; bar 2 is snappy, crunchy, clicky and a boom; bar 3 is metallic, square, a laser zap and a tick; '
                 'bar 4 falls. Every hit has at most two locks and a note. A is the same kick sixteen times.',
    patterns=['A: sixteen identical kicks', 'B: four bars, sixteen different kicks, the same rhythm']),
    song=[0, 0, 1, 1, LOOP],
    checks=[('A: the kicks are identical', lambda p: not spread(0, 'k', 'centroid', 1.1)(p)),
            ('B: the kicks differ strongly in brightness', spread(1, 'k', 'centroid', 2.5)),
            ('B: and in length', spread(1, 'k', 'decay', 3.0))]))

# =====================================================================================================================
# Evolving Snare
# =====================================================================================================================
ES_KIT = make_kit(
    ctx_kick(), 
    SN(Waveform=1, Coarse=55, Noise_Osc_Mix=70, Decay=14, Pitch_Mod=35, Pitch_Decay=20, Filter_Type=1, Filter_Freq=30, Drive=45, Click_Type=11, Click_Level=50, Velocity_Volume=1),
    ctx_hat(), *silent(D2, D3, CY))
ES_A = pat(swing=50, k='9...9...9...9...' * 4, s='....8.......8...' * 4, h='.4.4.4.4.4.4.4.4' * 4, o='..5...5...5...5.' * 4)
ES_B = ES_A.copy()
_s_states = [
    [],                                                                    # 1 plain
    [('Decay', 8)],                                                        # 2 tight and high (note +7)
    [('Attack', 12), ('Repeat Count', 4)],                                 # 3 repeat counter (needs an attack time: it is the spacing of the repeats): a clap-like flutter
    [('Waveform', 0), ('Noise / Osc Mix', 20)],                            # 4 sine body: a tonal rim / tom
    [('Filter Freq', 90), ('Decay', 24)],                                  # 5 only the high noise: airy
    [('Decay', 26)],                                                       # 6 deep thud (note -12)
    [('Click Level', 127), ('Click Type', 9)],                             # 7 a sample clap on top
    [('Decay', 40), ('Filter Freq', 10)],                                  # 8 full-band, long
]
_s_notes = [0, 7, 0, 0, 0, -12, 0, 0]
for step, locks, n in zip(sorted(ES_B.steps[3]), _s_states, _s_notes):
    if n: ES_B.at('s', step, note=60 + n)
    for name, v in locks: ES_B.lock('s', [step], 'Snare', name, {step: v})
ES_C = ES_A.copy()
ES_C.lock_seq('s', 'Snare', 'Noise / Osc Mix', [0, 20, 40, 60, 80, 100, 115, 127]).lock_seq('s', 'Snare', 'Decay', [24, 22, 20, 18, 16, 14, 12, 10])   # a scan from tone to noise
PRESETS.append(Preset('Evolving Snare', ES_KIT, [ES_A, ES_B, ES_C], dict(
    category='Technique', level=3, character='one backbeat, eight snares',
    technique='locks on the snare voice: noise mix, filter, decay, waveform, repeat counter, click layer',
    secondary=['repeat counter as a clap flutter', 'sample layer by Click Type lock', 'a morph from tone to noise across bars'],
    voices='Kick, hat: plain. Snare: triangle + noise, high-passed, driven, sample snare click.',
    key='no key (snare body D3; B uses note offsets +7 and -12)', bpm=120,
    demonstrates='The snare plays on 2 and 4 for four bars and is a different drum each time: B changes its length, filter, waveform, repeat counter and sample layer; '
                 'C morphs it from a pure tone to pure noise (Noise/Osc Mix locked 0 -> 127) while the decay shortens.',
    patterns=['A: the same snare eight times', 'B: eight different snares (tight, clap, rim, airy, thud, sample, long)', 'C: one scan from tone to noise']),
    song=[0, 0, 1, 1, 2, 2, LOOP],
    checks=[('A: the snares are identical', lambda p: not spread(0, 's', 'centroid', 1.1)(p)),
            ('B: the snares differ strongly in character', spread(1, 's', 'centroid', 1.8)),
            ('C: the scan goes from dark (tone) to bright (noise)', differs(2, 's', [4], [60], 'centroid', ratio=2.0))]))

# =====================================================================================================================
# Moving Hats
# =====================================================================================================================
MH_KIT = make_kit(
    ctx_kick(), ctx_clap(),
    ctx_hat(LFO_Wave=1, LFO_Sync=4, LFO_Amount=0, LFO_Target=tgt('Hi-hat: Filter Freq')), *silent(D2, D3, CY))
_h = '6.4.5.4.6.4.5.4.' * 2
_hat_rows = dict(k='9...9...9...9...' * 2, s='....8.......8...' * 2, h=_h)
MH_A = pat(swing=50, **_hat_rows)
def _hat_lfo(pattern, locks):
    q = pattern.copy()
    for name, v in locks: q.lock('h', sorted(q.steps[5]), 'Hi-hat', name, v)
    return q
MH_B = _hat_lfo(MH_A, [('LFO Amount', 60)])                                                            # kit: triangle, 1/2 note
MH_C = _hat_lfo(MH_A, [('LFO Amount', 60), ('LFO Sync', 7)])                                           # sync 1/6: three times faster
MH_D = _hat_lfo(MH_A, [('LFO Amount', 70), ('LFO Wave', 5)])                                           # sample-and-hold: random cutoff per cycle
PRESETS.append(Preset('Moving Hats', MH_KIT, [MH_A, MH_B, MH_C, MH_D], dict(
    category='Technique', level=3, character='the same hi-hat row, four ways of moving',
    technique='a tempo-synced LFO on the hat filter, switched on and shaped by locks (amount, sync, wave)',
    secondary=['LFO amount as a per-hit switch', 'sync division and waveform changed by lock', 'high-pass sweep changes level as well as colour'],
    voices='Kick, clap: plain. Hat: driven, high-pass; LFO target = hat filter freq, amount 0 in the kit.',
    key='no key', bpm=126,
    demonstrates='A static hat row becomes alive without adding a note: B sweeps the high-pass slowly (triangle, half-note), C three times faster (1/6), D randomly (sample-and-hold). '
                 'The kit stores the LFO with amount 0; each pattern only locks the amount (and sync / wave) on the hat steps.',
    patterns=['A: static hats', 'B: slow triangle sweep', 'C: fast triangle sweep (1/6)', 'D: sample-and-hold (random) cutoff']),
    song=[0, 0, 1, 1, 2, 2, 3, 3, LOOP],
    checks=[('A: static hats (same brightness)', lambda p: not spread(0, 'h', 'centroid', 1.35)(p)),
            ('B: hats vary in brightness', spread(1, 'h', 'centroid', 1.5)),
            ('C: hats vary in brightness', spread(2, 'h', 'centroid', 1.5)),
            ('D: hats vary in brightness', spread(3, 'h', 'centroid', 1.5))]))

# =====================================================================================================================
# Metallic FM
# =====================================================================================================================
MF_KIT = make_kit(
    ctx_kick(),
    # (the FM depth follows the pitch envelope: Pitch Mod 0 = no pitch dive, a long Pitch Decay keeps the depth through the hit)
    D2(Waveform=0, FM_Waveform=0, Coarse=64, FM_Amount=0, FM_Freq=100, Decay=14, Pitch_Mod=0, Pitch_Decay=60, Drive=30, Velocity_Volume=1),
    D3(Waveform=1, FM_Waveform=0, Coarse=52, FM_Amount=0, FM_Freq=85, Decay=18, Pitch_Mod=0, Pitch_Decay=60, Drive=30, Velocity_Volume=1),
    *silent(SN, CY, HH))
_mf_k = '9...9...9...9...' * 2
_mf = '9.7.8.7.9.7.8.7.' * 2
MF_A = pat(swing=50, k=_mf_k, d2=_mf)                                                                  # FM 0: a soft sine tom
MF_B = MF_A.copy().lock_seq('d2', 'Drum 2', 'FM Amount', [int(i * 127 / 15) for i in range(16)])      # FM amount ramps 0 -> 127: wood to metal
MF_C = MF_A.copy().lock('d2', sorted(MF_A.steps[1]), 'Drum 2', 'FM Amount', 85).lock_seq('d2', 'Drum 2', 'FM Freq', [int(10 + i * 110 / 15) for i in range(16)])   # fixed FM amount, ratio sweeps
MF_D = pat(swing=50, k=_mf_k, d2=_mf, d3='........9.......' * 2)
MF_D.lock_seq('d2', 'Drum 2', 'FM Amount', [int(i * 127 / 15) for i in range(16)]).lock('d3', sorted(MF_D.steps[2]), 'Drum 3', 'FM Amount', 110).tune('d3', [-7, -12])
PRESETS.append(Preset('Metallic FM', MF_KIT, [MF_A, MF_B, MF_C, MF_D], dict(
    category='Technique', level=3, character='soft tone to bell to clang, on the same rhythm',
    technique='FM amount and FM ratio (FM freq) as timbre dials, locked per hit',
    secondary=['modulator ratio sweep at constant depth', 'FM through the pitch envelope: depth falls as the hit decays', 'second FM voice an octave and more below'],
    voices='Kick: plain. Drum 2: sine FM\'d by a sine (FM amount 0 in the kit). Drum 3: the same, lower.',
    key='E (drum 2 E4, drum 3 A3; D keeps the octave under)', bpm=110,
    demonstrates='FM Amount is the timbre dial: in B it rises across sixteen hits from 0 to 127, so one tom changes from a soft sine tone to a wooden knock to a metallic clang '
                 'without changing pitch or rhythm. C holds the depth and sweeps the modulator ratio instead, which moves the inharmonic partials.',
    patterns=['A: FM 0: a soft sine tom', 'B: FM amount ramps 0 -> 127 over 16 hits', 'C: FM amount fixed, ratio sweeps', 'D: B plus a second FM voice, lower, bright']),
    song=[0, 0, 1, 1, 2, 2, 3, 3, LOOP],
    checks=[('A: the toms are identical', lambda p: not spread(0, 'd2', 'centroid', 1.1)(p)),
            ('B: brightness rises a lot across the ramp (wood to metal)', differs(1, 'd2', [0], [30], 'centroid', ratio=4.0)),
            ('C: the ratio sweep changes the timbre', spread(2, 'd2', 'centroid', 1.8))]))

# =====================================================================================================================
# Envelope Clicks
# =====================================================================================================================
EC_KIT = make_kit(
    # everything is a few milliseconds long: a sine thump of one block plus a sample click, a 1-block sine blip, noise snaps
    D1(Waveform=0, Coarse=38, Decay=1, Pitch_Mod=90, Pitch_Decay=3, Click_Type=5, Click_Level=127, Click_Pitch=40, Drive=100, Velocity_Volume=1),
    D2(Waveform=0, Coarse=84, Decay=1, Pitch_Mod=30, Pitch_Decay=4, FM_Amount=25, FM_Freq=90, Drive=30, Velocity_Volume=1),
    D3(Waveform=1, Coarse=72, Decay=0, Pitch_Mod=0, Click_Type=4, Click_Level=127, Click_Pitch=70, Velocity_Volume=1),
    SN(Waveform=4, Coarse=80, Noise_Osc_Mix=127, Decay=1, Pitch_Mod=0, Filter_Type=1, Filter_Freq=40, Drive=60, Velocity_Volume=1),
    CY(Wave_1=4, Wave_2=4, Wave_3=4, Coarse=90, Decay=1, Attack=0, Filter_Type=2, Filter_Freq=100, Resonance=40, Drive=60, Velocity_Volume=1),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=80, Mod_Osc_1_Gain=100, Mod_Osc_2_Gain=100, Filter_Type=1, Filter_Freq=75, Decay_closed=0, Decay_open=2, Drive=90, Velocity_Volume=1))
EC_A = pat(swing=52,
    k='9..7..9..7.7..7.' * 2, d2='..5..4...5..4.5.' * 2, d3='.4.5.4.5.4.5.4.5' * 2, s='....9.......9.5.' * 2, c='......5.......3.' * 2, h='5.3.5.3.5.3.5.3.' * 2)
EC_B = EC_A.copy()
EC_B.lock_seq('d2', 'Drum 2', 'Decay', [0, 1, 2, 3, 5, 8, 12, 18, 26, 36])
PRESETS.append(Preset('Envelope Clicks', EC_KIT, [EC_A, EC_B], dict(
    category='Technique', level=3, character='a groove made of clicks, ticks and blips',
    technique='extremely short envelopes: clicks from the sample layer, one-block blips, noise snaps; then decay locks stretch single hits',
    secondary=['click pitch dial', 'every voice a few milliseconds', 'decay lock turns a blip into a tone'],
    voices='Drum 1: 1-block sine thump + kick sample click. Drum 2: 1-block sine blip. Drum 3: tick sample. Snare: noise snap. Cymbal: noise zip. Hat: tick.',
    key='no key', bpm=130,
    demonstrates='Decay 0 is one 1.45 ms control block: the voices produce clicks and ticks, which at 130 bpm are a rhythm of pure transients. In B, a decay lock stretches the blip '
                 'voice from 0 to about 300 ms hit by hit, so a click becomes a pitched tone.',
    patterns=['A: the groove of transients', 'B: the blip voice\'s decay locked from click to tone']),
    song=[0, 0, 1, LOOP], rms_floor=-40,
    checks=[('B: the last blip rings much longer than the first', differs(1, 'd2', [2], [28], 'decay', delta=150))]))

# =====================================================================================================================
# Resonant Sweep
# =====================================================================================================================
# Noise through a band-pass at high resonance rings at the cutoff: the cutoff is a pitch. Calibrated on the engine (noise, band-pass, resonance 120):
PING_HZ = [(16, 129), (20, 177), (24, 226), (28, 296), (32, 393), (36, 397), (40, 480), (44, 560), (48, 652), (52, 700), (56, 819), (60, 916), (64, 1008), (68, 1175), (72, 1272),
           (76, 1439), (80, 1697), (84, 1870), (88, 2128), (92, 2437), (96, 2748), (100, 3271), (104, 3793), (108, 4531), (112, 5578), (116, 7103), (120, 9336)]
def ping_cutoff(midi_note):
    """filter cutoff (0..127) at which the resonant noise ping sounds closest to a MIDI note"""
    f = hz(midi_note)
    for (c0, f0), (c1, f1) in zip(PING_HZ, PING_HZ[1:]):
        if f0 <= f <= f1: return int(round(c0 + (c1 - c0) * (math.log(f / f0) / math.log(f1 / f0))))
    raise ValueError(midi_note)

RS_KIT = make_kit(
    ctx_kick(), ctx_clap(),
    # drum 3: the pinger: noise through a band-pass at resonance 120, 170 ms; drum 2: the same with a longer ring
    D3(Waveform=4, Coarse=60, Decay=14, Pitch_Mod=0, Filter_Type=2, Filter_Freq=60, Resonance=120, Drive=20, Velocity_Volume=1),
    D2(Waveform=4, Coarse=60, Decay=26, Pitch_Mod=0, Filter_Type=2, Filter_Freq=40, Resonance=124, Drive=20, Velocity_Volume=1),
    ctx_hat(), *silent(CY))
_rs_row = '9.7.8.7.9.7.8.7.' * 2
_rs_ctx = dict(k='9...9...9...9...' * 2, s='....8.......8...' * 2, h='.4.4.4.4.4.4.4.4' * 2)
RS_A = pat(swing=50, d3=_rs_row, **_rs_ctx)                                                    # cutoff 60: every ping the same pitch
_scale = [60, 63, 65, 67, 70, 72, 75, 79]                                                      # C minor pentatonic, from middle C up
_melody = [60, 63, 67, 65, 70, 67, 72, 75, 79, 75, 72, 70, 67, 65, 63, 60]
RS_B = RS_A.copy().lock_seq('d3', 'Drum 3', 'Filter Freq', [ping_cutoff(n) for n in _melody])    # a tune played by the filter cutoff alone
RS_C = RS_A.copy().lock('d3', sorted(RS_A.steps[2]), 'Drum 3', 'Filter Freq', ping_cutoff(67)).lock_seq('d3', 'Drum 3', 'Resonance', [int(20 + i * 107 / 15) for i in range(16)])   # fixed cutoff, resonance sweeps
RS_D = pat(swing=50, d2='9.......7.......8.......7.......', **_rs_ctx)
RS_D.lock_seq('d2', 'Drum 2', 'Filter Freq', [22, 62, 100, 118])                                # a rising sweep over four long rings
PRESETS.append(Preset('Resonant Sweep', RS_KIT, [RS_A, RS_B, RS_C, RS_D], dict(
    category='Technique', level=3, character='pings that play a melody, resonance that rings',
    technique='noise through a resonant band-pass: the cutoff is the pitch, the resonance is the ring; both locked per hit',
    secondary=['melody in C minor pentatonic with no oscillator pitch involved', 'resonance sweep at a fixed cutoff', 'long rings with a rising cutoff'],
    voices='Kick, clap, hat: plain. Drum 3: noise -> band-pass at resonance 120 (170 ms ping). Drum 2: the same with a longer ring.',
    key='C minor pentatonic (C Eb F G Bb ...)', bpm=124,
    demonstrates='A resonant filter excited by noise rings at its cutoff, so a p-lock on Filter Freq is a note: B plays a sixteen-hit tune that is made only of filter cutoffs '
                 '(the cutoff values come from a calibration of the engine\'s cutoff-to-frequency curve). C holds the pitch and sweeps resonance from damped to ringing.',
    patterns=['A: one cutoff: every ping the same pitch', 'B: the cutoff locked to a melody', 'C: cutoff fixed, resonance 20 -> 127', 'D: four long rings with a rising cutoff']),
    song=[0, 0, 1, 1, 2, 2, 3, 3, LOOP],
    checks=[('A: pings are all the same pitch', lambda p: not spread(0, 'd3', 'dominant', 1.15)(p)),
            ('B: pings cover about an octave and a half', spread(1, 'd3', 'dominant', 2.2)),
            ('C: the ping narrows (darker, more tonal) as resonance rises', differs(2, 'd3', [0], [30], 'centroid', ratio=1.3))]))

# =====================================================================================================================
# Velocity Is Timbre
# =====================================================================================================================
VT_KIT = make_kit(
    # velocity does two things on every voice: loudness (Velocity > Volume) and a velocity target
    D1(Waveform=0, Coarse=30, Decay=18, Pitch_Mod=40, Pitch_Decay=24, Drive=55, Velocity_Volume=1, Velocity_Target=tgt('Drum 1: Pitch Mod'), Velocity_Amount=60),
    # snare: noise-heavy through a low-pass (no sample layer, little drive: they would hide the filter), so the velocity -> cutoff target is plainly audible
    SN(Waveform=1, Coarse=55, Noise_Osc_Mix=100, Decay=13, Pitch_Mod=35, Pitch_Decay=20, Filter_Type=0, Filter_Freq=65, Drive=25,
       Velocity_Volume=1, Velocity_Target=tgt('Snare: Filter Freq'), Velocity_Amount=45),
    ctx_hat(Decay_closed=3, Velocity_Target=tgt('Hi-hat: Decay (closed)'), Velocity_Amount=35), *silent(D2, D3, CY))
_vt_ctx = dict(k='9...9...9...9...' * 2, o='..6...6...6...6.' * 2)
VT_A = pat(swing=50, s='....9.......9...' * 2, h='9.9.9.9.9.9.9.9.' * 2, **_vt_ctx)               # every velocity 9: flat
VT_B = pat(swing=54, s='....9..2.3..8..3' * 2, h='9.3.6.3.9.3.6.3.' * 2, **_vt_ctx)               # the same rhythm class with graded velocities: accents, ghosts
VT_C = pat(swing=50, s='....9.......9...' + '....9.....124579', h='9.3.6.3.9.3.6.3.' * 2, **_vt_ctx)   # a snare crescendo roll: velocity 1 -> 7 over the last steps
PRESETS.append(Preset('Velocity Is Timbre', VT_KIT, [VT_A, VT_B, VT_C], dict(
    category='Technique', level=3, character='dynamics that change the sound, not only the level',
    technique='velocity > volume plus velocity targets: filter on the snare, pitch depth on the kick, decay on the hat',
    secondary=['ghost notes that are darker and shorter, accents that are brighter and longer', 'a crescendo roll whose last hits are the brightest'],
    voices='Kick: velocity -> pitch mod. Snare: noise through a low-pass, velocity -> cutoff. Hat: velocity -> closed decay. Everything also gets louder with velocity.',
    key='no key', bpm=128,
    demonstrates='Without Velocity > Volume a step\'s velocity does nothing at all; with it, velocity is loudness, and a velocity target adds a second dimension. Here a soft snare is dark and a hard one is '
                 'bright and snappy, a soft hat is short and a hard hat rings, a soft kick has less beater. A has only full velocities, B has accents and ghosts, C ends in a crescendo roll.',
    patterns=['A: full velocity everywhere (flat)', 'B: accents and ghost notes: both louder and brighter', 'C: crescendo snare roll: darker to brighter as it rises']),
    song=[0, 0, 1, 1, 2, 2, LOOP],
    checks=[('B: the hardest snares are brighter than the ghost snares', differs(1, 's', [7, 9, 19, 25], [4, 12, 20, 28], 'centroid', ratio=1.1)),
            ('C: the roll ends brighter than it starts', differs(2, 's', [26], [31], 'centroid', ratio=1.1))]))

# =====================================================================================================================
# Noise Lab
# =====================================================================================================================
NL_KIT = make_kit(
    # an all-noise kit. The noise oscillator is sample-and-hold at the voice's pitch: low notes are crunchy rumble, high notes are white hiss.
    D1(Waveform=4, Coarse=30, Decay=16, Pitch_Mod=0, Filter_Type=0, Filter_Freq=34, Drive=50, Velocity_Volume=1),
    D2(Waveform=4, Coarse=60, Decay=12, Pitch_Mod=0, Filter_Type=0, Filter_Freq=127, Drive=30, Velocity_Volume=1),
    D3(Waveform=4, Coarse=84, Decay=5, Pitch_Mod=0, Filter_Type=1, Filter_Freq=70, Drive=100, Velocity_Volume=1),
    SN(Waveform=4, Coarse=60, Noise_Osc_Mix=127, Attack=10, Decay=20, Pitch_Mod=0, Filter_Type=2, Filter_Freq=62, Resonance=15, Drive=100, Velocity_Volume=1),
    CY(Wave_1=4, Wave_2=4, Wave_3=4, Coarse=85, Attack=22, Decay=62, Filter_Type=2, Filter_Freq=90, Resonance=20, Drive=0, Velocity_Volume=1),
    HH(Wave_1=4, Wave_2=4, Wave_3=4, Coarse=90, Mod_Osc_1_Gain=0, Mod_Osc_2_Gain=0, Filter_Type=1, Filter_Freq=60, Decay_closed=3, Decay_open=20, Drive=45, Velocity_Volume=1))
NL_A = pat(swing=52, k='9...9...9...9...' * 2, s='....8.......8...' * 2, h='.5.4.5.4.5.4.5.4' * 2, o='..6...6...6...6.' * 2, d3='.......4........' * 2, d2='...6.......4..7.' * 2)
NL_B = NL_A.copy().tune('d2', [-24, -12, 0, 12, 24, 36])
NL_C = NL_A.copy().lock_seq('s', 'Snare', 'Repeat Count', [0, 2, 4, 6])
PRESETS.append(Preset('Noise Lab', NL_KIT, [NL_A, NL_B, NL_C], dict(
    category='Technique', level=3, character='a groove made only of noise',
    technique='noise synthesis: kick, tom, hat, clap, wash and tick are all the noise oscillator, shaped by filters, envelopes, drive and the repeat counter',
    secondary=['noise colour by note (sample-and-hold rate)', 'clap flutter by Repeat Count locks', 'noise as a kick (low rate + low-pass + drive)'],
    voices='Drum 1: noise thump. Drum 2: open noise perc. Drum 3: noise tick. Snare: noise clap. Cymbal: noise wash (slow attack). Hat: all-noise hat.',
    key='no key', bpm=118,
    demonstrates='A complete groove from one source: the noise oscillator is sample-and-hold at the voice pitch, so a low note is crunchy rumble and a high note is hiss. In B the noise perc '
                 'walks the note from -24 to +36: the colour of the noise moves from rumble to hiss. In C the snare\'s repeat counter turns a hit into a flutter.',
    patterns=['A: the noise groove', 'B: noise colour by note (perc walks -24 .. +36)', 'C: clap flutter: repeat count 0, 2, 4, 6']),
    song=[0, 0, 1, 1, 2, 2, LOOP], targets=dict(d3=-12, c=-18),
    checks=[('B: the noise perc gets brighter as the note rises', differs(1, 'd2', [3], [30], 'centroid', ratio=1.6))]))

# =====================================================================================================================
# Odd Meters
# =====================================================================================================================
OM_KIT = make_kit(
    ctx_kick(), ctx_clap(),
    D2(Waveform=0, Coarse=58, Decay=10, Pitch_Mod=40, Pitch_Decay=16, Click_Type=12, Click_Level=30, Drive=40, Velocity_Volume=1),
    D3(Waveform=1, Coarse=33, Decay=15, Pitch_Mod=30, Pitch_Decay=14, Filter_Type=0, Filter_Freq=70, Resonance=30, Drive=55, Velocity_Volume=1),
    ctx_hat(), *silent(CY))
OM_A = pat(swing=50, k='9...9...9...9...', s='....8.......8...', h='9.5..5.5..5.', d3='..7.......5.')       # three against four: the hat figure is 12 steps
OM_A.tune('d3', [0, 3])
OM_B = pat(swing=50, k='9...9...9...9...', s='....8.......8...', h='.5.5.5.5.5.5.5.5', d2='9..5.7..5..6.5..7..5')      # five against four: a 20-step tom figure
OM_B.tune('d2', [0, 5, 3, 7, 5, 0, 3, 7])
OM_C = pat(swing=50, k='9...9...9.....', s='....8...7...5.', h='6.4.5.4.6.4.5.', o='......5.....5.', d3='..7...5.....3.')       # seven eighths: 14 steps, grouped 4 + 4 + 6
OM_C.tune('d3', [0, 3, 5])
OM_D = pat(swing=50, k='9...9...9...9...', s='........8.......' + '', h='7.5.7.5.7.', d2='.9..7.5..7..5.', d3='9.....7...5.')                 # stack: 16 / 16 / 10 / 14 / 12
OM_D.tune('d2', [0, 5, 7, 3, 0]).tune('d3', [0, 7, 3])
PRESETS.append(Preset('Odd Meters', OM_KIT, [OM_A, OM_B, OM_C, OM_D], dict(
    category='Technique', level=3, character='grooves that are not 16 steps',
    technique='per-track pattern lengths: 12 against 16, 20 against 16, a 14-step bar (7/8), and a stack of 10 / 12 / 14 against 16',
    secondary=['polymeter: each track loops at its own length', 'patterns switch only when the longest track wraps', 'tuned perc figures by note'],
    voices='Kick, clap, hat: plain. Drum 2: tuned tom. Drum 3: low-passed bass blip.',
    key='D (bass voice D1 / F / G)', bpm=118,
    demonstrates='Track lengths are independent: A puts a 12-step hat figure over the 16-step kick (three against four, a full cycle in three bars), B a 20-step tom figure (five against four), '
                 'C is a single 14-step bar (7/8, grouped 4 + 4 + 6), D stacks 10, 12 and 14 against 16 so the combined loop is far longer than any one track.',
    patterns=['A: 12 against 16 (3:4)', 'B: 20 against 16 (5:4)', 'C: a bar of 14 steps (7/8)', 'D: 10 / 12 / 14 against 16']),
    song=[0, 0, 0, 1, 1, 1, 1, 2, 2, 3, 3, 3, LOOP]))

# =====================================================================================================================
# Swing Lab
# =====================================================================================================================
SW_L_KIT = make_kit(
    ctx_kick(), ctx_clap(),
    D3(Waveform=1, Coarse=31, Decay=13, Pitch_Mod=20, Pitch_Decay=12, Filter_Type=0, Filter_Freq=65, Resonance=30, Drive=55, Velocity_Volume=1),
    ctx_hat(), *silent(D2, CY))
_sw_rows = dict(k='9...9...9...9...', s='....8.......8...', h='7343' * 4, o='..6...6...6...6.', d3='..7....5..7..5..')
def _swing(pct): return pat(swing=pct, **_sw_rows).tune('d3', [0, 0, 5, 3])
SL_P = [_swing(50), _swing(54), _swing(58), _swing(62), _swing(66.7)]
PRESETS.append(Preset('Swing Lab', SW_L_KIT, SL_P, dict(
    category='Technique', level=3, character='one groove at five different swing amounts',
    technique='pattern shuffle: every odd 16th is delayed by a fraction of the step pair',
    secondary=['the same notes in all five patterns', 'swing percentages: 50 (straight), 54, 58, 62, 66.7 (triplet)'],
    voices='Kick, clap, hat, open hat, bass blip: plain.',
    key='G (bass G1)', bpm=122,
    demonstrates='The only difference between the patterns is the shuffle value: 50 % is straight, about 54-58 % is the lazy swing of deep house, about 62 % is jackin\', 66.7 % is a full triplet. '
                 'Shuffle delays only the odd 16ths (hats and the syncopated bass), so the kick and clap stay on the grid while the groove leans.',
    patterns=['A: straight (50 %)', 'B: 54 %', 'C: 58 %', 'D: 62 %', 'E: 66.7 % (triplet)']),
    song=[0, 0, 1, 1, 2, 2, 3, 3, 4, 4, LOOP],
    checks=[('A: no delay on odd steps', swing_delay(0, 'h', -2.0, 2.0)),
            ('B: odd 16ths about 10 ms late (54 %)', swing_delay(1, 'h', 7.0, 14.0)),
            ('C: about 20 ms late (58 %)', swing_delay(2, 'h', 16.0, 25.0)),
            ('D: about 30 ms late (62 %)', swing_delay(3, 'h', 26.0, 36.0)),
            ('E: about 41 ms late (66.7 %)', swing_delay(4, 'h', 36.0, 47.0))]))

# =====================================================================================================================
# Flam & Shift
# =====================================================================================================================
FS_KIT = make_kit(
    ctx_kick(), ctx_clap(),
    D3(Waveform=0, Coarse=50, Decay=14, Pitch_Mod=45, Pitch_Decay=20, Drive=40, Velocity_Volume=1),
    ctx_hat(), *silent(D2, CY))
_fs_ctx = dict(k='9...9...9...9...' * 4, h='.5.4.5.4.5.4.5.4' * 4)
FS_A = pat(swing=50, s='....8.......9...' * 4, **_fs_ctx)
for bar, flam in enumerate([1, 2, 3, 5]): FS_A.at('s', bar * 16 + 12, flam=flam)                         # x2, x3, x4, x8 on the second clap of each bar
FS_B = pat(swing=50, s='....8.......8...' * 4, **_fs_ctx)
_hat_steps = sorted(FS_B.steps[5])
for st in _hat_steps:
    bar = st // 16
    if bar == 1: FS_B.at('h', st, shift=4)                          # bar 2: the hats rush (3 units = 3/8 of a step early)
    elif bar == 2: FS_B.at('h', st, shift=10)                       # bar 3: the hats lay back (3 units late)
    elif bar == 3: FS_B.at('h', st, shift=5 if (st // 2) % 2 == 0 else 9)   # bar 4: alternately early and late (drunk)
FS_C = pat(swing=50, s='....8.......8...' * 3 + '....8...6.6.7.8.', d3='..........9.....' * 4, **_fs_ctx)
for st, flam, sh in ((56, 3, 5), (58, 2, 9), (60, 1, 5), (62, 4, 7)): FS_C.at('s', st, flam=flam, shift=sh)
FS_C.at('d3', 58, flam=1)
PRESETS.append(Preset('Flam & Shift', FS_KIT, [FS_A, FS_B, FS_C], dict(
    category='Technique', level=3, character='timing inside the step',
    technique='flams (x2 to x8) and shift (micro-timing, +-7 units of 1/8 step) per step',
    secondary=['rush / lay back / drunk hats by shift', 'a roll fill from flams plus shift', 'both are timing only: pitch and timbre are untouched'],
    voices='Kick, clap, hat, tom: plain.',
    key='no key', bpm=124,
    demonstrates='A step can fire several times (flam x2, x3, x4, x6, x8) and can be moved by a few milliseconds without leaving the grid (shift). A builds a flam ladder over four bars, '
                 'B moves the hats of bars 2, 3, 4 early, late and alternately, C ends with a roll made from flams and shifts.',
    patterns=['A: clap flam ladder x2, x3, x4, x8', 'B: hats rush, lay back, and wobble', 'C: a four-step roll fill']),
    song=[0, 0, 1, 1, 2, 2, LOOP],
    checks=[('A: the last clap flam fires 8 times in one step', max_triggers_per_step(0, 's', 8)),
            ('C: the fill has multi-trigger steps', max_triggers_per_step(2, 's', 4))]))

# =====================================================================================================================
# Probability Garden
# =====================================================================================================================
PG_KIT = make_kit(
    ctx_kick(), ctx_clap(),
    D2(Waveform=0, FM_Waveform=0, Coarse=64, FM_Amount=40, FM_Freq=95, Decay=14, Pitch_Mod=0, Pitch_Decay=40, Drive=30, Velocity_Volume=1),
    D3(Waveform=1, Coarse=33, Decay=15, Pitch_Mod=30, Pitch_Decay=14, Filter_Type=0, Filter_Freq=66, Resonance=30, Drive=55, Velocity_Volume=1),
    ctx_hat(), *silent(CY))
_pg = dict(k='9...9...9...9...' * 2, s='....8.......8...' * 2)
PG_A = pat(swing=54, h='9363' * 8, d2='...5..4....5..4.' * 2, d3='..6....4..6..4..' * 2, **_pg).tune('d2', [0, 7, 4, 12, 9, 7, 4, 2])
def _probs(p, hat, pd2, pd3):
    """hat = probability by step position in the beat (downbeat, 16th, 8th offbeat, 16th); the tuned perc and the bass blip get one probability each"""
    for st in sorted(p.steps[5]): p.at('h', st, prob=hat[st % 4])
    for st in sorted(p.steps[1]): p.at('d2', st, prob=pd2)
    for st in sorted(p.steps[2]): p.at('d3', st, prob=pd3)
    return p
_probs(PG_A, [100, 30, 70, 30], 45, 70)
PG_B = _probs(PG_A.copy(), [100, 15, 40, 15], 25, 40)                                                     # sparser: everything optional is rarer
PG_C = _probs(PG_A.copy(), [100, 60, 90, 60], 70, 90)                                                     # busier
PRESETS.append(Preset('Probability Garden', PG_KIT, [PG_A, PG_B, PG_C], dict(
    category='Technique', level=3, character='a loop that never repeats the same way twice',
    technique='step probability in tiers: the groove is certain (100 %), the decoration is not (15 - 90 %)',
    secondary=['hat tiers: downbeat 100 %, offbeat 8ths, then 16ths', 'tuned perc and a bass blip that only sometimes answer', 'sparse (B) and busy (C) versions of the same garden'],
    voices='Kick, clap, hat: plain. Drum 2: FM bell-ish tom. Drum 3: low-passed bass blip.',
    key='no key', bpm=125,
    demonstrates='Probability is a per-step number (1-100 %), checked every time the step comes round. A fixed backbone plus tiers of optional hits gives a groove that is stable but never identical; '
                 'the seed is fixed in the offline audit, in the plugin each pass is different. B halves and C raises all the optional probabilities.',
    patterns=['A: the garden', 'B: sparse (optional hits are rare)', 'C: busy (optional hits are likely)']),
    song=[0, 0, 0, 0, 1, 1, 2, 2, LOOP],
    checks=[('the hats change between random seeds', varies_with_seed(0, 'h')), ('the perc changes between random seeds', varies_with_seed(0, 'd2'))]))

# =====================================================================================================================
# Ring Mod Throws
# =====================================================================================================================
RM_KIT = make_kit(
    ctx_kick(), ctx_clap(),
    # two tuned toms go to the FX bus; the ring modulator is there with dry/wet 0 (so they pass dry) until a lock switches it on for that hit
    D2(Waveform=0, Coarse=52, Decay=16, Pitch_Mod=30, Pitch_Decay=20, Drive=40, Velocity_Volume=1, Audio_Out=6),
    D3(Waveform=0, Coarse=45, Decay=18, Pitch_Mod=30, Pitch_Decay=20, Drive=40, Velocity_Volume=1, Audio_Out=6),
    ctx_hat(), *silent(CY),
    FX(FX_Type=2, FX_Dry_Wet=0, FX_P1=40, FX_Wave=3))
_rm_ctx = dict(k='9...9...9...9...' * 2, s='....8.......8...' * 2, h='.4.4.4.4.4.4.4.4' * 2)
RM_A = pat(swing=50, d2='9..7..8..7..8.7.' * 2, d3='...8.......8....' * 2, **_rm_ctx)
RM_A.tune('d2', [0, 7, 3, 5, 7, 10, 7, 3, 5, 0, 3, 5])
RM_B = RM_A.copy()
_wet = [0, 100, 0, 100, 0, 0, 100, 100, 0, 100, 0, 100]
_p1 = [40, 22, 40, 60, 40, 40, 90, 127, 40, 30, 40, 100]
RM_B.lock_seq('d2', 'FX', 'FX Dry/Wet', _wet).lock_seq('d2', 'FX', 'FX P1', _p1)
RM_C = RM_A.copy()
RM_C.lock('d2', sorted(RM_C.steps[1]), 'FX', 'FX Dry/Wet', 100).lock_seq('d2', 'FX', 'FX P1', [int(8 + i * 119 / 11) for i in range(12)])
PRESETS.append(Preset('Ring Mod Throws', RM_KIT, [RM_A, RM_B, RM_C], dict(
    category='Technique', level=3, character='clean toms that turn metallic on command',
    technique='an FX-bus ring modulator switched on per hit: FX dry/wet and FX carrier frequency as p-locks',
    secondary=['FX parameters are lockable like any other', 'rectangle carrier for a bright clang', 'carrier sweep over a phrase'],
    voices='Kick, clap, hat: plain. Drum 2 + Drum 3: tuned toms routed to the FX bus (ring modulator, rectangle carrier, dry/wet 0 in the kit).',
    key='F (toms F3 / A3 area, ring partials follow the carrier)', bpm=112,
    demonstrates='The FX slot is a part of the instrument you can play: the kit leaves the ring modulator at dry/wet 0 (A is a plain tom pattern); B locks dry/wet and carrier frequency on selected hits so '
                 'those toms clang while their neighbours stay clean; C locks the ring modulator on for every hit and sweeps the carrier from 60 to 880 Hz across the phrase. '
                 'The lock holds until that voice\'s next trigger, and the FX bus is shared by every voice routed to it.',
    patterns=['A: toms, plain (ring mod at dry/wet 0)', 'B: selected toms thrown through the ring modulator', 'C: carrier sweep across all hits']),
    song=[0, 0, 1, 1, 2, 2, LOOP],
    checks=[('B: the thrown toms are much brighter than the clean ones', differs(1, 'd2', [0, 6, 12], [3, 9, 16], 'centroid', ratio=1.5))]))
