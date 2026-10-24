# LynnDrum preset library

The factory library is a set of kit + pattern combinations that each answer one question about the instrument:
**"What can I do with this drum machine that isn't immediately obvious?"** It is both a bank to make music with and a set of lessons. It is
generated from source (`Tools/kits/library/*.py`) and everything below this introduction (the catalogue, the pattern grids, the locks) is generated
from the presets themselves by `python3 Tools/kits/make_library.py`, so it cannot drift from what the plugin loads.

In the plugin: the preset menu is grouped by genre; the **i** button next to it shows the character, the technique and, most important, **what the preset
demonstrates**. Every preset has two to five patterns (the pattern bar, 1 .. n); the first is always the plain version and the next ones add the technique to
the same rhythm, so *playing pattern 1 and then pattern 2 is the lesson*. Switching on **SONG** plays them in a sensible order. The tempo is not part of a preset (the plugin follows the host); each preset lists a suggested BPM.

## Three levels

| Level | Purpose | Presets |
|---|---|---|
| 1 - immediate | sounds good at once, needs no explanation | Foggy Dub, Midnight Assembly, Late Night House, Break Engine, Liquid Glass, Chrome Percussion, Glass Rain, Tape Insects |
| 2 - production | a starting point for a track, adaptable | the remaining genre presets |
| 3 - educational | one technique, exaggerated enough to hear at once | the 16 presets of the *Technique* group |

A ten-minute tour that shows what the instrument is: **Late Night House** (groove is part of the instrument) - **Filter Motion** (one parameter moves, rhythm does not) -
**Locked Kick** (sixteen kicks, one rhythm) - **One Voice, Six Drums** (one voice is a kit) - **Pitch Percussion** (a drum is a melodic instrument) -
**Metallic FM** and **Resonant Sweep** (timbre as a dial; a filter as a note) - **Neuro Bite** (modulation as sound design) - **Glass Rain** (it all together).

## How a preset is stored (nothing new)

A library preset is exactly what the plugin already stores (`Source/Plugin/PresetManager.cpp`, schema 1): the kit (every sound parameter by stable id), up to 64
patterns (per step: velocity, probability, note, flam, shift and two p-locks; per track: length; per pattern: shuffle), a song and the mutes. The only addition is an
optional `meta` object (documentation: category, level, what it demonstrates, ...) that the loader ignores and the preset browser shows.
**Not part of a preset** (so not part of the library): tempo, mixer faders, master, host-sync/run, solo.

Authoring: `Tools/kits/library/core.py` is a small DSL over that same structure (one string per track, `9...7...` = velocity digits, string length = track length), and every
constructor validates what the engine would silently ignore (steps beyond a track's length, locks that the engine would undo, see below).

```text
python3 Tools/kits/make_library.py                 write Presets/factory/*.lynnpreset and this document
python3 Tools/kits/make_library.py --check         fail if the committed files differ from what the source generates
python3 Tools/kits/make_library.py --audit [name]  render every pattern through the real engine and sequencer (lxr_render_seq) and check level, clipping,
                                                   and that each lesson's technique is *measurably* audible (locked hits differ from plain hits)
python3 Tools/kits/make_library.py --balance --write [name]   find the per-voice volumes and one overall gain (stored in library/balance.json)
python3 Tools/kits/make_library.py --preview [name]           WAVs + spectrograms in build-previews/ (git-ignored): listen without a DAW
```

## What the instrument does (found by measuring it while authoring)

These are facts about the engine as implemented, each one measured, several of them surprising. They shaped the presets; they are also the practical manual.

| Finding | Consequence for presets |
|---|---|
| **A step's velocity does nothing unless the voice's `Velocity > Volume` is on** (default: off). | Every library kit switches it on where velocity matters. (The first factory kits had ghost notes at full level; fixed.) |
| **A step has two p-lock slots and a note.** A lock holds from its trigger until that track's *next* trigger, which restores the stored value. The note is a semitone offset from 60 on top of the voice's Coarse/Fine. | At most two parameters and a pitch can change per hit: the lessons are built around exactly that budget. |
| **A parameter that a velocity target or an LFO target points at can not be p-locked**: the engine rewrites such parameters every control tick (1.45 ms), undoing the lock. | `core.py` refuses to build such a preset. Where both are wanted, two twin voices are used (Filter Motion). |
| **FM depth follows the pitch envelope** (index ~ amount squared x pitch EG). A short pitch decay collapses the FM within a few ms. | For FM timbres use `Pitch Mod 0` and a long `Pitch Decay`; with a high FM ratio the centroid moves from 390 Hz to 6.5 kHz as FM Amount goes 0 -> 127 (Metallic FM). |
| **A resonant band-pass on noise rings at its cutoff**: the cutoff is a pitch (about 130 Hz at 16, 920 Hz at 60, 3.3 kHz at 100, 9.3 kHz at 120). | A p-lock on `Filter Freq` plays notes (Resonant Sweep, calibrated table in `lessons.py`). |
| **The noise oscillator is sample-and-hold at the voice pitch**: low note = crunchy rumble, high note = hiss. | Noise colour by note (Noise Lab). |
| **The LFO's "Target Voice" parameter does nothing.** An LFO targets any parameter of any voice; **LFO Amount is lockable** and works as a per-hit switch, as do LFO Sync and Wave. | Kits store LFOs with amount 0; patterns switch them on (Filter Motion, Moving Hats). |
| **Hats are quiet**: at equal Volume, a hat with the default high-pass is 15-25 dB under a kick in RMS. `Drive`, `Filter Drive`, a lower high-pass and the Hat click layer each add 6-14 dB. | Library hats use Drive 45-100 and a high-pass of 60-88; velocity digits 5-9. |
| **A single voice peaks around 0.25 at Volume 127** (a clean sine kick); Drive raises that. | Voice volumes are a balance (loudest = 127) plus one `gain` <= 1 per preset, found by `--balance`. Master is not saved in presets and goes to 2.0. |
| **The snare filter only acts on the noise**; a sample layer (Click) or heavy Drive hides it. | Where a filter is the point (Velocity Is Timbre) the snare is noise-heavy, low-passed, no click. |
| **FX bus**: only voices routed to `FX bus` pass through it. Delay time = about 6 ms x P1 at range 127 (1.6 ms x P1 at range 64). **Distortion: P1 drive, P2 offset (Fold: any offset is a constant DC! keep 0), P3 tone, P4 output gain**; fold is level-insensitive (its output stays loud as the input falls). Ring mod: P1 = carrier x 880 Hz, `FX Wave` picks the carrier (rectangle = clang). FX parameters are lockable. | Foggy Dub (dub throws), Liquid Glass, Glass Rain, Clockwork Cathedral (delays set in ms for the suggested tempo), Ring Mod Throws. |
| **Shuffle is linear**: the delay of odd 16ths is shuffle x 0.265 % of a step pair (shuffle 64 = 66.7 % triplet). Only the odd steps move; flams inside an odd step are compressed (original behaviour, decision D8). | `shuffle_for(percent)`; Swing Lab is checked against the measured delays (54 % = 10 ms at 122 bpm ...). |
| `Repeat Count` (snare, cymbal) retriggers the voice's own envelope: a flutter or clap. `Click Pitch` is playback speed of the sample layer: a tuned click without an oscillator. `Decay 0` is one control block (1.45 ms). | Clockwork Cathedral (ratchet), Minimal Dew (pitched clicks), Envelope Clicks. |
| Pattern length is per track (1-64) and **steps at or beyond the length never play**. Patterns switch only when the longest track wraps. | Constructors check the length; polymeter is used where it sounds musical (Glass Rain, Clockwork Cathedral, Concrete Roller, Odd Meters). |

## Not used, or not expressible in a preset

- **Kit per pattern** (the firmware switches the kit with the pattern) is parked in LynnDrum: all patterns of a preset share its kit. Where two timbres are wanted, the patterns use p-locks or twin voices.
- **LXR kit/pattern import** is parked; every library kit is authored from scratch (clean-room, as the other factory presets).
- **Only one FX slot**, and only voices routed to the FX bus use it; the FX type itself can not be locked (its parameters can).
- Roll and Euclid are live/editing features: they leave no trace in a preset beyond the resulting steps.
- The engine has **no filter envelope**; filter movement is LFO, velocity target, or p-lock. Presets say which.

## Catalogue

| Preset | Genre | Level | BPM | Primary technique |
|---|---|---|---|---|
| Warehouse Pulse | Techno | 2 | 132 | phrase-ending locks on kick/snare, stepped filter lock on a tuned bass voice |
| Concrete Roller | Techno | 2 | 128 | polymeter (12 and 10 steps against 16) + a slow tempo-synced LFO on a filter |
| Foggy Dub | Techno | 1 | 122 | FX delay as an instrument: voices routed to the FX bus, delay feedback and time locked per step |
| Slag Works | Techno | 2 | 138 | industrial sound design: FM, hard drive, sample-rate crush, a fast LFO shaking FM depth |
| Midnight Assembly | Techno | 1 | 133 | a tom that plays a melody (per-step note) over a swung backbeat |
| Hardwire | Techno | 2 | 150 | distortion as part of the voice: kick and rumble overdriven inside the voice, crushed hats |
| Late Night House | House | 1 | 122 | groove: 57 % swing, shaker accents by velocity (and velocity-driven brightness), ghosted clap |
| Raw Basement | House | 2 | 124 | sample-rate reduction on every voice, locked per step to crush single hits; late snares by shift |
| Jack Tracks | House | 2 | 126 | strong swing (60 %) with a syncopated kick, ghost flam claps and a bass riff played by a tuned stab voice |
| Minimal Dew | House | 2 | 124 | probability and tiny envelopes: a few clicks, ticks and noise puffs that never quite repeat |
| Squelch Lane | House | 2 | 124 | a drum voice as an acid line: note + filter-cutoff lock + long/short decay lock per step, accents adding filter drive via velocity |
| Break Engine | Drum & Bass | 1 | 168 | ghost snares (velocity must be on: Velocity > Volume) and a fill by tuned toms |
| Rolling Tide | Drum & Bass | 2 | 174 | a rolling hat made entirely of velocity: every 16th plays, the accent pattern and the velocity-driven filter make the groove |
| Dark Matter | Drum & Bass | 2 | 172 | modulation as aggression: a saw LFO sweeps a resonant filter at near-audio rate; its rate is locked per hit |
| Liquid Glass | Drum & Bass | 1 | 172 | tuned FM bells through a delay over a shuffled two-step: the percussion carries the harmony |
| Neuro Bite | Drum & Bass | 2 | 174 | fast modulation: a sample-and-hold LFO on FM depth and a tempo-synced LFO on a resonant filter turn drum voices into growling bass |
| Broken Circuit | Electro & Broken | 2 | 130 | rhythmic displacement: the same kick and bass hits rotated two steps against fixed hats |
| Chrome Percussion | Electro & Broken | 1 | 124 | FM percussion: tuned FM voices (metal toms, a bell) with FM depth moved per hit |
| Glass Rain | Experimental | 1 | 96 | three tuned FM bells of different pattern lengths (12 / 16 / 19 steps) through a ping-pong delay: slow phasing makes an endless pentatonic cascade |
| Clockwork Cathedral | Experimental | 2 | 100 | polymeter as composition: loop lengths of 11, 9, 7, 13, 29 and 4 steps strike a drone chord; the whole figure repeats after thousands of steps |
| Tape Insects | Experimental | 1 | 140 | random LFOs and sample-rate crush on tiny sounds with probabilities: every pass sounds different |
| Filter Motion | Technique | 3 | 124 | filter cutoff as the only thing that changes: stepped sweeps by p-lock and smooth sweeps by LFO |
| Pitch Percussion | Technique | 3 | 118 | per-step note on a drum voice: one tom becomes a melodic instrument |
| One Voice, Six Drums | Technique | 3 | 100 | parameter locks + step note turn Drum 3 into a kick, snare, hat, tom, bell and bass |
| Locked Kick | Technique | 3 | 126 | per-step locks on one drum voice: the rhythm is identical, the timbre is not |
| Evolving Snare | Technique | 3 | 120 | locks on the snare voice: noise mix, filter, decay, waveform, repeat counter, click layer |
| Moving Hats | Technique | 3 | 126 | a tempo-synced LFO on the hat filter, switched on and shaped by locks (amount, sync, wave) |
| Metallic FM | Technique | 3 | 110 | FM amount and FM ratio (FM freq) as timbre dials, locked per hit |
| Envelope Clicks | Technique | 3 | 130 | extremely short envelopes: clicks from the sample layer, one-block blips, noise snaps; then decay locks stretch single hits |
| Resonant Sweep | Technique | 3 | 124 | noise through a resonant band-pass: the cutoff is the pitch, the resonance is the ring; both locked per hit |
| Velocity Is Timbre | Technique | 3 | 128 | velocity > volume plus velocity targets: filter on the snare, pitch depth on the kick, decay on the hat |
| Noise Lab | Technique | 3 | 118 | noise synthesis: kick, tom, hat, clap, wash and tick are all the noise oscillator, shaped by filters, envelopes, drive and the repeat counter |
| Odd Meters | Technique | 3 | 118 | per-track pattern lengths: 12 against 16, 20 against 16, a 14-step bar (7/8), and a stack of 10 / 12 / 14 against 16 |
| Swing Lab | Technique | 3 | 122 | pattern shuffle: every odd 16th is delayed by a fraction of the step pair |
| Flam & Shift | Technique | 3 | 124 | flams (x2 to x8) and shift (micro-timing, +-7 units of 1/8 step) per step |
| Probability Garden | Technique | 3 | 125 | step probability in tiers: the groove is certain (100 %), the decoration is not (15 - 90 %) |
| Ring Mod Throws | Technique | 3 | 112 | an FX-bus ring modulator switched on per hit: FX dry/wet and FX carrier frequency as p-locks |

## Techno

### Warehouse Pulse

| | |
|---|---|
| Genre | Techno |
| Level | Level 2 - production |
| Character | dark, hard, short, controlled |
| Primary technique | phrase-ending locks on kick/snare, stepped filter lock on a tuned bass voice |
| Secondary techniques | velocity accents (Velocity > Volume on every voice); two-bar phrase; tuned percussion in the kick's key |
| Voices used | Kick: short, distorted, tick click. Drum 2: metallic FM ting. Drum 3: tuned saw bass stab. Snare: noise + dark body. Cymbal: tight ride. Hat: bright, controlled. |
| Key | G (kick 49 Hz, bass voice root G1) |
| BPM | 132 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 51% |
| **What this demonstrates** | Pattern B is rhythmically the same as A; only per-step locks differ: the last kick of the phrase gets a higher pitch and shorter decay, the snare accents get brighter and snappier, and the bass voice climbs a minor-third line while its filter opens. |

**Pattern 1** - core groove, plain

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   ....|...6|....|....|....|....|..4.|...6
D3   ..7.|....|....|.5..|..7.|....|5...|....
S    ....|8...|....|8...|....|8...|....|8...
H    .4.5|.4.5|.4.5|.4.5|.4.5|.4.5|.4.5|.4.5
O    ..7.|..7.|..7.|..7.|..7.|..7.|..7.|..7.
```

**Pattern 2** - same groove + phrase-ending locks, pitched/filtered bass line

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   ....|...6|....|....|....|....|..4.|...6
D3   ..7.|....|....|.5..|..7.|....|5...|....
S    ....|8...|....|8...|....|8...|....|8...
H    .4.5|.4.5|.4.5|.4.5|.4.5|.4.5|.4.5|.4.5
O    ..7.|..7.|..7.|..7.|..7.|..7.|..7.|..7.
```

- K step 29: note +3
- K step 29: lock Drum 1 Decay = 11
- D2 lock Drum 2 FM Amount: 8=40, 27=100
- D3 step 14: note +3
- D3 step 25: note +5
- D3 lock Drum 3 Filter Freq: 3=35, 14=55, 19=75, 25=95
- S step 29: note +6
- S step 29: lock Snare Filter Freq = 90
- S step 29: lock Snare Decay = 8
- O step 31: lock Hi-hat Decay (open) = 60

Song (switch on SONG in the pattern bar): 1 1 2 1 1 2 LOOP.

### Concrete Roller

| | |
|---|---|
| Genre | Techno |
| Level | Level 2 - production |
| Character | hypnotic, warm, patient |
| Primary technique | polymeter (12 and 10 steps against 16) + a slow tempo-synced LFO on a filter |
| Secondary techniques | tuned tick figure by per-step note; hat pitch/decay accents by lock |
| Voices used | Kick: round, a little drive. Drum 2: wooden tuned tick. Drum 3: triangle sub pulse, LFO-swept low-pass. Snare: dry noise rim. Hat: dry ticks. |
| Key | F# (kick 46 Hz, sub pulse F#1, tick figure in F# minor pentatonic) |
| BPM | 128 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 10, 12) |
| Swing | 50% |
| **What this demonstrates** | Nothing in the groove is complicated; the movement comes from track lengths that do not line up (16 / 12 / 10) and from a slow LFO that opens and closes the sub-pulse filter, so each repeat of the one-bar kick sounds like a different bar. |

