"""House family: deep, raw, jackin', minimal, acid-adjacent. Groove first: swing, ghost notes, velocity that is allowed to matter."""
from library.core import *
from library.audit import differs, spread

PRESETS = []

# =====================================================================================================================
# Late Night House - deep house, 122 bpm, 57 % swing. Soft kick, noise shaker, clap, tuned rim, sub bass that plays chord roots.
# =====================================================================================================================
LN_KIT = make_kit(
    D1(Waveform=0, Coarse=28, Decay=20, Pitch_Mod=42, Pitch_Decay=26, Drive=55, Volume=127, Velocity_Volume=1),
    # drum 2: a low conga, sine with a quick pitch drop and a touch of tom click
    D2(Waveform=0, Coarse=52, Decay=11, Pitch_Mod=34, Pitch_Decay=14, Click_Type=12, Click_Level=30, Volume=85, Velocity_Volume=1),
    # drum 3: sub bass, pure sine that plays the chord roots (A1, above the kick's E1 so the two do not beat against each other)
    D3(Waveform=0, Coarse=33, Decay=26, Pitch_Mod=6, Pitch_Decay=8, Drive=35, Volume=120, Velocity_Volume=1),
    # clap: band-passed noise with the sample clap, a longer softer tail than a techno clap
    SN(Waveform=4, Coarse=57, Noise_Osc_Mix=127, Decay=24, Pitch_Mod=0, Filter_Type=2, Filter_Freq=58, Resonance=10, Click_Type=9, Click_Level=85,
       Volume=75, Velocity_Volume=1),
    # cymbal voice as a tuned rimshot: sine, no modulators, very short
    CY(Wave_1=0, Wave_2=0, Wave_3=0, Coarse=84, Mod_Osc_1_Gain=0, Mod_Osc_2_Gain=0, Decay=5, Filter_Type=7, Volume=70, Velocity_Volume=1, Click_Type=6, Click_Level=60),
    # hat voice as a shaker: all noise, soft, velocity also opens the high-pass a little (accents are brighter)
    HH(Wave_1=4, Wave_2=4, Wave_3=4, Coarse=60, Mod_Osc_1_Gain=0, Mod_Osc_2_Gain=0, Filter_Type=1, Filter_Freq=88, Decay_closed=5, Decay_open=24,
       Velocity_Target=tgt('Hi-hat: Filter Freq'), Velocity_Amount=18, Volume=80, Velocity_Volume=1, Drive=85),
)
LN_A = pat(swing=57,
    k='9...9...9...9...' * 2,
    s='....8.......8... ....8.......8..3',
    h='2523252325232523' * 2,
    o='..5.......5...5. ..5.......5.....',
    c='.....4.......4.. .....4......4...',
    d3='..8.....5.....7. ..8.....5.......')
LN_A.rel('d3', {2: 0, 8: 0, 14: 3, 18: 0, 24: -2})
LN_A.at('s', 31, shift=6, prob=60)
LN_B = LN_A.copy().set_length('d2', 32)
LN_B.add('d2', 3, 55).add('d2', 7, 70).add('d2', 11, 45).add('d2', 19, 55).add('d2', 23, 70).add('d2', 27, 45).add('d2', 30, 60)
LN_B.rel('d2', {3: 0, 7: 5, 11: 0, 19: 0, 23: 7, 27: 3, 30: 10})
LN_B.lock('d3', [14, 24], 'Drum 3', 'Filter Freq', {14: 70, 24: 55}).lock('h', [15, 31], 'Hi-hat', 'Decay (closed)', {15: 10, 31: 14})
PRESETS.append(Preset('Late Night House', LN_KIT, [LN_A, LN_B], dict(
    category='House', level=1, character='deep, soft, swung, warm',
    technique='groove: 57 % swing, shaker accents by velocity (and velocity-driven brightness), ghosted clap',
    secondary=['sub bass playing chord roots by per-step note', 'low conga by tuned tom voice added in B', 'rimshot from the cymbal voice'],
    voices='Kick: soft, round. Drum 2: low conga. Drum 3: sine sub. Snare: soft clap (noise + sample). Cymbal: tuned rimshot. Hat: noise shaker.',
    key='A minor (kick E1 41 Hz, sub bass A1 / C2 / G1 above it, congas around E3)', bpm=122,
    demonstrates='The feel comes from the instrument, not from the notes: the shuffle swings every odd 16th, shaker velocities alternate soft/hard, and the velocity of a hit also '
                 'shifts the shaker\'s high-pass, so accents are brighter as well as louder.',
    patterns=['A: two-bar groove', 'B: congas added, bass filter and shaker decay accents locked']),
    song=[0, 0, 1, 1, LOOP], targets={'h': -24, 'o': -22, 'c': -20}))

