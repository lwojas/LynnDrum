# Proposed VST3 architecture

Guiding principle (from the brief): **preserve the DSP and instrument architecture; adapt the platform layer.**
All statements about the original refer to `lxr-architecture.md`, `lxr-dsp.md`, `lxr-audio-flow.md`.

---

## 1. What the source forces on the design

| Finding in the source | Design consequence |
|---|---|
| The engine is **global-state C** (`voiceArray[3]`, `snareVoice`, `hatVoice`, `cymbalVoice`, `fxBus`, `velocityModulators[6]`, `activeParameters[]`, `mixer_*` arrays, `FX_BUFFER`). | **Two plugin instances in one host process would share and corrupt this state.** The engine must be made *instance-based* (one `LxrEngine` struct per plugin instance). This is the single largest mechanical change. |
| Parameters can only be set through `midiParser_ccHandler` (CC switch with UI/seq/uart side effects). | Extract the *transform half* of the switch into `lxr_apply_param(engine, PAR, value)`. Discard the MIDI protocol half. |
| Modulation writes back through the same handler and relies on "reset targets every block". | Keep base values (host) separate from effective values (modulated); apply the original transforms to the effective ones. |
| Fixed **44 140 Hz**, fixed **64-frame** block baked into constants (EG increments, LFO, delay, compressor, RAT filter…). | Run the engine at its native rate and block size; adapt at the edges (§4). |
| int16 buses with saturating adds; `__QADD16`, `__SSAT`, `__PKHBT`, `__fp16`, ITCM/DTCM attributes, hardware TRNG, ADC faders, GPIO jack detect. | A small **platform shim** supplies these; hardware-only pieces are replaced (§5). |
| Event timing is quantised to the 64-frame block. | Our scheduler quantises the same way (§6) — that *is* the original behaviour. |
| VLAs (`int16_t buf[size]`) and `(int32_t*)int16_t*` aliasing. | Replace by fixed `[64]` arrays (VLAs are not portable to MSVC); build with `-fno-strict-aliasing` or `memcpy`. |

---

## 2. Layering

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ Source/Plugin        JUCE AudioProcessor / AudioProcessorEditor, bus layout, bypass, host info │
│   ├─ ParameterLayer      APVTS built from the generated parameter table                         │
│   ├─ StateManager        getState/setState, kit I/O (versioned ValueTree)                       │
│   ├─ EventScheduler      MidiBuffer + param deltas + UI events + SEQUENCER triggers → ordered   │
│   ├─ Sequencer (Source/Sequencer)  host-PPQ clock → sub-ticks → lxr_seq → triggers + p-locks    │
│   ├─ UiBridge            lock-free queues + meter/telemetry snapshot (no engine access from UI) │
│   └─ WebUI host          JUCE WebBrowserComponent + relays (see lxr-ui-architecture.md)         │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ Source/Engine        C++ façade  `LxrEngineHost`: tick loop, SR adapter, output FIFO            │
│   └─ lxr_engine.h    **C API** (no JUCE types):  create / reset / set_param / trigger / render  │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ Source/Engine/lxr_core   GPL-derived DSP: voices, osc, SVF, EGs, LFO, mod, mixer, FX            │
│ Source/Platform          hal_shim: intrinsics, PRNG, fp16, ITCM macros (replaces stm32 headers) │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

Rules:
- `lxr_core` and `Platform` **must compile without JUCE** and without the plugin headers. A CLI test renderer links only these.
- The UI never calls the engine. It talks to `ParameterLayer` (host-visible params) and `UiBridge` (non-parameter events). `PluginProcessor` is thin glue: it owns the objects and forwards `processBlock`.
- No `PluginProcessor`-resident instrument logic. The "instrument" is `lxr_core`.

### Engine C API (draft)

