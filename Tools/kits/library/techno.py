"""Techno family: warehouse, hypnotic, industrial, dub, Detroit-minded, hard, broken, electro.
No artist is imitated: each kit is built from a sound idea (what the voices are for) and each pattern pair answers one question."""
from library.core import *
from library.audit import differs, spread

PRESETS = []

# =====================================================================================================================
# Warehouse Pulse - driving warehouse techno, 132 bpm
# =====================================================================================================================
WP_KIT = make_kit(
    # kick: short, powerful, slightly distorted, a small tick of click on top; tuned to G1 (49 Hz) = the key of the whole kit
    D1(Waveform=0, Coarse=31, Decay=17, Pitch_Mod=68, Pitch_Decay=22, Drive=75, Click_Type=2, Click_Level=45, Volume=127, Velocity_Volume=1),
    # drum 2: metallic resonant "ting": triangle FM triangle through a ringing band-pass
    D2(Waveform=1, FM_Waveform=1, Coarse=66, FM_Amount=70, FM_Freq=45, Decay=14, Pitch_Mod=30, Pitch_Decay=8, Filter_Type=2, Filter_Freq=80, Resonance=60,
       Volume=118, Velocity_Volume=1, Drive=60),
    # drum 3: tuned bass voice (saw through a low-pass), used as a melodic stab line
    D3(Waveform=2, Coarse=31, Decay=20, Pitch_Mod=0, Filter_Type=0, Filter_Freq=45, Resonance=40, Drive=50, Volume=110, Velocity_Volume=1),
    # snare: noisy, sharp transient (rim click), dark body (low sine), noise high-passed
    SN(Waveform=0, Coarse=50, Noise_Osc_Mix=85, Decay=15, Pitch_Mod=35, Pitch_Decay=18, Filter_Type=1, Filter_Freq=35, Drive=40, Click_Type=6, Click_Level=45,
       Volume=88, Velocity_Volume=1),
    # cymbal voice as a tight metallic ride
    CY(Wave_1=3, Wave_2=2, Wave_3=3, Coarse=85, Mod_Osc_1_Gain=127, Mod_Osc_1_Freq=80, Mod_Osc_2_Freq=40, Decay=36, Filter_Type=1, Filter_Freq=70,
       Volume=80, Velocity_Volume=1),
    # hats: bright but controlled
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=63, Mod_Osc_1_Gain=100, Mod_Osc_2_Gain=100, Filter_Type=1, Filter_Freq=95, Decay_closed=3, Decay_open=22,
       Volume=110, Velocity_Volume=1, Drive=85),
)

_k = '9...9...9...9...'
WP_A = pat(swing=51,
    k=_k * 2,
    s='....8.......8...' * 2,
    o='..7...7...7...7.' * 2,
    h='.4.5.4.5.4.5.4.5' [:16] * 2,
    d3='..7..........5..' + '..7.....5.......',
    d2='.......6...........' [:16] + '..........4....6')
WP_B = WP_A.copy()
WP_B.lock('k', [28], 'Drum 1', 'Decay', 11).at('k', 28, note=63)                                   # bar-2 last kick: higher + shorter = phrase ending
WP_B.lock('s', [28], 'Snare', 'Filter Freq', 90).lock('s', [28], 'Snare', 'Decay', 8).at('s', 28, note=66)   # last snare: higher, brighter, snappier (a lift into the next phrase)
WP_B.rel('d3', {2: 0, 13: 3, 18: 0, 24: 5}).lock('d3', [2, 13, 18, 24], 'Drum 3', 'Filter Freq', {2: 35, 13: 55, 18: 75, 24: 95})
WP_B.lock('d2', [7, 26], 'Drum 2', 'FM Amount', {7: 40, 26: 100}).lock('o', [30], 'Hi-hat', 'Decay (open)', 60)

def _wp_checks(p):
    return [('kick: locked last hit has a shorter decay than the plain hits', differs(1, 'k', [0, 4, 8, 12], [28], 'decay', ratio=1.25)),
            ('kick: locked last hit is higher in pitch (note +3)', differs(1, 'k', [0, 4, 8, 12], [28], 'centroid', ratio=1.12)),
            ('snare: last hit is higher and snappier than the plain hits', differs(1, 's', [4, 12, 20], [28], 'dominant', ratio=1.25)),
            ('snare: last hit decays much faster', differs(1, 's', [4, 12, 20], [28], 'decay', ratio=1.5)),
            ('bass voice: stepped filter lock makes every note a different brightness', spread(1, 'd3', 'centroid', 1.5))]

