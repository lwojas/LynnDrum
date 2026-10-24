"""Drum & bass family: classic break, modern rolling, techstep, liquid, neuro. 160-175 bpm: a 16th is ~87 ms, so a bar of 16 steps is one 2-step cycle."""
from library.core import *
from library.audit import differs, spread

PRESETS = []

# =====================================================================================================================
# Break Engine - classic breakbeat-inspired drum & bass, 168 bpm, 53 % swing. Ghost snares, a tom fill, and the percussion changes in B.
# =====================================================================================================================
BE_KIT = make_kit(
    D1(Waveform=0, Coarse=32, Decay=12, Pitch_Mod=78, Pitch_Decay=18, Drive=60, Click_Type=2, Click_Level=30, Volume=127, Velocity_Volume=1),
    # drum 2 / 3: two tuned toms for the fills
    D2(Waveform=1, Coarse=58, Decay=14, Pitch_Mod=50, Pitch_Decay=20, Drive=45, Volume=100, Velocity_Volume=1),
    D3(Waveform=1, Coarse=50, Decay=16, Pitch_Mod=50, Pitch_Decay=22, Drive=45, Volume=100, Velocity_Volume=1),
    # snare: triangle body + high-passed noise, a sample snare on top, driven
    SN(Waveform=1, Coarse=56, Noise_Osc_Mix=70, Decay=13, Pitch_Mod=35, Pitch_Decay=18, Filter_Type=1, Filter_Freq=35, Drive=55, Click_Type=11, Click_Level=50,
       Volume=100, Velocity_Volume=1),
    # cymbal voice: ride (B) and crash
    CY(Wave_1=3, Wave_2=2, Wave_3=3, Coarse=90, Mod_Osc_1_Gain=127, Mod_Osc_1_Freq=80, Mod_Osc_2_Freq=40, Decay=44, Filter_Type=1, Filter_Freq=60, Drive=40,
       Volume=70, Velocity_Volume=1),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=66, Mod_Osc_1_Gain=100, Mod_Osc_1_Freq=70, Mod_Osc_2_Gain=100, Filter_Type=1, Filter_Freq=75, Decay_closed=2, Decay_open=16, Drive=85,
       Volume=80, Velocity_Volume=1),
)
BE_A = pat(swing=53,
    k='9.5.......9..... 9.......5.9..7..',
    s='....9..2.3..9..2 ....9..2....9.32',
    h='5.5.5.5.5.5.5.5. 5.5.5.5.5.5.5.5.',
    o='..............5. ..............5.',
    d2='................ ............7.6.',
    d3='................ ..............7.')
BE_A.rel('d2', {28: 0, 30: -3}).rel('d3', {30: -5})
BE_A.at('s', 7, shift=6).at('s', 9, shift=8).at('s', 15, prob=70)
BE_B = BE_A.copy()
BE_B.remove('h', range(32)); BE_B.remove('o', range(32))
BE_B.steps[4] = {i: dict(vol=v) for i, v in {0: 127, 2: 70, 4: 90, 6: 70, 8: 90, 10: 70, 12: 90, 14: 70, 16: 90, 18: 70, 20: 90, 22: 70, 24: 90, 26: 70}.items()}; BE_B.length[4] = 32
BE_B.add('d2', 26, 80).add('d2', 27, 90).add('d3', 29, 100).add('d3', 31, 127, flam=1)
BE_B.rel('d2', {26: 3, 27: 0, 28: 0, 30: -3}).rel('d3', {29: -2, 30: -5, 31: -10})
BE_B.lock('s', [28], 'Snare', 'Decay', {28: 24}).lock('d3', [31], 'Drum 3', 'Decay', {31: 40})
BE_B.lock('c', [0], 'Cymbal', 'Decay', {0: 90}).lock('c', [0], 'Cymbal', 'Filter Freq', {0: 30})        # step 1: the ride becomes a crash
PRESETS.append(Preset('Break Engine', BE_KIT, [BE_A, BE_B], dict(
    category='Drum & Bass', level=1, character='punchy, tight, classic',
    technique='ghost snares (velocity must be on: Velocity > Volume) and a fill by tuned toms',
    secondary=['changing percussion between patterns (hats in A, ride + crash in B)', 'micro-timed ghost notes by shift', 'last-hit decay lock on the fill'],
    voices='Kick: short, punchy, click. Drum 2/3: two tuned toms. Snare: triangle + noise + sample, driven. Cymbal: ride/crash. Hat: bright metallic.',
    key='kick 49 Hz (G1), toms D3 and A#3-ish', bpm=168,
    demonstrates='The backbeat is only a few notes; the break comes from ghost snares at a quarter of the level and a few milliseconds off the grid. '
                 'B keeps the same drums but swaps the hats for a ride (with a crash made from the same voice by two locks) and extends the tom fill downwards.',
    patterns=['A: break with ghost snares, hats, tom fill', 'B: same break, ride + crash instead of hats, longer tom fill']),
    song=[0, 0, 1, LOOP]))

