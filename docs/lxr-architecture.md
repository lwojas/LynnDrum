# LXR firmware — architecture map

Source studied: `Reference/lxr-desktop-app` @ `a43cd4f` ("GCC 15 adds thread-jumps by default…", 2026-10-23), a `--depth 1` clone of
<https://github.com/erica-synths/lxr-desktop-app>. The clone is treated as read-only reference. Nothing in it was modified.

Depth of reading: the DSP, mixer, FX bus, parameter/CC layer, voice triggering, LFO/modulation, clock sync and the sequencer's clock/trigger/flam/shift/probability/automation path were read
line by line (a second pass on the sequencer followed the scope decision that it is part of the product; see `lxr-sequencer.md`). The reverb internals, the menu/LCD/button code, USB/FatFs/HAL, the preset file serialisation and the sequencer's pattern-editing
code were only skimmed or identified by name. Where a statement depends on code I did not read, it says so.

---

## 1. Licensing and source boundary (Phase 0)

### 1.1 What the repository says

| Item | Finding |
|---|---|
| Licence | **GPL-3.0-only** (not "or later"). `LICENSE` is the stock GPLv3 text. 155 files carry `SPDX-License-Identifier: GPL-3.0-only`. |
| `NOTICE.md` | Adds **GPLv3 §7 terms**: (a) permission to link with ST-licensed code (SLA0044), (b) **§7(e) trademark term**, (c) **§7(c) "marked modified versions"** term. |
| Trademark term | No rights in "Erica Synths", "LXR", "LXR-02" or logos. They may not be used for any product, firmware, service or activity, commercial or not, "in a way that suggests that it comes from, is approved by or is affiliated with Erica Synths" without written permission. *Truthful compatibility statements* ("custom firmware for the Erica Synths LXR-02") are allowed. |
| Modified-version term | Modified versions must be marked as different. The notice states the device start-up screen must show it is modified, and the work must not be presented as official firmware. For a plugin the analogue is a visible "unofficial, derived from LXR firmware" marking (to be confirmed with counsel / the licensor). |
| Hardware | Schematics, PCB, enclosure and appearance are explicitly **not** licensed. Not in the repo. Irrelevant to the DSP port but relevant to the *look* of any UI. |
| Third-party components | HAL (BSD-3), CMSIS (Apache-2.0), ST USB library (SLA0044), FatFs (BSD-style), HD44780 LCD routines (mikrocontroller.net). **None are needed for a plugin.** Leave them behind and the ST licence question disappears. |

### 1.2 Things the notice does *not* cover (must be resolved before any distribution)

1. **Transient sample data** (`Core/Src/Soundengine/DSPAudio/transientTables.c`). `transientTables.h` credits `4102__patchen__atik-2-10-stereoatik` (freesound.org). A web lookup reported that sound as **CC-BY 4.0** (attribution required). I fetched the page through a summarising tool, so re-check the licence page by hand. `NOTICE.md` does not mention it. The repo's GPL grant cannot relicense third-party audio. **Decision: keep the tables and attribute** (author "patchen", title "ATIK 2 - 10 stereoatik.wav", CC BY 4.0, link, and a note that the data was converted/edited) in the About/credits panel and in the repository's `NOTICE`/`CREDITS` file. Whether all 12 tables derive from that one sample is not established (only one source is named); when attributing, state "transient samples derived from the LXR firmware, which credits …" and keep the upstream comment verbatim.
2. **Crash sample** (`Samples.c`): CC0 per its comment (freesound, Matias Reccius). **It is unused by the current engine** (all `crashSample` readers are commented out or `#if 0`). Omit it.
3. **Init kit** (`Inc/Preset/InitKit.h`, `Src/Preset/initKit.c`): comment says "init kit from hrtlkits_batch3.zip". Provenance and licence unknown. Do not ship it as a factory preset until established. Use it only for private validation.
4. **`NOTICE.md` names directories that do not exist here** (`LXR_V2_STM32F765/`, `LXR_V2_STM32F765_Bootloader/`). This repo is flat (`Core/`, `Drivers/` …) and has no bootloader dir. The per-file headers still point to `NOTICE.md`, so I read the notice as applying repo-wide, but this is an upstream inconsistency worth asking Erica Synths about.
5. **Wavetable / filter lineage**: `wavetable.c` header text mentions "Samplerate: 44000 / 128 wavetables a 256 samples" (stale; the actual arrays are 11×1024). Authorship of the table generation is not recorded. Treated as part of the GPL source.
6. `ResonantFilter.c` is a ZDF SVF whose structure and the comment about "Fig 3.11" follow Zavalishin's *The Art of VA Filter Design*. The `tanhXdX` and `softClipTwo` rational approximations are standard tricks. This is generic DSP knowledge, not copyrightable expression, but it is relevant for category 3 below.