PRESETS.append(Preset('Warehouse Pulse', WP_KIT, [WP_A, WP_B], dict(
    category='Techno', level=2, character='dark, hard, short, controlled',
    technique='phrase-ending locks on kick/snare, stepped filter lock on a tuned bass voice',
    secondary=['velocity accents (Velocity > Volume on every voice)', 'two-bar phrase', 'tuned percussion in the kick\'s key'],
    voices='Kick: short, distorted, tick click. Drum 2: metallic FM ting. Drum 3: tuned saw bass stab. Snare: noise + dark body. Cymbal: tight ride. Hat: bright, controlled.',
    key='G (kick 49 Hz, bass voice root G1)', bpm=132,
    demonstrates='Pattern B is rhythmically the same as A; only per-step locks differ: the last kick of the phrase gets a higher pitch and shorter decay, '
                 'the snare accents get brighter and snappier, and the bass voice climbs a minor-third line while its filter opens.',
    patterns=['A: core groove, plain', 'B: same groove + phrase-ending locks, pitched/filtered bass line']),
    song=[0, 0, 1, 0, 0, 1, LOOP], checks=_wp_checks(None)))


# =====================================================================================================================
# Concrete Roller - hypnotic minimal techno, 128 bpm. Three against four: a 12-step hat figure rolls over a 16-step kick.
# =====================================================================================================================
CR_KIT = make_kit(
    D1(Waveform=0, Coarse=30, Decay=21, Pitch_Mod=52, Pitch_Decay=24, Drive=60, Volume=120, Velocity_Volume=1),
    # drum 2: a tuned wooden tick (sine + a little FM), the voice that plays the figure in pattern B
    D2(Waveform=0, FM_Waveform=0, Coarse=76, FM_Amount=30, FM_Freq=60, Decay=5, Pitch_Mod=15, Pitch_Decay=6, Volume=105, Velocity_Volume=1),
    # drum 3: sub pulse, triangle through a low-pass that a slow tempo-synced LFO opens and closes
    D3(Waveform=1, Coarse=30, Decay=18, Pitch_Mod=10, Pitch_Decay=10, Filter_Type=0, Filter_Freq=40, Resonance=35, Volume=110, Velocity_Volume=1,
       LFO_Wave=1, LFO_Sync=2, LFO_Amount=45, LFO_Target=tgt('Drum 3: Filter Freq')),
    # snare voice as a dry noise rim: band-passed noise burst, very short
    SN(Waveform=0, Coarse=68, Noise_Osc_Mix=100, Decay=7, Pitch_Mod=0, Filter_Type=2, Filter_Freq=82, Resonance=25, Volume=95, Velocity_Volume=1, Drive=60),
    CY(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=70, Mod_Osc_1_Gain=100, Mod_Osc_2_Gain=100, Decay=70, Filter_Type=0, Filter_Freq=60, Attack=10, Volume=70, Velocity_Volume=1),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=66, Mod_Osc_1_Gain=100, Mod_Osc_2_Gain=100, Filter_Type=1, Filter_Freq=88, Decay_closed=2, Decay_open=18,
       Volume=110, Velocity_Volume=1, Drive=85),
)
CR_A = pat(swing=50,
    k='9...9...9...9...',
    s='....5.......5...',
    d3='..6...5...6...5.',
    h='6..4..5..4..',                       # every third step: three against the kick's four
    d2='..4...3...4...3.')
