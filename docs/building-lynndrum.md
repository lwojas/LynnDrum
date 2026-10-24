# Building LynnDrum — report

How a 2020-era embedded drum-machine firmware (Erica Synths LXR) became a VST3 with a React UI, what the DSP actually does, what went
wrong on the way, which tricks worked, and what to reuse next time. Written 2026-10-24 after the first playable. Detail lives in the other
docs; this is the narrative and the lessons. Where a number is quoted it comes from `plugin.md`, `DEVIATIONS.md` or the study docs.

---

## 1. What exists

A macOS arm64 VST3 (and a standalone app) with:

- the LXR sound engine, **bit-exact** against the unmodified firmware code on 818 scripted scenarios (max |diff| = 0);
- the LXR step sequencer (7 tracks x up to 64 steps, flam, shift, probability, p-locks, shuffle, Euclid, roll, 64 patterns, song mode),
  bit-exact on 75 golden event streams, wrapped in a host-synced transport (start, locate and loop re-anchor to the host's 16th grid);
- 233 automatable sound parameters generated from the firmware's own tables, plus clean-room factory presets and user presets;
- a React/Tailwind UI in a JUCE WebView: mixer, tabbed sound deck (main synth with filter and envelope graphs, mod matrix, click,
  kit routing), step sequencer with pattern bank, p-lock editor, Euclid and roll, solo, real-unit readouts (Hz, ms, dB, notes, cents);
- tests: a reference-vs-derived null test, sequencer oracle tests, UBSan builds, multi-instance tests, host-layer tests, a hosted-bundle
  smoke test, preset and transport tests, and pluginval at strictness 5. The user ran each milestone in Ableton Live.

Not done and deliberately parked: kit-per-pattern, importing real LXR kit files (no hardware to compare against), morph, undo/redo.
Not yet checked: REAPER, a malloc-trap run of `processBlock`, CI for the plugin build, an ear audition of the factory kits by someone
other than the author, and the UI inside the real WKWebView as seen by the author (the user has seen it in Live).

---

## 2. The method in one page

The unusual part of this project is the order of work. Almost nothing was written before something could prove it right.

1. **Study first** (nine documents, no code): what the firmware does, its licence, which parts are portable, what is hardware-bound.
2. **Reference harness** (`Tools/ref-harness`): compile the *unmodified* upstream DSP and parameter handler on the Mac, behind a few
   shim headers, and render audio from scripts. This is the oracle. The same was done for the sequencer: it emits a logical event stream.
3. **Extract** (`Source/Engine/lxr_core`, `Source/Sequencer/lxr_seq`) by a *generator script* (`Tools/port/make_core.py`, `make_seq.py`)
   that applies asserted text edits to the upstream files. Gate: the null test must stay at max |diff| = 0.
4. **Host layer**: resampler, block scheduling, event offsets, transport anchoring — all tested without JUCE first.
5. **Plugin shell, parameters, presets, UI** on top, each step shipped to a DAW and tested before the next.

The consequence: when something sounded or behaved wrong, there were only two places it could be (the derived code, the host layer),
and the first had a proof of correctness. Debugging was bisection, not archaeology.

---

## 3. Architecture

```
 React UI (WebView)                       message thread                       audio thread
 ------------------                       --------------                       ------------
 knobs, steps, tabs  --JSON cmd-->  SeqBridge (UI-side mirror of  --SPSC-->  drain at block start
 readouts, canvas     <-state/telemetry-  whole bank, edit queue)   queue      |
                                                                               v
 host automation <-> JUCE APVTS <-------- parameter events at block start --> EngineHost
                                                                               |  lxrseq_tick (once per engine block)
                                                                               |  lxr_core: 64-frame engine blocks @ 44 140 Hz
                                                                               v
                                                              pull-based Kaiser resampler --> host rate, stereo
```

| Layer | Role | Notes |
|---|---|---|
| `lxr_core` (C) | the sound engine | state moved from file-scope globals into an `LxrEngine` struct; derived (GPL) |
| `lxr_seq` (C) | the sequencer | same technique in `LxrSeq`; the firmware's own 0.25 ms systick is *injected*, not reimplemented; derived (GPL) |
| `Source/Host` | resampler, `EngineHost`, `SeqBridge` | ours; no JUCE dependency, so unit-testable in isolation |
| `Source/Plugin` | JUCE shell, `PresetManager`, editor | parameters, transport hand-over, state, WebView |
| `Source/UI/web` | the UI | built into one `index.html`, committed, embedded as binary data |

Threading rules that held up: the UI never touches the engine; every edit is a small command on a lock-free SPSC queue (8192 entries,
overflow parked in a message-thread deque, so the producer never blocks and ordering survives); the audio thread publishes telemetry
(playhead, pattern, peaks) as a few atomic words; host parameter changes are delivered to the engine once per block.

---

## 4. How the DSP works

(Full treatment with measured numbers: `lxr-dsp.md`, `lxr-audio-flow.md`.)

**Two clocks.** Audio runs per sample in 64-frame blocks at a fixed **44 140 Hz** (1.4499 ms per block). Everything "slow" — envelopes,
LFOs, modulation writes, filter coefficient recompute, oscillator frequency — runs once per block at the control rate (~690 Hz). Time
constants are therefore "increment per block", tied to B = 64 and Fs = 44 140. This is why the plugin runs the engine at its native rate
and resamples, rather than changing the rate.

**Voices.** Six sound voices on seven sequencer tracks (the closed and open hi-hat tracks share one voice):
- three *drum* voices: two-operator FM (oscillator + modulator, half-wave FM), a pitch envelope with a snap stage, a click/transient layer;
- a *snare*: oscillator + noise with its own mix and filter, optional repeat-decay;
- a *cymbal* and a *hi-hat*: three oscillators plus two modulation oscillators, metallic by ring/FM interaction.

**Oscillators.** `uint32` phase accumulator, band-limited wavetables chosen per block from the frequency (with a documented quirk around
440 Hz where the table selection wraps). Frequency is constant inside a block, so a kick's pitch sweep is a staircase of 1.45 ms steps.

**Filter.** One zero-delay-feedback state-variable filter per voice (lowpass, highpass, band, notch, peak, ...). The cutoff curve is a
shaped mapping of the 7-bit value; resonance is clamped so it cannot self-oscillate into trouble.

**Envelopes.** Amplitude `SlopeEg2` (double precision; attack, decay, and a slope control that bends the curve with a rational shaper),
`DecayEg` for pitch, a snap EG for the transient. Parameter value 127 on a decay means "never decays". Time is `block time / increment`,
which is how the UI computes milliseconds.

**Modulation.** Each voice has one LFO and a velocity modulator; each can target any of 229 destinations. Writes happen in a fixed order
inside the control tick (reset targets, velocity, LFO, filter coefficients, per-voice EGs, per-voice audio) — the order is audible, so it
is preserved.

**Mixer and FX.** Six-voice mixer with per-voice drive, sample-rate reducer, pan and output routing, summed to two stereo buses (the plugin
sums them), plus a single FX slot (distortion, ring-mod, compressor, delay) fed by routing.

**Sequencer.** 96 PPQ, 24 sub-ticks per 16th, polled once per engine block as the firmware polled its systick. Per track: length, steps with
velocity/probability/note/flam/shift/two p-lock slots; shuffle delays only sub-tick 0 of odd steps (kept as the original, decision D8).
The firmware's integer tempo division means the real tempo is `60000/floor(60000/bpm)` (87 becomes 87.1); the host layer scales the
injected clock so the plugin still lands on the host grid.

---

## 5. Gotchas (all of these cost time)

| Gotcha | What happened | What fixed it |
|---|---|---|
| **Upstream constants lie** | A comment said 228 sound parameters; the real `END_OF_SOUND_PARAMETERS` is 247 | Compile the header to get the number; `_Static_assert` it |
| **Upstream bugs reproduced on purpose** | CC#0 / parameter 127 out-of-bounds write; Euclid length 16 stored as 0 then `% 0`; a shift by 64 | Patched in the harness where it was UB, registered in `DEVIATIONS.md`, kept bit-exact otherwise |
| **Hardware-isms** | `__attribute__((section))` rejected by Mach-O; ARM intrinsics; fp16; HAL RNG | Shim headers; empty `__attribute__` after system headers; seeded xorshift |
| **Globals to instances** | Turning file-scope state into struct members breaks every `foo` reference | Macros mapping the old identifier to a thread-local current instance (see 6.1) |
| **Macros hijack member names** | A struct field named like an upstream global became a macro expansion | `m_` prefix on members, `push_macro`, local renames |
| **Duplicate symbols across libraries** | `automationNode` existed in both libs; the crash looked like memory corruption | One definition per symbol, enforced by a link test |
| **CRLF upstream files** | Python diffs and rewrites changed bytes | Patches via shell `diff`; files read and written with `newline=''` |
| **Sanitizers** | ASan hung at startup on this setup | UBSan (minus alignment/bounds/shift-base where noted) |
| **Initial state mismatch** | A demo pattern in the bridge constructor left the UI mirror and engine out of sync | Constructor is empty; presets load as diffs through the queue |
| **`getSampleRate()` is 0 in tests** | Test hosts do not set it | The processor stores `currentRate` itself |
| **Regex on C tables** | Mod-target regex captured 241 entries instead of 229 | Restrict it to the array body, then assert the count |
| **Port clash in dev** | Another app was serving on the default Vite port; screenshots showed the wrong app | `--strictPort` on an unusual port; look at the screenshot, not just "no errors" |
| **A generated-file hazard** | An over-greedy edit clobbered `store.tsx` | Rewrite in full and let `tsc` judge |
| **Test-logic mistakes** | Tolerances, never-true equalities, stale default kits in old tests | Make tests assert what they claim (e.g. mute-wins-over-solo checked at audio level) |

Process gotchas worth remembering: downloading and running external binaries needs explicit permission (pluginval was granted
explicitly); pushing to the remote was authorised per request, not standing.

---

## 6. Clever solutions

**6.1 Instance-ising C by macro, with a generator.** Instead of rewriting thousands of lines to pass an engine pointer, every upstream
global identifier is `#define`d to a field of a thread-local "current instance" (`lxr_state.h`, `lxrseq_macros.h`), and the entry points set the current
instance. The derived files are *generated* from upstream by `make_core.py`/`make_seq.py`, whose edits are each asserted (if upstream
changes, the generator fails loudly). The diff to upstream stays small and reviewable, multiple instances and threads work, and
bit-exactness is preserved. Proof: `test_instances` (alone, interleaved, two threads).

**6.2 The oracle is the original code.** The harness compiles upstream *unmodified* (plus a handful of numbered patches) and the null test
compares sample by sample. "Does the port match" is a mechanical yes/no, not a listening session.

**6.3 Inject time, do not reimplement the clock.** The sequencer's clock is the firmware's own 0.25 ms systick, advanced by the host once per
engine block. All the delicate timing (shuffle, flam, swing) is therefore the original code. Host sync is a thin wrapper
(`lxrseq_start_at` re-anchors every track to `absolute_step % length`), tested with a scripted play head.

**6.4 A pull-based resampler instead of changing the engine rate.** The engine renders 64-frame blocks on demand as the resampler
(64-tap Kaiser polyphase, 1024 phases) pulls. Result: block-size independent (max |diff| = 0 for host blocks 1 to 4096), residual below
-108 dB at the common rates, and events can be applied at host sample offsets by splitting the host block.

**6.5 Generate everything that is a table.** `gen_params.py` builds the C++ parameter layout, the TypeScript parameter table, ids, ranges,
choice lists and defaults from the firmware's own datatype table and enum headers. 233 parameters were never typed by hand. A sweep test
drives every parameter to both ends of its domain with all voices triggered and checks the output stays finite and bounded.

**6.6 Let the engine produce the UI's numbers.** For readouts, a tiny C program (`Tools/params/readout_tables.c`) dumps the engine's own
mappings (attack, decay, cutoff Hz, Q, LFO Hz, detune, click pitch) as 128-entry tables into `readout.golden.json`, which the UI imports.
No formula is duplicated in TypeScript, so the display cannot drift from the sound. Only trivial closed forms (note to Hz, dB) live in the UI.

**6.7 Reuse the firmware's algorithms for UI features.** The Euclid preview runs the firmware's generator in a *scratch* sequencer instance
(possible only because of 6.1) and the preview is the real rhythm. Solo needed no sequencer change: the bridge sends the effective mute
`muted || (anySolo && !soloed)` through the existing mute path.

**6.8 Keep per-frame work out of React.** The playhead highlight is a `data-playing` attribute set directly on the step's DOM node, the meter is a
canvas driven by `requestAnimationFrame`, and low-rate values go through `useSyncExternalStore` selectors. Result: no re-render per
telemetry frame.

**6.9 One-file UI.** Vite plus `vite-plugin-singlefile` produces one committed `index.html`, embedded with `juce_add_binary_data` and served
by a resource provider. No loose assets, no path problems in the host, and the browser dev mock (`src/bridge.ts`) runs the same page without
the plugin, which made Playwright-driven checks cheap.

**6.10 Presets by stable ids and diffs.** Preset JSON stores parameters by lower-cased `PAR_` name, so renaming or reordering cannot break old
files; missing entries fall back to Init, out-of-range values are clamped, unknown schemas rejected. Plugin state is versioned (schemas
1 to 3 still load). Presets apply as diffs through the same queue as edits, so there is one path to test.

**6.11 Record every deviation.** `DEVIATIONS.md` lists each place the derived code differs from upstream, why, and which test pins it.
The licence story (`NOTICE.md`) and "what is faithful" are answered from one file.

---

## 7. What the design teaches

- **Embedded firmware is a good source for a plugin** when the DSP is block-based and state is mostly in a few structs: a fixed block size,
  explicit control-rate/audio-rate split and no dynamic allocation are exactly what a real-time plugin wants.
- **The hard parts were the seams, not the DSP**: sample-rate conversion, transport anchoring, parameter delivery timing, and the UI/audio
  boundary. The DSP was 'free' once the harness existed; the seams needed design.
- **Fidelity is a choice you can price.** Keeping the fixed rate, 7-bit parameters and once-per-block parameter delivery means no intra-block
  automation and no smoothing. That is a deliberate deviation list item (P2), not an accident.
- **Constraints can be features.** The firmware's integer tempo, its shuffle rule and its probability window are part of the feel;
  reproducing them (D8) gave the instrument its character and made the oracle meaningful.
- **A derived-GPL boundary is cheap if it is a directory**: derived code only in two folders, everything else ours. This made the licence
  statement short and truthful.

---

## 8. Insights for future plugins

A checklist distilled from this build; most of it applies to any plugin, not just ports.

**Before code**
1. Decide the correctness oracle first. Port: the original, compiled on the host. Original design: a slow, obvious reference implementation.
   Without an oracle, "sounds right" is the only test and it does not scale.
2. Write the licence/provenance statement and the deviations file on day one; keep them current.
3. List the hardware-bound or UB-prone parts of any source you reuse; those are where bugs will hide.

**Engine**
4. Keep the DSP core free of the framework (plain C or C++ with a small C API, no JUCE types). It is then testable by a script, a sanitizer
   build and a null test in seconds, and reusable in another host or in WebAssembly.
5. Make state instance-based from the start; test two instances interleaved and on two threads.
6. Choose the internal sample rate and block size deliberately; if they are fixed, put a good resampler at the boundary and test
   block-size independence (host blocks of 1 and 4096).
7. Parameter changes: decide where they land (block start, sample offset) and say so; test that the audio is identical for different host
   block sizes.

**Host layer**
8. Treat transport as a state machine you can script: start, stop, locate, loop wrap, tempo change. A fake `AudioPlayHead` plus assertions on
   trigger times found every anchoring bug before a DAW did.
9. UI to audio: commands on a lock-free queue, state mirrored on the UI side, telemetry back as atomics. Never share mutable state.
10. Ship a hosted-bundle test (load the actual `.vst3`, several rates and block sizes, MIDI, state round-trip, several instances) and run
    pluginval at a high strictness from the first working build, not at the end.

**Parameters and state**
11. Generate parameter tables from one source of truth (code, headers, a spreadsheet) and emit C++ and TypeScript from it. Give every
    parameter a stable string id before the first release.
12. Version the state from day one and keep loaders for old versions under test.

**UI**
13. A WebView UI works well if the page is a pure function of a small state plus a bridge with a mock implementation. Build against the mock in a
    plain browser; automate screenshots and console-error checks. Look at the pictures.
14. Anything that updates per frame (playhead, meters, scopes) bypasses the UI framework's render cycle: DOM attributes, canvas, or an external
    store with selectors.
15. Get displayed values from the engine, not from re-derived formulas.
16. Make the UI fluid from the first component; retrofitting layout is far more expensive than designing for it.

**Process**
17. Ship small vertical slices to a real DAW after each milestone; the user's "tested in Live, all green" after every step kept risk low.
18. Commit often, push only when asked, and record permission boundaries explicitly (external downloads, pushes).
19. When a test passes on the first try, ask whether it can fail. The solo audio test passed only because "soloing another track silences
    the kick" is checked as a *must be zero* case alongside the positive ones.

**On "it went smoothly"**: it did, mostly because of items 1, 4, 6.1 and 6.2. The friction listed in section 5 (stale constants upstream,
macro hijacks, duplicate symbols, a few self-inflicted test mistakes, one wrong-app screenshot) was real but each was caught by a test within
minutes, which is the point of the method.

---

## 9. Where things are

| Need | Look at |
|---|---|
| What is built, how to build and test | `docs/plugin.md` |
| Every difference from upstream | `DEVIATIONS.md` |
| Licence and derivation statement | `NOTICE.md`, `LICENSE` |
| How the DSP works (measured) | `docs/lxr-dsp.md`, `docs/lxr-audio-flow.md`, `docs/lxr-parameter-map.md` |
| The sequencer | `docs/lxr-sequencer.md` |
| The reference harness | `docs/ref-harness.md` |
| The original plan and decisions | `docs/README.md`, `docs/implementation-plan.md` |
| Parked work | end of `docs/plugin.md` |