**Pattern 1** - kick 16, hat 12 (three against four), sub pulse with LFO

```text
K    9...|9...|9...|9...
D2   ..4.|..3.|..4.|..3.
D3   ..6.|..5.|..6.|..5.
S    ....|5...|....|5...
H    6..4|..5.|.4..
```

**Pattern 2** - adds a 10-step tuned tick figure; hats get pitch and decay accents

```text
K    9...|9...|9...|9...
D2   .6.4|..6.|45
D3   ..6.|..5.|..6.|..5.
S    ....|5...|....|5...
H    6..4|..5.|.4..
```

- D2 step 4: note +7
- D2 step 7: note +3
- D2 step 9: note +10
- D2 step 10: note +5
- H step 7: note +2
- H steps 4,10: lock Hi-hat Decay (closed) = 10

Song (switch on SONG in the pattern bar): 1 1 1 2 2 LOOP.

### Foggy Dub

| | |
|---|---|
| Genre | Techno |
| Level | Level 1 - immediate |
| Character | deep, hazy, spacious |
| Primary technique | FX delay as an instrument: voices routed to the FX bus, delay feedback and time locked per step |
| Secondary techniques | tuned dyad stabs (per-step note); swing 54 %; ghosted hats by velocity |
| Voices used | Kick: soft and deep. Drum 2 + Drum 3: square-wave stabs a minor third apart, FX bus. Snare: tuned rim, FX bus. Cymbal: filtered noise wash. Hat: soft. |
| Key | F (stabs Fm third, kick E1) |
| BPM | 122 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 |
| Swing | 54% |
| **What this demonstrates** | One rim hit carries two FX locks (feedback and delay time): the echoes swell and bend after it, a dub-mixer throw played by the sequencer. The delay time is in milliseconds, set to a dotted eighth at 122 bpm. |

**Pattern 1** - one dyad stab and one rim into the delay

```text
K    9...|9...|9...|9...
D2   ....|.5..|....|....
D3   ....|.5..|....|....
S    ....|....|...4|....
H    .2.3|.2.3|.2.3|.2.3
O    ..6.|....|..6.|....
```

**Pattern 2** - the dyad moves, the rim throws the delay

```text
K    9...|9...|9...|9...
D2   ....|.5..|..6.|..4.
D3   ....|.5..|..6.|..4.
S    ....|....|...4|....
H    .2.3|.2.3|.2.3|.2.3
O    ..6.|....|..6.|....
```

- D2 step 11: note -2
- D2 step 15: note +3
- D2 step 15: lock Drum 2 Filter Freq = 90
- D3 step 11: note -2
- D3 step 15: note +3
- D3 step 15: lock Drum 3 Filter Freq = 90
- S step 12: lock FX FX P4 = 112
- S step 12: lock FX FX P1 = 76

Song (switch on SONG in the pattern bar): 1 1 2 2 LOOP.

### Slag Works

| | |
|---|---|
| Genre | Techno |
| Level | Level 2 - production |
| Character | mechanical, abrasive, dense |
| Primary technique | industrial sound design: FM, hard drive, sample-rate crush, a fast LFO shaking FM depth |
| Secondary techniques | anvil riff by note + FM locks; snare flam roll with shift; three-step machine rhythm against four-on-the-floor |
| Voices used | Kick: FM + drive + crush. Drum 2: FM anvil, ringing band-pass. Drum 3: saw motor, LFO on FM depth. Snare: clipped clang. Cymbal: steam burst. Hat: crushed ticks. |
| Key | no tuned key; kick 44 Hz, anvil riff climbs from C5 |
| BPM | 138 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 50% |
| **What this demonstrates** | Every sound has an edge from a different mechanism (FM, clipping, sample-rate reduction, a fast square LFO on FM depth); in pattern B two bars climb to a fill where the anvil's FM depth and the snare's filter are locked per hit. |

**Pattern 1** - four on the floor, a machine rhythm of three against four, clang on 2 and 4

```text
K    9...|9...|9...|9...
D2   ..5.|.5..|5..5|..5.
D3   .7..|....|....|....
S    ....|7...|....|7...
H    6363|6363|6363|6363
```

**Pattern 2** - two bars: the second climbs into a drop-out fill (flam roll, anvil riff, steam)

```text
K    9...|9...|9...|9...|9...|9...|9...|....
D2   ..5.|.5..|5..5|..5.|..5.|.5..|5..5|..5.
D3   .7..|....|....|....|.7..|....|....|....
S    ....|7...|....|7...|....|7...|....|6.6.
C    ....|....|....|....|....|....|....|...4
H    6363|6363|6363|6363|6363|6363|6363|6.3.
```

- D2 step 22: note +3
- D2 step 25: note +5
- D2 step 28: note +7
- D2 step 31: note +10
- D2 lock Drum 2 FM Amount: 25=110, 31=127
- D3 step 18: lock Drum 3 LFO Rate = 110
- S step 29: flam x4
- S step 31: flam x6
- S step 31: shift -2
- S lock Snare Filter Freq: 29=40, 31=80

Song (switch on SONG in the pattern bar): 1 1 2 LOOP.

### Midnight Assembly

| | |
|---|---|
| Genre | Techno |
| Level | Level 1 - immediate |
| Character | warm, melodic, driving |
| Primary technique | a tom that plays a melody (per-step note) over a swung backbeat |
| Secondary techniques | 55 % swing on the whole pattern; hat accents by lock; cowbell FM voice added in B |
| Voices used | Kick: round, warm. Drum 2: FM cowbell. Drum 3: tuned tom (hook). Snare: noise + sample clap. Cymbal: ride. Hat: bright, swung. |
| Key | G minor (kick 49 Hz; hook G2 - Bb - C - D) |
| BPM | 133 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 |
| Swing | 55% |
| **What this demonstrates** | A tom is a pitched voice: the same hit with different per-step notes gives a hook; pattern B moves the hook up a fourth and adds a cowbell without touching the groove. |

**Pattern 1** - groove + tom hook

```text
K    9...|9...|9...|9...
D3   ...7|..6.|....|7.6.
S    ....|8...|....|8...
H    .5.3|.5.3|.5.3|.5.3
O    ..6.|..6.|..6.|..6.
```

- D3 step 7: note +3
- D3 step 15: note +5

**Pattern 2** - hook moves up, extra kick/clap ghost, cowbell, last hat brightens, last open hat snaps shut

```text
K    9...|9...|9.6.|9...
D2   ....|..5.|....|..4.
D3   ...7|..6.|.6..|7.6.
S    ....|8...|....|8..3
H    .5.3|.5.3|.5.3|.5.3
O    ..6.|..6.|..6.|..6.
```

- D2 lock Drum 2 Filter Freq: 7=60, 15=90
- D3 steps 4,13: note +5
- D3 step 7: note +8
- D3 step 10: note +7
- D3 step 15: note +3
- S step 16: flam x2
- H step 16: lock Hi-hat Filter Freq = 112
- O step 15: lock Hi-hat Decay (open) = 8

Song (switch on SONG in the pattern bar): 1 1 1 2 LOOP.

### Hardwire

| | |
|---|---|
| Genre | Techno |
| Level | Level 2 - production |
| Character | relentless, distorted, fast |
| Primary technique | distortion as part of the voice: kick and rumble overdriven inside the voice, crushed hats |
| Secondary techniques | kick-bass interlock: the sub voice plays every 16th the kick leaves free; flam roll fill; sub walks by per-step note + filter lock |
| Voices used | Kick: rectangle, hard drive, filter, kick click. Drum 2: falling zap. Drum 3: distorted sub rumble. Snare: distorted noise clap. Cymbal: crash. Hat: crushed. |
| Key | E (rumble E1, minor third G, fourth A) |
| BPM | 150 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 |
| Swing | 50% |
| **What this demonstrates** | The kick and the rumble voice are overdriven inside the voice, so the 16ths between the kicks pump without a compressor; in B the rumble walks up a minor third and the snare rolls into the bar. |

**Pattern 1** - four on the floor + rumble 16ths

```text
K    9...|9...|9...|9...
D2   ....|....|....|...4
D3   .776|.776|.776|.776
S    ....|9...|....|9...
H    .3.3|.3.3|.3.3|.3.3
O    ..6.|..6.|..6.|..6.
```

**Pattern 2** - rumble walks, snare flam roll, long zap on the turnaround