```c
typedef struct LxrEngine LxrEngine;
typedef struct { uint32_t seed; int ref_int16_mode; /* bit-exact int16 path */ } LxrConfig;

LxrEngine* lxr_create(const LxrConfig*);          // allocs (FX buffer etc.). NOT real-time safe.
void       lxr_destroy(LxrEngine*);
void       lxr_reset(LxrEngine*);                 // zero all DSP state, keep parameters
void       lxr_load_kit(LxrEngine*, const uint8_t par7[228]);          // set base values, re-derive all DSP state

// real-time-safe from here down, audio thread only ------------------------------------------------
void lxr_set_param(LxrEngine*, uint16_t par, uint8_t v7);              // base value (what the host/kit holds)
void lxr_set_fader(LxrEngine*, uint8_t voice, float gain);             // hardware-fader replacement (not in kit)
void lxr_set_mute(LxrEngine*, uint8_t track, uint8_t mute);
void lxr_set_override(LxrEngine*, uint8_t track, uint16_t par, uint8_t v7);   // sequencer p-lock: replaces the base value of `par` (per voice/track) until cleared
void lxr_clear_override(LxrEngine*, uint8_t track, uint16_t par);          // restores the base value
void lxr_set_bpm(LxrEngine*, float bpm);                               // LFO sync
void lxr_trigger(LxrEngine*, uint8_t track /*0..6*/, uint8_t note, uint8_t vel);   // 6 = open hat on the hat voice
void lxr_render_block(LxrEngine*, float outL[64], float outR[64], LxrAux* aux /*optional*/);   // exactly ONE engine tick
```

Implementation notes: `LxrEngine` aggregates what are today file-scope globals; each existing `Foo_calc*(…)` that touched a global gains an `LxrEngine*` (or a pointer to the sub-struct it needs). The lower-level DSP (`OscInfo`, `ResonantFilter`, `SlopeEg2`, `Delay`, …) already takes struct pointers and needs no change.

---

## 3. Parameters, automation, thread safety

### 3.1 Single parameter table

`Source/Parameters/lxr_params.json` (one row per sound parameter, ~200 rows) → generated `lxr_params.h/.cpp`, the APVTS layout, the UI metadata (`WebUI/src/generated/params.ts`) and the docs. It extends Appendix A of `lxr-parameter-map.md` with display functions (Hz/ms/dB strings), default values (from a *clean-room* init kit — not the upstream `initKit`, see licence notes), and groups.

### 3.2 Parameter flow (the boundary the brief asked for)

```
 DAW automation ─┐
 Plugin UI ──────┼─► APVTS (host-visible, 127-step normalised values, atomics)
 State restore ──┘            │
                              │  (audio thread, start of processBlock: poll each parameter's raw atomic;
                              │   compare with last applied 7-bit value; emit SetParam events)
                              ▼
                     EventScheduler  (fixed-capacity, pre-allocated, time-ordered)
                              │      + SEQUENCER triggers/p-locks (host-PPQ sub-ticks)  + MidiBuffer notes (sample offsets)  + UI events (audition pad, kit load, mute, pattern edits) from a SPSC FIFO
                              ▼
                     engine tick loop  →  lxr_set_param / lxr_set_override / lxr_trigger  →  lxr_render_block
                              ▼
        modulation stage inside the engine: effective = base ⊕ (LFO, velocity) → transforms (the ccHandler "recipes")
```

- **Quantisation:** host values are `round(norm·127)`. `AudioParameterFloat` with interval `1/127` makes the host/UI present exactly the 128 hardware steps; automation curves are therefore faithful to what a kit can express. (Smoother automation is a *Phase 9* option.)
- **Sample-accuracy:** JUCE delivers parameter changes at block granularity; the engine applies them at tick granularity (≤ 1.45 ms). Nothing is lost relative to the original, which applied everything at block boundaries.
- **No UI → DSP callbacks.** UI writes parameters via relays → APVTS. Non-parameter UI gestures (pad audition, kit load) are posted to a lock-free SPSC queue with fixed-size POD messages.
- **State loading** (`setStateInformation`, message thread): parse into a `KitSnapshot` (228 bytes + fader/mute/mode flags), publish via a double-buffered atomic pointer; the audio thread picks it up at the next tick and calls `lxr_load_kit`. No engine access from the message thread.
- **Telemetry to the UI** (meters, voice activity, EG phase for the graph "dots"): audio thread writes into a fixed struct of atomics; the UI polls at 30–60 Hz via the bridge. Never any callback into JS from the audio thread.
- **Modulation vs host parameters:** the engine's effective values never feed back to APVTS (the original *did* overwrite and restore the stored value every block — see porting notes). The UI can show modulated position via telemetry.

### 3.3 Real-time rules