# =====================================================================================================================
# Raw Basement - raw lo-fi house, 124 bpm, 58 % swing, crushed and a little drunk (micro-timing by shift).
# =====================================================================================================================
RB_KIT = make_kit(
    D1(Waveform=1, Coarse=31, Decay=18, Pitch_Mod=62, Pitch_Decay=22, Drive=55, Sample_Rate_Reducer=88, Click_Type=5, Click_Level=40, Volume=127, Velocity_Volume=1),
    D2(Waveform=0, Coarse=47, Decay=10, Pitch_Mod=36, Pitch_Decay=14, Sample_Rate_Reducer=90, Volume=90, Velocity_Volume=1),
    # drum 3: a bass blip, triangle through a low-pass
    D3(Waveform=1, Coarse=33, Decay=15, Pitch_Mod=14, Pitch_Decay=10, Filter_Type=0, Filter_Freq=58, Resonance=30, Drive=45, Sample_Rate_Reducer=95, Volume=110, Velocity_Volume=1),
    SN(Waveform=1, Coarse=53, Noise_Osc_Mix=90, Decay=16, Pitch_Mod=30, Pitch_Decay=18, Filter_Type=1, Filter_Freq=30, Drive=70, Sample_Rate_Reducer=72, Click_Type=11, Click_Level=60,
       Volume=88, Velocity_Volume=1),
    # cymbal voice as a dirty noise clap
    CY(Wave_1=4, Wave_2=4, Wave_3=4, Coarse=105, Decay=14, Attack=0, Filter_Type=2, Filter_Freq=62, Resonance=20, Drive=40, Sample_Rate_Reducer=80, Volume=70, Velocity_Volume=1),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=60, Mod_Osc_1_Gain=100, Mod_Osc_2_Gain=100, Filter_Type=1, Filter_Freq=85, Decay_closed=3, Decay_open=20, Drive=85,
       Sample_Rate_Reducer=70, Volume=85, Velocity_Volume=1),
)
RB_A = pat(swing=58,
    k='9...9...9...9...',
    s='....8.......8...',
    c='.........3.....2',
    h='5.3.5.3.5.3.5.3.',
    o='..4.......4.....',
    d3='.......6.....5..')
RB_A.add('k', 7, 40, shift=8); RB_A.at('s', 4, shift=8).at('s', 12, shift=8)       # lazy backbeat: the snare sits a little late
RB_A.rel('d3', {7: 0, 13: 5})
RB_B = RB_A.copy()
RB_B.add('k', 10, 100).add('c', 14, 70, flam=1).add('d2', 11, 60).add('d2', 15, 75)
RB_B.rel('d2', {11: 0, 15: 5})
RB_B.lock('h', [4, 12], 'Hi-hat', 'Sample Rate Reducer', {4: 25, 12: 18}).lock('s', [12], 'Snare', 'Sample Rate Reducer', {12: 20})
PRESETS.append(Preset('Raw Basement', RB_KIT, [RB_A, RB_B], dict(
    category='House', level=2, character='dirty, lo-fi, loose',
    technique='sample-rate reduction on every voice, locked per step to crush single hits; late snares by shift',
    secondary=['58 % swing', 'ghost kick by velocity + shift', 'dirty noise clap from the cymbal voice'],
    voices='Kick: triangle, driven, crushed, kick click. Drum 2: crushed tuned perc. Drum 3: low-passed bass blip. Snare: driven noise + sample. Cymbal: dirty clap. Hat: crushed.',
    key='G (kick 49 Hz, bass blip A1 and D2)', bpm=124,
    demonstrates='Sample-rate reduction is a per-voice dial and it can be locked per hit: in B two hats and the snare are crushed much harder than their neighbours for a dusty sampler feel, '
                 'while the snares sit a few milliseconds late for a lazy backbeat.',
    patterns=['A: raw groove, lazy snare', 'B: extra kick, flam clap, per-hit crush locks']),
    song=[0, 0, 1, LOOP]))