```text
K    9...|9...|9...|9...
D2   ....|....|....|...4
D3   .776|.776|.776|.776
S    ....|9...|....|9.67
H    .3.3|.3.3|.3.3|.3.3
O    ..6.|..6.|..6.|..6.
```

- D2 step 16: note +12
- D2 step 16: lock Drum 2 Decay = 40
- D3 steps 4,15: note +3
- D3 step 12: note +5
- D3 step 16: note +7
- D3 lock Drum 3 Filter Freq: 4=85, 12=85, 16=100
- S step 13: flam x3
- S step 15: flam x4
- S step 15: shift -2
- S step 16: flam x6

Song (switch on SONG in the pattern bar): 1 1 1 2 LOOP.

## House

### Late Night House

| | |
|---|---|
| Genre | House |
| Level | Level 1 - immediate |
| Character | deep, soft, swung, warm |
| Primary technique | groove: 57 % swing, shaker accents by velocity (and velocity-driven brightness), ghosted clap |
| Secondary techniques | sub bass playing chord roots by per-step note; low conga by tuned tom voice added in B; rimshot from the cymbal voice |
| Voices used | Kick: soft, round. Drum 2: low conga. Drum 3: sine sub. Snare: soft clap (noise + sample). Cymbal: tuned rimshot. Hat: noise shaker. |
| Key | A minor (kick E1 41 Hz, sub bass A1 / C2 / G1 above it, congas around E3) |
| BPM | 122 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 57% |
| **What this demonstrates** | The feel comes from the instrument, not from the notes: the shuffle swings every odd 16th, shaker velocities alternate soft/hard, and the velocity of a hit also shifts the shaker's high-pass, so accents are brighter as well as louder. |

**Pattern 1** - two-bar groove

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D3   ..8.|....|5...|..7.|..8.|....|5...|....
S    ....|8...|....|8...|....|8...|....|8..3
C    ....|.4..|....|.4..|....|.4..|....|4...
H    2523|2523|2523|2523|2523|2523|2523|2523
O    ..5.|....|..5.|..5.|..5.|....|..5.|....
```

- D3 step 15: note +3
- D3 step 25: note -2
- S step 32: probability 60%
- S step 32: shift -1

**Pattern 2** - congas added, bass filter and shaker decay accents locked

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   ...4|...5|...3|....|...4|...5|...3|..4.
D3   ..8.|....|5...|..7.|..8.|....|5...|....
S    ....|8...|....|8...|....|8...|....|8..3
C    ....|.4..|....|.4..|....|.4..|....|4...
H    2523|2523|2523|2523|2523|2523|2523|2523
O    ..5.|....|..5.|..5.|..5.|....|..5.|....
```

- D2 step 8: note +5
- D2 step 24: note +7
- D2 step 28: note +3
- D2 step 31: note +10
- D3 step 15: note +3
- D3 step 25: note -2
- D3 lock Drum 3 Filter Freq: 15=70, 25=55
- S step 32: probability 60%
- S step 32: shift -1
- H lock Hi-hat Decay (closed): 16=10, 32=14

Song (switch on SONG in the pattern bar): 1 1 2 2 LOOP.

### Raw Basement

| | |
|---|---|
| Genre | House |
| Level | Level 2 - production |
| Character | dirty, lo-fi, loose |
| Primary technique | sample-rate reduction on every voice, locked per step to crush single hits; late snares by shift |
| Secondary techniques | 58 % swing; ghost kick by velocity + shift; dirty noise clap from the cymbal voice |
| Voices used | Kick: triangle, driven, crushed, kick click. Drum 2: crushed tuned perc. Drum 3: low-passed bass blip. Snare: driven noise + sample. Cymbal: dirty clap. Hat: crushed. |
| Key | G (kick 49 Hz, bass blip A1 and D2) |
| BPM | 124 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 |
| Swing | 58% |
| **What this demonstrates** | Sample-rate reduction is a per-voice dial and it can be locked per hit: in B two hats and the snare are crushed much harder than their neighbours for a dusty sampler feel, while the snares sit a few milliseconds late for a lazy backbeat. |

**Pattern 1** - raw groove, lazy snare

```text
K    9...|9..3|9...|9...
D3   ....|...6|....|.5..
S    ....|8...|....|8...
C    ....|....|.3..|...2
H    5.3.|5.3.|5.3.|5.3.
O    ..4.|....|..4.|....
```

- K step 8: shift +1
- D3 step 14: note +5
- S steps 5,13: shift +1

**Pattern 2** - extra kick, flam clap, per-hit crush locks

```text
K    9...|9..3|9.7.|9...
D2   ....|....|...4|...5
D3   ....|...6|....|.5..
S    ....|8...|....|8...
C    ....|....|.3..|..52
H    5.3.|5.3.|5.3.|5.3.
O    ..4.|....|..4.|....
```

- K step 8: shift +1
- D2 step 16: note +5
- D3 step 14: note +5
- S steps 5,13: shift +1
- S step 13: lock Snare Sample Rate Reducer = 20
- C step 15: flam x2
- H lock Hi-hat Sample Rate Reducer: 5=25, 13=18

Song (switch on SONG in the pattern bar): 1 1 2 LOOP.

### Jack Tracks

| | |
|---|---|
| Genre | House |
| Level | Level 2 - production |
| Character | bouncy, chunky, party |
| Primary technique | strong swing (60 %) with a syncopated kick, ghost flam claps and a bass riff played by a tuned stab voice |
| Secondary techniques | four-step tom run as a fill without extra tracks (note + decay locks); crash on the downbeat from the cymbal voice |
| Voices used | Kick: chunky, driven. Drum 2: tuned tom. Drum 3: rectangle bass stab. Snare: noise clap + sample. Cymbal: crash. Hat: bright, swung. |
| Key | G minor (kick 49 Hz; stab G1 - Bb1 - C2) |
| BPM | 126 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 |
| Swing | 60% |
| **What this demonstrates** | At 60 % swing every odd 16th lands late and the extra kick on step 11 pushes against it; in B a four-note tom run (descending by note, with a longer last hit) replaces a fill that would otherwise need more tracks. |

**Pattern 1** - swung groove with bass stab riff

```text
K    9...|9...|9.5.|9...
D3   .7..|7.5.|..7.|.5..
S    ....|9...|....|9.3.
H    .4.5|.4.5|.4.5|.4.5
O    ..6.|..6.|..6.|..6.
```

- D3 steps 7,14: note +3
- D3 step 11: note +5
- S step 15: flam x2

**Pattern 2** - stab filter opens, tom-run fill, crash on the one

```text
K    9...|9...|9.5.|9...
D2   ....|....|....|6667
D3   .7..|7.5.|..7.|.5..
S    ....|9...|....|9.3.
C    6...|....|....|....
H    .4.5|.4.5|.4.5|.4.5
O    ..6.|..6.|..6.|..6.
```

- D2 step 13: note +7
- D2 step 14: note +5
- D2 step 15: note +3
- D2 lock Drum 2 Decay: 13=10, 16=28
- D3 steps 7,14: note +3
- D3 step 11: note +5
- D3 lock Drum 3 Filter Freq: 2=80, 7=95
- S step 15: flam x2

Song (switch on SONG in the pattern bar): 1 1 1 2 LOOP.

### Minimal Dew

| | |
|---|---|
| Genre | House |
| Level | Level 2 - production |
| Character | sparse, clicky, intimate |
| Primary technique | probability and tiny envelopes: a few clicks, ticks and noise puffs that never quite repeat |
| Secondary techniques | click pitch locked per hit (a pitched click without an oscillator); tonal blips by per-step note; two-bar loop |
| Voices used | Kick: short, soft. Drum 2: tom sample click, pitch by Click Pitch. Drum 3: 3 ms triangle blip. Snare: tick. Cymbal: noise puff. Hat: ultra-short tick. |
| Key | blips in B minor-ish (B6 as the base) |
| BPM | 124 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 54% |
| **What this demonstrates** | Most hits are one or two milliseconds long; the music is in which ones play. Probability makes each pass through the two bars slightly different, and in B the click voice becomes a pitched instrument via the Click Pitch dial, locked per hit. |

**Pattern 1** - sparse clicks with probabilities

```text
K    9...|9...|9...|9...
D2   ..5.|.4..|..5.|.4..|.4..|5...|.4..|5...
D3   .3..|..5.|...3|....|..5.|...3|....|5...
S    ....|...4|....|....|....|4...|....|....
C    ....|....|..5.|....|....|..3.|....|....
H    .4.3|.4.3|.4.3|.4.3
O    ....|....|....|...4
```

- D2 step 3: probability 80%
- D2 step 6: probability 60%
- D2 step 18: probability 70%
- D3 step 7: probability 70%
- S step 8: probability 60%

**Pattern 2** - clicks pitched by lock, blip line by note

```text
K    9...|9...|9...|9...
D2   ..5.|.4..|..5.|.4..|.4..|5...|.4..|5...
D3   .3..|..5.|...3|..4.|..5.|...3|....|5...
S    ....|...4|....|....|....|4...|....|....
C    ....|....|..5.|....|....|..3.|....|....
H    .4.3|.4.3|.4.3|.4.3
O    ....|....|....|...4
```

- D2 step 3: probability 80%
- D2 step 6: probability 60%
- D2 step 18: probability 70%
- D2 lock Drum 2 Click Pitch: 3=40, 11=110, 21=60, 29=127
- D3 step 7: note +7
- D3 step 7: probability 70%
- D3 step 12: note +3
- D3 step 15: note -2
- D3 step 19: note +10
- D3 step 24: note +5
- D3 step 29: note +12
- S step 8: probability 60%

Song (switch on SONG in the pattern bar): 1 1 2 LOOP.

### Squelch Lane

| | |
|---|---|
| Genre | House |
| Level | Level 2 - production |
| Character | squelchy, rolling, club |
| Primary technique | a drum voice as an acid line: note + filter-cutoff lock + long/short decay lock per step, accents adding filter drive via velocity |
| Secondary techniques | velocity target on filter drive (accent = louder and dirtier); resonant band-pass zap on Drum 2 |
| Voices used | Kick: punchy. Drum 2: resonant band-pass zap. Drum 3: saw, resonant low-pass (the acid voice). Snare: noise clap. Cymbal: ride. Hat: bright. |
| Key | C (acid voice C2; riff C, C+12, Eb, G ...) |
| BPM | 124 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 |
| Swing | 52% |
| **What this demonstrates** | There is no filter envelope in this engine, so the acid movement is played: per-step cutoff locks (two locks and a note per step) in pattern 2, and a velocity target on filter drive, so accented steps get louder and dirtier. (A velocity or LFO target can not share a parameter with a lock: the engine rewrites it every control tick, which is why accent does not target the cutoff.) |

**Pattern 1** - riff with velocity accents adding filter drive

```text
K    9...|9...|9...|9...
D3   9.5.|6.9.|5.5.|6.9.
S    ....|8...|....|8...
H    .4.4|.4.4|.4.4|.4.4
O    ..5.|..5.|..5.|..5.
```

- D3 step 5: note +12
- D3 step 9: note +3
- D3 step 13: note +7

**Pattern 2** - cutoff and decay locked step by step, long accent notes

```text
K    9...|9...|9...|9...
D2   ....|....|....|...6
D3   9.5.|6.9.|5.5.|6.9.
S    ....|8...|....|8...
H    .4.4|.4.4|.4.4|.4.4
O    ..5.|..5.|..5.|..5.
```

- D2 step 16: lock Drum 2 Filter Freq = 95
- D3 step 5: note +12
- D3 step 9: note +3
- D3 step 13: note +7
- D3 lock Drum 3 Filter Freq: 1=35, 3=45, 5=80, 7=50, 9=60, 11=40, 13=95, 15=55
- D3 lock Drum 3 Decay: 5=28, 13=32

Song (switch on SONG in the pattern bar): 1 1 2 2 LOOP.

## Drum & Bass

### Break Engine

| | |
|---|---|
| Genre | Drum & Bass |
| Level | Level 1 - immediate |
| Character | punchy, tight, classic |
| Primary technique | ghost snares (velocity must be on: Velocity > Volume) and a fill by tuned toms |
| Secondary techniques | changing percussion between patterns (hats in A, ride + crash in B); micro-timed ghost notes by shift; last-hit decay lock on the fill |
| Voices used | Kick: short, punchy, click. Drum 2/3: two tuned toms. Snare: triangle + noise + sample, driven. Cymbal: ride/crash. Hat: bright metallic. |
| Key | kick 49 Hz (G1), toms D3 and A#3-ish |
| BPM | 168 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 53% |
| **What this demonstrates** | The backbeat is only a few notes; the break comes from ghost snares at a quarter of the level and a few milliseconds off the grid. B keeps the same drums but swaps the hats for a ride (with a crash made from the same voice by two locks) and extends the tom fill downwards. |

