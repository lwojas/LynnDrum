# Implementation plan (revised 2026-10-24)

**What changed in this revision:** the step sequencer is now a first-class deliverable (main USP) with its own track of work (stages S0–S3) and is part of the first playable; the product name is **LynnDrum**; CC-BY transient samples are kept and attributed; the project is destined to be free and open source (GPL-3 accepted); there is no hardware reference, so validation is against the source and online references; the UI is fluid/responsive from the first component (fixed window is only a starting convenience).

Order is chosen so that **correctness of the engine is established before any plugin or UI work**, and so that every later layer can be validated against a fixed reference. Effort figures are rough single-engineer estimates (working days) with wide error bars; they are for sequencing, not commitment.

## 0. Decisions

| # | Decision | Status |
|---|---|---|
| D1 | Product name / branding | **Resolved:** "LynnDrum" for now. No "LXR"/"Erica Synths" in name, UI header or window title; truthful derivation statement in About/credits (NOTICE §7(e)). |
| D2 | Ground truth | **Resolved:** no hardware. Validate against (a) the source via the host harness, (b) online references (published LXR demos/manual/community notes) for *plausibility*, never as null tests. |
| D3 | Distribution intent | **Resolved:** free and open source → GPL-3 for the whole plugin is accepted. |
| D4 | Sequencer in first playable? | **Resolved: yes** (USP). See §1 stages S0–S3 and `lxr-sequencer.md`. |
| D5 | Window | **Resolved:** fixed size is acceptable to start, but the layout is fluid from day one (`lxr-ui-architecture.md` §6). |
| D6 | Transient sample licence | **Resolved:** keep and attribute (CC BY 4.0 as reported; verify page manually). |
| D7 | `guideline.md` | Still outstanding; UI work can start from the mockup. |
| D8 | Pattern-change commit semantics (S6), roll granularity, per-track choke fix, free-run mode defaults | Open — decide when S1/S2 results are in. |

## 1. Phases, milestones, dependencies

Two parallel tracks that meet in integration: the **engine track** (P1 → P2 → P4 → P5 → P6) and the **sequencer track** (S0 → S1 → S2 → S3). The UI track (P7) starts early on mocks.

```
P0 ✔ ─► P1 Ref harness ─► P2 Engine extraction ───────────► P4 Integration ─► P5 Params ─► P6 State ─┬─► P8 Validation ─► P9 Refinement
            │                       └► P3 JUCE shell (parallel) ─► P4                                  │
            └► S0 Seq harness ─► S1 Seq core (lxr_seq) ─► S2 Seq clock/transport/edits ─► S3 Patterns/song ┘   (S2 joins at P4; S3 after P6)
                                                                    P7 UI: spike after P3; deck on mocks after S1; full bind after P5/S2
```

### Phase 0 — Source and licence analysis *(✔ study done; actions remain)*
Deliverables: the docs (now ten, incl. `lxr-sequencer.md`). Remaining non-engineering actions: verify the CC-BY page by hand and prepare the attribution text; draft the NOTICE/CREDITS and About text; add `LICENSE` (GPL-3.0-only, matching upstream) and per-file headers policy for `lxr_core`/`lxr_seq`.

