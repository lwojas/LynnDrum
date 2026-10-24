"""Electro and broken beats: displaced rhythms, metallic FM, tuned percussion."""
from library.core import *
from library.audit import differs, spread

PRESETS = []

# =====================================================================================================================
# Broken Circuit - broken techno, 130 bpm. The kick and bass are displaced against a straight hat/tick grid.
# =====================================================================================================================
BC_KIT = make_kit(
    D1(Waveform=0, Coarse=32, Decay=14, Pitch_Mod=70, Pitch_Decay=20, Drive=65, Click_Type=2, Click_Level=35, Volume=127, Velocity_Volume=1),
    # drum 2: a tuned clave, short sine
    D2(Waveform=0, FM_Waveform=0, Coarse=80, FM_Amount=20, FM_Freq=70, Decay=4, Pitch_Mod=12, Pitch_Decay=6, Volume=90, Velocity_Volume=1),
    # drum 3: a tom that is really a bass: sine with a quick pitch drop, played by note
    D3(Waveform=0, Coarse=34, Decay=26, Pitch_Mod=55, Pitch_Decay=22, Drive=30, Volume=112, Velocity_Volume=1),
    SN(Waveform=1, Coarse=57, Noise_Osc_Mix=80, Decay=14, Pitch_Mod=30, Pitch_Decay=18, Filter_Type=1, Filter_Freq=40, Click_Type=6, Click_Level=40, Volume=95, Velocity_Volume=1),
    CY(Wave_1=3, Wave_2=2, Wave_3=3, Coarse=88, Mod_Osc_1_Gain=127, Mod_Osc_1_Freq=75, Mod_Osc_2_Freq=45, Decay=22, Filter_Type=1, Filter_Freq=80, Volume=70, Velocity_Volume=1),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=66, Mod_Osc_1_Gain=100, Mod_Osc_2_Gain=100, Filter_Type=1, Filter_Freq=96, Decay_closed=3, Decay_open=16, Volume=85, Velocity_Volume=1, Drive=85),
)
BC_A = pat(
    k='9..8..9...9..8..',
    s='....9..3....9.4.',
    d3='.6......6..6...6',
    h='5.34.5.35.4.53.4',
    d2='.4..3...4..3.4..')
BC_A.at('s', 7, prob=70).at('s', 14, prob=60).at('s', 12, shift=6).at('h', 7, shift=8).rel('d3', {1: 0, 8: 0, 11: -2, 15: 3})
BC_B = BC_A.copy().rotate('k', 2).rotate('d3', 2)
BC_B.lock('k', [2], 'Drum 1', 'FM Amount', 40).at('k', 2, note=65)
BC_B.lock('d3', [3, 10, 13], 'Drum 3', 'Decay', {3: 12, 10: 40, 13: 12})
PRESETS.append(Preset('Broken Circuit', BC_KIT, [BC_A, BC_B], dict(
    category='Electro & Broken', level=2, character='tense, off-kilter, dry',
    technique='rhythmic displacement: the same kick and bass hits rotated two steps against fixed hats',
    secondary=['micro-timing by shift (snare early, hat late)', 'ghost snares with probability', 'tom-as-bass by per-step note'],
    voices='Kick: dry, punchy. Drum 2: tuned clave. Drum 3: tom used as a bass line. Snare: tight crack. Cymbal: short metallic. Hat: tight.',
    key='G# (kick 52 Hz, bass voice D2 and neighbours)', bpm=130,
    demonstrates='B contains exactly the same kick and bass triggers as A, moved two steps later; against the unchanged hats and snare the groove leans differently. '
                 'The snare is pulled slightly early and one hat pushed late, and the ghost snares only play some of the time.',
    patterns=['A: broken kick / bass / snare groove', 'B: kick and bass displaced by two steps, bass decays locked']),
    song=[0, 0, 1, 0, 1, LOOP]))

