# Plugin shell, host layer and first playable pieces (P3 + P4 + S2-lite)

Status 2026-10-24. Everything here builds with the top-level `CMakeLists.txt` (JUCE 8.0.9 is fetched at configure time).

```
cmake -S . -B build-lynn && cmake --build build-lynn -j8          # VST3 + Standalone + tests
build-lynn/Tools/host_tests/host_tests                            # JUCE-free host-layer tests
build-lynn/Source/Plugin/plugin_tests/plugin_smoke_artefacts/Release/plugin_smoke \
    build-lynn/Source/Plugin/LynnDrum_artefacts/Release/VST3/LynnDrum.vst3   # loads the real bundle like a host
build-lynn/Tools/host_tests/host_tests --demo demo.wav            # 4 bars of the authored demo beat
```

## Layers

| Layer | Where | Role |
|---|---|---|
| `lxr_core`, `lxr_seq` | `Source/Engine`, `Source/Sequencer` | derived GPL code (bit-exact vs the oracle) |
| `lynn::Resampler` | `Source/Host/Resampler.*` | pull-based 64-tap Kaiser (beta 9) polyphase sinc, 1024 phases, engine 44 140 Hz -> any host rate; gain error < 0.001 %, residual < -108 dB at 44.1/48/88.2/96/192 kHz |
| `lynn::EngineHost` | `Source/Host/EngineHost.*` | owns engine + sequencer, splits a host block at event offsets, renders 64-frame engine blocks on demand, sums DAC1+DAC2, applies master gain; one `lxrseq_tick` per engine block (the firmware loop) |
| `LynnDrumProcessor` | `Source/Plugin` | JUCE shell: stereo out, MIDI in, parameters, transport/tempo hand-over, state |

## Behaviour