CR_B = CR_A.copy()
CR_B.remove('d2', range(16))
CR_B.steps[1] = {i: dict(vol=v) for i, v in {1: 80, 3: 55, 6: 80, 8: 55, 9: 70}.items()}; CR_B.length[1] = 10      # a 10-step figure against 16 and 12: the loop takes 15 bars to repeat
CR_B.tune('d2', [0, 7, 3, 10, 5])
CR_B.rel('h', {0: 0, 3: 0, 6: 2, 9: 0}).lock('h', [3, 9], 'Hi-hat', 'Decay (closed)', 10)
PRESETS.append(Preset('Concrete Roller', CR_KIT, [CR_A, CR_B], dict(
    category='Techno', level=2, character='hypnotic, warm, patient',
    technique='polymeter (12 and 10 steps against 16) + a slow tempo-synced LFO on a filter',
    secondary=['tuned tick figure by per-step note', 'hat pitch/decay accents by lock'],
    voices='Kick: round, a little drive. Drum 2: wooden tuned tick. Drum 3: triangle sub pulse, LFO-swept low-pass. Snare: dry noise rim. Hat: dry ticks.',
    key='F# (kick 46 Hz, sub pulse F#1, tick figure in F# minor pentatonic)', bpm=128,
    demonstrates='Nothing in the groove is complicated; the movement comes from track lengths that do not line up (16 / 12 / 10) and from a slow LFO that opens and closes the sub-pulse filter, '
                 'so each repeat of the one-bar kick sounds like a different bar.',
    patterns=['A: kick 16, hat 12 (three against four), sub pulse with LFO', 'B: adds a 10-step tuned tick figure; hats get pitch and decay accents']),
    song=[0, 0, 0, 1, 1, LOOP]))

# =====================================================================================================================
# Foggy Dub - dub techno, 122 bpm. Stabs and a rim go through the delay; the delay's feedback and time are played with locks.
# =====================================================================================================================
FD_KIT = make_kit(
    D1(Waveform=0, Coarse=28, Decay=26, Pitch_Mod=38, Pitch_Decay=28, Amp_Slope=70, Drive=55, Volume=122, Velocity_Volume=1),
    # two square-wave stabs a minor third apart (a dyad), both into the FX delay
    D2(Waveform=3, Coarse=53, Decay=12, Pitch_Mod=0, Filter_Type=0, Filter_Freq=62, Resonance=45, Volume=100, Velocity_Volume=1, Audio_Out=6, Drive=40),
    D3(Waveform=3, Coarse=56, Decay=12, Pitch_Mod=0, Filter_Type=0, Filter_Freq=58, Resonance=45, Volume=100, Velocity_Volume=1, Audio_Out=6, Drive=40),
    SN(Waveform=0, Coarse=72, Noise_Osc_Mix=30, Decay=6, Pitch_Mod=15, Pitch_Decay=8, Filter_Type=2, Filter_Freq=75, Volume=95, Velocity_Volume=1, Audio_Out=6, Drive=50),
    CY(Wave_1=4, Wave_2=4, Wave_3=4, Coarse=80, Decay=48, Filter_Type=2, Filter_Freq=75, Resonance=30, Attack=14, Volume=70, Velocity_Volume=1),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=60, Mod_Osc_1_Gain=90, Mod_Osc_2_Gain=90, Filter_Type=1, Filter_Freq=88, Decay_closed=4, Decay_open=26,
       Volume=100, Velocity_Volume=1, Drive=85),
    # delay: about a dotted eighth at 122 bpm (369 ms), dark, long feedback, 55 % wet
    FX(FX_Type=4, FX_Dry_Wet=55, FX_P1=61, FX_P2=127, FX_P3=60, FX_P4=78),
)
FD_A = pat(swing=54,
    k='9...9...9...9...',
    o='..6.......6.....',
    h='.2.3.2.3.2.3.2.3',
    d2='.....5..........',
    d3='.....5..........',
    s='...........4....')
FD_B = FD_A.copy()
FD_B.add('d2', 10, 80).add('d3', 10, 80).add('d2', 14, 60).add('d3', 14, 60)
FD_B.rel('d2', {5: 0, 10: -2, 14: 3}).rel('d3', {5: 0, 10: -2, 14: 3})              # Fm7-ish -> Eb -> Ab: the dyad moves
FD_B.lock('s', [11], 'FX', 'FX P4', 112).lock('s', [11], 'FX', 'FX P1', 76)         # dub throw: feedback up and the delay time bent on one rim hit
FD_B.lock('d2', [14], 'Drum 2', 'Filter Freq', 90).lock('d3', [14], 'Drum 3', 'Filter Freq', 90)
PRESETS.append(Preset('Foggy Dub', FD_KIT, [FD_A, FD_B], dict(
    category='Techno', level=1, character='deep, hazy, spacious',
    technique='FX delay as an instrument: voices routed to the FX bus, delay feedback and time locked per step',
    secondary=['tuned dyad stabs (per-step note)', 'swing 54 %', 'ghosted hats by velocity'],
    voices='Kick: soft and deep. Drum 2 + Drum 3: square-wave stabs a minor third apart, FX bus. Snare: tuned rim, FX bus. Cymbal: filtered noise wash. Hat: soft.',
    key='F (stabs Fm third, kick E1)', bpm=122,
    demonstrates='One rim hit carries two FX locks (feedback and delay time): the echoes swell and bend after it, a dub-mixer throw played by the sequencer. '
                 'The delay time is in milliseconds, set to a dotted eighth at 122 bpm.',
    patterns=['A: one dyad stab and one rim into the delay', 'B: the dyad moves, the rim throws the delay']),
    song=[0, 0, 1, 1, LOOP]))


