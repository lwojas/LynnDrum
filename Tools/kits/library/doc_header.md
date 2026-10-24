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