# =====================================================================================================================
# Rolling Tide - modern rolling drum & bass, 174 bpm, 54 % swing: the hats never stop, velocity makes the roll.
# =====================================================================================================================
RT_KIT = make_kit(
    D1(Waveform=0, Coarse=30, Decay=14, Pitch_Mod=60, Pitch_Decay=20, Drive=55, Volume=127, Velocity_Volume=1),
    # drum 2: a rim ghost tick, a short tuned triangle
    D2(Waveform=1, Coarse=82, Decay=4, Pitch_Mod=20, Pitch_Decay=6, Click_Type=6, Click_Level=40, Volume=90, Velocity_Volume=1),
    # drum 3: a second, softer snare for the ghost notes: sine body, little noise, low-passed
    D3(Waveform=0, Coarse=54, Decay=10, Pitch_Mod=40, Pitch_Decay=14, Filter_Type=0, Filter_Freq=100, Drive=30, Click_Type=12, Click_Level=40, Volume=90, Velocity_Volume=1),
    SN(Waveform=1, Coarse=54, Noise_Osc_Mix=75, Decay=12, Pitch_Mod=30, Pitch_Decay=16, Filter_Type=1, Filter_Freq=40, Drive=55, Click_Type=11, Click_Level=40,
       Volume=100, Velocity_Volume=1),
    # cymbal voice as a shaker: noise burst, short attack
    CY(Wave_1=4, Wave_2=4, Wave_3=4, Coarse=80, Decay=9, Attack=5, Filter_Type=2, Filter_Freq=92, Resonance=10, Drive=60, Volume=70, Velocity_Volume=1),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=68, Mod_Osc_1_Gain=100, Mod_Osc_2_Gain=100, Filter_Type=1, Filter_Freq=72, Decay_closed=2, Decay_open=14, Drive=90,
       Volume=80, Velocity_Volume=1,
       Velocity_Target=tgt('Hi-hat: Filter Freq'), Velocity_Amount=22),
)
RT_A = pat(swing=54,
    k='9.........7..... 9.....5...9.....',
    s='....9.......9... ....9.......9...',
    d3='.......3.2.....3 .......3.2....3.',
    h='6233523362335233 6233523362335233',
    c='.3.....3.....3.. .3.....3.....3.3',
    o='............5... ..............5.')
RT_B = RT_A.copy().set_length('d2', 32)
RT_B.remove('h', range(32))
for i in range(32): RT_B.add('h', i, 100 if i % 3 == 0 else 40)                 # accents every third 16th: a cycle of three over the bar of sixteen
RT_B.add('d2', 3, 70).add('d2', 11, 60).add('d2', 19, 80).add('d2', 27, 70).add('d2', 29, 50)
RT_B.tune('d2', [0, 3, 0, 5, 7]).lock('d2', [11, 27], 'Drum 2', 'Decay', {11: 9, 27: 12})
RT_B.lock('h', [8, 24], 'Hi-hat', 'Decay (closed)', {8: 6, 24: 6})
PRESETS.append(Preset('Rolling Tide', RT_KIT, [RT_A, RT_B], dict(
    category='Drum & Bass', level=2, character='fluid, relentless, light',
    technique='a rolling hat made entirely of velocity: every 16th plays, the accent pattern and the velocity-driven filter make the groove',
    secondary=['ghost snare voice (Drum 3) at low velocity', 'shaker from the cymbal voice', 'hat accent cycle changes between patterns 1 and 2'],
    voices='Kick: tight. Drum 2: rim tick. Drum 3: soft ghost snare. Snare: tight crack. Cymbal: noise shaker. Hat: driven metallic, velocity opens the high-pass.',
    key='kick 46 Hz (F#1), rim tick pitched around A5-C#6', bpm=174,
    demonstrates='There is no rhythmic variation in the hats at all (every 16th); the pattern is in the velocities. Velocity changes the loudness and also, through the velocity '
                 'target on the filter, how bright each hat is, so accents are heard as both.',
    patterns=['A: hats on every 16th with a 4-step velocity cycle, ghosts, shaker', 'B: accents every third 16th (a cycle of three over the bar of sixteen) plus a tuned rim figure']),
    song=[0, 0, 1, 0, LOOP], targets=dict(c=-24, d3=-14, d2=-16)))

