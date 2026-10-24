"""Experimental: tuned FM percussion as an ensemble, polymetric machines, glitch and noise."""
from library.core import *
from library.audit import differs, spread

PRESETS = []

# =====================================================================================================================
# Glass Rain - 96 bpm. Three FM bells in three registers play pentatonic lines of different lengths (12, 16, 20 steps) through a ping-pong delay;
# raindrop ticks and a swelling shimmer on top. The loop takes 60 bars to repeat.
# =====================================================================================================================
GR_KIT = make_kit(
    # all three drum voices are bells: sine FM'd by a sine; the registers are C3, C4, C5
    D1(Waveform=0, FM_Waveform=0, Coarse=48, FM_Amount=45, FM_Freq=95, Decay=34, Pitch_Mod=0, Drive=25, Volume=100, Velocity_Volume=1, Audio_Out=6),
    D2(Waveform=0, FM_Waveform=0, Coarse=60, FM_Amount=45, FM_Freq=105, Decay=30, Pitch_Mod=0, Drive=25, Volume=95, Velocity_Volume=1, Audio_Out=6),
    D3(Waveform=0, FM_Waveform=0, Coarse=72, FM_Amount=50, FM_Freq=112, Decay=26, Pitch_Mod=0, Drive=25, Volume=90, Velocity_Volume=1, Audio_Out=6),
    # snare voice: a breath, band-passed noise that swells in
    SN(Waveform=4, Coarse=80, Noise_Osc_Mix=127, Attack=34, Decay=34, Pitch_Mod=0, Filter_Type=2, Filter_Freq=88, Resonance=45, Drive=30, Volume=60, Velocity_Volume=1, Audio_Out=6),
    # cymbal voice: a slow shimmer
    CY(Wave_1=0, Wave_2=0, Wave_3=1, Coarse=96, Mod_Osc_1_Gain=70, Mod_Osc_2_Gain=40, Mod_Osc_1_Freq=88, Mod_Osc_2_Freq=100, Attack=40, Decay=70, Filter_Type=1, Filter_Freq=40, Drive=20,
       Volume=60, Velocity_Volume=1, Audio_Out=6),
    # hat voice: raindrops, very high, very short, dry
    HH(Wave_1=0, Wave_2=0, Wave_3=4, Coarse=108, Mod_Osc_1_Gain=60, Mod_Osc_2_Gain=60, Filter_Type=1, Filter_Freq=60, Decay_closed=1, Decay_open=6, Drive=60,
       Volume=60, Velocity_Volume=1),
    # ping-pong delay, about 3/8 at 96 bpm (469 ms, per side), long feedback
    FX(FX_Type=4, FX_Delay_Type=1, FX_Dry_Wet=60, FX_P1=77, FX_P2=127, FX_P3=80, FX_P4=78),
)
GR_A = pat(
    k='7..4...6.4..',                                         # 12 steps
    d2='5...4..6..3...4.',                                    # 16
    d3='3.......4......3.5.',                                 # 19
    s='2' + '.' * 23,                                         # 24: one breath per cycle
    c='3' + '.' * 46,                                         # 47: one shimmer per cycle
    h='.5..3.4....2...3.5.3.4.')                              # 23: raindrops
GR_A.tune('k', [0, 7, 4, 9]).tune('d2', [7, 4, 9, 2, 7]).tune('d3', [14, 11, 7, 9])
for t, p in (('h', 70), ('d3', 80)):
    for i in list(GR_A.steps[TRACKS[t]]): GR_A.at(t, i, prob=p)
GR_B = GR_A.copy()
GR_B.lock_seq('d2', 'Drum 2', 'FM Amount', [100, None, None, 20, None]).lock_seq('d3', 'Drum 3', 'FM Amount', [120, None, 25, None])
GR_B.lock_seq('k', 'Drum 1', 'Decay', [None, 60, None, 12])
PRESETS.append(Preset('Glass Rain', GR_KIT, [GR_A, GR_B], dict(
    category='Experimental', level=1, character='shimmering, spacious, hypnotic',
    technique='three tuned FM bells of different pattern lengths (12 / 16 / 19 steps) through a ping-pong delay: slow phasing makes an endless pentatonic cascade',
    secondary=['FM amount and decay locked per bell hit', 'probability on the raindrops', 'swelling noise breath and shimmer from the snare and cymbal voices'],
    voices='Drum 1/2/3: FM bells in C3, C4, C5 (all through the FX delay). Snare: swelling noise breath. Cymbal: slow shimmer. Hat: raindrop ticks (dry).',
    key='C major pentatonic (C D E G A)', bpm=96,
    demonstrates='Each bell is the same simple voice; the music is in the track lengths (12, 16, 19 steps plus 24, 47 and 23 for breath, shimmer and drops) which drift against each other, '
                 'and in the FM amount that is locked on some hits to make them glassier or woodier. Delay time is in ms (469 ms = three eighths at 96 bpm).',
    patterns=['A: sparse cascade', 'B: the same notes, bell timbres and decays locked on selected hits']),
    song=[0, 1, LOOP], volumes=(127, 127, 127, 90, 110, 127)))