# =====================================================================================================================
# Slag Works - industrial techno, 138 bpm. Noise, FM, distortion, resonance, very short envelopes.
# =====================================================================================================================
SW_KIT = make_kit(
    # kick: FM sine kick, hard drive, crushed sample rate, a second click on top
    D1(Waveform=0, Coarse=29, Decay=20, Pitch_Mod=60, Pitch_Decay=18, FM_Amount=55, FM_Freq=30, Drive=90, Sample_Rate_Reducer=100, Click_Type=3, Click_Level=60,
       Volume=127, Velocity_Volume=1),
    # drum 2: anvil, rectangle FM'd by a saw through a ringing band-pass
    D2(Waveform=3, FM_Waveform=2, Coarse=71, FM_Amount=90, FM_Freq=75, Decay=13, Pitch_Mod=6, Pitch_Decay=6, Filter_Type=2, Filter_Freq=85, Resonance=55, Drive=60,
       Volume=100, Velocity_Volume=1),
    # drum 3: motor growl, a saw at 33 Hz whose FM depth a fast LFO shakes
    D3(Waveform=2, Coarse=24, Decay=18, Pitch_Mod=0, FM_Amount=40, FM_Freq=50, Filter_Type=0, Filter_Freq=55, Resonance=20, Drive=100, Volume=105, Velocity_Volume=1,
       LFO_Wave=4, LFO_Rate=75, LFO_Amount=60, LFO_Target=tgt('Drum 3: FM Amount')),
    # snare: a clang, rectangle + noise, clipped, with a snare click on top; through the fold distortion
    SN(Waveform=3, Coarse=64, Noise_Osc_Mix=45, Decay=20, Pitch_Mod=0, Filter_Type=1, Filter_Freq=20, Drive=60, Click_Type=11, Click_Level=70,
       Volume=45, Velocity_Volume=1, Audio_Out=0),
    # cymbal: a burst of steam, band-passed noise
    CY(Wave_1=4, Wave_2=4, Wave_3=4, Coarse=90, Decay=30, Attack=6, Filter_Type=2, Filter_Freq=80, Resonance=45, Volume=80, Velocity_Volume=1, Drive=0),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=75, Mod_Osc_1_Gain=127, Mod_Osc_2_Gain=127, Filter_Type=1, Filter_Freq=85, Decay_closed=1, Decay_open=12, Drive=70,
       Sample_Rate_Reducer=100, Volume=70, Velocity_Volume=1),
)
SW_A = pat(
    k='9...9...9...9...',
    d2='..5..5..5..5..5.',
    s='....7.......7...',
    h='6363636363636363',
    d3='.7..............')
SW_B = pat(
    k='9...9...9...9... 9...9...9.......',
    d2='..5..5..5..5..5. ..5..5..5..5..5.',
    s='....7.......7... ....7.......6.6.',
    h='6363636363636363 6363636363636.3.',
    c='................ ...............4',
    d3='.7.............. .7..............')