# =====================================================================================================================
# Jack Tracks - jackin' house, 126 bpm, 60 % swing: a chunky syncopated kick, claps with ghost flams, a bass stab riff.
# =====================================================================================================================
JT_KIT = make_kit(
    D1(Waveform=0, Coarse=29, Decay=20, Pitch_Mod=52, Pitch_Decay=24, Drive=60, Volume=127, Velocity_Volume=1),
    # drum 2: tuned tom for the turnaround fill
    D2(Waveform=0, Coarse=48, Decay=17, Pitch_Mod=45, Pitch_Decay=22, Drive=20, Volume=95, Velocity_Volume=1),
    # drum 3: bass stab, rectangle through a low-pass with a short envelope, plays the riff
    D3(Waveform=3, Coarse=31, Decay=15, Pitch_Mod=0, Filter_Type=0, Filter_Freq=62, Resonance=35, Drive=30, Volume=100, Velocity_Volume=1),
    SN(Waveform=4, Coarse=57, Noise_Osc_Mix=127, Decay=20, Pitch_Mod=0, Filter_Type=2, Filter_Freq=64, Resonance=20, Click_Type=9, Click_Level=100, Volume=92, Velocity_Volume=1),
    CY(Wave_1=3, Wave_2=2, Wave_3=3, Coarse=88, Mod_Osc_1_Gain=127, Mod_Osc_1_Freq=80, Mod_Osc_2_Freq=40, Decay=52, Filter_Type=1, Filter_Freq=62, Volume=60, Velocity_Volume=1),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=63, Mod_Osc_1_Gain=100, Mod_Osc_2_Gain=100, Filter_Type=1, Filter_Freq=86, Decay_closed=3, Decay_open=22, Volume=95, Velocity_Volume=1, Drive=85),
)
JT_A = pat(swing=60,
    k='9...9...9.5.9...',
    s='....9.......9.3.',
    h='.4.5.4.5.4.5.4.5',
    o='..6...6...6...6.',
    d3='.7..7.5...7..5..')
JT_A.rel('d3', {1: 0, 4: 0, 6: 3, 10: 5, 13: 3})
JT_A.at('s', 14, flam=1)
JT_B = JT_A.copy()
JT_B.add('d2', 12, 85).add('d2', 13, 80).add('d2', 14, 90).add('d2', 15, 100).add('c', 0, 80)
JT_B.rel('d2', {12: 7, 13: 5, 14: 3, 15: 0}).lock('d2', [12, 15], 'Drum 2', 'Decay', {12: 10, 15: 28})
JT_B.lock('d3', [1, 6], 'Drum 3', 'Filter Freq', {1: 80, 6: 95})
PRESETS.append(Preset('Jack Tracks', JT_KIT, [JT_A, JT_B], dict(
    category='House', level=2, character='bouncy, chunky, party',
    technique='strong swing (60 %) with a syncopated kick, ghost flam claps and a bass riff played by a tuned stab voice',
    secondary=['four-step tom run as a fill without extra tracks (note + decay locks)', 'crash on the downbeat from the cymbal voice'],
    voices='Kick: chunky, driven. Drum 2: tuned tom. Drum 3: rectangle bass stab. Snare: noise clap + sample. Cymbal: crash. Hat: bright, swung.',
    key='G minor (kick 49 Hz; stab G1 - Bb1 - C2)', bpm=126,
    demonstrates='At 60 % swing every odd 16th lands late and the extra kick on step 11 pushes against it; in B a four-note tom run (descending by note, with a longer last hit) '
                 'replaces a fill that would otherwise need more tracks.',
    patterns=['A: swung groove with bass stab riff', 'B: stab filter opens, tom-run fill, crash on the one']),
    song=[0, 0, 0, 1, LOOP]))