**Pattern 1** - break with ghost snares, hats, tom fill

```text
K    9.5.|....|..9.|....|9...|....|5.9.|.7..
D2   ....|....|....|....|....|....|....|7.6.
D3   ....|....|....|....|....|....|....|..7.
S    ....|9..2|.3..|9..2|....|9..2|....|9.32
H    5.5.|5.5.|5.5.|5.5.|5.5.|5.5.|5.5.|5.5.
O    ....|....|....|..5.|....|....|....|..5.
```

- D2 step 31: note -3
- D3 step 31: note -5
- S step 8: shift -1
- S step 10: shift +1
- S step 16: probability 70%

**Pattern 2** - same break, ride + crash instead of hats, longer tom fill

```text
K    9.5.|....|..9.|....|9...|....|5.9.|.7..
D2   ....|....|....|....|....|....|..66|7.6.
D3   ....|....|....|....|....|....|....|.779
S    ....|9..2|.3..|9..2|....|9..2|....|9.32
C    9.5.|6.5.|6.5.|6.5.|6.5.|6.5.|6.5.|....
```

- D2 step 27: note +3
- D2 step 31: note -3
- D3 step 30: note -2
- D3 step 31: note -5
- D3 step 32: note -10
- D3 step 32: flam x2
- D3 step 32: lock Drum 3 Decay = 40
- S step 8: shift -1
- S step 10: shift +1
- S step 16: probability 70%
- S step 29: lock Snare Decay = 24
- C step 1: lock Cymbal Decay = 90
- C step 1: lock Cymbal Filter Freq = 30

Song (switch on SONG in the pattern bar): 1 1 2 LOOP.

### Rolling Tide

| | |
|---|---|
| Genre | Drum & Bass |
| Level | Level 2 - production |
| Character | fluid, relentless, light |
| Primary technique | a rolling hat made entirely of velocity: every 16th plays, the accent pattern and the velocity-driven filter make the groove |
| Secondary techniques | ghost snare voice (Drum 3) at low velocity; shaker from the cymbal voice; hat accent cycle changes between patterns 1 and 2 |
| Voices used | Kick: tight. Drum 2: rim tick. Drum 3: soft ghost snare. Snare: tight crack. Cymbal: noise shaker. Hat: driven metallic, velocity opens the high-pass. |
| Key | kick 46 Hz (F#1), rim tick pitched around A5-C#6 |
| BPM | 174 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 54% |
| **What this demonstrates** | There is no rhythmic variation in the hats at all (every 16th); the pattern is in the velocities. Velocity changes the loudness and also, through the velocity target on the filter, how bright each hat is, so accents are heard as both. |

**Pattern 1** - hats on every 16th with a 4-step velocity cycle, ghosts, shaker

```text
K    9...|....|..7.|....|9...|..5.|..9.|....
D3   ....|...3|.2..|...3|....|...3|.2..|..3.
S    ....|9...|....|9...|....|9...|....|9...
C    .3..|...3|....|.3..|.3..|...3|....|.3.3
H    6233|5233|6233|5233|6233|5233|6233|5233
O    ....|....|....|5...|....|....|....|..5.
```

**Pattern 2** - accents every third 16th (a cycle of three over the bar of sixteen) plus a tuned rim figure

```text
K    9...|....|..7.|....|9...|..5.|..9.|....
D2   ...5|....|...4|....|...6|....|...5|.4..
D3   ....|...3|.2..|...3|....|...3|.2..|..3.
S    ....|9...|....|9...|....|9...|....|9...
C    .3..|...3|....|.3..|.3..|...3|....|.3.3
H    7337|3373|3733|7337|3373|3733|7337|3373
O    ....|....|....|5...|....|....|....|..5.
```

- D2 step 12: note +3
- D2 step 28: note +5
- D2 step 30: note +7
- D2 lock Drum 2 Decay: 12=9, 28=12
- H steps 9,25: lock Hi-hat Decay (closed) = 6

Song (switch on SONG in the pattern bar): 1 1 2 1 LOOP.

### Dark Matter

| | |
|---|---|
| Genre | Drum & Bass |
| Level | Level 2 - production |
| Character | dark, heavy, menacing |
| Primary technique | modulation as aggression: a saw LFO sweeps a resonant filter at near-audio rate; its rate is locked per hit |
| Secondary techniques | bass-like hits played by a drum voice (Drum 3); metal rims placed off the grid by shift; distorted snare with sample layer |
| Voices used | Kick: sub, driven. Drum 2: FM metal rim. Drum 3: saw growl with LFO-swept low-pass. Snare: heavily driven. Cymbal: crash. Hat: driven. |
| Key | E (kick 41 Hz, growl E1 with +5, +3 neighbours) |
| BPM | 172 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 50% |
| **What this demonstrates** | The LFO runs at tens of hertz (sampled at the 690 Hz control rate), so it is part of the timbre, not movement: locking its rate per hit gives each growl a different character while the notes stay the same. |

**Pattern 1** - sparse, heavy two-bar loop

```text
K    9...|....|..9.|....|9...|....|..9.|....
D2   ..2.|....|3...|.5.2|..3.|....|2...|.5..
D3   9...|....|....|....|....|....|....|....
S    ....|9...|....|9...|....|9...|....|9.5.
H    ..5.|..5.|5.5.|..5.|..5.|..5.|5.5.|..5.
```

- D2 steps 9,30: note +7
- D2 step 14: note +3
- D2 step 16: shift +1
- D2 step 19: note +5
- D2 step 19: shift -1

**Pattern 2** - growl hits with different LFO rates, flammed snare into the loop

```text
K    9...|....|..9.|....|9...|....|..9.|....
D2   ..2.|....|3...|.5.2|..3.|....|2...|.5..
D3   9...|....|..8.|....|....|....|7...|9...
S    ....|9...|....|9...|....|9...|....|9.5.
H    ..5.|..5.|5.5.|..5.|..5.|..5.|5.5.|..5.
```

- D2 steps 9,30: note +7
- D2 step 14: note +3
- D2 step 16: shift +1
- D2 step 19: note +5
- D2 step 19: shift -1
- D3 step 11: note +5
- D3 step 25: note +3
- D3 step 29: flam x2
- D3 lock Drum 3 LFO Rate: 1=40, 11=90, 25=110, 29=127
- D3 lock Drum 3 Resonance: 11=90, 25=25
- S step 31: flam x4
- S step 31: lock Snare Decay = 28

Song (switch on SONG in the pattern bar): 1 1 2 LOOP.

### Liquid Glass

| | |
|---|---|
| Genre | Drum & Bass |
| Level | Level 1 - immediate |
| Character | soft, airy, flowing |
| Primary technique | tuned FM bells through a delay over a shuffled two-step: the percussion carries the harmony |
| Secondary techniques | 56 % swing; bell FM amount locked on the higher notes (brighter as they climb); round snare from the sine + soft noise |
| Voices used | Kick: soft. Drum 2: FM glass bell (FX delay). Drum 3: sine bass pluck. Snare: round pop. Cymbal: noise shaker. Hat: crisp shuffle. |
| Key | C (bells: C - G - C - F - A# - D; pluck F#1/C#2) |
| BPM | 172 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 56% |
| **What this demonstrates** | Percussion that plays a line: six bell hits with different per-step notes and two FM locks give a rising melody; the delay (time set in ms to a dotted eighth at 172 bpm) turns each hit into a short phrase. |

**Pattern 1** - soft two-step, shuffled hats, bass pluck

```text
K    9...|....|..7.|....|9...|..6.|..9.|....
D3   ....|.3..|....|..4.|....|....|..3.|....
S    ....|8...|....|8...|....|8...|....|8...
C    5.2.|3.2.|5.2.|3.2.|5.2.|3.2.|5.2.|3.2.
H    .3.5|.3.5|.3.5|.3.5|.3.5|.3.5|.3.5|.3.5
```

- D3 step 15: note +5

**Pattern 2** - the bell line climbs, FM amount locked on the top notes

```text
K    9...|....|..7.|....|9...|..6.|..9.|....
D2   ..5.|...4|....|6...|..4.|...4|....|6...
D3   ....|.3..|....|..4.|....|....|..3.|....
S    ....|8...|....|8...|....|8...|....|8...
C    5.2.|3.2.|5.2.|3.2.|5.2.|3.2.|5.2.|3.2.
H    .3.5|.3.5|.3.5|.3.5|.3.5|.3.5|.3.5|.3.5
```

- D2 step 8: note +7
- D2 step 13: note +12
- D2 step 19: note +5
- D2 step 24: note +10
- D2 step 29: note +14
- D2 lock Drum 2 FM Amount: 13=90, 29=105
- D3 step 15: note +5

Song (switch on SONG in the pattern bar): 1 1 2 2 LOOP.

### Neuro Bite

| | |
|---|---|
| Genre | Drum & Bass |
| Level | Level 2 - production |
| Character | aggressive, animated, synthetic |
| Primary technique | fast modulation: a sample-and-hold LFO on FM depth and a tempo-synced LFO on a resonant filter turn drum voices into growling bass |
| Secondary techniques | FM ratio and LFO rate locked per note; resonance lock on the second growl; driven snare |
| Voices used | Kick: tight, driven. Drum 2: FM growl, resonant low-pass swept in sync. Drum 3: saw-FM bite, random LFO on FM depth. Snare: heavily driven. Cymbal: crash. Hat: driven. |
| Key | F (growls F1 and D2, notes up to +10) |
| BPM | 174 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 50% |
| **What this demonstrates** | A hit of the bite voice is not one sound: its FM depth is being shaken by a random LFO the moment it triggers, and the locks move the modulator ratio (FM Freq) and the LFO rate per note, so one voice produces a line of different growls. (The LFO owns FM Amount, so that one can not be locked.) |

**Pattern 1** - groove with a simple bite line

```text
K    9...|....|..7.|....|9...|....|7.9.|....
D3   5...|..7.|....|7...|5..5|....|..7.|...5
S    ....|9...|....|9...|....|9...|....|9...
H    .4.5|.4.5|.4.5|.4.5|.4.5|.4.5|.4.5|.4.5
```

- D3 steps 7,27: note +3
- D3 step 13: note +7
- D3 step 20: note +5
- D3 step 32: note +10

**Pattern 2** - the same line with FM ratio and LFO rate locked per note, a second growl voice

```text
K    9...|....|..7.|....|9...|....|7.9.|....
D2   ....|....|....|..7.|....|....|....|8...
D3   5...|..7.|....|7...|5..5|....|..7.|...5
S    ....|9...|....|9...|....|9...|....|9...
H    .4.5|.4.5|.4.5|.4.5|.4.5|.4.5|.4.5|.4.5
```

- D2 step 29: note +5
- D2 lock Drum 2 Resonance: 15=90, 29=40
- D3 steps 7,27: note +3
- D3 step 13: note +7
- D3 step 20: note +5
- D3 step 32: note +10
- D3 lock Drum 3 FM Freq: 1=20, 7=55, 13=90, 17=30, 20=110, 27=70, 32=127
- D3 lock Drum 3 LFO Rate: 7=30, 13=90, 20=110, 32=127

Song (switch on SONG in the pattern bar): 1 1 2 LOOP.

## Electro & Broken

### Broken Circuit

| | |
|---|---|
| Genre | Electro & Broken |
| Level | Level 2 - production |
| Character | tense, off-kilter, dry |
| Primary technique | rhythmic displacement: the same kick and bass hits rotated two steps against fixed hats |
| Secondary techniques | micro-timing by shift (snare early, hat late); ghost snares with probability; tom-as-bass by per-step note |
| Voices used | Kick: dry, punchy. Drum 2: tuned clave. Drum 3: tom used as a bass line. Snare: tight crack. Cymbal: short metallic. Hat: tight. |
| Key | G# (kick 52 Hz, bass voice D2 and neighbours) |
| BPM | 130 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 |
| Swing | 50% |
| **What this demonstrates** | B contains exactly the same kick and bass triggers as A, moved two steps later; against the unchanged hats and snare the groove leans differently. The snare is pulled slightly early and one hat pushed late, and the ghost snares only play some of the time. |

**Pattern 1** - broken kick / bass / snare groove

```text
K    9..8|..9.|..9.|.8..
D2   .4..|3...|4..3|.4..
D3   .6..|....|6..6|...6
S    ....|9..3|....|9.4.
H    5.34|.5.3|5.4.|53.4
```

- D3 step 12: note -2
- D3 step 16: note +3
- S step 8: probability 70%
- S step 13: shift -1
- S step 15: probability 60%
- H step 8: shift +1

**Pattern 2** - kick and bass displaced by two steps, bass decays locked

```text
K    ..9.|.8..|9...|9..8
D2   .4..|3...|4..3|.4..
D3   .6.6|....|..6.|.6..
S    ....|9..3|....|9.4.
H    5.34|.5.3|5.4.|53.4
```

- K step 3: note +5
- K step 3: lock Drum 1 FM Amount = 40
- D3 step 2: note +3
- D3 step 14: note -2
- D3 lock Drum 3 Decay: 4=12, 11=40, 14=12
- S step 8: probability 70%
- S step 13: shift -1
- S step 15: probability 60%
- H step 8: shift +1

Song (switch on SONG in the pattern bar): 1 1 2 1 2 LOOP.

### Chrome Percussion

| | |
|---|---|
| Genre | Electro & Broken |
| Level | Level 1 - immediate |
| Character | metallic, bright, precise |
| Primary technique | FM percussion: tuned FM voices (metal toms, a bell) with FM depth moved per hit |
| Secondary techniques | 12-step bell figure against 16 (polymeter); tuned toms answer the bell; bright ride by the cymbal voice |
| Voices used | Kick: FM sine. Drum 2: FM metal tom. Drum 3: FM bell. Snare: resonant tang. Cymbal: bright ride. Hat: metallic. |
| Key | C minor-ish (bell C4, G4, C5, D#4 ...) |
| BPM | 124 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 12) |
| Swing | 52% |
| **What this demonstrates** | FM Amount is the timbre dial: on the bell it moves a hit from a soft tone to a clanging one, and on the metal tom from wooden to metallic, while the rhythm and pitch of the pattern stay the same. |

**Pattern 1** - groove + bell figure (12 steps)

```text
K    9...|9...|9...|9...
D3   7.5.|6.4.|7.5.
S    ....|8...|....|8.4.
H    .5.3|.5.3|.5.3|.5.3
O    ..5.|..5.|..5.|..5.
```

- D3 steps 3,7,11: note +7
- D3 step 5: note +12
- D3 step 9: note +3

**Pattern 2** - metal-tom answers; FM amount locked per hit

```text
K    9...|9...|9...|9...
D2   ....|..6.|..65|..6.
D3   7.5.|6.4.|7.5.
S    ....|8...|....|8.4.
C    ....|....|....|...4
H    .5.3|.5.3|.5.3|.5.3
O    ..5.|..5.|..5.|..5.
```

- D2 step 7: note +7
- D2 step 12: note +3
- D2 step 15: note -5
- D2 lock Drum 2 FM Amount: 11=127, 15=40
- D3 steps 3,7,11: note +7
- D3 step 5: note +12
- D3 step 9: note +3
- D3 lock Drum 3 FM Amount: 5=85, 9=127

Song (switch on SONG in the pattern bar): 1 1 2 LOOP.

## Experimental

### Glass Rain

| | |
|---|---|
| Genre | Experimental |
| Level | Level 1 - immediate |
| Character | shimmering, spacious, hypnotic |
| Primary technique | three tuned FM bells of different pattern lengths (12 / 16 / 19 steps) through a ping-pong delay: slow phasing makes an endless pentatonic cascade |
| Secondary techniques | FM amount and decay locked per bell hit; probability on the raindrops; swelling noise breath and shimmer from the snare and cymbal voices |
| Voices used | Drum 1/2/3: FM bells in C3, C4, C5 (all through the FX delay). Snare: swelling noise breath. Cymbal: slow shimmer. Hat: raindrop ticks (dry). |
| Key | C major pentatonic (C D E G A) |
| BPM | 96 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 12, 19, 23, 24, 47) |
| Swing | 50% |
| **What this demonstrates** | Each bell is the same simple voice; the music is in the track lengths (12, 16, 19 steps plus 24, 47 and 23 for breath, shimmer and drops) which drift against each other, and in the FM amount that is locked on some hits to make them glassier or woodier. Delay time is in ms (469 ms = three eighths at 96 bpm). |

**Pattern 1** - sparse cascade

```text
K    7..4|...6|.4..
D2   5...|4..6|..3.|..4.
D3   3...|....|4...|...3|.5.
S    2...|....|....|....|....|....
C    3...|....|....|....|....|....|....|....|....|....|....|...
H    .5..|3.4.|...2|...3|.5.3|.4.
```

- K step 4: note +7
- K step 8: note +4
- K step 10: note +9
- D2 steps 1,15: note +7
- D2 step 5: note +4
- D2 step 8: note +9
- D2 step 11: note +2
- D3 step 1: note +14
- D3 steps 1,9,16,18: probability 80%
- D3 step 9: note +11
- D3 step 16: note +7
- D3 step 18: note +9
- H steps 2,5,7,12,16,18,20,22: probability 70%

**Pattern 2** - the same notes, bell timbres and decays locked on selected hits

```text
K    7..4|...6|.4..
D2   5...|4..6|..3.|..4.
D3   3...|....|4...|...3|.5.
S    2...|....|....|....|....|....
C    3...|....|....|....|....|....|....|....|....|....|....|...
H    .5..|3.4.|...2|...3|.5.3|.4.
```

- K step 4: note +7
- K step 8: note +4
- K step 10: note +9
- K lock Drum 1 Decay: 4=60, 10=12
- D2 steps 1,15: note +7
- D2 step 5: note +4
- D2 step 8: note +9
- D2 step 11: note +2
- D2 lock Drum 2 FM Amount: 1=100, 11=20
- D3 step 1: note +14
- D3 steps 1,9,16,18: probability 80%
- D3 step 9: note +11
- D3 step 16: note +7
- D3 step 18: note +9
- D3 lock Drum 3 FM Amount: 1=120, 16=25
- H steps 2,5,7,12,16,18,20,22: probability 70%

Song (switch on SONG in the pattern bar): 1 2 LOOP.

### Clockwork Cathedral

| | |
|---|---|
| Genre | Experimental |
| Level | Level 2 - production |
| Character | vast, mechanical, ritual |
| Primary technique | polymeter as composition: loop lengths of 11, 9, 7, 13, 29 and 4 steps strike a drone chord; the whole figure repeats after thousands of steps |
| Secondary techniques | a ratchet from the snare voice's repeat counter, its count locked in B; long dark delay in the FX bus; bell pitch sweep and FM depth locked on the first hits |
| Voices used | Drum 1: great bell, very long. Drum 2/3: inharmonic FM bells (FX delay). Snare: noise ratchet (repeat counter). Cymbal: gong. Hat: 2 ms clock tick. |
| Key | C (bells C2, G3, C4) |
| BPM | 100 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 4, 7, 9, 11, 13, 29) |
| Swing | 50% |
| **What this demonstrates** | None of the loops share a length, so the strikes fall on different beats every bar. The ratchet is the snare voice retriggering itself (Repeat Count), and the locks make the first hit of each cycle brighter or darker than later ones. Pattern lengths are shown in the pattern editor. |