### Phase 1 — Reference environment (host harness) *(M1)*
**Goal:** build the *unmodified* upstream DSP + CC handler on the host and render audio from a script, deterministically.
- `Tools/ref-harness/`: shim headers first on the include path (`stm32f7xx_hal.h`, `main.h`; `__QADD16/__SSAT/__PKHBT/__CLZ/APSR`, `__fp16` or software half, `FPU->FPDSCR`, `HAL_RNG_*` → seeded xorshift), plus a stub TU for the menu/UART/USB/preset/adc symbols that `MidiParser.c`, `MidiVoiceControl.c`, `DrumVoice.c` etc. reference (≈ 40–60 symbols; the `lxr_dsp` OBJECT-library boundary in `Core/CMakeLists.txt` is the natural cut).
- CLI `lxr_ref_render`: script (kit bytes, `ccHandler` writes, notes by block index, faders, BPM) → calls `midiParser_ccHandler` / `voiceControl_noteOn` / `mixer_calcNextSampleBlock` as the firmware does → 44 140 Hz stereo WAV (int16 + float) + per-block parameter trace.
- Only edits to upstream bytes: `.patch` files for the padded wavetable guard and the PRNG seed.
**Exit:** identical WAVs on macOS arm64 and Linux x86-64, or a documented difference (the negative-float cast, fixed by an explicit saturating helper and registered). **Complexity:** M (4–7 d). **Risks:** hidden hardware dependencies (GPIO reads in the mixer, `adc_*`, `systick_ticks`), ARM-only constructs. **Dependencies:** none.

### Stage S0 — Sequencer harness *(M1b, right after P1; overlaps P2)*
**Goal:** a deterministic oracle for the sequencer, and answers to the open items in `lxr-sequencer.md` §9.
- Extend the harness to compile `sequencer.c`, `clockSync.c`, `EuklidGenerator.c`, `automationNode.c` with stubs for LEDs/UART/menu/trigger-out and an **injected** `systick_ticks` (advanced explicitly) and injected RNG.
- CLI `lxr_ref_seq`: script (pattern data, track lengths, shuffle, BPM, mute, roll, pattern switches) → logical event stream `(sub-tick index, track, note, vol, p-lock writes)` + the audio via the engine path.
- Resolve: systick unit (0.25 ms), shuffle formula and "odd step", `choke*` coupling, roll mapping, pattern-switch semantics, p-lock vs modulation ordering.
**Exit:** golden event streams for ≥ 30 scripted scenarios; the open items are answered (or explicitly accepted as unknown). **Complexity:** M (4–6 d). **Risks:** more hardware entanglement (menu/LED calls inside `seq_nextStep`) than expected → mitigated by stubs; resist editing upstream.

### Phase 2 — Engine extraction / adaptation *(M2)*
**Goal:** the instrument produces sound without JUCE, via a clean C API, bit-exact to the harness.
1. Copy files per porting §1.1 into `Source/Engine/lxr_core` (headers intact, one commit per group).
2. Introduce `LxrEngine` (globals → members; voices as an array of 6 type-tagged descriptors where it removes duplication, per-type code paths kept). Mechanical changes only: engine pointer, remove `INDTCM/ITCM`, VLAs → `[64]`, intrinsics/PRNG/fp16 → `Platform/`.
3. Extract `lxr_apply_param` from `ccHandler`; base / override / effective split for modulation and p-locks; `lxr_trigger`; `lxr_render_block`.
4. `Tools/compare` null tester; CLI `lxr_render`.
**Exit:** **max |diff| = 0** vs the harness for every golden scenario (T0), reference mode, 44 140 Hz; registered deviations pinned by tests. **Complexity:** L (10–15 d). **Risks:** control-tick ordering; the modulation/override rewrite; instance-ising touches every file. **Dependencies:** P1.

### Stage S1 — Sequencer core (`lxr_seq`) *(M2b)*
**Goal:** the sequencer *logic* as an instance-based, JUCE-free library, bit-exact (in logical events) to S0's oracle.
- Port `PatternSet`, step/timing structs, main-step bitmaps, flam/shift mask builders, 3-slot probability window, `seq_nextStep`/`seq_processFlam` driven by an explicit **sub-tick index**, p-lock node logic against the override API, track lengths (incl. polymetric master track), Euclid, rotation, mute, roll. Pattern/song switching stubs (S3).
- API sketch: `seq_create/destroy/reset`, `seq_set_*` edit calls, `seq_advance(state, subTickIndex, TriggerSink*)`, `seq_start/stop/locate(stepCounter)`.
**Exit:** T0 on the event streams for all S0 scenarios (reference mode includes the shared `choke*` state); property tests for flam/shift mask algebra; fuzz (random patterns/edits, no UB under ASan/UBSan). **Complexity:** M (6–9 d). **Dependencies:** S0 (oracle), P2 steps 1–3 (override API).