# =====================================================================================================================
# Clockwork Cathedral - 100 bpm. A drone chord struck by mechanisms that never line up (7, 9, 11, 13 steps).
# =====================================================================================================================
CC_KIT = make_kit(
    # drum 1: the great bell, very low, very long (the "toll")
    D1(Waveform=0, FM_Waveform=0, Coarse=36, FM_Amount=25, FM_Freq=50, Decay=60, Pitch_Mod=8, Pitch_Decay=40, Drive=30, Volume=110, Velocity_Volume=1, Audio_Out=6),
    # drum 2 / 3: metal bells a fifth and an octave above, FM with inharmonic ratios
    D2(Waveform=0, FM_Waveform=3, Coarse=55, FM_Amount=70, FM_Freq=70, Decay=40, Pitch_Mod=0, Drive=25, Volume=90, Velocity_Volume=1, Audio_Out=6),
    D3(Waveform=0, FM_Waveform=1, Coarse=60, FM_Amount=85, FM_Freq=85, Decay=32, Pitch_Mod=0, Drive=25, Volume=85, Velocity_Volume=1, Audio_Out=6),
    # snare voice: a ratchet, noise with the repeat counter (the voice retriggers its own envelope; the attack time is the spacing of the repeats)
    SN(Waveform=4, Coarse=70, Noise_Osc_Mix=127, Attack=12, Decay=20, Repeat_Count=7, Pitch_Mod=0, Filter_Type=2, Filter_Freq=82, Resonance=35, Drive=50, Volume=80, Velocity_Volume=1),
    # cymbal voice: a gong
    CY(Wave_1=0, Wave_2=1, Wave_3=1, Coarse=62, Mod_Osc_1_Gain=100, Mod_Osc_2_Gain=100, Mod_Osc_1_Freq=40, Mod_Osc_2_Freq=55, Decay=90, Attack=2, Filter_Type=0, Filter_Freq=85,
       Drive=30, Volume=70, Velocity_Volume=1, Audio_Out=6),
    # hat voice: the clock tick, 2 ms
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=80, Mod_Osc_1_Gain=60, Mod_Osc_2_Gain=60, Filter_Type=1, Filter_Freq=70, Decay_closed=0, Decay_open=4, Drive=80, Volume=70, Velocity_Volume=1),
    # delay: cathedral, 0.6 s, long feedback, dark
    FX(FX_Type=4, FX_Delay_Type=0, FX_Dry_Wet=55, FX_P1=100, FX_P2=127, FX_P3=55, FX_P4=85),
)
CC_A = pat(
    k='8.........5',                                          # 11
    d2='6....4...',                                           # 9
    d3='5.4....',                                             # 7
    s='.........4...',                                        # 13
    c='5' + '.' * 28,                                         # 29: a gong every 29 steps
    h='4.2.')                                                 # 4: the clock
CC_A.tune('k', [0, 7]).tune('d2', [0, 5]).tune('d3', [0, 7])
CC_B = CC_A.copy()
CC_B.lock_seq('k', 'Drum 1', 'Pitch Mod', [40, None]).lock_seq('d2', 'Drum 2', 'FM Amount', [110, 30]).lock_seq('d3', 'Drum 3', 'FM Amount', [20, None]).lock_seq('s', 'Snare', 'Repeat Count', [3])
PRESETS.append(Preset('Clockwork Cathedral', CC_KIT, [CC_A, CC_B], dict(
    category='Experimental', level=2, character='vast, mechanical, ritual',
    technique='polymeter as composition: loop lengths of 11, 9, 7, 13, 29 and 4 steps strike a drone chord; the whole figure repeats after thousands of steps',
    secondary=['a ratchet from the snare voice\'s repeat counter, its count locked in B', 'long dark delay in the FX bus', 'bell pitch sweep and FM depth locked on the first hits'],
    voices='Drum 1: great bell, very long. Drum 2/3: inharmonic FM bells (FX delay). Snare: noise ratchet (repeat counter). Cymbal: gong. Hat: 2 ms clock tick.',
    key='C (bells C2, G3, C4)', bpm=100,
    demonstrates='None of the loops share a length, so the strikes fall on different beats every bar. The ratchet is the snare voice retriggering itself (Repeat Count), and the locks '
                 'make the first hit of each cycle brighter or darker than later ones. Pattern lengths are shown in the pattern editor.',
    patterns=['A: the mechanism', 'B: first strikes locked: sweep on the toll, FM depth on the bells, a shorter ratchet']),
    song=[0, 1, LOOP], volumes=(90, 110, 110, 127, 80, 70)))

