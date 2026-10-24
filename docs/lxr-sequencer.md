# Sequencer — scope, original behaviour, and plugin design

**Status:** added 2026-10-24 after the decision that the step sequencer is part of the product's main USP and belongs in the first playable (not a later phase).
Source: `Core/Src/Soundengine/Sequencer/{sequencer.c, clockSync.c, EuklidGenerator.c}`, `Inc/Preset/SeqStep.h`, `DSPAudio/automationNode.c`. I read the clock, `seq_nextStep`,
`seq_processFlam`, flam/shift pattern builders, probability window, automation path, pattern/song switching and roll. I did **not** read the pattern-editing UI helpers (copy/paste/clear
implementations, recording quantiser `seq_addNote`, MIDI-record paths) or the Euclid maths beyond its interface. Items needing the reference build are listed in §9.

---

## 1. Data model (as implemented)

| Entity | Definition |
|---|---|
| Tracks | **7** (`NUM_TRACKS`): voices 0–5 plus track 6 = **open hi-hat** (same hat voice, long decay) |
| Steps | **64** per pattern per track (`NUM_STEPS`), as **4 bars × 16** (`NUM_BARS` = 4; the active-step bitmap is a `uint64`/4×`uint16` union) |
| Patterns | **64** (`NUM_PATTERN`); each carries `length[track]` (per-track length, 0 ⇒ 16), `shuffle`, `kitNr` |
| Step (`Step`) | `volume` (7 bit; bit 7 = active in some paths), `prob` (1…100), `note` (7 bit), `param1Nr/param1Val`, `param2Nr/param2Val` (the **p-locks**, 7-bit; `0xff` = none) |
| Step timing (`StepTiming`) | `flam:4` (0 off, 1 ×2, 2 ×3, 3 ×4, 4 ×6, 5 ×8) and `shift:4` (index 0…14 → **−7…+7**; 7 = none) |
| Main-step bitmap | `seq_mainSteps[bar][pattern][track]` — one bit per step: step on/off |
| Song | `seq_songData[kit slot][MAX_SONG_LENGTH = 64]` of pattern numbers; `SONG_END` (64) / `SONG_LOOP` (65) sentinels |
| Memory | `PatternSet` ≈ 64·7·64·(7 + 1) B ≈ **229 kB** + bitmaps — trivial for a desktop plugin; stored in plugin state (compressed) |

All values are 7-bit by construction (MIDI-era). The port keeps these ranges.

## 2. Original timing model

```
 systick_ticks        TIM14 free-running timer, 0.25 ms units (4 kHz)  [inferred: prescaler 13500/period 1; the ×4 in seq_calcDeltaT and the /4 in sync_calcBpm only make sense with 0.25 ms ticks]
 internal clock       96 PPQ.  subTickPeriod(ticks) = (60000/bpm)/96 × 4          → bpm here is the real BPM
 sub-tick             24 per 16th-note step  (seq_prescaleCounter 0…23);  step = 24 sub-ticks = 1/4 beat
 seq_tick()           polled once per audio block (1.45 ms) from the TIM2 ISR/main loop.   On each elapsed sub-tick period:
                        if counter == 0 and internal clock: seq_nextStep()      // advances every track's stepIndex, handles pattern switch at master wrap
                        seq_processFlam(counter)                                 // fires triggers whose bit (23-counter) is set
                        counter = (counter+1) % 24                               // elapsed-time remainder carried into the next period ("rest")
 shuffle              odd steps are delayed: after sub-tick 22 the next period is lengthened by  shuffle·subTick·16  and the following period shortened by the same amount
 external MIDI clock  24 PPQN; every 6th pulse = master step (seq_nextStep); sub-ticks between pulses are upscaled by the internal clock (96 PPQ)
```

Quantisation of the original: sub-tick events are polled per audio block, so a trigger is delayed to the next block boundary (≤ 1.45 ms) and then to the next engine tick for the voice
(same boundary). **Net timing resolution ≈ 1.45 ms with jitter**, not sample-accurate.

## 3. Trigger logic

`seq_nextStep()` per track: `stepIndex++`; wrap at `length[track]` (or 64); skip if the track is muted; if the main-step bit is set, **draw a random number** for the probability window:

```
rnd.prev ← rnd.current;  rnd.current ← rnd.next;  rnd.next ← GetRng() % 100 + 1        // 1…100
```

`seq_processFlam(idx)` for each sub-tick `idx` ∈ 0…23, per non-muted track, with `cur`, `next = (cur+1) % length`, `prev = (cur−1) wrap`:

```
mask(step, pos):               // 24-bit mask, bit (23-idx) ⇒ trigger at sub-tick idx
   if step's main bit is off → 0
   if rnd[pos] > step.prob   → 0                         // pos = prev/current/next uses the matching entry of the 3-slot window
   m = flamPattern(step.flam)                            // off:1@0   ×2: 0,12   ×3: 0,8,16   ×4: 0,6,12,18   ×6: 0,4,…,20   ×8: 0,3,…,21
   s = 3 · shift(step.shift)  (−21…+21 sub-ticks)
   s == 0: CURRENT → m;   PREV, NEXT → 0
   s  > 0: PREV → (m << (24−s)) & 0xFFFFFF   (tail that spilled into this step)   CURRENT → m >> s    NEXT → 0
   s  < 0: NEXT → m >> (24−|s|)               (head pulled back from next step)    CURRENT → m << |s|  PREV → 0
fire:  if mask(next)[idx]: trigger(next-step data), chokeNext = 1
       elif mask(cur)[idx] and !chokeNext: trigger(cur data), chokeCurrent = 1
       elif mask(prev)[idx] and !chokeNext and !chokeCurrent: trigger(prev data)
       elif lastWasNoteOn: lastWasNoteOn = 0; noteOff(track)                     // MIDI-out bookkeeping only
```

Observations that matter for a faithful port: priority is **next > current > prev** *per track per sub-tick* (a shifted-back note from the next step wins over the current one); `chokeNext/chokeCurrent` are **file-scope variables shared across all tracks and all sub-ticks of a step**: they are reset only when `idx == 0` (once per step, before the track loop) and then stay set. So once *any* track fires a shifted-back (`next`) note, `current`/`prev` triggers on **every** track are suppressed for the remainder of that step; likewise a fired `current` suppresses later `prev` triggers on all tracks. This looks unintended (it was presumably meant to be per track) but is the reference behaviour; port it faithfully (reference mode) and register it as a deviation candidate for a per-track fix (**[verify]** on the sequencer harness before deciding).

`seq_triggerVoice(track, vol, note)`: parse the step's p-locks → `voiceControl_noteOff(track)` → `voiceControl_noteOn(track, note, vol)` → MIDI-out bookkeeping.

**P-locks (automation nodes)**: two `AutomationNode`s per track. At each trigger: `setDestination(node, step.paramNr)` — if the *previous* destination differs it is **restored to its stored original value**; then `updateValue(node, step.paramVal)` pushes the value through the same parameter handler (`ccHandler`) as a live write. So a p-lock acts from its trigger until the track's next trigger replaces or clears it, and it does not alter the stored kit value. (`param1Nr == 0xff` clears.) Port: p-lock = *per-track base-value override* applied through `lxr_apply_param` with the override mask; restoring = re-applying the base.

**Roll**: while a roll button is held, at each `seq_nextStep` the track retriggers whenever `stepIndex % seq_rollRate == 0` (`seq_rollRate` = 1/16 → every step, 1/8 → every 2nd, 1/4 → every 4th, 1/2 → every 8th, 1/1 → every 16th; the code stores `{0,1,3,7,15}+1`). So **roll granularity is whole steps at step boundaries**, not sub-ticks. Velocity is fixed `ROLL_VOLUME = 100`, the note is the step's note, and rolled notes can be recorded; with the sequencer stopped (or rate = one-shot) a press triggers once. **Euclid**: `euklid_calcRecursive(length, steps, …)` (Bjorklund) writes the main-step bitmap for the active track; rotation by `PAR_EUKLID_ROTATION`. **Track rotation** (`PAR_TRACK_ROTATION`) shifts the track.

**Patterns/songs**: patterns switch only when the **master track (the longest) wraps** (`masterStepPos == 0`); `seq_pendingPattern` is applied then (`seq_setPendingPatternActive` resets all `stepIndex`es and loads kit/shuffle of the new pattern). Song mode advances `seq_songPositionPointer`; `SONG_END` stops, `SONG_LOOP` restarts. A pattern carries a `kitNr` (kit change with pattern — in the plugin: kit snapshot switch, Phase S3).

## 4. Plugin design (what we build)

### 4.1 Module boundaries

```
 Source/Sequencer/
   lxr_seq/            (GPL-derived, category 1)  PatternSet, step/flam/shift masks, probability window, p-lock logic, pattern/song switching, euclid
   SeqClock            (ours)  host-PPQ / free-run → sub-tick boundaries with sample offsets
   SeqTransport        (ours)  start/stop/continue/locate handling, anchoring of step counters
   SeqBridge           (ours)  edit commands (UI → audio thread), playhead telemetry (audio → UI)
```