SW_B.rel('d2', {18: 0, 21: 3, 24: 5, 27: 7, 30: 10}).lock('d2', [24, 30], 'Drum 2', 'FM Amount', {24: 110, 30: 127})
SW_B.at('s', 28, flam=3).at('s', 30, flam=4, shift=5).lock('s', [28, 30], 'Snare', 'Filter Freq', {28: 40, 30: 80})
SW_B.lock('d3', [17], 'Drum 3', 'LFO Rate', {17: 110})
PRESETS.append(Preset('Slag Works', SW_KIT, [SW_A, SW_B], dict(
    category='Techno', level=2, character='mechanical, abrasive, dense',
    technique='industrial sound design: FM, hard drive, sample-rate crush, a fast LFO shaking FM depth',
    secondary=['anvil riff by note + FM locks', 'snare flam roll with shift', 'three-step machine rhythm against four-on-the-floor'],
    voices='Kick: FM + drive + crush. Drum 2: FM anvil, ringing band-pass. Drum 3: saw motor, LFO on FM depth. Snare: clipped clang. Cymbal: steam burst. Hat: crushed ticks.',
    key='no tuned key; kick 44 Hz, anvil riff climbs from C5', bpm=138,
    demonstrates='Every sound has an edge from a different mechanism (FM, clipping, sample-rate reduction, a fast square LFO on FM depth); '
                 'in pattern B two bars climb to a fill where the anvil\'s FM depth and the snare\'s filter are locked per hit.',
    patterns=['A: four on the floor, a machine rhythm of three against four, clang on 2 and 4', 'B: two bars: the second climbs into a drop-out fill (flam roll, anvil riff, steam)']),
    song=[0, 0, 1, LOOP]))

# =====================================================================================================================
# Midnight Assembly - Detroit-minded techno, 133 bpm: round kick, clap, tuned toms that play a hook, swung hats.
# =====================================================================================================================
MA_KIT = make_kit(
    D1(Waveform=0, Coarse=29, Decay=25, Pitch_Mod=48, Pitch_Decay=28, Drive=55, Volume=127, Velocity_Volume=1),
    # drum 2: cowbell-ish, two rectangles in FM through a band-pass
    D2(Waveform=3, FM_Waveform=3, Coarse=72, FM_Amount=50, FM_Freq=95, Decay=11, Pitch_Mod=4, Pitch_Decay=6, Filter_Type=2, Filter_Freq=72, Resonance=30,
       Volume=80, Velocity_Volume=1),
    # drum 3: a tuned tom, the hook voice
    D3(Waveform=0, Coarse=43, Decay=22, Pitch_Mod=42, Pitch_Decay=24, Drive=20, Click_Type=12, Click_Level=30, Volume=112, Velocity_Volume=1),
    # snare voice as a clap: noise through a band-pass, sample clap on top
    SN(Waveform=4, Coarse=57, Noise_Osc_Mix=127, Decay=18, Pitch_Mod=0, Filter_Type=2, Filter_Freq=60, Resonance=15, Click_Type=9, Click_Level=100,
       Volume=88, Velocity_Volume=1),
    CY(Wave_1=3, Wave_2=2, Wave_3=3, Coarse=85, Mod_Osc_1_Gain=127, Mod_Osc_1_Freq=80, Mod_Osc_2_Freq=40, Decay=42, Filter_Type=1, Filter_Freq=65,
       Volume=60, Velocity_Volume=1),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=63, Mod_Osc_1_Gain=100, Mod_Osc_2_Gain=100, Filter_Type=1, Filter_Freq=88, Decay_closed=3, Decay_open=20,
       Volume=95, Velocity_Volume=1, Drive=85),
)
MA_A = pat(swing=55,
    k='9...9...9...9...',
    s='....8.......8...',
    o='..6...6...6...6.',
    h='.5.3.5.3.5.3.5.3',
    d3='...7..6.....7.6.')
MA_A.rel('d3', {3: 0, 6: 3, 12: 0, 14: 5})
MA_B = MA_A.copy()
MA_B.add('k', 10, 90).add('s', 15, 40, flam=1).add('d2', 6, 70).add('d2', 14, 55).add('d3', 9, 80)
MA_B.rel('d3', {3: 5, 6: 8, 9: 7, 12: 5, 14: 3})                                   # the hook moves up a fourth
MA_B.lock('h', [15], 'Hi-hat', 'Filter Freq', 112).lock('o', [14], 'Hi-hat', 'Decay (open)', 8).lock('d2', [6, 14], 'Drum 2', 'Filter Freq', {6: 60, 14: 90})
PRESETS.append(Preset('Midnight Assembly', MA_KIT, [MA_A, MA_B], dict(
    category='Techno', level=1, character='warm, melodic, driving',
    technique='a tom that plays a melody (per-step note) over a swung backbeat',
    secondary=['55 % swing on the whole pattern', 'hat accents by lock', 'cowbell FM voice added in B'],
    voices='Kick: round, warm. Drum 2: FM cowbell. Drum 3: tuned tom (hook). Snare: noise + sample clap. Cymbal: ride. Hat: bright, swung.',
    key='G minor (kick 49 Hz; hook G2 - Bb - C - D)', bpm=133,
    demonstrates='A tom is a pitched voice: the same hit with different per-step notes gives a hook; pattern B moves the hook up a fourth and adds a cowbell without touching the groove.',
    patterns=['A: groove + tom hook', 'B: hook moves up, extra kick/clap ghost, cowbell, last hat brightens, last open hat snaps shut']),
    song=[0, 0, 0, 1, LOOP]))