### 1.3 Implications of distributing a plugin built from this source

- Any plugin that **contains or links** adapted LXR code is a covered work. The **whole plugin binary** must be offered under GPL-3.0 with complete corresponding source. That includes our JUCE shell and our UI bundle. JUCE 8 is itself AGPL-3 / commercial, and GPLv3 §13 permits GPLv3 + AGPLv3 combination. A closed-source or JUCE-commercial-licence build is **not** possible while the engine is derived from LXR. **Project decision (2026-10-24): LynnDrum will end up free and open source, so GPL-3 is accepted, not a problem to route around.**
- VST3: the Steinberg SDK relicensed to MIT in 2025 (to be verified against the SDK version actually used). Compatible with GPLv3.
- The **§7(e) trademark term binds our branding**. The supplied mockup header reads **"LXR-02 · DIGITAL DRUM SYNTH · SONIC POTIONS × ERICA SYNTHS"** and the window title says "LXR-02 … VST3 Instrument". Shipping that suggests affiliation or approval. **Decision: the product is called LynnDrum for now** (a name of the user's choosing; may change later). The mockup's header and window title must therefore be rewritten (no "LXR-02", no "Erica Synths" credit line). Include a truthful statement such as "LynnDrum is derived from the open-source LXR firmware by Erica Synths; it is not affiliated with or endorsed by Erica Synths" — truthful compatibility/derivation statements are explicitly allowed by the notice.
- Commercial distribution is **not ruled out by GPL** (selling GPL software is allowed) but gives buyers the right to the source and to redistribute. Whether that is acceptable is a business decision. Per the brief we are not optimising for it now.

### 1.4 Source-category boundaries for this project

| # | Category | In this project |
|---|---|---|
| 1 | **Code directly derived from LXR** | `Source/Engine/lxr_core/**` only: adapted copies of the `Core/Src/Soundengine/DSPAudio/**`, `FxBus.c`, `mixer.c`, `MidiVoiceControl.c` and the tables. Every file keeps its upstream header; every deviation is listed in `lxr-porting-notes.md`. |
| 2 | **Independent implementation from studying the source** | Parameter table, event scheduler, sample-rate adapter, state/preset format, UI bridge. Written by us. They are still GPL once linked. The **sequencer** is a hybrid: its *data model and trigger logic* (step struct, flam/shift bit patterns, probability window, track lengths, pattern switching) are **derived** from `sequencer.c` and therefore category 1 (`Source/Sequencer/lxr_seq/**`); its *clock, transport and host integration* are ours (category 2). |
| 3 | **Generic DSP knowledge** | Rational soft-clip `(1+k)x/(1+k|x|)`, ZDF SVF, Padé tan, Schroeder/Dattorro-style allpass reverb, one-pole smoothing. May be reimplemented freely. |
| 4 | **JUCE / plugin infrastructure** | `Source/Plugin/**`, CMake, relays, APVTS. |
| 5 | **Our UI and application code** | `WebUI/**`, mixer/sequencer view code. |

*Overall licence outcome:* by project decision LynnDrum is released free and open source under GPL-3, so category boundaries serve **provenance, attribution and maintainability** (what is derived, what is ours), not licence avoidance.

`Reference/` is never compiled into the plugin. It is only built by the host harness (`Tools/ref-harness`) to generate golden audio. Keeping it as a separate, unmodified clone (or a submodule pinned to `a43cd4f`) is what makes "what did we change?" answerable.

---

## 2. Repository structure

```
lxr-desktop-app/
├── CMakeLists.txt, CMakePresets.json, cmake/        ARM cross-build (arm-none-eabi-gcc), .img packer
├── STM32F765VGTX_FLASH.ld                           linker script (ITCM/DTCM placement)
├── Core/
│   ├── Inc/, Src/                                   application sources (flat + Soundengine/ + menu/ + IO/ + Preset/)
│   ├── Startup/                                     ST startup .s
│   └── CMakeLists.txt                               defines OBJECT libs: lxr_platform, lxr_io, lxr_ui, lxr_preset, lxr_dsp, …
├── Drivers/                                         ST HAL + CMSIS (third party)
├── Middlewares/JS/STM32_USB_Device_Library          modified ST USB stack → USB-MIDI class
├── Middlewares/Third_Party/FatFs                    FAT filesystem for SD
├── USB_DEVICE_MIDI/, FATFS/                         CubeMX-generated glue
├── README.md, NOTICE.md, LICENSE, mod_targ_lineup.ods (modulation target list spreadsheet)
└── (no tests, no host build, no bootloader sources)
```

**There are no tests and no host (non-ARM) build target.** The only build is the cross-compile. The reference harness is something we have to create.

Size: ~71 k lines in `Core`/middleware, of which ~9.2 k are data tables (`wavetable.c` 7.5 k, `transientTables.c` 1.7 k) and ~6 k are FatFs. The engine proper is ≈ 6 k lines.

### Module responsibilities (`Core/`)

| Path | Responsibility | Needed for plugin? |
|---|---|---|
| `Src/Soundengine/DSPAudio/` — `DrumVoice`, `Snare`, `HiHat`, `CymbalVoice` | The four voice *types* (6 voice instances) | **Yes (core)** |
| `…/Oscillator`, `wavetable`, `Samples` | Table oscillators, noise, PWM, sine table; crash sample (dead) | **Yes** (not `Samples`) |
| `…/SlopeEg2`, `Decay`, `snapEg` | Amp EG, pitch EG, "snap" transient EG | **Yes** |
| `…/ResonantFilter`, `1PoleLp`, `TiltEq` | SVF, one-pole smoother, tilt EQ (reverb only) | **Yes** (`TiltEq` only if reverb) |
| `…/transientGenerator`, `transientTables` | Click/transient one-shots (12 × 2205 samples, int8) | **Yes** (licence caveat §1.2) |
| `…/lfo`, `modulationNode`, `automationNode` | Per-voice LFO, velocity & LFO modulators, step automation nodes | **Yes** (modulation); automation later |
| `…/distortion`, `dither` | Per-voice soft clipper; dither (unused in active path) | **Yes** / no |
| `…/mixer` | Block orchestrator: runs all voices and routes to outputs/FX bus | **Yes**, must be adapted |
| `…/FX/*`, `Src/Soundengine/FxBus.c` | Single global FX slot: drive / ring-mod / compressor / delay (reverb compiled out) | **Yes** |
| `Src/Soundengine/MIDI/MidiParser.c` (+ `ParameterArray.c`, `MidiVoiceControl.c`) | CC→DSP parameter *and* MIDI parsing *and* note routing (tangled) | **Parameter half: yes (adapt). MIDI half: replace** |
| `Src/Soundengine/Sequencer/*`, `DSPAudio/automationNode.c` | Step sequencer (7 tracks × 64 steps × 64 patterns), flam/shift/probability, roll, Euclid, pattern chaining/song, p-lock automation nodes, clock sync | **Yes — in scope (USP).** Logic derived; ms-clock and MIDI-clock-slave parts replaced by a host-PPQ clock |
| `Src/Soundengine/cs4344_cs5343.c`, `AudioCodecManager.c`, `Soundengine.c` | I2S/DMA ping-pong glue and the block scheduler | **No** — replaced by JUCE |
| `Src/Soundengine/MIDI/Uart.c`, `USB/usb_manager.c`, `Src/IO/*` | DIN MIDI, USB-MIDI, ADC pots/faders, DIO | No |
| `Src/Preset/*`, `Inc/Preset/*` | Kit/pattern/project files on SD; morph | Format idea only |
| `Src/menu/*`, `lcd.c`, `graphic.c`, `buttonHandler.c`, `ledHandler.c`, `encoder.c`, `frontPanelParser.c` | Hardware UI | No |
| `Src/Parameters.c`, `Inc/Parameters.h` | Parameter enum (PAR_*), value tables for the UI | Source of the parameter table |

The firmware is a **single-core, mostly cooperative** program: one main loop and two timer interrupts, no RTOS, no dynamic allocation in the engine (all statics; the only large arrays are `FX_BUFFER` and the pattern set).

---

## 3. Build targets

One executable (`LXR_V2_STM32F765.elf`) → `.bin` → `.img` for the bootloader. Relevant compile-time switches in `Inc/Soundengine/config.h` and neighbours that change the engine's *behaviour* (the values below are what this build uses):

| Switch | Value | Effect |
|---|---|---|
| `OUTPUT_DMA_SIZE` (`USE_BIG_SAMPLE_BUFFER=1`) | **64** | Engine block = 64 stereo frames. Also the control-rate tick (~689.7 Hz). The comments saying "16/32 samples" are stale. |
| `REAL_FS` | **44140.0 Hz** | The true I2S rate (prescaler cannot hit 44.1 k). Used everywhere. |
| `AMP_EG_SYNC` | 0 | Amp EG evaluated once per block; gain is linearly interpolated across the block. |
| `ENABLE_MIX_OSC`, `ENABLE_DRUM_SVF` | 1 | Mix-vs-FM option and filter present on drum voices. |
| `INTERPOLATE_OSC`, `INTERPOLATE_FM_OSC` | 1 | Linear table interpolation. |
| `USE_AMP_FILTER` | **undefined** | The per-sample amp one-pole and its `if(egClosed)` phase-reset guard are *compiled out*: see porting notes (phase is **always** reset on trigger). |
| `USE_REVERB` | **0** (`FxBus.h`) | Reverb code exists but is not part of this firmware. The FX list is Off/Drive/Ring/Comp/Delay. |
| `USE_DECIMATOR` | 1 | Per-voice sample-rate reducer in the mixer. |
| `USE_TRIGGERED_PAN` | 1 | Pan is sampled **at trigger time** (`triggeredPanL/R`). Changing pan mid-note has no effect until the next trigger. |
| `USE_SQRT_LUT` | undefined | Pan law computed with `sqrtf`. |
| `USE_FADER_VOLUME` | 1 | Hardware fader value multiplies voice volume (front-panel faders, not stored in the kit). |
| `SMOOTH_MIXER_VOL_PAN_DRIVE` | 1 | One-pole smoothing on voice volume and (drum voices 1–3 only) drive. |
| `ENABLE_NONLINEAR_INTEGRATORS`, `USE_SHAPER_NONLINEARITY` | 0 | SVF runs **linear** (only the input soft-clip + output tanh remain). |
| `FPU->FPDSCR.FZ` | set | Flush-to-zero denormals. |

---

## 4. Execution model and thread assumptions

```
 I2S DMA complete ──► (flips bCurrentSampleValid)         [audio hardware clock, 64-frame ping-pong]
 TIM2 ISR (prio 1)   ─► seq_tick(); soundengine_calcNextSampleBlock(); uart_processMidi();
 main loop           ─► soundengine_process()  (also does seq_tick + calc if CALC_SAMPLES_IN_INTERRUPT=1),
                        usb_getMidi → midiParser_parseMidiMessage, buttons, faders, menu, LEDs, SD, morph tick
 TIM14 ISR (prio 0)  ─► systick_ticks++ (1 ms-ish) and menu repaint
```

Key consequences for a port:

- **Everything that touches DSP state happens in one cooperative sequence** per block: MIDI/sequencer → parameter writes → `mixer_calcNextSampleBlock`. `soundengine_process` explicitly disables the TIM2 interrupt while it runs the sequencer and the block. There is **no locking and no atomic parameter exchange** in the engine. It relies on single-core ordering.
- **All events are quantised to block boundaries.** A trigger or parameter change takes effect at the *start of the next 64-frame block* (≈1.45 ms granularity, jitter up to one block).
- The sequencer's clock is **wall-clock time** (`systick_ticks`, a 4 kHz timer: **0.25 ms units**, inferred from the TIM14 config and the `×4` in `seq_calcDeltaT`), not sample-accurate (see §7). It runs a **96 PPQ internal clock with 24 sub-ticks per 16th-note step**. Swing/shuffle uses time deltas.
- The audio deadline is protected by `bCurrentSampleValid` ping-pong flags, not by a ring buffer.

---

## 5. The central structural problem: the parameter layer is the MIDI CC parser

The engine has **no setter API**. The only way parameters reach the DSP is `midiParser_ccHandler(MidiMsg, updateOriginal, isFloatModulator, v)` — one ~1,300-line `switch` in `MidiParser.c`.

- 228 "sound parameters" (`PAR_*`, indices 0…227): **128 CC-style** (`MIDI_CC`, with the infamous "stupid offset" `data1 += 1; data1 &= 0x7f`) and **100 "CC2/NRPN-style"** parameters (indices 128–227, addressed through NRPN data-entry or the front-panel protocol).
- Values are **7-bit integers 0…127**; floats are derived as `itg/127`. A parallel `activeParameters[]` byte array mirrors the kit, and `parameterArray[idx] = {void* ptr, type}` holds pointers into the voice structs (used only by modulators to read the "original value" and by `modNode`).
- **Modulation re-enters through the same handler**: each block the engine (a) re-applies the stored original value of every modulated target through `ccHandler`, then (b) lets each LFO and velocity modulator compute `orig + amount·(2·v−1)` and write the result through `ccHandler` again (`isFloatModulator=1`, so the float is passed unquantised to float-typed destinations but `itg = v·127` to integer-typed ones).
- `ccHandler` also performs UI side effects (`menu_switchSubPage`, `uart_sendFrontpanelByte`, `seq_setMute`…).

So the engine cannot be driven without either carrying the whole CC parser, or extracting a clean `lxr_set_param(index, value)` that preserves the same per-parameter transforms. That extraction is the heart of the port (see `lxr-porting-notes.md`, `lxr-parameter-map.md`).

---

## 6. Voices at a glance

Six voice **instances**, **four voice types**, seven sequencer **tracks** (track 6 = open hat on the same hat voice):

| Idx | Struct | Type | Core signal chain |
|---|---|---|---|
| 0, 1, 2 | `DrumVoice` | "Drum" (kick/tom) | osc ⟷ modOsc (FM *or* mix) + transient → SVF → amp EG → velocity → soft-clip → vol (×fader) → pan/route |
| 3 | `SnareVoice` | Snare | tuned S&H noise → SVF; + osc; mix; + transient → vol·vel·EG·fader → soft-clip |
| 4 | `CymbalVoice` | Cymbal / clap | osc FM'd by (modOsc·g1 + modOsc2·g2), `modOsc2` default noise → SVF + transient → vol·vel·EG(repeat)·fader → soft-clip |
| 5 | `HiHatVoice` | Hi-hat | as cymbal; closed/open decays; track 6 retriggers the same voice with the open decay |

All four types are **monophonic**. There is no voice pool, allocation or stealing. A trigger **re-uses the single voice** (see `lxr-dsp.md` §5).

---

## 7. Sequencer, MIDI, presets (summary)

*Sequencer* (`Soundengine/Sequencer/sequencer.c`, 2.8 k lines, now **in scope**; full description in `lxr-sequencer.md`): 7 tracks × 64 steps × 64 patterns; per step `volume` (7 bit + active flag), `prob` (1–100), `note`, two p-lock slots (param, value), `flam` (off/×2/×3/×4/×6/×8) and `shift` (−7…+7 in units of 3 sub-ticks). 24 sub-ticks per step; each sub-tick `seq_processFlam(idx)` resolves which of the previous/current/next step's 24-bit trigger masks fires (*next > current > prev*). Independent per-track lengths (polymetric; the longest track is the master that gates pattern switches), roll, Euclid generator, shuffle, pattern chaining, song mode, MIDI-clock slave. The internal clock derives sub-tick time from BPM (`seq_calcDeltaT`) and is polled from the audio-block interrupt.

*MIDI*: voices are bound to **MIDI channels** (not note numbers). A note on a voice's channel triggers it at the incoming pitch (`note − 60` semitones relative to the voice's coarse tune), unless the optional *note override* (`PAR_MIDI_NOTE n ≠ 0`) is set. In that case only that note triggers and it plays at the default pitch. Note-off is ignored by the DSP (the amp EG is self-timed; it exists only for MIDI-out bookkeeping). Mute (a sequencer flag) also blocks MIDI notes.

*Presets*: a kit is one byte per sound parameter (init kit array = 254 bytes), saved as files on the SD card, plus patterns/songs/projects; a **morph** linearly interpolates two kits' 7-bit parameters one parameter per main-loop tick (`preset_morph_tick`), skipping audio routing.

*Tests / CI*: none in the repo.