`lxr_seq` has **no JUCE, no wall clock, no globals**: `SeqState` is an instance member; the single entry point is
`seq_advance(SeqState*, uint32_t subTickIndex, TriggerSink*)` called once per 1/96-beat sub-tick in order. It emits `Trigger{track, note, vol, plocks[2]}` into the sink — the **same
`EventScheduler`** that handles MIDI notes. The engine never knows whether a trigger came from MIDI or the sequencer (as in the original: both end in `voiceControl_noteOn`).

### 4.2 Clock (the part we replace)

| Original | Plugin |
|---|---|
| 96 PPQ internal clock from `systick_ticks` (0.25 ms) | **Host PPQ** from `AudioPlayHead` (`ppqPosition`, `isPlaying`, `bpm`, time signature), converted to the 96-PPQ sub-tick grid; each sub-tick boundary inside a host block gets an exact **sample offset** |
| Poll once per 1.45 ms block | Evaluate every sub-tick boundary in the block, in order, each with a timestamp |
| Event → next block boundary | Timestamp → **engine tick boundary** (same quantisation as the original; ≤ 1.45 ms, deterministic) |
| Start/stop buttons, MTC | Host transport. Two modes: **Host-sync** (default; position = host ppq; plays when the host plays) and **Free-run** (own start/stop button, internal sample counter at host tempo; for hosts that never start transport or for jamming) |
| MIDI-clock slave, clock sync averaging | Dropped (host provides tempo/position) |
| Shuffle by lengthening periods | Shuffle expressed in the PPQ domain: odd steps start `shuffle·16/24` of a step later (derived from `seq_calcDeltaT`; **[verify]**), flam/shift offsets measured from that moved step start |
| Pattern switch at master-track wrap | Same rule, evaluated at the step boundary |

**Position model.** The original counts steps from start; the sequencer is *relative* to its start. In host-sync mode we keep `stepCounter` anchored at transport start / any playhead discontinuity (locate, loop) so that `stepIndex[track] = (stepCounter − anchor) mod length[track]`. Loop-playing a 4-bar region in the DAW then stays phase-correct for any track length, including polymetric ones. Locating mid-pattern recomputes the indices (the original never needed this).

**Latency.** Engine and resampler latency (see `lxr-vst-architecture.md` §4) delays *sound* but the sequencer runs on host time; the event scheduler subtracts the reported latency compensation exactly as for MIDI so that the sequencer and live MIDI stay aligned.

### 4.3 Parameters and state

- Sequencer values are **not** part of the 228-row sound-parameter table. They form a second set: **global** (`BPM` read-only/host, `Shuffle`, `Run mode`, `Sync`, `Roll rate`, `Active pattern`, `Pattern chain/song`), **per-track** (length, rotation, mute), **per-step** (volume, prob, note, flam, shift, p-lock 1/2). Per-step data lives in the plugin state (binary blob in the `ValueTree`), **not** as host parameters (hundreds of thousands of automation lanes make no sense).
- Host-automatable subset (new, small): `Seq Run/Hold`, `Pattern select` (0–63), `Shuffle`, track mutes, `Roll` hold per voice. These are APVTS parameters that feed the sequencer through the event queue.
- Pattern edits come from the UI via a lock-free SPSC queue of **edit commands** (`SetStep`, `ClearTrack`, `CopyTrack`, `Euclid`, `SetLength`, …) applied by the audio thread at a sub-tick boundary; the UI reads pattern data from a mirrored **UI-side copy** updated from the same commands (single writer per direction, no shared mutable pattern memory).
- State save: whole `PatternSet` (+ song, kit slots later), schema-versioned. Undo/redo is a UI feature built on the command log (nice-to-have).

### 4.4 UI mapping (mockup deck)