`prepareToPlay` allocates everything (engine, FX buffer, resampler, queues). `processBlock`: no allocation, no locks, no file/UI/JS access, no `std::function`, no exceptions. `juce::ScopedNoDenormals` plus the engine's own FTZ-style guard. `logf/expf/sqrtf` appear in the compressor and pan code: acceptable.

---

## 4. Sample rate and block size

**Finding:** the engine fundamentally assumes `Fs = 44140 Hz` and `B = 64`. (Both are used in ~40 places plus precomputed constants; see `lxr-dsp.md` §3.5 for the inventory.)

### Options

| Option | How | Pros | Cons |
|---|---|---|---|
| **A. Fixed engine rate + resampler at the edge** *(recommended for the prototype)* | Engine runs at 44 140 Hz in 64-frame ticks; output is resampled to host rate (and the tick clock is derived from the host sample counter) | Bit-exact vs reference at the engine output; zero DSP changes; envelope, LFO, filter, delay timings *exactly* as hardware; trivially testable. | One resampler (CPU, latency). The resampler's quality becomes part of the sound. |
| **B. Parametrise the engine by host rate** | Replace `REAL_FS` and block constants by runtime values; the control tick becomes `64·Fs_host/44140` (non-integer) or keep integer blocks and re-derive increments | No resampler; potentially lower latency | Touches every time-based constant; changes oscillator aliasing character (wavetable choice is rate-dependent), delay/compressor/RAT filter coefficients; not null-testable against the reference. High regression risk. |
| **C. Oversample the engine to the nearest multiple** | Not applicable: 44 140 is not an integer divisor/multiple of 48/96/88.2 k. | — | — |

### Recommendation

**A for the prototype.** *Do not use JUCE's `LagrangeInterpolator`/linear* (alias/imaging at 1–3 kHz+ would be audible in hat/cymbal). Requirements to put in the test plan:

- ≥ 96 dB stop-band rejection, passband flat to ≥ 0.45·min(Fs_in, Fs_out) (or 20 kHz), linear-phase or minimum-phase *documented*;
- ratio support 44 140 → {44 100, 48 000, 88 200, 96 000, 176 400, 192 000}; at `Fs_host == 44 140` bypass;
- latency reported through `setLatencySamples` (polyphase sinc ≈ 32–64 host samples) and **compensated for event timestamps** (§6) so note-on → sound delay remains ≤ ~3 ms;
- a candidate with a permissive licence compatible with GPLv3 (e.g. r8brain-free-src, MIT) or our own windowed-sinc polyphase.

Because the engine output is mostly < 20 kHz but includes aliased content (noise, FM, tables), resampling is a plain bandlimited interpolation of a 44.14 kHz signal; there is nothing special to "preserve" beyond not adding artefacts. *Note 44 100 vs 44 140:* the hardware's real rate is 44 140 (`REAL_FS` comment: the prescaler cannot hit 44 100). Running the engine at 44 100 and calling it equal would detune by 1.57 cents and alter all time constants by 0.09 %. Treated as a deliberate **adaptation to document, not to make silently**: A uses 44 140 and resamples even at host 44 100.

**B is a Phase 9 experiment** ("native-rate mode"), gated behind a flag, validated by envelope-timing and spectral tests, never by null.

**Block size:** the host block is arbitrary. The façade keeps a ring FIFO of engine output frames and renders ticks on demand until the host block is satisfied (a classic fixed-block adapter). Engine events are timestamped in engine ticks (§6).

---

## 5. Platform adaptation