# =====================================================================================================================
# Hardwire - hard / distorted techno, 150 bpm.
# =====================================================================================================================
HW_KIT = make_kit(
    D1(Waveform=3, Coarse=33, Decay=19, Pitch_Mod=90, Pitch_Decay=16, Drive=100, Filter_Type=0, Filter_Freq=68, Filter_Drive=40, Click_Type=5, Click_Level=60,
       Volume=127, Velocity_Volume=1),
    # drum 2: zap, a saw whose pitch falls from 8 kHz-ish
    D2(Waveform=2, Coarse=72, Decay=11, Pitch_Mod=118, Pitch_Decay=14, Drive=40, Filter_Type=0, Filter_Freq=127, Volume=110, Velocity_Volume=1),
    # drum 3: rumble, a distorted sub that plays the 16ths between the kicks
    D3(Waveform=0, Coarse=28, Decay=14, Pitch_Mod=20, Pitch_Decay=12, Drive=80, Filter_Type=0, Filter_Freq=60, Volume=105, Velocity_Volume=1),
    SN(Waveform=4, Coarse=57, Noise_Osc_Mix=127, Decay=20, Pitch_Mod=0, Filter_Type=2, Filter_Freq=62, Resonance=20, Drive=90, Click_Type=9, Click_Level=90,
       Volume=70, Velocity_Volume=1),
    CY(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=80, Mod_Osc_1_Gain=127, Mod_Osc_2_Gain=127, Decay=72, Filter_Type=1, Filter_Freq=40, Attack=0, Volume=75, Velocity_Volume=1),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=70, Mod_Osc_1_Gain=127, Mod_Osc_2_Gain=127, Filter_Type=1, Filter_Freq=70, Decay_closed=3, Decay_open=18, Drive=100,
       Sample_Rate_Reducer=90, Volume=85, Velocity_Volume=1),
)
HW_A = pat(
    k='9...9...9...9...',
    d3='.776' * 4,
    s='....9.......9...',
    o='..6...6...6...6.',
    h='.3.3.3.3.3.3.3.3',
    d2='...............4')
HW_B = HW_A.copy()
HW_B.rel('d3', {3: 3, 11: 5, 14: 3, 15: 7})                                         # the rumble walks: root ... minor third, fourth, minor third, fifth
HW_B.lock('d3', [3, 11, 15], 'Drum 3', 'Filter Freq', {3: 85, 11: 85, 15: 100})
HW_B.at('s', 12, flam=2).add('s', 14, 90, flam=3, shift=5).add('s', 15, 100, flam=4)
HW_B.lock('d2', [15], 'Drum 2', 'Decay', 40).at('d2', 15, note=72)
PRESETS.append(Preset('Hardwire', HW_KIT, [HW_A, HW_B], dict(
    category='Techno', level=2, character='relentless, distorted, fast',
    technique='distortion as part of the voice: kick and rumble overdriven inside the voice, crushed hats',
    secondary=['kick-bass interlock: the sub voice plays every 16th the kick leaves free', 'flam roll fill', 'sub walks by per-step note + filter lock'],
    voices='Kick: rectangle, hard drive, filter, kick click. Drum 2: falling zap. Drum 3: distorted sub rumble. Snare: distorted noise clap. Cymbal: crash. Hat: crushed.',
    key='E (rumble E1, minor third G, fourth A)', bpm=150,
    demonstrates='The kick and the rumble voice are overdriven inside the voice, so the 16ths between the kicks pump without a compressor; in B the rumble walks up a minor third and the snare rolls into the bar.',
    patterns=['A: four on the floor + rumble 16ths', 'B: rumble walks, snare flam roll, long zap on the turnaround']),
    song=[0, 0, 0, 1, LOOP]))