**Pattern 1** - the mechanism

```text
K    8...|....|..5
D2   6...|.4..|.
D3   5.4.|...
S    ....|....|.4..|.
C    5...|....|....|....|....|....|....|.
H    4.2.
```

- K step 11: note +7
- D2 step 6: note +5
- D3 step 3: note +7

**Pattern 2** - first strikes locked: sweep on the toll, FM depth on the bells, a shorter ratchet

```text
K    8...|....|..5
D2   6...|.4..|.
D3   5.4.|...
S    ....|....|.4..|.
C    5...|....|....|....|....|....|....|.
H    4.2.
```

- K step 11: note +7
- K step 1: lock Drum 1 Pitch Mod = 40
- D2 step 6: note +5
- D2 lock Drum 2 FM Amount: 1=110, 6=30
- D3 step 3: note +7
- D3 step 1: lock Drum 3 FM Amount = 20
- S step 10: lock Snare Repeat Count = 3

Song (switch on SONG in the pattern bar): 1 2 LOOP.

### Tape Insects

| | |
|---|---|
| Genre | Experimental |
| Level | Level 1 - immediate |
| Character | chirping, crunchy, alive |
| Primary technique | random LFOs and sample-rate crush on tiny sounds with probabilities: every pass sounds different |
| Secondary techniques | sample-and-hold LFO re-pitches each chirp and re-tunes each tick; LFO rate and crush locked per buzz; polymeter 32 / 24 / 27 / 16 |
| Voices used | Drum 1: chirp (random pitch). Drum 2: band-pass tick (random band). Drum 3: crushed saw buzz, LFO on fine pitch. Snare: static snap. Cymbal: noise puff. Hat: cricket. |
| Key | none (random pitches around F#6) |
| BPM | 140 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 24, 25, 31, 32) |
| Swing | 52% |
| **What this demonstrates** | Sample-and-hold LFOs are modulation sources that never repeat: each chirp lands on a new pitch, each tick on a new band, while probabilities decide which of them play. In B, the buzz voice has its LFO rate and sample-rate reduction locked per hit, from a slow rattle to a high whine. |

**Pattern 1** - the swarm

```text
K    5..3|.4..|.5..|3.4.|.5.3|.4.5|..3.|4...
D2   .4.3|.5.2|.4.3|.5.2|.4.3|.5.2
D3   ....|...6|....|...4|....|...3|....|...
S    ....|6...|....|....|4...|....
C    ....|....|..2.|....|..3.|....|.
H    3.2.|4.3.|2.3.|4.2.
```

- K steps 1,4,6,10,13,15,18,20,22,24,27,29: probability 70%
- D2 steps 2,4,6,8,10,12,14,16,18,20,22,24: probability 75%
- D3 steps 8,16,24: probability 80%
- S steps 5,17: probability 70%
- C steps 11,19: probability 65%
- H steps 1,3,5,7,9,11,13,15: probability 60%

**Pattern 2** - buzz LFO rate and crush locked, chirp pitch sweep locked

```text
K    5..3|.4..|.5..|3.4.|.5.3|.4.5|..3.|4...
D2   .4.3|.5.2|.4.3|.5.2|.4.3|.5.2
D3   ....|...6|....|...4|....|...3|....|...
S    ....|6...|....|....|4...|....
C    ....|....|..2.|....|..3.|....|.
H    3.2.|4.3.|2.3.|4.2.
```

- K steps 1,4,6,10,13,15,18,20,22,24,27,29: probability 70%
- K lock Drum 1 Pitch Mod: 1=40, 15=127
- D2 steps 2,4,6,8,10,12,14,16,18,20,22,24: probability 75%
- D3 steps 8,16,24: probability 80%
- D3 lock Drum 3 LFO Rate: 8=40, 16=100, 24=127
- D3 lock Drum 3 Sample Rate Reducer: 8=40, 24=100
- S steps 5,17: probability 70%
- C steps 11,19: probability 65%
- H steps 1,3,5,7,9,11,13,15: probability 60%

Song (switch on SONG in the pattern bar): 1 2 LOOP.

## Technique

### Filter Motion

| | |
|---|---|
| Genre | Technique |
| Level | Level 3 - educational |
| Character | simple 4/4 with a moving filter |
| Primary technique | filter cutoff as the only thing that changes: stepped sweeps by p-lock and smooth sweeps by LFO |
| Secondary techniques | LFO amount used as a per-hit switch; tempo-synced triangle LFOs (1/1 on the bass, 1/2 on the hat); a locked parameter must not also be an LFO target |
| Voices used | Kick, clap: plain. Drum 3 and Drum 2: the same saw bass with resonant low-pass (Drum 3 locked, Drum 2 LFO). Hat: driven, high-pass, LFO amount 0 in the kit. |
| Key | G (bass G1) |
| BPM | 124 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 50% |
| **What this demonstrates** | Filter modulation makes movement without changing the rhythm: A is static, B moves the bass cutoff by a p-lock on every step (up, then down over two bars), C plays the same bass line on a twin voice whose cutoff an LFO sweeps smoothly, and the hats' high-pass is swept too (the locks only switch the LFOs on). |

**Pattern 1** - static (every cutoff constant)

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D3   .55.|.55.|.55.|.55.|.55.|.55.|.55.|.55.
S    ....|8...|....|8...|....|8...|....|8...
H    6.4.|6.4.|6.4.|6.4.|6.4.|6.4.|6.4.|6.4.
```

**Pattern 2** - bass cutoff locked step by step (stepped sweep)

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D3   .55.|.55.|.55.|.55.|.55.|.55.|.55.|.55.
S    ....|8...|....|8...|....|8...|....|8...
H    6.4.|6.4.|6.4.|6.4.|6.4.|6.4.|6.4.|6.4.
```

- D3 lock Drum 3 Filter Freq: 2=30, 3=41, 6=53, 7=64, 10=76, 11=87, 14=99, 15=110, 18=110, 19=99, 22=87, 23=76, 26=64, 27=53, 30=41, 31=30