# =====================================================================================================================
# Minimal Dew - minimal house, 124 bpm. Clicks, ticks and noise puffs; sparse, probability does the varying.
# =====================================================================================================================
MD_KIT = make_kit(
    D1(Waveform=0, Coarse=30, Decay=14, Pitch_Mod=40, Pitch_Decay=22, Drive=60, Volume=127, Velocity_Volume=1),
    # drum 2: the tom sample alone (oscillator at 8 Hz = silent, decay 4 plays the whole 50 ms sample); its playback speed is the Click Pitch dial
    D2(Waveform=0, Coarse=0, Decay=4, Pitch_Mod=0, Click_Type=12, Click_Level=127, Click_Pitch=80, Volume=100, Velocity_Volume=1),
    # drum 3: a tonal blip, triangle, 3 ms of decay: pitches by note
    D3(Waveform=1, Coarse=88, Decay=2, Pitch_Mod=0, Volume=95, Velocity_Volume=1),
    SN(Waveform=0, Coarse=76, Noise_Osc_Mix=35, Decay=4, Pitch_Mod=0, Filter_Type=1, Filter_Freq=40, Click_Type=4, Click_Level=60, Volume=85, Velocity_Volume=1),
    CY(Wave_1=4, Wave_2=4, Wave_3=4, Coarse=80, Decay=11, Attack=7, Filter_Type=2, Filter_Freq=90, Resonance=15, Volume=70, Velocity_Volume=1),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=72, Mod_Osc_1_Gain=100, Mod_Osc_2_Gain=100, Filter_Type=1, Filter_Freq=88, Decay_closed=1, Decay_open=9, Volume=90, Velocity_Volume=1, Drive=85),
)
MD_A = pat(swing=54,
    k='9...9...9...9...',
    d2='..5..4....5..4.. .4..5....4..5...',
    d3='.3....5....3.... ..5....3....5...',
    s='.......4........ ....4...........',
    c='..........5..... ......3.........',
    h='.4.3.4.3.4.3.4.3',
    o='...............4')
MD_A.at('d2', 2, prob=80).at('d2', 5, prob=60).at('d2', 17, prob=70).at('d3', 6, prob=70).at('s', 7, prob=60)
MD_B = MD_A.copy()
MD_B.lock('d2', [2, 10, 20, 28], 'Drum 2', 'Click Pitch', {2: 40, 10: 110, 20: 60, 28: 127})
MD_B.rel('d3', {1: 0, 6: 7, 11: 3, 18: 10, 23: 5, 28: 12})
MD_B.add('d3', 14, 60).rel('d3', {14: -2})
PRESETS.append(Preset('Minimal Dew', MD_KIT, [MD_A, MD_B], dict(
    category='House', level=2, character='sparse, clicky, intimate',
    technique='probability and tiny envelopes: a few clicks, ticks and noise puffs that never quite repeat',
    secondary=['click pitch locked per hit (a pitched click without an oscillator)', 'tonal blips by per-step note', 'two-bar loop'],
    voices='Kick: short, soft. Drum 2: tom sample click, pitch by Click Pitch. Drum 3: 3 ms triangle blip. Snare: tick. Cymbal: noise puff. Hat: ultra-short tick.',
    key='blips in B minor-ish (B6 as the base)', bpm=124,
    demonstrates='Most hits are one or two milliseconds long; the music is in which ones play. Probability makes each pass through the two bars slightly different, '
                 'and in B the click voice becomes a pitched instrument via the Click Pitch dial, locked per hit.',
    patterns=['A: sparse clicks with probabilities', 'B: clicks pitched by lock, blip line by note']),
    song=[0, 0, 1, LOOP], targets={'d2': -24, 'd3': -20, 's': -20, 'c': -24, 'h': -24, 'o': -24},
    checks=[('pattern 2: the click voice changes colour with the Click Pitch locks', spread(1, 'd2', 'centroid', 1.8))]))