- **Events** (MIDI notes, sequencer run/stop) are applied at the host sample offset; they reach the sound at the next engine block boundary plus the resampler look-ahead. Reported plugin latency = `ceil((32 + 64) / ratio)` host samples (96 @ 44.1 k, 105 @ 48 k, 209 @ 96 k). Measured note-to-sound delay stays below the reported latency (host tests).
- **Block-size independence**: identical audio for host blocks 1, 7, 32, 65, 128, 480, 1024, 4096 (max |diff| = 0).
- **Sequencer transport**: `Seq Sync = Host` follows `isPlaying`, tempo and PPQ position; `Free` uses `Seq Run` and `Tempo` and starts at step 0. In host mode a start, a locate/jump while playing and a loop wrap **re-anchor** the sequencer to the host's 16th-note grid (`lxrseq_start_at`: every track plays step `absolute_step % track_length`, sub-tick phase and swing parity included), so starting mid-song, jumping around and looping odd lengths stay phase-correct, also for polymetric tracks.
- **Tempo (finding, deviation S8)**: the sequencer core computes `seq_deltaT = (1000*60)/bpm` with an **integer division**, so the LXR actually runs at `60000/floor(60000/bpm)` BPM (e.g. "87" is 87.1, "140" is 140.2). The host layer scales the injected clock by `hostBpm / thatEffectiveBpm`, so fractional host tempos land on the host grid with no drift. Measured: kick on every beat, 16 bars, tempos 87…140.0 at 44.1/48/96 kHz, any block size -> deviation from the host grid within two engine blocks (≈ 2.9 ms), no accumulation.
- **MIDI map** (default): 36 Drum 1, 41 Drum 2, 43 Drum 3, 38 Snare, 49 Cymbal, 42 Closed hat, 46 Open hat.
- **Parameters** so far: Master, 7 voice levels (= the hardware fader multiplier), Seq Sync, Seq Run (Free), Tempo (Free). 233 sound parameters (generated, see below) in per-voice groups, plus FX.
- **Sound source**: clean-room factory presets (see *Presets* below). The upstream `initKit` is no longer used by the plugin or the host tests (only by the reference harness comparison).
- Loudness: the engine is loud by design (hardware headroom is the kit designer's job); the demo beat touches 0 dBFS at Master = 1.

## Validation done

`host_tests` (resampler quality at 5 rates, block independence, event latency, 12 sequencer grid cases), `plugin_smoke` (bundle loads; 3 rates × 6 block sizes incl. 1 and 4096 with MIDI; no NaN/Inf, sane level; state round-trip by parameter name; 3 interleaved instances; free-run sequencer produces sound). **pluginval, strictness level 5: SUCCESS** (2026-10-24, VST3 build; includes plugin state, automation at 44.1/48/96 kHz × 64…1024, editor, bus layouts; the VST3 SDK validator and auval steps were skipped by the tool as not configured). Not yet done: DAW load test (Live 12 / REAPER are installed), malloc-trap check of `processBlock`, bypass handling, AU.

## UI (phase 7 first slice, 2026-10-24)

React 18 + TypeScript + Tailwind (tokens from the concept) in `Source/UI/web`, built by `Tools/ui/build.sh` (Vite + vite-plugin-singlefile) into **one** `dist/index.html` that is committed and embedded with `juce_add_binary_data`; the editor is a JUCE `WebBrowserComponent` (WKWebView) serving it through the resource provider. Resizable 900×600 … 2400×1600, default 1300×860, layout is fluid (grid/flex, `clamp()`).

Contents: header (LynnDrum, Host/Free sync, run, BPM, master), voice matrix & mixer (7 strips: select, level fader bound to the `faderN` parameters, mute), sound-deck frame (voice banner + four module panels - **empty until the parameter phase**), step-sequencer deck (7 tracks × up to 64 steps in bars of 16: toggle, per-step volume bar, probability/note/flam/shift inspector, track length, swing, clear/copy/paste/random, per-track playhead).

Plumbing:
- Host-automatable parameters (`master`, `tempo`, `faderN`, `seqRun`, `seqSync`) use JUCE web relays/attachments (gesture begin/end, automation both ways).
- Pattern edits: JSON commands `["step",track,idx,on]`… → `SeqBridge::applyUiCommand` (message thread: updates the mirror, enqueues) → lock-free SPSC queue (8192 entries, overflow parked in a message-thread deque) → `SeqBridge::drain` at the start of `processBlock` → `lxrseq_*`. The mirror is what the editor shows and what is stored in the plugin state (`pattern`, base64 of a compact schema-1 blob); a restore re-sends everything through the same queue.
- Playhead: the audio thread publishes one atomic word per block (step index of each track + running); a 30 Hz timer emits it to the page.
- Browser development: `cd Source/UI/web && npm run dev` runs the page against a mock bridge (`src/bridge.ts`), no plugin needed; Playwright screenshots work against `npm run preview`.

Verified: `tsc` strict, Vite build, headless-browser render without console errors at 1300×860 and 960×640, `host_tests` (bridge command → sequencer, clear/length, state round-trip, queue overflow ordering), pluginval level 5 with the editor open (SUCCESS). **Not verified: how it looks inside the real WKWebView** (no screen-capture permission in the authoring session) - please look at it in Live.
Known gaps: no pan/solo/drive/send (parameter phase), p-lock editing, pattern select/chain/song, Euclid, roll, kit browser/morph, level meter, undo/redo, accessibility pass.

## Parameter phase (P5, 2026-10-24)

`Tools/params/gen_params.py` -> `Source/Plugin/GeneratedParams.h` (C++) and `Source/UI/web/src/params.generated.ts` (UI), from the pinned upstream: enumerator values are compiled from `Parameters.h`; ranges/types from `parameter_dtypes[]` (`menu.c`, positional - checked against the table's own comments), choice lists from `MenuText.h`, voice grouping from `menuPages.h`, mod-target list from `Cc2Text.c`, defaults from the kit.
Result: **233 automatable sound parameters** (Drum 1/2/3 37 each, Snare 36, Cymbal 37, Hi-hat 37, FX 11, Global 1) in VST3 parameter groups, + 229 modulation targets. Host edits -> `EngineHost` `Param` / `ModTarget` events at the start of the next block -> `lxr_param` / `lxr_set_mod_target`.

UI: knob (vertical drag, shift = fine, double-click = default, bipolar arcs for ±63 params), select, switch; the sound deck shows the five groups of the selected voice (OSC & FM, Filter, Envelopes, LFO & velocity, output row) and the global FX bus strip. CH and OH both edit the Hi-hat group (open/closed decay each shown for its own track).

Tests added: generated table vs engine (mod-target count, defaults in range), all 233 parameters driven to both ends of their domain with all voices triggered stays finite and bounded, hosted-bundle test (Drum 1 / Volume = 0 silences the kick), pluginval level 5.
Not done: filter / envelope graphs (needs analytic curves of the real SVF/EG), MOD MATRIX / SAMPLE / KIT ROUTING tabs, parameter value text in dB/Hz (raw 0-127 shown), kit save/load (P6), solo.

## Presets and state (P6, 2026-10-24)

**Preset** = a kit (all 233 sound parameters by stable id) + an optional step pattern, one small JSON file (`*.lynnpreset`, schema 1; `Presets/factory/` for the shipped ones, embedded via BinaryData; user presets in `~/Library/Application Support/LynnDrum/Presets`). Missing kit entries fall back to the Init defaults, out-of-range values are clamped, wrong step indices are skipped, unknown schemas are rejected. Loading goes through the normal host-parameter path (the host sees every change) and replaces the pattern through the sequencer bridge.

- **Factory presets** (clean-room, `Tools/kits/make_factory.py`; defaults of all parameters = the *Init* preset, so `gen_params.py` reads `Presets/factory/init.lynnpreset`): Init, Tight 4/4, Deep Backbeat, Metal Broken. Authored with the formulas of `docs/lxr-dsp.md` and checked by measurement (`Presets/factory/README.md`: level, -40 dB decay, dominant pitch, brightness per voice; patterns peak at -6 dBFS and do not clip). **Not auditioned by ear.**
- **Plugin state** schema 2: parameters, pattern (compact blob), current preset name/factory flag/dirty flag; schema-1 states (earlier builds) still load. A fresh instance starts on *Tight 4/4*.
- **UI**: preset bar in the header (previous/next, list with Factory/User groups, `*MOD` dirty marker, Save / Save As / Delete for user presets; factory names are reserved). Dirty = any sound parameter or pattern edit since the load.
- Not done yet: kit-only / pattern-only load, import of real LXR kit files (the SD format is unread), preset folders/tags, morph.

Tests: `preset_tests` (processor class driven directly: factory list and contents, every factory preset reproduces its kit, dirty tracking, save→load round trip is exact, name rules, delete, malformed/sloppy documents, state round-trip incl. schema 1 and garbage), plus the earlier suites. The host tests no longer need any upstream kit.

## Audition, meter, transport anchoring, step selection (2026-10-24, after the first Live tests)

- **Audition**: every mixer strip has a ▶ pad, clicking a voice name selects *and* plays it, keys **1-7** play voices 1-7, and the sound deck has a big **AUDITION** button plus **AUTO** (re-triggers the voice whenever a sound control is released: tweak a knob, hear it). Path: UI -> `lynn_audition` -> `SeqBridge` queue -> `lxr_trigger` at the start of the next block.
- **Output meter** (stereo peak with fall-back, dB readout) in the header; peaks are taken from the real output in `processBlock` and polled at 30 Hz.
- **Step selection**: click a step: empty -> turned on and selected; on but not selected -> selected; on and selected -> turned off. Shift-click / right-click only select. (The old behaviour toggled on every click.)
- **Transport anchoring** (S2): new `lxrseq_start_at`; `processBlock` emits `SeqRun`/`SeqLocate` with the host PPQ on start, on a jump larger than 0.03 beat, and at the sample where a loop wraps inside a block. Verified with a scripted play head (`transport_tests`): start at 0.75 beat -> first kick 1.626 s (ideal 1.625), start on the bar fires at once, fractional start, locate during playback (0.876 vs 0.875 s), a 2-beat loop restarts the bar every loop (6 kicks in 6 s, 1.000 s apart), stop/restart elsewhere.

## Pattern bank (2026-10-24)

64 patterns in 4 banks (A-D) of 16: the sequencer deck has a pattern bar (click = edit it **and** play it next - queued to the end of the bar while running, immediate while stopped; shift-click = edit only; FOLLOW makes the edit view track the playing pattern; copy / paste / clear whole patterns), a SONG toggle and a song editor (up to 64 entries, END / LOOP, current position highlighted). Each pattern has its own steps, track lengths and swing; mutes are global. Pattern edits no longer get lost when the sequencer leaves a pattern (deviation Q9 / S6: upstream restores a "backup buffer" over the pattern being left).
Factory presets now come with two patterns each (a main pattern and a variation/fill) and a short song (`Presets/factory/README.md`).
Verified with the scripted host: select while playing switches at the bar end (kick on the new pattern's step 9 at 3.006 s, not before), song 1,2,loop plays 0.006 / 3.006 / 4.005 s as expected; bridge tests for addressing, copy/clear pattern, song state, state round-trip with several patterns, a stale-engine restore, and queue overflow.
Still open: kit-per-pattern (`kitNr`), pattern chaining via the LXR "next pattern / repeat" settings (the song covers it), Euclid and roll UI, p-lock editing.

## P-lock editing (2026-10-24)

Every step has two p-lock slots: a destination (any plain sound parameter, grouped by voice with the selected track's own voice first; velocity/LFO target selectors are excluded) and a value (slider, or a list for choice parameters). The step shows a cyan **P-LCK** tag. Semantics are the firmware's: the lock is written through the parameter handler right before the step triggers, **kept until the track's next trigger**, and then the previous destination is restored to its stored base value (so locking a parameter does not change the kit; a following step without a lock restores it). The engine smooths some parameters (voice volume takes ~100 ms), so a locked volume fades rather than jumps; pitch/FM/filter/envelope locks act at once.
Plumbing: UI `stepLock` command -> mirror -> `SeqCommand::Step` (carries the four lock bytes) -> `lxrseq_set_plock` with the cortex destination numbering (`PAR+1` below 127, raw above). Presets store `lock1` / `lock2` as `[par, value]`; state schema 3 adds the four bytes per step (schema 2 and 1 still load). Factory *Metal Broken* demonstrates it (an FM-amount lock on the second kick, a resonant filter lock on the backbeat snare).
Verified: command -> sequencer data (both numbering ranges, clear, bad slot/parameter rejected), end to end through the sequencer (a pitch-mod lock removes the sweep of the locked hit only; the next hit is bit-for-bit the unlocked sound), preset and state round trips.

## Euclid and roll (2026-10-24)

- **Euclid** (deck button *EUCLID*): length (1-64), steps, rotation for the selected voice of the viewed pattern, a live preview of the rhythm and APPLY. The rhythm comes from the **firmware's own generator**: the bridge runs it in a private scratch sequencer instance (the derived code keeps its state in the instance, so the audio thread is never touched), then replaces the track's steps and length through the normal command path (steps that stay on keep their settings, new ones get volume 100). Checked against the oracle's recorded masks (16/5 = 0x1249, 16/7 rot 3 = 0xA54A, 13/5, 32/9) and the 64-step rotation case that the unguarded upstream shift would have erased (H8). Length 16 is stored as 16 (upstream stored 0, Q8).
- **Roll** (deck button *ROLL* + rate list): hold to retrigger the selected voice at 1/16, 1/8, 1/4, 1/2 or 1 bar (every 1, 2, 4, 8, 16 steps, on step boundaries, velocity 100, the step's note - the firmware's rule); *one-shot* or a stopped sequencer fire once per press. Releasing the pointer anywhere ends the roll. Not saved in presets (performance control). Measured through the engine: 1 s of hold at 120 BPM gives 8 hits at 1/16, 4 at 1/8, 1 in one-shot.