| Mockup | Sequencer feature |
|---|---|
| 16 pads, bar tabs 1–4 | 64 steps = 4 bars × 16, per track |
| TRIG | main step on; step volume = pad level (a second row/lane shows volume, as the mockup's bottom bar) |
| P-LCK badge, "P-LOCKS: ACTIVE (24 MODS)" | step has p-lock 1/2 (destination from the same `modTargets` list as LFO/velocity) |
| ROLL / FLAM | step `flam` (×2…×8) and live roll rate / hold; the mockup shows "ROLL 2x" on a step = flam ×2 |
| LOCK | (mockup) p-lock-only step — in the engine a step with a p-lock but no trigger **does not exist**: p-locks apply only at triggers. Show LOCK as "trig with p-lock" or drop |
| ACC | no accent concept — map to step volume or remove |
| RANDOM | randomise main steps/probability; Euclid generator is the faithful analogue |
| CLEAR / COPY / PASTE | `seq_clearTrack`, `seq_copyTrack`, pattern copy/clear |
| SCALE 1/16, LENGTH 16/16 | scale: original has only 1/16 steps (a quantisation setting exists for recording); length: per-track length (1…64) |
| Missing in mockup, present in engine | probability per step, shift (micro-timing ±7), per-track length/rotation, pattern/song, Euclid, shuffle, track mute |

### 4.5 First-playable scope for the sequencer (staged; see implementation plan)

- **S-A (in first playable):** 7 tracks × 64 steps, trigger + volume + note, per-track length, flam ×2…×8, shift, probability, shuffle, p-locks (2/step), host-sync transport, one active pattern (switching by command at master wrap), save/restore, full UI deck, deterministic playback.
- **S-B (right after):** 64 patterns with chaining/song mode, pattern copy/clear, Euclid, rotation, roll (live), kit-per-pattern.
- **S-C (later):** MIDI-record into the pattern (with the original quantiser), free-run mode polish, undo/redo, pattern-import from LXR project files.

## 5. Randomness

`GetRng() % 100 + 1` per step per track (3-slot window so shifted/flammed neighbours see consistent draws). In the port: a per-instance seeded PRNG (seed stored in state so that a bounce is repeatable; **reseed on transport start** is an option — hardware never reseeds). Probability tests assert statistical frequency and, with a fixed seed, exact sequences.

## 6. Interaction with the DSP engine (rules to keep)

1. A trigger is `lxr_trigger(track, note, vol)` after applying p-lock overrides and before the engine tick that contains the trigger's time.
2. Mute blocks triggers (sequencer and MIDI). The hat tracks 5/6 share the voice (choke by restart).
3. P-lock restore happens when the next trigger's destination differs — implemented in the sequencer, not the engine (the engine only supports "override base value for param P").
4. The sequencer reads the **host tempo** every block; `lxr_set_bpm` keeps LFO sync consistent with it.

## 7. Differences from the original that are intentional (register in `DEVIATIONS.md`)

| ID | Original | Plugin | Reason |
|---|---|---|---|
| S1 | ms/0.25 ms wall clock | host PPQ, sub-tick offsets | sample/transport accuracy, no drift |
| S2 | MIDI-clock slave, MTC | removed | host transport |
| S3 | position relative to start | anchored to host position (locate/loop-safe) | DAW workflow |
| S4 | `GetRng()` hardware | seeded PRNG | repeatable bounces |
| S5 | Shuffle by period lengthening | PPQ-domain offset of odd steps | same musical result in a stateless clock |
| S6 | Pattern RAM/backup buffer swap on pattern change (`copyBackupBufferToPattern`) | edits are committed immediately to the pattern; no "discard unsaved edits on pattern change" | desktop state model (confirm desired) |
| S7 | Front-panel LEDs, MIDI-out, trigger-out | removed | n/a |
| S8 | Tempo is an integer BPM (`seq_setBpm(uint16_t)`; also feeds LFO sync via `lfo_calcPhaseInc`) | float host tempo (e.g. 136.37) for the sequencer clock and LFO sync | host tempo is fractional; truncating would drift against the DAW grid. For reference-mode tests drive both with integer BPM (T0 stays exact). |

## 8. Tests

- **Harness-extended T0:** add `seq_tick` to the reference harness with a fake, deterministic `systick_ticks` driven by an injected clock; record the stream `(sub-tick index, track, note, vol, p-lock writes)` for scripted patterns (flam, shift ±, probability with injected RNG, lengths 1…64, polymetric, pattern switch, song loop). The plugin's `lxr_seq` must reproduce the stream exactly **in sub-tick units** (T0 on the logical event stream; wall-clock time is the deviation S1).
- **T2:** timing accuracy vs host PPQ (trigger sample offset error ≤ 1 engine tick), tempo changes mid-play, loop/locate behaviour, transport start/stop.
- Edge cases: shift +7 on the last step wrapping into the next pattern; flam ×8 + shift −7 (mask overlap); `length` = 1; track length 64; probability 1 vs 100; mute mid-pattern; pattern switch during a flam.
- Soak: random edits during playback (no allocation/locks; lock-free queue stress).

## 9. Open items (resolve in the sequencer harness phase)

1. The `chokeNext/chokeCurrent` cross-track coupling (see §3).
2. Exact shuffle formula and which steps are "odd" (`seq_masterStepCnt % 2`), including the first step after start.
3. Whether the 0.25 ms systick inference is right (check TIM14 clock tree) — only matters for the harness's fake clock.
4. Whether roll should keep step-boundary granularity in the plugin (faithful) or get a sub-tick option later.
5. Recording quantiser (`seq_addNote`, `seq_quantize`) — S-C.
6. Pattern-change semantics around `seq_copyBackupBufferToPattern` (S6).