# =====================================================================================================================
# Dark Matter - techstep, 172 bpm. Sub kick, a distorted crack, metal rims off the grid, a growling bass hit played by a drum voice.
# =====================================================================================================================
DM_KIT = make_kit(
    D1(Waveform=0, Coarse=28, Decay=18, Pitch_Mod=55, Pitch_Decay=22, Drive=70, Volume=127, Velocity_Volume=1),
    # drum 2: metal rim, FM square
    D2(Waveform=3, FM_Waveform=3, Coarse=84, FM_Amount=80, FM_Freq=60, Decay=6, Pitch_Mod=0, Filter_Type=2, Filter_Freq=85, Resonance=40, Drive=40,
       Volume=90, Velocity_Volume=1),
    # drum 3: growl, a saw at 33 Hz; a saw LFO sweeps its low-pass at audio-ish rate
    D3(Waveform=2, Coarse=28, Decay=34, Pitch_Mod=0, Filter_Type=0, Filter_Freq=55, Resonance=55, Drive=60, Volume=110, Velocity_Volume=1,
       LFO_Wave=2, LFO_Rate=62, LFO_Amount=55, LFO_Target=tgt('Drum 3: Filter Freq')),
    SN(Waveform=1, Coarse=52, Noise_Osc_Mix=55, Decay=18, Pitch_Mod=55, Pitch_Decay=22, Filter_Type=1, Filter_Freq=28, Drive=100, Click_Type=11, Click_Level=80,
       Volume=100, Velocity_Volume=1),
    CY(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=80, Mod_Osc_1_Gain=127, Mod_Osc_2_Gain=127, Decay=60, Filter_Type=1, Filter_Freq=45, Drive=40, Volume=70, Velocity_Volume=1),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=70, Mod_Osc_1_Gain=127, Mod_Osc_2_Gain=127, Filter_Type=1, Filter_Freq=70, Decay_closed=2, Decay_open=18, Drive=100,
       Volume=70, Velocity_Volume=1),
)
DM_A = pat(
    k='9.........9..... 9.........9.....',
    s='....9.......9... ....9.......9.5.',
    d2='..2.....3....5.2 ..3.....2....5..',
    h='..5...5.5.5...5. ..5...5.5.5...5.',
    d3='9............... ................')
DM_A.rel('d2', {2: 0, 8: 7, 13: 3, 15: 0, 18: 5, 24: 0, 29: 7})
DM_A.at('d2', 15, shift=8).at('d2', 18, shift=6)
DM_B = DM_A.copy()
DM_B.add('d3', 10, 110).add('d3', 24, 100).add('d3', 28, 127, flam=1)
DM_B.rel('d3', {0: 0, 10: 5, 24: 3, 28: 0})
DM_B.lock('d3', [0, 10, 24, 28], 'Drum 3', 'LFO Rate', {0: 40, 10: 90, 24: 110, 28: 127}).lock('d3', [10, 24], 'Drum 3', 'Resonance', {10: 90, 24: 25})
DM_B.at('s', 30, flam=3).lock('s', [30], 'Snare', 'Decay', {30: 28})
PRESETS.append(Preset('Dark Matter', DM_KIT, [DM_A, DM_B], dict(
    category='Drum & Bass', level=2, character='dark, heavy, menacing',
    technique='modulation as aggression: a saw LFO sweeps a resonant filter at near-audio rate; its rate is locked per hit',
    secondary=['bass-like hits played by a drum voice (Drum 3)', 'metal rims placed off the grid by shift', 'distorted snare with sample layer'],
    voices='Kick: sub, driven. Drum 2: FM metal rim. Drum 3: saw growl with LFO-swept low-pass. Snare: heavily driven. Cymbal: crash. Hat: driven.',
    key='E (kick 41 Hz, growl E1 with +5, +3 neighbours)', bpm=172,
    demonstrates='The LFO runs at tens of hertz (sampled at the 690 Hz control rate), so it is part of the timbre, not movement: locking its rate per hit gives each growl a '
                 'different character while the notes stay the same.',
    patterns=['A: sparse, heavy two-bar loop', 'B: growl hits with different LFO rates, flammed snare into the loop']),
    song=[0, 0, 1, LOOP]))