# =====================================================================================================================
# Squelch Lane - acid-adjacent house, 124 bpm. A drum voice plays the acid line: note, resonant filter lock and velocity accent per step.
# =====================================================================================================================
SL_KIT = make_kit(
    D1(Waveform=0, Coarse=29, Decay=19, Pitch_Mod=52, Pitch_Decay=24, Drive=65, Volume=127, Velocity_Volume=1),
    D2(Waveform=4, Coarse=60, Decay=13, Filter_Type=2, Filter_Freq=58, Resonance=95, Pitch_Mod=0, Volume=70, Velocity_Volume=1),
    # drum 3: the acid voice: saw, resonant low-pass, short decay; a velocity accent adds filter drive (like the 303's accent: louder and dirtier)
    D3(Waveform=2, Coarse=36, Decay=14, Pitch_Mod=0, Filter_Type=0, Filter_Freq=40, Resonance=88, Filter_Drive=10, Drive=15, Volume=110, Velocity_Volume=1,
       Velocity_Target=tgt('Drum 3: Filter Drive'), Velocity_Amount=55),
    SN(Waveform=4, Coarse=57, Noise_Osc_Mix=127, Decay=19, Pitch_Mod=0, Filter_Type=2, Filter_Freq=62, Resonance=15, Click_Type=9, Click_Level=90, Volume=85, Velocity_Volume=1),
    CY(Wave_1=3, Wave_2=2, Wave_3=3, Coarse=88, Mod_Osc_1_Gain=127, Mod_Osc_1_Freq=80, Mod_Osc_2_Freq=40, Decay=45, Filter_Type=1, Filter_Freq=65, Volume=55, Velocity_Volume=1),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=63, Mod_Osc_1_Gain=100, Mod_Osc_2_Gain=100, Filter_Type=1, Filter_Freq=88, Decay_closed=3, Decay_open=22, Volume=85, Velocity_Volume=1, Drive=85),
)
SL_A = pat(swing=52,
    k='9...9...9...9...',
    s='....8.......8...',
    h='.4.4.4.4.4.4.4.4',
    o='..5...5...5...5.',
    d3='9.5.6.9.5.5.6.9.')
SL_A.rel('d3', {0: 0, 2: 0, 4: 12, 6: 0, 8: 3, 10: 0, 12: 7, 14: 0})
SL_B = SL_A.copy()
SL_B.lock('d3', [0, 2, 4, 6, 8, 10, 12, 14], 'Drum 3', 'Filter Freq', {0: 35, 2: 45, 4: 80, 6: 50, 8: 60, 10: 40, 12: 95, 14: 55})
SL_B.lock('d3', [4, 12], 'Drum 3', 'Decay', {4: 28, 12: 32})
SL_B.add('d2', 15, 80).rel('d2', {15: 0}).lock('d2', [15], 'Drum 2', 'Filter Freq', {15: 95})
PRESETS.append(Preset('Squelch Lane', SL_KIT, [SL_A, SL_B], dict(
    category='House', level=2, character='squelchy, rolling, club',
    technique='a drum voice as an acid line: note + filter-cutoff lock + long/short decay lock per step, accents adding filter drive via velocity',
    secondary=['velocity target on filter drive (accent = louder and dirtier)', 'resonant band-pass zap on Drum 2'],
    voices='Kick: punchy. Drum 2: resonant band-pass zap. Drum 3: saw, resonant low-pass (the acid voice). Snare: noise clap. Cymbal: ride. Hat: bright.',
    key='C (acid voice C2; riff C, C+12, Eb, G ...)', bpm=124,
    demonstrates='There is no filter envelope in this engine, so the acid movement is played: per-step cutoff locks (two locks and a note per step) in pattern 2, and a velocity target on filter drive, '
                 'so accented steps get louder and dirtier. (A velocity or LFO target can not share a parameter with a lock: the engine rewrites it every control tick, which is why accent does not target the cutoff.)',
    patterns=['A: riff with velocity accents adding filter drive', 'B: cutoff and decay locked step by step, long accent notes']),
    song=[0, 0, 1, 1, LOOP], targets={'d2': -22, 'h': -18, 'o': -16}))