**Pattern 3** - same line on the LFO twin voice, LFO switched on per hit

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   .55.|.55.|.55.|.55.|.55.|.55.|.55.|.55.
S    ....|8...|....|8...|....|8...|....|8...
H    6.4.|6.4.|6.4.|6.4.|6.4.|6.4.|6.4.|6.4.
```

- D2 steps 2,3,6,7,10,11,14,15,18,19,22,23,26,27,30,31: lock Drum 2 LFO Amount = 80
- H steps 1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31: lock Hi-hat LFO Amount = 70

Song (switch on SONG in the pattern bar): 1 1 2 2 3 3 LOOP.

### Pitch Percussion

| | |
|---|---|
| Genre | Technique |
| Level | Level 3 - educational |
| Character | tuned toms playing a tune |
| Primary technique | per-step note on a drum voice: one tom becomes a melodic instrument |
| Secondary techniques | two-voice answer (drum 2 / drum 3); range of two and a half octaves from one voice |
| Voices used | Kick, clap, hat: plain. Drum 2: marimba-like tom. Drum 3: low tom. |
| Key | C major pentatonic (C D E G A) |
| BPM | 118 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 52% |
| **What this demonstrates** | A drum voice has a pitch, and the step note moves it by semitones from the kit tuning. A plays the toms on one pitch; B plays the same rhythm as a melody; C stretches it to two and a half octaves. |

**Pattern 1** - plain: the toms on a single pitch

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   9..7|..8.|9..7|.8..|9..7|..8.|9..7|.8..
D3   ...9|....|...9|....|...9|....|...9|....
S    ....|....|8...|....|....|....|8...|....
H    .4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4
```

**Pattern 2** - the same rhythm as a pentatonic melody

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   9..7|..8.|9..7|.8..|9..7|..8.|9..7|.8..
D3   ...9|....|...9|....|...9|....|...9|....
S    ....|....|8...|....|....|....|8...|....
H    .4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4
```

- D2 steps 4,14,25: note +7
- D2 steps 7,28: note +4
- D2 steps 9,20: note +12
- D2 steps 12,23: note +9
- D2 step 17: note +14
- D2 step 30: note +2
- D3 step 12: note -5
- D3 step 20: note -3
- D3 step 28: note -7

**Pattern 3** - the melody an octave and a fifth higher, the answer lower

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   9..7|..8.|9..7|.8..|9..7|..8.|9..7|.8..
D3   ...9|....|...9|....|...9|....|...9|....
S    ....|....|8...|....|....|....|8...|....
H    .4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4
```

- D2 step 1: note +12
- D2 steps 4,23: note +16
- D2 steps 7,28: note +9
- D2 steps 9,20: note +19
- D2 steps 12,25: note +14
- D2 steps 14,30: note +7
- D2 step 17: note +21
- D3 step 4: note -7
- D3 step 12: note -12
- D3 step 20: note -10
- D3 step 28: note -14

Song (switch on SONG in the pattern bar): 1 1 2 2 3 3 LOOP.

### One Voice, Six Drums

| | |
|---|---|
| Genre | Technique |
| Level | Level 3 - educational |
| Character | a whole kit from one voice |
| Primary technique | parameter locks + step note turn Drum 3 into a kick, snare, hat, tom, bell and bass |
| Secondary techniques | waveform lock (sine -> noise); decay locks from 3 to 30; FM amount lock for the bell, pitch-mod lock for the bass |
| Voices used | Only Drum 3 plays (every other voice is silent). Kit: sine with pitch envelope, drive, light high-pass. |
| Key | no tuned key; the note offsets are per drum (kick -17, hat +24, bell +24, bass -12) |
| BPM | 100 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 50% |
| **What this demonstrates** | Each step carries at most two locks and a note: a note offset and a decay lock make kick, tom and bass; a waveform lock to noise makes snare and hat; an FM lock makes the bell. A is the voice unlocked: all eight hits identical. |

**Pattern 1** - the voice unlocked (eight identical hits)

```text
D3   9.7.|9.8.|9.7.|9.8.
```

**Pattern 2** - the same eight hits as kick, hat, snare, hat, kick, tom, snare, bell

```text
D3   9.7.|9.8.|9.7.|9.8.
```

- D3 steps 1,9: note -17
- D3 steps 3,7,15: note +24
- D3 steps 5,13: note +5
- D3 step 11: note +7
- D3 lock Drum 3 Decay: 1=22, 3=3, 5=14, 7=3, 9=22, 11=16, 13=14, 15=26
- D3 steps 3,5,7,13: lock Drum 3 Waveform = 4
- D3 step 15: lock Drum 3 FM Amount = 100

**Pattern 3** - two bars, six different drums

```text
D3   9.7.|9.8.|9.7.|9.8.|9.7.|9.8.|9.7.|9.8.
```

- D3 steps 1,9,17: note -17
- D3 steps 3,7,11,23,25,27: note +24
- D3 steps 5,13,21,29: note +5
- D3 steps 15,31: note +7
- D3 step 19: note -12
- D3 lock Drum 3 Decay: 1=22, 3=3, 5=14, 7=3, 9=22, 11=3, 13=14, 15=16, 17=22, 19=30, 21=14, 23=3, 25=26, 27=3, 29=14, 31=16
- D3 steps 3,5,7,11,13,21,23,27,29: lock Drum 3 Waveform = 4
- D3 step 19: lock Drum 3 Pitch Mod = 0
- D3 step 25: lock Drum 3 FM Amount = 100

Song (switch on SONG in the pattern bar): 1 1 2 2 3 3 LOOP.

### Locked Kick

| | |
|---|---|
| Genre | Technique |
| Level | Level 3 - educational |
| Character | four on the floor, sixteen different kicks |
| Primary technique | per-step locks on one drum voice: the rhythm is identical, the timbre is not |
| Secondary techniques | phrase-ending pitch/decay lock; drive, click, FM, waveform and pitch-envelope locks; a falling scale by note and decay |
| Voices used | Kick: sine with pitch envelope and drive. Clap, hat: plain (the beat that stays the same). |
| Key | G (kick 49 Hz) |
| BPM | 126 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 64) |
| Swing | 50% |
| **What this demonstrates** | Four bars of four-on-the-floor in which no kick is like its neighbour: bar 1 ends higher and shorter; bar 2 is snappy, crunchy, clicky and a boom; bar 3 is metallic, square, a laser zap and a tick; bar 4 falls. Every hit has at most two locks and a note. A is the same kick sixteen times. |

**Pattern 1** - sixteen identical kicks

```text
K    9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...
S    ....|8...|....|8...|....|8...|....|8...|....|8...|....|8...|....|8...|....|8...
H    ..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.
O    .4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4
```

**Pattern 2** - four bars, sixteen different kicks, the same rhythm

```text
K    9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...
S    ....|8...|....|8...|....|8...|....|8...|....|8...|....|8...|....|8...|....|8...
H    ..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.
O    .4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4
```

- K step 13: note +3
- K step 29: note -5
- K step 53: note -3
- K step 57: note -6
- K step 61: note -9
- K lock Drum 1 Decay: 13=11, 21=24, 29=38, 45=10, 49=14, 53=20, 57=28, 61=40
- K steps 17,45: lock Drum 1 Pitch Mod = 100
- K step 21: lock Drum 1 Drive = 110
- K step 25: lock Drum 1 Click Level = 100
- K step 33: lock Drum 1 FM Amount = 70
- K step 33: lock Drum 1 FM Freq = 50
- K step 37: lock Drum 1 Waveform = 3
- K step 37: lock Drum 1 Filter Freq = 45
- K step 41: lock Drum 1 Pitch Decay = 60

Song (switch on SONG in the pattern bar): 1 1 2 2 LOOP.

### Evolving Snare

| | |
|---|---|
| Genre | Technique |
| Level | Level 3 - educational |
| Character | one backbeat, eight snares |
| Primary technique | locks on the snare voice: noise mix, filter, decay, waveform, repeat counter, click layer |
| Secondary techniques | repeat counter as a clap flutter; sample layer by Click Type lock; a morph from tone to noise across bars |
| Voices used | Kick, hat: plain. Snare: triangle + noise, high-passed, driven, sample snare click. |
| Key | no key (snare body D3; B uses note offsets +7 and -12) |
| BPM | 120 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 64) |
| Swing | 50% |
| **What this demonstrates** | The snare plays on 2 and 4 for four bars and is a different drum each time: B changes its length, filter, waveform, repeat counter and sample layer; C morphs it from a pure tone to pure noise (Noise/Osc Mix locked 0 -> 127) while the decay shortens. |

**Pattern 1** - the same snare eight times

```text
K    9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...
S    ....|8...|....|8...|....|8...|....|8...|....|8...|....|8...|....|8...|....|8...
H    .4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4
O    ..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.
```

**Pattern 2** - eight different snares (tight, clap, rim, airy, thud, sample, long)

```text
K    9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...
S    ....|8...|....|8...|....|8...|....|8...|....|8...|....|8...|....|8...|....|8...
H    .4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4
O    ..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.
```

- S step 13: note +7
- S step 45: note -12
- S lock Snare Decay: 13=8, 37=24, 45=26, 61=40
- S step 21: lock Snare Attack = 12
- S step 21: lock Snare Repeat Count = 4
- S step 29: lock Snare Waveform = 0
- S step 29: lock Snare Noise / Osc Mix = 20
- S lock Snare Filter Freq: 37=90, 61=10
- S step 53: lock Snare Click Level = 127
- S step 53: lock Snare Click Type = 9

**Pattern 3** - one scan from tone to noise

```text
K    9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...
S    ....|8...|....|8...|....|8...|....|8...|....|8...|....|8...|....|8...|....|8...
H    .4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4
O    ..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.|..5.
```

- S lock Snare Noise / Osc Mix: 5=0, 13=20, 21=40, 29=60, 37=80, 45=100, 53=115, 61=127
- S lock Snare Decay: 5=24, 13=22, 21=20, 29=18, 37=16, 45=14, 53=12, 61=10

Song (switch on SONG in the pattern bar): 1 1 2 2 3 3 LOOP.

### Moving Hats

| | |
|---|---|
| Genre | Technique |
| Level | Level 3 - educational |
| Character | the same hi-hat row, four ways of moving |
| Primary technique | a tempo-synced LFO on the hat filter, switched on and shaped by locks (amount, sync, wave) |
| Secondary techniques | LFO amount as a per-hit switch; sync division and waveform changed by lock; high-pass sweep changes level as well as colour |
| Voices used | Kick, clap: plain. Hat: driven, high-pass; LFO target = hat filter freq, amount 0 in the kit. |
| Key | no key |
| BPM | 126 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 50% |
| **What this demonstrates** | A static hat row becomes alive without adding a note: B sweeps the high-pass slowly (triangle, half-note), C three times faster (1/6), D randomly (sample-and-hold). The kit stores the LFO with amount 0; each pattern only locks the amount (and sync / wave) on the hat steps. |

**Pattern 1** - static hats

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
S    ....|8...|....|8...|....|8...|....|8...
H    6.4.|5.4.|6.4.|5.4.|6.4.|5.4.|6.4.|5.4.
```

**Pattern 2** - slow triangle sweep

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
S    ....|8...|....|8...|....|8...|....|8...
H    6.4.|5.4.|6.4.|5.4.|6.4.|5.4.|6.4.|5.4.
```

- H steps 1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31: lock Hi-hat LFO Amount = 60

**Pattern 3** - fast triangle sweep (1/6)

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
S    ....|8...|....|8...|....|8...|....|8...
H    6.4.|5.4.|6.4.|5.4.|6.4.|5.4.|6.4.|5.4.
```

- H steps 1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31: lock Hi-hat LFO Amount = 60
- H steps 1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31: lock Hi-hat LFO Sync = 7

**Pattern 4** - sample-and-hold (random) cutoff

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
S    ....|8...|....|8...|....|8...|....|8...
H    6.4.|5.4.|6.4.|5.4.|6.4.|5.4.|6.4.|5.4.
```

- H steps 1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31: lock Hi-hat LFO Amount = 70
- H steps 1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31: lock Hi-hat LFO Wave = 5

Song (switch on SONG in the pattern bar): 1 1 2 2 3 3 4 4 LOOP.

### Metallic FM