| Original | In the plugin | Class |
|---|---|---|
| `stm32f7xx_hal.h`, ARM intrinsics (`__QADD16`, `__SSAT`, `__PKHBT`, `__CLZ`), `APSR` | `Platform/arm_shim.h`: portable exact emulations, unit-tested against the ARM definitions | adapt (shim) |
| `INDTCM`, `INDTCMZ`, `IN_ITCM_RAM` | empty macros | remove |
| `__fp16 FX_BUFFER[32768]` | `uint16_t` storage with software half↔float (round-to-nearest-even, as the ARM conversion); per-instance, allocated in `lxr_create` | adapt |
| Hardware TRNG (`GetRngValue`) | seedable `xorshift32` (deterministic for tests; statistically white) | replace |
| `FPU->FPDSCR.FZ` | `ScopedNoDenormals` | replace |
| Static globals | `LxrEngine` instance members | adapt (mechanical, pervasive) |
| VLAs, strict-aliasing casts | fixed arrays; `memcpy`/`-fno-strict-aliasing` | adapt |
| `(uint32_t)negative_float` in FM | explicit `fm_phase_offset(float x)` helper with saturate-to-0 semantic (documented, test-covered), because x86-64 would otherwise differ | adapt (preserves behaviour) |
| `adc_getFaderVolume(v)` | `fader[v]` (parameter) | replace |
| `mixer_checkOutJackAvailable`, `switch_*` GPIO | removed (all jacks "connected") | remove |
| `seq_getBpm()` in `lfo.c` | `lxr_set_bpm` fed from host `AudioPlayHead` | replace |
| `voiceControl_*` MIDI-out bookkeeping, `uart_sendFrontpanelByte`, `seq_*` calls inside `voiceControl_noteOn` | removed | remove |
| **Sequencer logic** (`sequencer.c` data model, flam/shift/probability, p-locks, pattern/song) | `Source/Sequencer/lxr_seq` — in v1, see `lxr-sequencer.md` | adapt (logic kept, clock replaced) |
| Sequencer ms-clock, MIDI-clock slave, MTC, LED/MIDI-out bookkeeping | host-PPQ `SeqClock`/`SeqTransport` | replace |
| SD presets, LCD/menu/LED/buttons/encoders, USB/DIN MIDI | not carried over | remove |
| I2S/DMA/ISRs/`bCurrentSampleValid` | `processBlock` + façade FIFO | replace |
| 16-bit output, no master stage | **ref mode**: emulate int16 truncations/saturations (bit-exact); **float mode** (later): float path with the same clip points | adapt, selectable |

Two numeric modes are worth having from day one:

1. **Reference mode** — all int16 conversions, saturation and truncation reproduced exactly; used for null tests against the host harness build of the original source.
2. **Plugin mode** — same maths; int16 bus rounding replaced by float where it removes the 16-bit noise floor *only if tests show it is inaudible and the user opts in*. Default = reference mode until proven otherwise. (The brief asks us not to "improve" before the reference is established.)

---

## 6. MIDI and events

- **Input:** JUCE `MidiBuffer` (note on, velocity; CC/pitch bend ignored in v1; MIDI clock not needed — the host provides tempo/position).
- **Voice mapping (adaptation):** the hardware maps *MIDI channel → voice*; note number = pitch. A DAW wants *note → pad*. Support both, default **note map** (`PAR_MIDI_NOTE n` semantics: trigger voice n at default pitch when that note arrives): voices 0–5 on notes 36–41 and open hat (track 6) on 42 — editable. **Channel mode** reproduces the hardware (note number = tuning offset relative to 60).
- **Velocity:** 7-bit, passed straight through. Note-off: ignored (as in the original; amp EGs are self-timed).
- **Timing:** an event at host sample offset *s* is mapped to engine time `s_engine = (blockStart + s)·44140/Fs_host − latencyComp` and executed at the **start of the tick that contains it**. This is exactly the original's "applied at the next block boundary" semantics, jitter ≤ 1.45 ms. A sub-tick "sample-accurate trigger" mode is deliberately *not* offered: it would break the EG/phase relationships of the reference (control-rate state advances once per tick).
- **Mute:** applies to both sequencer and MIDI in the original; implement as engine mute flag (`lxr_set_mute`). **Solo** and per-voice output busses are plugin-shell additions (mixer only; no DSP change).
- **Transport/tempo:** the host transport (position, tempo, play state) drives the **sequencer clock** (§10) and `lxr_set_bpm(host bpm)` per block keeps LFO sync consistent.
- **Bypass:** host bypass → output silence, events dropped, voices not advanced; on un-bypass `lxr_reset` voices (tails not preserved). Documented adaptation.

---

## 7. Buses and outputs

- v1: one stereo output (`St1` + FX return summed as the hardware does when routed to the same destination). `St2`/`L1`/`R1`/`L2`/`R2` destinations are mapped to **aux output buses** (JUCE additional stereo output buses, disabled by default) in v1.1; until then, all routings fold to the main stereo out (documented, since folding changes pan/level for mono destinations).
- No audio input (the firmware has none in this build; `USE_DAC2` selects the second DAC instead of an ADC).

---

## 8. State and presets