### Phase 3 — JUCE plugin shell *(M3, parallel with late P2)*
Minimal VST3: stereo out, MIDI in, APVTS with 2 dummy params, a sine "engine", `pluginval` ≥ 5, state save/load, bypass, multiple instances; JUCE 8.x, CMake. **Exit:** passes pluginval; loads in target DAW(s); no allocations in `processBlock` (malloc-trap build). **Complexity:** S (2–3 d).

### Stage S2 — Sequencer clock, transport, edits, bridge *(M4b, with P4)*
- `SeqClock`: `AudioPlayHead` PPQ → 96-PPQ sub-tick boundaries with sample offsets (tempo changes, loops, locates, time-signature agnostic, hosts without position info → free-run); `SeqTransport`: host-sync + free-run, position anchoring (`lxr-sequencer.md` §4.2); shuffle in the PPQ domain.
- Sequencer triggers + p-lock overrides into the `EventScheduler`; latency compensation identical to MIDI.
- `SeqBridge`: lock-free edit-command queue (UI → audio), mirrored UI copy, playhead telemetry; state serialisation of the `PatternSet`; host-automatable sequencer controls (run/hold, pattern select, shuffle, mutes, roll hold).
**Exit:** (T0) with the clock fed the S0 sub-tick stream, plugin-rendered audio equals the harness; (T2) trigger sample-offset error ≤ 1 engine tick vs host PPQ at 44.1/48/96 kHz, block sizes 1…4096, tempo ramps, loop/locate/stop/start; no allocation/locks; state round-trip. **Complexity:** M–L (7–10 d). **Risks:** hosts with irregular `AudioPlayHead` data; position-anchoring bugs on locate/loop; shuffle-in-PPQ equivalence (S5). **Dependencies:** S1, P3, P4.

### Phase 4 — Engine integration *(M4)*
`EngineHost`: tick loop, output FIFO, resampler (44 140 → host), `EventScheduler` with tick-quantised timestamps, note map / channel mode, tempo, bypass, latency reporting.
**Exit:** at host 44 140 Hz (resampler bypassed) plugin output equals `lxr_render` bit-exactly; at 44.1/48/88.2/96/192 kHz metrics within tolerance (T2); note-on-to-sound latency documented. **Complexity:** M (5–8 d; resampler selection dominates). **Risks:** resampler quality/latency; block sizes not multiples of 64; timestamp mapping with latency compensation. **Dependencies:** P2, P3.

### Phase 5 — Parameters and automation *(M5)*
Generated parameter table (from Appendix A) + display functions + defaults; APVTS layout (127-step floats, choices, bools); audio-thread polling → `lxr_set_param`; generated modulation-destination lists (also used for p-lock destinations); per-voice `fader`/`mute`; automation round-trip tests; kit snapshot.
**Exit:** all ≈200 parameters automatable and audible; each parameter verified by a sweep test against the harness (T0 per parameter); pluginval automation tests pass. **Complexity:** M (5–8 d). **Risk:** table errors → generate and test, never hand-write.