| | |
|---|---|
| Genre | Technique |
| Level | Level 3 - educational |
| Character | soft tone to bell to clang, on the same rhythm |
| Primary technique | FM amount and FM ratio (FM freq) as timbre dials, locked per hit |
| Secondary techniques | modulator ratio sweep at constant depth; FM through the pitch envelope: depth falls as the hit decays; second FM voice an octave and more below |
| Voices used | Kick: plain. Drum 2: sine FM'd by a sine (FM amount 0 in the kit). Drum 3: the same, lower. |
| Key | E (drum 2 E4, drum 3 A3; D keeps the octave under) |
| BPM | 110 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 50% |
| **What this demonstrates** | FM Amount is the timbre dial: in B it rises across sixteen hits from 0 to 127, so one tom changes from a soft sine tone to a wooden knock to a metallic clang without changing pitch or rhythm. C holds the depth and sweeps the modulator ratio instead, which moves the inharmonic partials. |

**Pattern 1** - FM 0: a soft sine tom

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   9.7.|8.7.|9.7.|8.7.|9.7.|8.7.|9.7.|8.7.
```

**Pattern 2** - FM amount ramps 0 -> 127 over 16 hits

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   9.7.|8.7.|9.7.|8.7.|9.7.|8.7.|9.7.|8.7.
```

- D2 lock Drum 2 FM Amount: 1=0, 3=8, 5=16, 7=25, 9=33, 11=42, 13=50, 15=59, 17=67, 19=76, 21=84, 23=93, 25=101, 27=110, 29=118, 31=127

**Pattern 3** - FM amount fixed, ratio sweeps

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   9.7.|8.7.|9.7.|8.7.|9.7.|8.7.|9.7.|8.7.
```

- D2 steps 1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31: lock Drum 2 FM Amount = 85
- D2 lock Drum 2 FM Freq: 1=10, 3=17, 5=24, 7=32, 9=39, 11=46, 13=54, 15=61, 17=68, 19=76, 21=83, 23=90, 25=98, 27=105, 29=112, 31=120

**Pattern 4** - B plus a second FM voice, lower, bright

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   9.7.|8.7.|9.7.|8.7.|9.7.|8.7.|9.7.|8.7.
D3   ....|....|9...|....|....|....|9...|....
```

- D2 lock Drum 2 FM Amount: 1=0, 3=8, 5=16, 7=25, 9=33, 11=42, 13=50, 15=59, 17=67, 19=76, 21=84, 23=93, 25=101, 27=110, 29=118, 31=127
- D3 step 9: note -7
- D3 step 25: note -12
- D3 steps 9,25: lock Drum 3 FM Amount = 110

Song (switch on SONG in the pattern bar): 1 1 2 2 3 3 4 4 LOOP.

### Envelope Clicks

| | |
|---|---|
| Genre | Technique |
| Level | Level 3 - educational |
| Character | a groove made of clicks, ticks and blips |
| Primary technique | extremely short envelopes: clicks from the sample layer, one-block blips, noise snaps; then decay locks stretch single hits |
| Secondary techniques | click pitch dial; every voice a few milliseconds; decay lock turns a blip into a tone |
| Voices used | Drum 1: 1-block sine thump + kick sample click. Drum 2: 1-block sine blip. Drum 3: tick sample. Snare: noise snap. Cymbal: noise zip. Hat: tick. |
| Key | no key |
| BPM | 130 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 52% |
| **What this demonstrates** | Decay 0 is one 1.45 ms control block: the voices produce clicks and ticks, which at 130 bpm are a rhythm of pure transients. In B, a decay lock stretches the blip voice from 0 to about 300 ms hit by hit, so a click becomes a pitched tone. |

**Pattern 1** - the groove of transients

```text
K    9..7|..9.|.7.7|..7.|9..7|..9.|.7.7|..7.
D2   ..5.|.4..|.5..|4.5.|..5.|.4..|.5..|4.5.
D3   .4.5|.4.5|.4.5|.4.5|.4.5|.4.5|.4.5|.4.5
S    ....|9...|....|9.5.|....|9...|....|9.5.
C    ....|..5.|....|..3.|....|..5.|....|..3.
H    5.3.|5.3.|5.3.|5.3.|5.3.|5.3.|5.3.|5.3.
```

**Pattern 2** - the blip voice's decay locked from click to tone

```text
K    9..7|..9.|.7.7|..7.|9..7|..9.|.7.7|..7.
D2   ..5.|.4..|.5..|4.5.|..5.|.4..|.5..|4.5.
D3   .4.5|.4.5|.4.5|.4.5|.4.5|.4.5|.4.5|.4.5
S    ....|9...|....|9.5.|....|9...|....|9.5.
C    ....|..5.|....|..3.|....|..5.|....|..3.
H    5.3.|5.3.|5.3.|5.3.|5.3.|5.3.|5.3.|5.3.
```

- D2 lock Drum 2 Decay: 3=0, 6=1, 10=2, 13=3, 15=5, 19=8, 22=12, 26=18, 29=26, 31=36

Song (switch on SONG in the pattern bar): 1 1 2 LOOP.

### Resonant Sweep

| | |
|---|---|
| Genre | Technique |
| Level | Level 3 - educational |
| Character | pings that play a melody, resonance that rings |
| Primary technique | noise through a resonant band-pass: the cutoff is the pitch, the resonance is the ring; both locked per hit |
| Secondary techniques | melody in C minor pentatonic with no oscillator pitch involved; resonance sweep at a fixed cutoff; long rings with a rising cutoff |
| Voices used | Kick, clap, hat: plain. Drum 3: noise -> band-pass at resonance 120 (170 ms ping). Drum 2: the same with a longer ring. |
| Key | C minor pentatonic (C Eb F G Bb ...) |
| BPM | 124 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 50% |
| **What this demonstrates** | A resonant filter excited by noise rings at its cutoff, so a p-lock on Filter Freq is a note: B plays a sixteen-hit tune that is made only of filter cutoffs (the cutoff values come from a calibration of the engine's cutoff-to-frequency curve). C holds the pitch and sweeps resonance from damped to ringing. |

**Pattern 1** - one cutoff: every ping the same pitch

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D3   9.7.|8.7.|9.7.|8.7.|9.7.|8.7.|9.7.|8.7.
S    ....|8...|....|8...|....|8...|....|8...
H    .4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4
```

**Pattern 2** - the cutoff locked to a melody

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D3   9.7.|8.7.|9.7.|8.7.|9.7.|8.7.|9.7.|8.7.
S    ....|8...|....|8...|....|8...|....|8...
H    .4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4
```

- D3 lock Drum 3 Filter Freq: 1=26, 3=29, 5=32, 7=30, 9=39, 11=32, 13=42, 15=47, 17=55, 19=47, 21=42, 23=39, 25=32, 27=30, 29=29, 31=26

**Pattern 3** - cutoff fixed, resonance 20 -> 127

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D3   9.7.|8.7.|9.7.|8.7.|9.7.|8.7.|9.7.|8.7.
S    ....|8...|....|8...|....|8...|....|8...
H    .4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4
```

- D3 steps 1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31: lock Drum 3 Filter Freq = 32
- D3 lock Drum 3 Resonance: 1=20, 3=27, 5=34, 7=41, 9=48, 11=55, 13=62, 15=69, 17=77, 19=84, 21=91, 23=98, 25=105, 27=112, 29=119, 31=127

**Pattern 4** - four long rings with a rising cutoff

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   9...|....|7...|....|8...|....|7...|....
S    ....|8...|....|8...|....|8...|....|8...
H    .4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4
```

- D2 lock Drum 2 Filter Freq: 1=22, 9=62, 17=100, 25=118

Song (switch on SONG in the pattern bar): 1 1 2 2 3 3 4 4 LOOP.

### Velocity Is Timbre

| | |
|---|---|
| Genre | Technique |
| Level | Level 3 - educational |
| Character | dynamics that change the sound, not only the level |
| Primary technique | velocity > volume plus velocity targets: filter on the snare, pitch depth on the kick, decay on the hat |
| Secondary techniques | ghost notes that are darker and shorter, accents that are brighter and longer; a crescendo roll whose last hits are the brightest |
| Voices used | Kick: velocity -> pitch mod. Snare: noise through a low-pass, velocity -> cutoff. Hat: velocity -> closed decay. Everything also gets louder with velocity. |
| Key | no key |
| BPM | 128 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 50%, 54% |
| **What this demonstrates** | Without Velocity > Volume a step's velocity does nothing at all; with it, velocity is loudness, and a velocity target adds a second dimension. Here a soft snare is dark and a hard one is bright and snappy, a soft hat is short and a hard hat rings, a soft kick has less beater. A has only full velocities, B has accents and ghosts, C ends in a crescendo roll. |

**Pattern 1** - full velocity everywhere (flat)

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
S    ....|9...|....|9...|....|9...|....|9...
H    9.9.|9.9.|9.9.|9.9.|9.9.|9.9.|9.9.|9.9.
O    ..6.|..6.|..6.|..6.|..6.|..6.|..6.|..6.
```

**Pattern 2** - accents and ghost notes: both louder and brighter

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
S    ....|9..2|.3..|8..3|....|9..2|.3..|8..3
H    9.3.|6.3.|9.3.|6.3.|9.3.|6.3.|9.3.|6.3.
O    ..6.|..6.|..6.|..6.|..6.|..6.|..6.|..6.
```

**Pattern 3** - crescendo snare roll: darker to brighter as it rises

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
S    ....|9...|....|9...|....|9...|..12|4579
H    9.3.|6.3.|9.3.|6.3.|9.3.|6.3.|9.3.|6.3.
O    ..6.|..6.|..6.|..6.|..6.|..6.|..6.|..6.
```

Song (switch on SONG in the pattern bar): 1 1 2 2 3 3 LOOP.

### Noise Lab

| | |
|---|---|
| Genre | Technique |
| Level | Level 3 - educational |
| Character | a groove made only of noise |
| Primary technique | noise synthesis: kick, tom, hat, clap, wash and tick are all the noise oscillator, shaped by filters, envelopes, drive and the repeat counter |
| Secondary techniques | noise colour by note (sample-and-hold rate); clap flutter by Repeat Count locks; noise as a kick (low rate + low-pass + drive) |
| Voices used | Drum 1: noise thump. Drum 2: open noise perc. Drum 3: noise tick. Snare: noise clap. Cymbal: noise wash (slow attack). Hat: all-noise hat. |
| Key | no key |
| BPM | 118 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 52% |
| **What this demonstrates** | A complete groove from one source: the noise oscillator is sample-and-hold at the voice pitch, so a low note is crunchy rumble and a high note is hiss. In B the noise perc walks the note from -24 to +36: the colour of the noise moves from rumble to hiss. In C the snare's repeat counter turns a hit into a flutter. |

**Pattern 1** - the noise groove

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   ...6|....|...4|..7.|...6|....|...4|..7.
D3   ....|...4|....|....|....|...4|....|....
S    ....|8...|....|8...|....|8...|....|8...
H    .5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4
O    ..6.|..6.|..6.|..6.|..6.|..6.|..6.|..6.
```

**Pattern 2** - noise colour by note (perc walks -24 .. +36)

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   ...6|....|...4|..7.|...6|....|...4|..7.
D3   ....|...4|....|....|....|...4|....|....
S    ....|8...|....|8...|....|8...|....|8...
H    .5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4
O    ..6.|..6.|..6.|..6.|..6.|..6.|..6.|..6.
```

- D2 step 4: note -24
- D2 step 12: note -12
- D2 step 20: note +12
- D2 step 28: note +24
- D2 step 31: note +36

**Pattern 3** - clap flutter: repeat count 0, 2, 4, 6

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   ...6|....|...4|..7.|...6|....|...4|..7.
D3   ....|...4|....|....|....|...4|....|....
S    ....|8...|....|8...|....|8...|....|8...
H    .5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4
O    ..6.|..6.|..6.|..6.|..6.|..6.|..6.|..6.
```

- S lock Snare Repeat Count: 5=0, 13=2, 21=4, 29=6

Song (switch on SONG in the pattern bar): 1 1 2 2 3 3 LOOP.

### Odd Meters

| | |
|---|---|
| Genre | Technique |
| Level | Level 3 - educational |
| Character | grooves that are not 16 steps |
| Primary technique | per-track pattern lengths: 12 against 16, 20 against 16, a 14-step bar (7/8), and a stack of 10 / 12 / 14 against 16 |
| Secondary techniques | polymeter: each track loops at its own length; patterns switch only when the longest track wraps; tuned perc figures by note |
| Voices used | Kick, clap, hat: plain. Drum 2: tuned tom. Drum 3: low-passed bass blip. |
| Key | D (bass voice D1 / F / G) |
| BPM | 118 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 10, 12, 14, 20) |
| Swing | 50% |
| **What this demonstrates** | Track lengths are independent: A puts a 12-step hat figure over the 16-step kick (three against four, a full cycle in three bars), B a 20-step tom figure (five against four), C is a single 14-step bar (7/8, grouped 4 + 4 + 6), D stacks 10, 12 and 14 against 16 so the combined loop is far longer than any one track. |

**Pattern 1** - 12 against 16 (3:4)