- **Plugin state** = versioned `ValueTree`: `schema`, `params` (APVTS), `faders`, `mutes`, `noteMap`, `mode flags`, `sequencer` (PatternSet + song, binary blob). Parameters serialise as normalised floats (APVTS default) *and* are re-snapped to 7-bit on load so state ↔ engine are always consistent.
- **Kit I/O:** a 228-byte kit buffer (+ name) is the interchange unit. Importing real LXR kit files requires the SD kit format (`presetManager.c`, not yet read); marked as a later task.
- **Factory presets:** must be *clean-room* (own sound design). The upstream `initKit` has unknown provenance (`hrtlkits_batch3.zip`).
- **Morph:** the original blends two kits' 7-bit values stepwise. In a plugin this is a UI feature with an engine-side blend of two `KitSnapshot`s before `lxr_load_kit`/`set_param` (Phase B).

---

## 9. Project structure

```
LynnDrum/                               (git root; the upstream clone is vendored read-only or a submodule pinned to a43cd4f)
  CMakeLists.txt
  docs/                                 this study
  Reference/lxr-desktop-app/            pristine upstream (never edited, never linked into the plugin)
  third_party/JUCE/                     submodule
  Source/
    Plugin/        PluginProcessor, PluginEditor, WebViewBridge, StateManager
    Parameters/    lxr_params.json (source of truth), generator, APVTS layout, kit snapshot
    Engine/        lxr_engine.h (C API), EngineHost (tick loop, SR adapter, FIFO), Resampler
    Engine/lxr_core/   ← **category 1: GPL-derived**, one file per upstream file, headers preserved, DEVIATIONS.md
    Platform/      arm_shim.h, half.h, prng.h
    MIDI/          NoteMap, ChannelMap, EventScheduler
    Sequencer/     lxr_seq/ (GPL-derived sequencer logic), SeqClock, SeqTransport, SeqBridge  — see lxr-sequencer.md
  WebUI/           Vite + React + Tailwind source, dist/ (embedded by CMake into BinaryData/zip)
  Tests/           unit (Catch2), golden renders, null/diff harness, CLI renderer
  Tools/
    ref-harness/   builds UNMODIFIED upstream DSP + CC handler on the host with stubs → golden audio
    paramgen/      lxr_params.json → C++/TS
    compare/       null test, spectra, envelope-timing, CPU
```

The `Reference/` ↔ `lxr_core/` split is the licensing boundary (`lxr-architecture.md` §1.4). Everything under `Source/Engine/lxr_core` is a *covered work*; the rest of the repo is ours but is combined into a GPL-3 binary.

---

## 10. Sequencer (in scope — first-class module)

Decision (2026-10-24): the step sequencer is part of the product's USP and ships in the first playable. The full spec is **`lxr-sequencer.md`**; the architectural consequences are:

- `Source/Sequencer/lxr_seq` (GPL-derived logic: step/flam/shift masks, probability window, p-lock handling, pattern/song switching, Euclid) is a **separate library, no JUCE, no globals, no wall clock**. One instance per plugin instance, advanced one **sub-tick** (1/96 beat; 24 per 16th) at a time.
- `SeqClock`/`SeqTransport` (ours) derive sub-tick boundaries with exact sample offsets from `AudioPlayHead` (host-sync) or an internal sample counter (free-run); they replace the original's 0.25 ms systick clock, MIDI-clock slave and MTC.
- The sequencer emits `Trigger{track, note, vol, plocks[2]}` into the **same `EventScheduler`** as MIDI notes; the engine cannot tell the source (as in the original, where both end in `voiceControl_noteOn`). Scheduler timestamps are quantised to engine ticks (≤ 1.45 ms), the same granularity as the original.
- P-locks use the engine's **override** API (`lxr_set_override / lxr_clear_override`), not `set_param`: an override replaces the base value of a parameter until cleared; this reproduces the original's "write live value, restore stored original on next destination change" without touching host-visible parameters.
- Sequencer data (up to ≈ 230 kB) lives in the plugin state; edits flow UI → audio thread as **commands** over a lock-free SPSC queue; the UI keeps a mirrored copy (no shared mutable pattern memory); playhead/step telemetry flows back through the telemetry snapshot.
- Host-automatable sequencer controls (small set): run/hold, pattern select, shuffle, track mutes, per-voice roll hold.
- Transport rules and the position model (anchoring of step counters so loop/locate stay phase-correct) are in `lxr-sequencer.md` §4.2.