### Phase 6 — State and presets *(M6)*
Versioned state (`ValueTree`): params, faders, mutes, note map, **sequencer `PatternSet`** (S2), UI size; `KitSnapshot` double-buffered hand-off; kit save/load (`.lynnkit` = 228 bytes + name + schema); **clean-room** factory kits and a few factory patterns; preset-browser data model. Optional: LXR kit/pattern importer (needs `presetManager.c` reading — unresolved #6).
**Exit:** save → reload → render bit-identical (including patterns); old-schema states load; DAW project reload. **Complexity:** S–M (3–5 d).

### Stage S3 — Patterns, song, Euclid, roll, kit-per-pattern *(M6b)*
64 patterns, copy/clear, chaining and song mode (`SONG_END/LOOP`), pattern switching at master wrap from UI/automation/pattern-select, Euclid generator UI path, live roll (step-boundary granularity, faithful), per-pattern kit snapshots (kit switch on pattern change), undo/redo on the command log.
**Exit:** T0 event streams for pattern/song scenarios; switching during flam/shift cases; state round-trip with 64 patterns. **Complexity:** M (5–8 d). **Dependencies:** S2, P6.

### Phase 7 — UI *(M7, fluid from the start)*
7a. **WebView spike** (after P3): knob + meter in two DAWs; go/no-go. 7b. Mock-bridge dev environment + Playwright diffs against `screen.png` **at the design size and the responsive matrix** (`lxr-ui-architecture.md` §6.4). 7c. Mixer rack, header (LynnDrum branding, kit name, meter, BPM/sync/swing, transport), the four synth modules, fluid layout rules in every component. 7d. **Sequencer deck** (developed on a simulated playhead after S1; bound to the bridge after S2): step lane, inspector (volume/prob/note/flam/shift/p-locks), track length/rotation, bar tabs, pattern select, transport/sync. 7e. Mod/routing tabs. 7f. Click/transient tab. 7g. About/credits (derivation statement, CC-BY attribution, GPL notice). 7h. Polish vs `guideline.md`.
**Complexity:** L–XL (20–30 d incl. the deck). **Risks:** WebView/host quirks; scope creep from mockup-only controls; responsive regressions (mitigated by the screenshot matrix in CI). **Dependencies:** P3 (spike), P5/S2 for real binding.

### Phase 8 — Validation *(M8)*
Run the full catalogue (§3) on all targets: DAW matrix, CPU/profile, soak/fuzz, multi-instance, sample-rate sweep, transport/loop abuse for the sequencer, automation stress; produce the deviation register and the "plausibility vs online references" notes (informal listening against published LXR demos, clearly labelled as not a null test). **Complexity:** M (5–8 d, partly continuous). **Exit:** all T0 green, every deviation registered and justified.

### Phase 9 — Refinement (only after M8)
Opt-in candidates with their own tests: float-path "plugin mode", native-rate mode, sample-accurate trigger offsets, clean band-limiting vs the 440-Hz wrap, `rec`-table guard fix, full-wave FM, per-track choke fix, MIDI-record (S-C), Morph, aux outputs, FX chain / tempo-synced delay, reverb port, mockup-only controls (feedback, sends, 24 dB filter), pattern import from LXR projects, sub-tick roll.

## 2. Suggested order of implementation

1. **P1** reference harness, then **S0** sequencer harness (both are the oracles).
2. **P2** (DrumVoice + mixer first, then Snare, HiHat, Cymbal, FX) and **S1** in parallel — each behind its bit-exact gate.
3. **P3** shell in parallel; UI spike (7a) as soon as P3 exists.
4. **P4 + S2** together (this is when the plugin first plays a pattern in a DAW).
5. **P5 → P6**, then **S3**.
6. UI: deck on mocks from S1 onward; full binding after P5/S2. P8 continuously; P9 last.

**First playable prototype (end of P4+P5+S2, with P6 save/restore and UI panels 7c/7d):** MIDI notes and the **step sequencer** both trigger six voices (+ open hat); sequencer with 7 tracks × 64 steps, per-track length, probability, flam, shift, p-locks, shuffle, host-sync/free-run, one active pattern (switching by command); all ≈200 sound parameters automatable and saved together with the patterns; stereo out at any host rate; bypass; reference numeric mode; one global FX slot; fluid UI with mixer, synth modules and sequencer deck. *Patterns 2–64/song mode/Euclid/roll arrive in S3.*

**Explicitly not yet:** Morph, LXR kit/pattern-file import, reverb, FX chain or tempo-synced delay, aux/multi-out buses, float mode, native-rate mode, sample-accurate trigger offsets, MIDI/clock sync from external devices, MIDI-record, any DSP or sequencer "improvement" (including the per-track choke fix) before M8, and UI elements with no engine counterpart.

## 3. Testing and validation strategy

### 3.1 Three tiers (intentional ≠ accidental)

| Tier | Meaning | Criterion |
|---|---|---|
| **T0 — bit-exact** | Reference mode, 44 140 Hz, same seed/script | `max|diff| == 0` between `lxr_core` and the harness build of upstream, and (P4) between the plugin and `lxr_core`. For the sequencer: **identical logical event streams** (sub-tick index, track, note, vol, p-lock writes) between `lxr_seq` and S0's oracle. |
| **T1 — registered deviation** | Each intentional difference in `DEVIATIONS.md` (PRNG, table-10 guard, cast helper, fp16 implementation, S1–S7 for the sequencer, …) | A test asserts the *specific, expected* difference. No deviation without a test. |
| **T2 — metric equivalence** | Where bit-exactness is impossible by design (host sample rate ≠ 44 140, resampler, PPQ vs wall-clock timing) | Quantities within pre-written tolerances: pitch (cents), decay time (%), spectral envelope (dB/band), filter response (dB), delay time (samples), LFO rate (%), latency (ms), **sequencer trigger timing (≤ 1 engine tick from the ideal PPQ position)**. |

There is no T3 (hardware recordings) for now (D2). Online references are used for sanity listening and for sanity-checking numbers (e.g. documented parameter ranges), recorded in the validation notes, never as pass/fail criteria.

### 3.2 Test catalogue

| Area | Tests |
|---|---|
| Oscillators | FFT peak vs expected frequency per wave/note/coarse/fine/pitch-EG snapshot; start-phase tests; table selection vectors incl. <440 Hz wrap and band edges; noise statistics; PWM; FM depth (sine vs table carrier; negative-modulator cast). |
| Envelopes | Decay/attack sweep 0…127 vs closed form, slope sweep, repeat EG, retrigger mid-decay, parameter change while running, infinite-decay case, drum-vs-snare/hat gain ramp behaviour. |
| Filters | Impulse/noise response per type vs analytic TPT (and vs harness for the nonlinear path), cutoff/Q sweeps, drive, reset-on-trigger, NaN/instability fuzz. |
| Modulation | LFO rate/wave/sync, retrigger, phase offset, S&H wrap; velocity latch; destination restore; multi-writer order; **override (p-lock) vs modulation order**. |
| Voices / mixer / FX | Trigger/retrigger transients per type; hat choke; transient types; mute; velocity; pan latch; decimator; pan law; saturation; routing; FX impulse/static-curve tests; delay crossfade; compressor curve. |
| **Sequencer** | Event-stream T0 for: step on/off, volume/note, probability (injected RNG; and statistical test with seeded RNG), flam ×2…×8, shift −7…+7, flam+shift overlaps, `choke*` behaviour, track lengths 1…64 incl. polymetric master track, rotation, Euclid, shuffle, roll (step-boundary), mute mid-pattern, p-lock set/clear/restore, pattern switch at master wrap (S3), song loop/end (S3). T2: transport start/stop/locate/loop, tempo ramps, odd time signatures, hosts without position info → free-run, block sizes 1…4096, latency compensation alignment with MIDI. Robustness: edit-command fuzz during playback; queue overflow behaviour; state round-trip with full patterns. |
| Events | A trigger at host offset *s* lands on the next engine tick boundary; block sizes 1, 32, 64, 65, 128, 480, 1024, 4096; mid-block automation. |
| Platform | Intrinsic emulations vs ARM definitions (exhaustive for 16-bit); half conversions; PRNG distribution; denormals. |
| Robustness | Random-parameter/event fuzz (no NaN/Inf, no allocation, bounded output); long soak; multi-instance isolation; state round-trip. |
| Performance | ns/block per voice type and total; worst-case kit + dense pattern; CPU % in a DAW at 44.1/48/96 k; resampler cost; sequencer cost per sub-tick. |
| Plugin | `pluginval` ≥ 5; state recall; automation read/write; bypass; latency report vs measured. |
| UI | Playwright screenshot diff vs mockup at the design size; responsive matrix (800×560 … 1920×1080: no overflow, min control size, sequencer geometry); relay round-trip with a mocked bridge; gesture begin/end ordering; command-queue ordering for pattern edits. |

### 3.3 Distinguishing intentional adaptation from accidental divergence
1. Every change from upstream goes into `DEVIATIONS.md` (ID, rationale, files, pinning test).
2. The null tester prints the first differing sample/event, block, voice or track, and the last parameter/edit write before it (from the harness trace).
3. T0 scenarios are generated from the **parameter table** (one sweep per parameter per voice) and from a **pattern generator** (random but seeded patterns) plus hand-written musical cases.
4. CI runs T0 on every commit (harnesses are cheap).

## 4. Major risks

| Risk | Impact | Mitigation |
|---|---|---|
| **GPL-3 / open-source release** | Settled by decision D3 | Keep per-file headers, publish source, NOTICE/CREDITS, About text; keep `Reference/` separate |
| **Trademark / marking terms** (NOTICE §7) | Naming/credits constraints | Name = LynnDrum; truthful derivation statement; no Erica Synths logos; revisit if the name changes |
| **Third-party assets** (CC-BY transient sample; unknown `initKit`) | Attribution duty / unknown provenance | Attribute (D6); clean-room factory kits; verify other transient tables' sources |
| **Sequencer harness effort and unknowns** (shuffle, `choke*`, clock units) | Port diverges musically | S0 before S1; accept "unknown but pinned" as a recorded decision, never silent |
| **Host transport variety** (no PPQ, tempo jumps, loops) | Sequencer drifts/misplaces steps | Position-anchoring design, free-run fallback, T2 transport tests, DAW matrix |
| **Resampler quality/latency** | Artefacts/latency disputes | Requirements + T2 tests; bypass at 44 140 |
| **Instance-ising a global-state engine** | Large mechanical diff; ordering mistakes | One voice type at a time behind bit-exact gates |
| **Modulation/override rewrite** | Divergence in the most intricate subsystem | Original transform bodies kept; dedicated T0 scenarios; order verified on the harness |
| **Undefined behaviour in the original** | Platform-dependent sound | Explicit helpers, padded tables, cross-platform CI |
| **WebView in hosts** | Unstable UI | Early spike; generic host UI fallback; lazy creation |
| **Responsive UI regressions** | Layout breaks at some sizes | Fluid rules from component #1; screenshot matrix in CI |
| **UI scope creep** (mockup-only controls) | Time sink, divergence from engine | Per-control decision table in the UI doc; extensions only in Phase 9 |
| **Parameter table errors** | Silent wrong destinations | Generate from sources; per-parameter sweep tests |
| **No hardware ground truth** | "Sounds like the LXR" = "matches the source" | Stated openly; online references for sanity only |
| **Reading gaps** (pattern-edit helpers, recording quantiser, kit-file format, mod-destination setters, reverb) | Surprises later | Scheduled reads before the phase that needs them (S0/S3/P6); listed in porting notes §4 |

## 5. Assumptions to validate before implementation

1. The shipping firmware = this source with these build flags.
2. Half-wave FM (negative → 0) is real (P1 harness).
3. 44 140 Hz is the real I2S rate (no hardware: accept the code's claim; flag if online references contradict it).
4. `systick_ticks` = 0.25 ms (S0).
5. The CC-BY attribution requirements are as reported (manual page check).
6. JUCE 8 WebView relays/resource provider behave in the target hosts.
7. 7-bit parameter resolution is acceptable for host automation.
8. `AudioPlayHead` data (PPQ, tempo, play state) is available in the target hosts, with free-run as the fallback.
9. Upstream licence terms at the pinned commit are as stated (re-check at release).