# =====================================================================================================================
# Liquid Glass - liquid drum & bass, 172 bpm, 56 % swing. Soft body, shuffling hats, glass bells through a delay.
# =====================================================================================================================
LG_KIT = make_kit(
    D1(Waveform=0, Coarse=30, Decay=16, Pitch_Mod=50, Pitch_Decay=22, Drive=50, Volume=127, Velocity_Volume=1),
    # drum 2: glass bell, sine FM'd by a sine at a high ratio, into the delay
    D2(Waveform=0, FM_Waveform=0, Coarse=72, FM_Amount=60, FM_Freq=105, Decay=28, Pitch_Mod=0, Drive=20, Volume=80, Velocity_Volume=1, Audio_Out=6),
    # drum 3: bass pluck, sine with a fast pitch drop (round, soft)
    D3(Waveform=0, Coarse=30, Decay=24, Pitch_Mod=30, Pitch_Decay=16, Drive=40, Volume=105, Velocity_Volume=1),
    # snare: round sine body, soft noise, low-passed top: the liquid pop
    SN(Waveform=0, Coarse=54, Noise_Osc_Mix=45, Decay=15, Pitch_Mod=40, Pitch_Decay=18, Filter_Type=0, Filter_Freq=105, Drive=45, Click_Type=12, Click_Level=40,
       Volume=100, Velocity_Volume=1),
    CY(Wave_1=4, Wave_2=4, Wave_3=4, Coarse=80, Decay=10, Attack=6, Filter_Type=2, Filter_Freq=95, Drive=50, Volume=70, Velocity_Volume=1),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=64, Mod_Osc_1_Gain=90, Mod_Osc_2_Gain=90, Filter_Type=1, Filter_Freq=70, Decay_closed=2, Decay_open=16, Drive=80,
       Volume=80, Velocity_Volume=1),
    # delay for the bells: 1/8 at 172 bpm = 174 ms = P1 29 at range 127 ... dotted 1/8 is 262 ms = P1 43
    FX(FX_Type=4, FX_Dry_Wet=50, FX_P1=43, FX_P2=127, FX_P3=70, FX_P4=60),
)
LG_A = pat(swing=56,
    k='9.........7..... 9.....6...9.....',
    s='....8.......8... ....8.......8...',
    h='.3.5.3.5.3.5.3.5 .3.5.3.5.3.5.3.5',
    c='5.2.3.2.5.2.3.2. 5.2.3.2.5.2.3.2.',
    d3='.....3........4. ..........3.....')
LG_A.rel('d3', {5: 0, 14: 5, 26: 0})
LG_B = LG_A.copy().set_length('d2', 32)
LG_B.add('d2', 2, 70).add('d2', 7, 55).add('d2', 12, 80).add('d2', 18, 60).add('d2', 23, 55).add('d2', 28, 85)
LG_B.tune('d2', [0, 7, 12, 5, 10, 14])                          # a rising line of bells: C - G - C - F - A# - D
LG_B.lock('d2', [12, 28], 'Drum 2', 'FM Amount', {12: 90, 28: 105})
PRESETS.append(Preset('Liquid Glass', LG_KIT, [LG_A, LG_B], dict(
    category='Drum & Bass', level=1, character='soft, airy, flowing',
    technique='tuned FM bells through a delay over a shuffled two-step: the percussion carries the harmony',
    secondary=['56 % swing', 'bell FM amount locked on the higher notes (brighter as they climb)', 'round snare from the sine + soft noise'],
    voices='Kick: soft. Drum 2: FM glass bell (FX delay). Drum 3: sine bass pluck. Snare: round pop. Cymbal: noise shaker. Hat: crisp shuffle.',
    key='C (bells: C - G - C - F - A# - D; pluck F#1/C#2)', bpm=172,
    demonstrates='Percussion that plays a line: six bell hits with different per-step notes and two FM locks give a rising melody; the delay (time set in ms to a dotted eighth at 172 bpm) '
                 'turns each hit into a short phrase.',
    patterns=['A: soft two-step, shuffled hats, bass pluck', 'B: the bell line climbs, FM amount locked on the top notes']),
    song=[0, 0, 1, 1, LOOP], targets=dict(d2=-18, c=-24)))