```text
K    9...|9...|9...|9...
D3   ..7.|....|..5.
S    ....|8...|....|8...
H    9.5.|.5.5|..5.
```

- D3 step 11: note +3

**Pattern 2** - 20 against 16 (5:4)

```text
K    9...|9...|9...|9...
D2   9..5|.7..|5..6|.5..|7..5
S    ....|8...|....|8...
H    .5.5|.5.5|.5.5|.5.5
```

- D2 steps 4,12: note +5
- D2 steps 6,17: note +3
- D2 steps 9,20: note +7

**Pattern 3** - a bar of 14 steps (7/8)

```text
K    9...|9...|9...|..
D3   ..7.|..5.|....|3.
S    ....|8...|7...|5.
H    6.4.|5.4.|6.4.|5.
O    ....|..5.|....|5.
```

- D3 step 7: note +3
- D3 step 13: note +5

**Pattern 4** - 10 / 12 / 14 against 16

```text
K    9...|9...|9...|9...
D2   .9..|7.5.|.7..|5.
D3   9...|..7.|..5.
S    ....|....|8...|....
H    7.5.|7.5.|7.
```

- D2 step 5: note +5
- D2 step 7: note +7
- D2 step 10: note +3
- D3 step 7: note +7
- D3 step 11: note +3

Song (switch on SONG in the pattern bar): 1 1 1 2 2 2 2 3 3 4 4 4 LOOP.

### Swing Lab

| | |
|---|---|
| Genre | Technique |
| Level | Level 3 - educational |
| Character | one groove at five different swing amounts |
| Primary technique | pattern shuffle: every odd 16th is delayed by a fraction of the step pair |
| Secondary techniques | the same notes in all five patterns; swing percentages: 50 (straight), 54, 58, 62, 66.7 (triplet) |
| Voices used | Kick, clap, hat, open hat, bass blip: plain. |
| Key | G (bass G1) |
| BPM | 122 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 |
| Swing | 50%, 54%, 58%, 62%, 67% |
| **What this demonstrates** | The only difference between the patterns is the shuffle value: 50 % is straight, about 54-58 % is the lazy swing of deep house, about 62 % is jackin', 66.7 % is a full triplet. Shuffle delays only the odd 16ths (hats and the syncopated bass), so the kick and clap stay on the grid while the groove leans. |

**Pattern 1** - straight (50 %)

```text
K    9...|9...|9...|9...
D3   ..7.|...5|..7.|.5..
S    ....|8...|....|8...
H    7343|7343|7343|7343
O    ..6.|..6.|..6.|..6.
```

- D3 step 11: note +5
- D3 step 14: note +3

**Pattern 2** - 54 %

```text
K    9...|9...|9...|9...
D3   ..7.|...5|..7.|.5..
S    ....|8...|....|8...
H    7343|7343|7343|7343
O    ..6.|..6.|..6.|..6.
```

- D3 step 11: note +5
- D3 step 14: note +3

**Pattern 3** - 58 %

```text
K    9...|9...|9...|9...
D3   ..7.|...5|..7.|.5..
S    ....|8...|....|8...
H    7343|7343|7343|7343
O    ..6.|..6.|..6.|..6.
```

- D3 step 11: note +5
- D3 step 14: note +3

**Pattern 4** - 62 %

```text
K    9...|9...|9...|9...
D3   ..7.|...5|..7.|.5..
S    ....|8...|....|8...
H    7343|7343|7343|7343
O    ..6.|..6.|..6.|..6.
```

- D3 step 11: note +5
- D3 step 14: note +3

**Pattern 5** - 66.7 % (triplet)

```text
K    9...|9...|9...|9...
D3   ..7.|...5|..7.|.5..
S    ....|8...|....|8...
H    7343|7343|7343|7343
O    ..6.|..6.|..6.|..6.
```

- D3 step 11: note +5
- D3 step 14: note +3

Song (switch on SONG in the pattern bar): 1 1 2 2 3 3 4 4 5 5 LOOP.

### Flam & Shift

| | |
|---|---|
| Genre | Technique |
| Level | Level 3 - educational |
| Character | timing inside the step |
| Primary technique | flams (x2 to x8) and shift (micro-timing, +-7 units of 1/8 step) per step |
| Secondary techniques | rush / lay back / drunk hats by shift; a roll fill from flams plus shift; both are timing only: pitch and timbre are untouched |
| Voices used | Kick, clap, hat, tom: plain. |
| Key | no key |
| BPM | 124 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 64) |
| Swing | 50% |
| **What this demonstrates** | A step can fire several times (flam x2, x3, x4, x6, x8) and can be moved by a few milliseconds without leaving the grid (shift). A builds a flam ladder over four bars, B moves the hats of bars 2, 3, 4 early, late and alternately, C ends with a roll made from flams and shifts. |

**Pattern 1** - clap flam ladder x2, x3, x4, x8

```text
K    9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...
S    ....|8...|....|9...|....|8...|....|9...|....|8...|....|9...|....|8...|....|9...
H    .5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4
```

- S step 13: flam x2
- S step 29: flam x3
- S step 45: flam x4
- S step 61: flam x8

**Pattern 2** - hats rush, lay back, and wobble

```text
K    9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...
S    ....|8...|....|8...|....|8...|....|8...|....|8...|....|8...|....|8...|....|8...
H    .5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4
```

- H steps 18,20,22,24,26,28,30,32: shift -3
- H steps 34,36,38,40,42,44,46,48: shift +3
- H steps 50,54,58,62: shift -2
- H steps 52,56,60,64: shift +2

**Pattern 3** - a four-step roll fill

```text
K    9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...|9...
D3   ....|....|..9.|....|....|....|..9.|....|....|....|..9.|....|....|....|..9.|....
S    ....|8...|....|8...|....|8...|....|8...|....|8...|....|8...|....|8...|6.6.|7.8.
H    .5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4|.5.4
```

- D3 step 59: flam x2
- S step 57: flam x4
- S steps 57,61: shift -2
- S step 59: flam x3
- S step 59: shift +2
- S step 61: flam x2
- S step 63: flam x6

Song (switch on SONG in the pattern bar): 1 1 2 2 3 3 LOOP.

### Probability Garden

| | |
|---|---|
| Genre | Technique |
| Level | Level 3 - educational |
| Character | a loop that never repeats the same way twice |
| Primary technique | step probability in tiers: the groove is certain (100 %), the decoration is not (15 - 90 %) |
| Secondary techniques | hat tiers: downbeat 100 %, offbeat 8ths, then 16ths; tuned perc and a bass blip that only sometimes answer; sparse (B) and busy (C) versions of the same garden |
| Voices used | Kick, clap, hat: plain. Drum 2: FM bell-ish tom. Drum 3: low-passed bass blip. |
| Key | no key |
| BPM | 125 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 54% |
| **What this demonstrates** | Probability is a per-step number (1-100 %), checked every time the step comes round. A fixed backbone plus tiers of optional hits gives a groove that is stable but never identical; the seed is fixed in the offline audit, in the plugin each pass is different. B halves and C raises all the optional probabilities. |

**Pattern 1** - the garden

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   ...5|..4.|...5|..4.|...5|..4.|...5|..4.
D3   ..6.|...4|..6.|.4..|..6.|...4|..6.|.4..
S    ....|8...|....|8...|....|8...|....|8...
H    9363|9363|9363|9363|9363|9363|9363|9363
```

- D2 steps 4,7,12,15,20,23,28,31: probability 45%
- D2 steps 7,23: note +7
- D2 steps 12,28: note +4
- D2 step 15: note +12
- D2 step 20: note +9
- D2 step 31: note +2
- D3 steps 3,8,11,14,19,24,27,30: probability 70%
- H steps 2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32: probability 30%
- H steps 3,7,11,15,19,23,27,31: probability 70%

**Pattern 2** - sparse (optional hits are rare)

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   ...5|..4.|...5|..4.|...5|..4.|...5|..4.
D3   ..6.|...4|..6.|.4..|..6.|...4|..6.|.4..
S    ....|8...|....|8...|....|8...|....|8...
H    9363|9363|9363|9363|9363|9363|9363|9363
```

- D2 steps 4,7,12,15,20,23,28,31: probability 25%
- D2 steps 7,23: note +7
- D2 steps 12,28: note +4
- D2 step 15: note +12
- D2 step 20: note +9
- D2 step 31: note +2
- D3 steps 3,8,11,14,19,24,27,30: probability 40%
- H steps 2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32: probability 15%
- H steps 3,7,11,15,19,23,27,31: probability 40%

**Pattern 3** - busy (optional hits are likely)

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   ...5|..4.|...5|..4.|...5|..4.|...5|..4.
D3   ..6.|...4|..6.|.4..|..6.|...4|..6.|.4..
S    ....|8...|....|8...|....|8...|....|8...
H    9363|9363|9363|9363|9363|9363|9363|9363
```

- D2 steps 4,7,12,15,20,23,28,31: probability 70%
- D2 steps 7,23: note +7
- D2 steps 12,28: note +4
- D2 step 15: note +12
- D2 step 20: note +9
- D2 step 31: note +2
- D3 steps 3,8,11,14,19,24,27,30: probability 90%
- H steps 2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32: probability 60%
- H steps 3,7,11,15,19,23,27,31: probability 90%

Song (switch on SONG in the pattern bar): 1 1 1 1 2 2 3 3 LOOP.

### Ring Mod Throws

| | |
|---|---|
| Genre | Technique |
| Level | Level 3 - educational |
| Character | clean toms that turn metallic on command |
| Primary technique | an FX-bus ring modulator switched on per hit: FX dry/wet and FX carrier frequency as p-locks |
| Secondary techniques | FX parameters are lockable like any other; rectangle carrier for a bright clang; carrier sweep over a phrase |
| Voices used | Kick, clap, hat: plain. Drum 2 + Drum 3: tuned toms routed to the FX bus (ring modulator, rectangle carrier, dry/wet 0 in the kit). |
| Key | F (toms F3 / A3 area, ring partials follow the carrier) |
| BPM | 112 (suggested; the plugin follows the host tempo) |
| Pattern length | 16 (tracks of 32) |
| Swing | 50% |
| **What this demonstrates** | The FX slot is a part of the instrument you can play: the kit leaves the ring modulator at dry/wet 0 (A is a plain tom pattern); B locks dry/wet and carrier frequency on selected hits so those toms clang while their neighbours stay clean; C locks the ring modulator on for every hit and sweeps the carrier from 60 to 880 Hz across the phrase. The lock holds until that voice's next trigger, and the FX bus is shared by every voice routed to it. |

**Pattern 1** - toms, plain (ring mod at dry/wet 0)

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   9..7|..8.|.7..|8.7.|9..7|..8.|.7..|8.7.
D3   ...8|....|...8|....|...8|....|...8|....
S    ....|8...|....|8...|....|8...|....|8...
H    .4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4
```

- D2 steps 4,13,17: note +7
- D2 steps 7,20,29: note +3
- D2 steps 10,23,31: note +5
- D2 step 15: note +10

**Pattern 2** - selected toms thrown through the ring modulator

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   9..7|..8.|.7..|8.7.|9..7|..8.|.7..|8.7.
D3   ...8|....|...8|....|...8|....|...8|....
S    ....|8...|....|8...|....|8...|....|8...
H    .4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4
```

- D2 steps 4,13,17: note +7
- D2 steps 7,20,29: note +3
- D2 steps 10,23,31: note +5
- D2 step 15: note +10
- D2 lock FX FX Dry/Wet: 1=0, 4=100, 7=0, 10=100, 13=0, 15=0, 17=100, 20=100, 23=0, 26=100, 29=0, 31=100
- D2 lock FX FX P1: 1=40, 4=22, 7=40, 10=60, 13=40, 15=40, 17=90, 20=127, 23=40, 26=30, 29=40, 31=100

**Pattern 3** - carrier sweep across all hits

```text
K    9...|9...|9...|9...|9...|9...|9...|9...
D2   9..7|..8.|.7..|8.7.|9..7|..8.|.7..|8.7.
D3   ...8|....|...8|....|...8|....|...8|....
S    ....|8...|....|8...|....|8...|....|8...
H    .4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4|.4.4
```

- D2 steps 4,13,17: note +7
- D2 steps 7,20,29: note +3
- D2 steps 10,23,31: note +5
- D2 step 15: note +10
- D2 steps 1,4,7,10,13,15,17,20,23,26,29,31: lock FX FX Dry/Wet = 100
- D2 lock FX FX P1: 1=8, 4=18, 7=29, 10=40, 13=51, 15=62, 17=72, 20=83, 23=94, 26=105, 29=116, 31=127

Song (switch on SONG in the pattern bar): 1 1 2 2 3 3 LOOP.