# =====================================================================================================================
# Chrome Percussion - electro-techno, 124 bpm. FM metal: toms, a bell that plays an arpeggio, a bright ride.
# =====================================================================================================================
CP_KIT = make_kit(
    D1(Waveform=0, Coarse=30, Decay=21, Pitch_Mod=55, Pitch_Decay=24, FM_Amount=35, FM_Freq=40, Drive=55, Volume=127, Velocity_Volume=1),
    # drum 2: a metal tom, sine FM'd by a triangle
    D2(Waveform=0, FM_Waveform=1, Coarse=52, FM_Amount=80, FM_Freq=70, Decay=18, Pitch_Mod=40, Pitch_Decay=20, Volume=100, Velocity_Volume=1),
    # drum 3: an FM bell, a long-ish ring with a bright inharmonic modulator
    D3(Waveform=0, FM_Waveform=0, Coarse=64, FM_Amount=40, FM_Freq=100, Decay=30, Pitch_Mod=5, Pitch_Decay=8, Volume=100, Velocity_Volume=1),
    SN(Waveform=0, Coarse=58, Noise_Osc_Mix=50, Decay=16, Pitch_Mod=50, Pitch_Decay=22, Filter_Type=2, Filter_Freq=75, Resonance=40, Volume=88, Velocity_Volume=1),
    CY(Wave_1=3, Wave_2=3, Wave_3=3, Coarse=95, Mod_Osc_1_Gain=127, Mod_Osc_2_Gain=127, Mod_Osc_1_Freq=90, Mod_Osc_2_Freq=30, Decay=55, Filter_Type=1, Filter_Freq=50,
       Volume=70, Velocity_Volume=1),
    HH(Wave_1=3, Wave_2=2, Wave_3=3, Coarse=70, Mod_Osc_1_Gain=127, Mod_Osc_2_Gain=100, Filter_Type=1, Filter_Freq=92, Decay_closed=3, Decay_open=24, Volume=85, Velocity_Volume=1, Drive=85),
)
CP_A = pat(swing=52,
    k='9...9...9...9...',
    s='....8.......8.4.',
    h='.5.3.5.3.5.3.5.3',
    o='..5...5...5...5.',
    d3='7.5.6.4.7.5.')                                                            # 12-step bell figure over 16
CP_A.rel('d3', {0: 0, 2: 7, 4: 12, 6: 7, 8: 3, 10: 7})
CP_B = CP_A.copy()
CP_B.add('d2', 6, 90).add('d2', 10, 90).add('d2', 11, 70).add('d2', 14, 90)
CP_B.rel('d2', {6: 7, 10: 0, 11: 3, 14: -5}).lock('d2', [10, 14], 'Drum 2', 'FM Amount', {10: 127, 14: 40})
CP_B.lock('d3', [4, 8], 'Drum 3', 'FM Amount', {4: 85, 8: 127}).add('c', 15, 60)
PRESETS.append(Preset('Chrome Percussion', CP_KIT, [CP_A, CP_B], dict(
    category='Electro & Broken', level=1, character='metallic, bright, precise',
    technique='FM percussion: tuned FM voices (metal toms, a bell) with FM depth moved per hit',
    secondary=['12-step bell figure against 16 (polymeter)', 'tuned toms answer the bell', 'bright ride by the cymbal voice'],
    voices='Kick: FM sine. Drum 2: FM metal tom. Drum 3: FM bell. Snare: resonant tang. Cymbal: bright ride. Hat: metallic.',
    key='C minor-ish (bell C4, G4, C5, D#4 ...)', bpm=124,
    demonstrates='FM Amount is the timbre dial: on the bell it moves a hit from a soft tone to a clanging one, and on the metal tom from wooden to metallic, '
                 'while the rhythm and pitch of the pattern stay the same.',
    patterns=['A: groove + bell figure (12 steps)', 'B: metal-tom answers; FM amount locked per hit']),
    song=[0, 0, 1, LOOP],
    checks=[('bell: FM-locked hits are much brighter than plain bell hits', differs(1, 'd3', [0, 2, 6, 10], [8], 'centroid', ratio=1.25)),
            ('metal tom: FM locks change the timbre between hits', spread(1, 'd2', 'centroid', 1.4))]))