# =====================================================================================================================
# Neuro Bite - neuro-inspired drum & bass, 174 bpm. A drum voice becomes a bass: FM, a random LFO on FM depth, per-step notes and rates.
# =====================================================================================================================
NB_KIT = make_kit(
    D1(Waveform=0, Coarse=29, Decay=13, Pitch_Mod=70, Pitch_Decay=18, Drive=65, Volume=127, Velocity_Volume=1),
    # drum 2: a second growl, rectangle FM'd by a saw, its filter swept by a tempo-synced LFO
    D2(Waveform=3, FM_Waveform=2, Coarse=38, FM_Amount=55, FM_Freq=45, Decay=22, Pitch_Mod=0, Filter_Type=0, Filter_Freq=60, Resonance=60, Drive=60, Volume=100,
       Velocity_Volume=1, LFO_Wave=1, LFO_Sync=8, LFO_Amount=60, LFO_Target=tgt('Drum 2: Filter Freq')),
    # drum 3: the bite, saw FM'd by a saw; a sample-and-hold LFO shakes the FM depth
    D3(Waveform=2, FM_Waveform=2, Coarse=33, FM_Amount=50, FM_Freq=40, Decay=26, Pitch_Mod=0, Filter_Type=0, Filter_Freq=75, Resonance=30, Drive=70, Volume=105,
       Velocity_Volume=1, LFO_Wave=5, LFO_Rate=70, LFO_Amount=60, LFO_Target=tgt('Drum 3: FM Amount')),
    SN(Waveform=1, Coarse=53, Noise_Osc_Mix=60, Decay=14, Pitch_Mod=45, Pitch_Decay=20, Filter_Type=1, Filter_Freq=32, Drive=85, Click_Type=11, Click_Level=60,
       Volume=100, Velocity_Volume=1),
    CY(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=85, Mod_Osc_1_Gain=127, Mod_Osc_2_Gain=127, Decay=50, Filter_Type=1, Filter_Freq=55, Drive=50, Volume=60, Velocity_Volume=1),
    HH(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=70, Mod_Osc_1_Gain=127, Mod_Osc_2_Gain=127, Filter_Type=1, Filter_Freq=72, Decay_closed=2, Decay_open=14, Drive=95,
       Volume=70, Velocity_Volume=1),
)
NB_A = pat(
    k='9.........7..... 9.......7.9.....',
    s='....9.......9... ....9.......9...',
    h='.4.5.4.5.4.5.4.5 .4.5.4.5.4.5.4.5',
    d3='5.....7.....7... 5..5......7....5')
NB_A.rel('d3', {0: 0, 6: 3, 12: 7, 16: 0, 19: 5, 26: 3, 31: 10})
NB_B = NB_A.copy().set_length('d2', 32)
NB_B.lock('d3', [0, 6, 12, 16, 19, 26, 31], 'Drum 3', 'FM Freq', {0: 20, 6: 55, 12: 90, 16: 30, 19: 110, 26: 70, 31: 127})
NB_B.lock('d3', [6, 12, 19, 31], 'Drum 3', 'LFO Rate', {6: 30, 12: 90, 19: 110, 31: 127})
NB_B.add('d2', 14, 100).add('d2', 28, 110).rel('d2', {14: 0, 28: 5}).lock('d2', [14, 28], 'Drum 2', 'Resonance', {14: 90, 28: 40})
PRESETS.append(Preset('Neuro Bite', NB_KIT, [NB_A, NB_B], dict(
    category='Drum & Bass', level=2, character='aggressive, animated, synthetic',
    technique='fast modulation: a sample-and-hold LFO on FM depth and a tempo-synced LFO on a resonant filter turn drum voices into growling bass',
    secondary=['FM ratio and LFO rate locked per note', 'resonance lock on the second growl', 'driven snare'],
    voices='Kick: tight, driven. Drum 2: FM growl, resonant low-pass swept in sync. Drum 3: saw-FM bite, random LFO on FM depth. Snare: heavily driven. Cymbal: crash. Hat: driven.',
    key='F (growls F1 and D2, notes up to +10)', bpm=174,
    demonstrates='A hit of the bite voice is not one sound: its FM depth is being shaken by a random LFO the moment it triggers, and the locks move the modulator ratio (FM Freq) and the LFO rate per note, '
                 'so one voice produces a line of different growls. (The LFO owns FM Amount, so that one can not be locked.)',
    patterns=['A: groove with a simple bite line', 'B: the same line with FM ratio and LFO rate locked per note, a second growl voice']),
    song=[0, 0, 1, LOOP]))