# =====================================================================================================================
# Tape Insects - 140 bpm. Chirps, clicks, buzz and static: sample-rate crush, random LFOs and probability make a loop that never repeats.
# =====================================================================================================================
TI_KIT = make_kit(
    # drum 1: chirp, a high sine with a steep pitch fall; a random LFO re-pitches every chirp
    D1(Waveform=0, Coarse=84, Decay=4, Pitch_Mod=100, Pitch_Decay=7, Drive=40, Sample_Rate_Reducer=85, Volume=90, Velocity_Volume=1,
       LFO_Wave=5, LFO_Rate=35, LFO_Amount=45, LFO_Target=tgt('Drum 1: Coarse')),
    # drum 2: tick, band-passed noise with a random LFO on the band
    D2(Waveform=4, Coarse=80, Decay=2, Pitch_Mod=0, Filter_Type=2, Filter_Freq=85, Resonance=60, Drive=50, Volume=90, Velocity_Volume=1,
       LFO_Wave=5, LFO_Rate=50, LFO_Amount=50, LFO_Target=tgt('Drum 2: Filter Freq')),
    # drum 3: buzz, a saw whose pitch the LFO shakes at a fast rate, crushed
    D3(Waveform=2, Coarse=70, Decay=9, Pitch_Mod=0, Drive=60, Sample_Rate_Reducer=70, Filter_Type=0, Filter_Freq=100, Volume=85, Velocity_Volume=1,
       LFO_Wave=4, LFO_Rate=85, LFO_Amount=35, LFO_Target=tgt('Drum 3: Fine')),
    SN(Waveform=4, Coarse=76, Noise_Osc_Mix=127, Decay=3, Pitch_Mod=0, Filter_Type=1, Filter_Freq=50, Drive=70, Sample_Rate_Reducer=45, Volume=80, Velocity_Volume=1),
    CY(Wave_1=4, Wave_2=4, Wave_3=4, Coarse=100, Decay=14, Attack=0, Filter_Type=2, Filter_Freq=100, Resonance=30, Drive=60, Sample_Rate_Reducer=60, Volume=70, Velocity_Volume=1),
    HH(Wave_1=0, Wave_2=0, Wave_3=4, Coarse=105, Mod_Osc_1_Gain=127, Mod_Osc_2_Gain=127, Filter_Type=1, Filter_Freq=65, Decay_closed=1, Decay_open=7, Drive=70,
       Sample_Rate_Reducer=80, Volume=70, Velocity_Volume=1),
)
TI_A = pat(swing=52,
    k='5..3.4...5..3.4..5.3.4.5..3.4...',
    d2='.4.3.5.2.4.3.5.2.4.3.5.2',                            # 24
    d3='.......6.......4.......3.......',
    s='....6...........4.......',                             # 24
    c='..........2.......3......',                            # 27
    h='3.2.4.3.2.3.4.2.')                                     # 16
for t, p in (('k', 70), ('d2', 75), ('d3', 80), ('s', 70), ('c', 65), ('h', 60)):
    for i in list(TI_A.steps[TRACKS[t]]): TI_A.at(t, i, prob=p)
TI_B = TI_A.copy()
TI_B.lock_seq('d3', 'Drum 3', 'LFO Rate', [40, 100, 127]).lock_seq('d3', 'Drum 3', 'Sample Rate Reducer', [40, None, 100])
TI_B.lock_seq('k', 'Drum 1', 'Pitch Mod', [40, None, None, None, None, 127, None, None, None, None, None, None])
PRESETS.append(Preset('Tape Insects', TI_KIT, [TI_A, TI_B], dict(
    category='Experimental', level=1, character='chirping, crunchy, alive',
    technique='random LFOs and sample-rate crush on tiny sounds with probabilities: every pass sounds different',
    secondary=['sample-and-hold LFO re-pitches each chirp and re-tunes each tick', 'LFO rate and crush locked per buzz', 'polymeter 32 / 24 / 27 / 16'],
    voices='Drum 1: chirp (random pitch). Drum 2: band-pass tick (random band). Drum 3: crushed saw buzz, LFO on fine pitch. Snare: static snap. Cymbal: noise puff. Hat: cricket.',
    key='none (random pitches around F#6)', bpm=140,
    demonstrates='Sample-and-hold LFOs are modulation sources that never repeat: each chirp lands on a new pitch, each tick on a new band, while probabilities decide which of them play. '
                 'In B, the buzz voice has its LFO rate and sample-rate reduction locked per hit, from a slow rattle to a high whine.',
    patterns=['A: the swarm', 'B: buzz LFO rate and crush locked, chirp pitch sweep locked']),
    song=[0, 1, LOOP], volumes=(127, 127, 100, 90, 110, 110), rms_floor=-31))
