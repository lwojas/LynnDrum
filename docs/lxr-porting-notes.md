# Porting notes

Classification of every upstream piece, plus the "found problems" log. Format for problems, as requested:

> **Original behaviour → problem/constraint → proposed VST adaptation → reason.**

The first implementation stays recognisably derived from the LXR architecture. Nothing in §3 is "fixed" in reference mode; fixes are Phase-9 candidates unless a problem is a *portability* issue (then the adaptation preserves the original result).

## 1. Classification

### 1.1 Direct ports (copied, mechanically cleaned, behaviour identical)

| Upstream | Notes |
|---|---|
| Sequencer step/flam/shift/probability/p-lock/Euclid logic (`sequencer.c`, `EuklidGenerator.c`, `SeqStep.h`) | Pure logic once the clock and UI hooks are cut; first ported with the original's step-count-based interface (`seq_nextStep` / `seq_processFlam(idx)`) and driven by sub-tick index. Shared `choke*` state kept in reference mode. |
| `Oscillator.c`, `wavetable.c` (sine/tri/saw/rec tables) | Strip HAL include; fixed arrays; add guard column per §3 item 4. |
| `SlopeEg2.c`, `Decay.c`, `snapEg.c` | Pure maths. |
| `ResonantFilter.c` | Drop `removeMaliciousSample`'s `-O0` pragma trick (replace with `isfinite` check, same effect), drop cheap variant. |
| `1PoleLp.c`, `distortion.c`, `dither.c` (kept but unused) | |
| `lfo.c` | Needs `seq_getBpm()` → engine tempo field. |
| `transientGenerator.c`, `transientTables.c` | **Licence-gated** (CC-BY sample, §0 of the architecture doc). |
| `DrumVoice.c`, `Snare.c`, `HiHat.c`, `CymbalVoice.c` | Voice DSP identical; globals → instance members; `adc_getFaderVolume` → `fader[]`; drop `TriggerOut`/`MidiVoiceControl` includes. |
| `FX/Distortion.c`, `Ringmod.c`, `Compressor.c`, `Delay.c`, `FxBus.c` | Ecc83/1N914 tables included. |
| Parameter *transforms* in `MidiParser.c::ccHandler` | Extracted into `lxr_apply_param`, one `case` per `PAR`, bodies unchanged. |
| Modulator maths (`modulationNode.c`, `lfo.c`) | Re-hosted on base/effective split (§2). |
| `mixer.c` summation, pan law, decimator | Block orchestrator adapted (6 voices, FX bus); saturating adds emulated. |

### 1.2 Adaptations (same intent, different mechanism)

| Item | Adaptation |
|---|---|
| Global state | One `LxrEngine` struct per instance (multi-instance safety). |
| `ccHandler` | Split: transforms kept, MIDI framing/NRPN/menu/UART/sequencer side effects removed. |
| Modulation | `base[]` (from host) vs `effective[]`; apply transform to effective, no write-back. |
| Intrinsics / fp16 / RNG / FTZ | `Platform/` shim. |
| Block scheduling | EngineHost tick loop + resampler (SR adapter). |
| Voice trigger path | `lxr_trigger` = `voiceControl_noteOn` minus MIDI-out/front-panel bookkeeping. |
| Sequencer | `sequencer.c` logic → `Source/Sequencer/lxr_seq` (instance state, sub-tick-driven `seq_advance`, trigger sink instead of `voiceControl_*`); wall-clock/MIDI-clock/LED/UI parts replaced (`lxr-sequencer.md` §4, §7). P-lock `AutomationNode`s → engine override API. |
| Note → voice | Note map default; channel mode available. |
| Mute | engine flag; solo added in plugin shell. |
| Routing | `AUDIO_OUT` kept; jack-fallback removed; mono/aux destinations folded or mapped to aux buses. |
| Presets | 228-byte kit snapshot inside plugin state. |

### 1.3 Replacements (new code, our own)

APVTS layer + generated parameter table; EventScheduler; StateManager; resampler; WebUI; telemetry bridge; test harness; sequencer **clock/transport/bridge** (`SeqClock`, `SeqTransport`, `SeqBridge` — the sequencer *logic* is a derived port, §1.1/§1.2).

### 1.4 Omissions (not carried over)

Bootloader/`.img` tooling, LCD/menu/screensaver/LED/button/encoder code, ADC pots, front-panel UART protocol, USB/DIN MIDI stacks, SD/FatFs/preset files (v1), `TriggerOut` (gate/trigger jacks), MTC/SPP/MIDI-clock slave, sequencer LED/front-panel/MIDI-out bookkeeping, `reverb` (compiled out upstream), `Samples.c` crash sample (dead). *(The sequencer, p-lock automation nodes, song mode and pattern chaining are no longer omitted — see `lxr-sequencer.md`; song/chaining are scheduled for stage S-B.)*

## 2. Structural conversions that need care (not bugs)

1. **Modulation re-entrancy.** Original: each block `modNode_resetTargets()` pushes the *stored* original value back through `ccHandler`, then LFO/velocity push modulated values through it again (re-running `osc_recalcFreq`, `lfo_setFreq`, enum switches…). Port: for each target, `effective = clamp(base + amount·(2v−1))`, call the same transform with `(itg = trunc(effective·127), flt = effective)`; for a target that stopped being modulated, call the transform once with the base value. **Equivalent, cheaper, and removes the side effects.** Order of evaluation must match (velocity first, then LFO 0…5; later writers win).
2. **Parameters with several PAR indices pointing to one field.** `COARSE n` and `FINE n` both point at `osc.modNodeValue` in `parameterArray[]` (type `SPECIAL_F`), but the actual handlers write `midiFreq` hi/lo. Modulating "coarse" therefore multiplies `modNodeValue` (a frequency *multiplier*), it does not change the coarse note. Preserve: the destination table must record *what the modulator writes*, not just the param name.
3. **`TYPE_SPECIAL_F` original value is hard-set to 1** (`modNode_setDestination`). Port must restore `1.0` not the stored coarse/fine.
4. **Voice indexing** differs by type (`voiceArray[0..2]`, `snareVoice`, `cymbalVoice`, `hatVoice` vs index 3,4,5): the `lxr_core` switch keeps the "stems" but uses an array of 6 voice descriptors to remove the copy-paste per voice.

## 3. Found problems / constraints — original → problem → adaptation → reason

**1. Fixed 44 140 Hz, 64-frame block**
*Original:* both are literals in 40+ places; EG/LFO/snap constants are per-block increments.
*Problem:* arbitrary host sample rates/blocks.
*Adaptation:* engine stays at 44 140 Hz / 64; high-quality resampler at the edge; fractional-block native-rate mode deferred to Phase 9.
*Reason:* preserves envelope timing, filter coefficients, delay times and aliasing character exactly; makes the port null-testable.

**2. Single-instance global state**
*Original:* ~15 file-scope globals; one engine per process.
*Problem:* two plugin instances would corrupt each other (and a host may load multiple instances in one process).
*Adaptation:* `LxrEngine` aggregate; every function takes it.
*Reason:* correctness; no behavioural change.

**3. `(uint32_t)(negative float)` in all FM paths**
*Original:* `index = phase + ((uint32_t)(m[i]*fmMod) << S)`; on Cortex-M7 a negative float converts to 0 (saturating), so only the positive half of the modulator contributes.
*Problem:* UB in C; x86-64 would wrap instead (different timbre). Arm64 hosts behave like the original.
*Adaptation:* `fm_phase(float x)` returns `x <= 0 ? 0 : (uint32_t)min(x, 4294967295.f)`, used everywhere; unit test pins it.
*Reason:* reproduce the sound on every platform. **Verify on a harness build** that the half-wave behaviour is real, and consider (Phase 9) whether a "full-wave FM" option is wanted.

**4. Wavetable interpolation reads index 1024**
*Original:* `table[k][itg+1]` with `itg ≤ 1023` reads the next row's first element (row-major layout) and, for `k=10`, the byte after the array.
*Problem:* UB at the last sample of each cycle; for `rec` tables 8–9 the target differs noticeably from the wrap value (measured up to ≈7 % FS for 1/1024 of the cycle); `[10]` reads an unspecified neighbour.
*Adaptation:* tables stored with a 1025th guard element; for `k<10` guard = next row's `[0]` (identical to hardware's accidental behaviour); for `k=10` guard = own `[0]` (deviation, ≥14 kHz, documented). The reference harness uses the same padded arrays so null tests stay bit-exact.
*Reason:* eliminate UB without changing in-band output; a clean "fix" (guard = own `[0]`) is a Phase-9 option.

**5. Table selection by octave with a `uint8_t` wrap**
*Original:* `f<440 Hz → table 4`; tables 0–3 never used; octave band edges at 440·2ⁿ; harmonics exceed Nyquist near the top of each band (§1.3 of `lxr-dsp.md`).
*Problem:* mild aliasing; looks like an accident.
*Adaptation:* **none in reference mode** (port the exact expression incl. the wrap, with a comment and test vectors). Phase-9: optional "clean band-limiting" mode.
*Reason:* it is part of the instrument's sound.

**6. Phase-reset guard compiled out (`USE_AMP_FILTER` undefined)**
*Original:* an `if(envelope closed)` guard around the phase reset in `Drum_trigger` is commented away: **always** resets (hard discontinuity if the voice is ringing).
*Problem:* retrigger clicks; possibly accidental regression upstream.
*Adaptation:* none (always reset); keep a build flag `LXR_RESET_PHASE_ONLY_WHEN_CLOSED` for experiments.
*Reason:* the shipping firmware's behaviour is the reference.

**7. int16 truncation, saturating bus adds, no dither, no master stage**
*Original:* `float→int16` truncation at several points; 6 voices + FX summed with saturation.
*Problem:* a 16-bit noise floor and hard clipping on loud kits; host expects float.
*Adaptation:* reference mode reproduces exactly; output scaled `×1/32768`; no master limiter added. Float-path mode is a later, test-gated option.
*Reason:* faithful first, improve second.

**8. Hardware TRNG for noise**
*Original:* `HAL_RNG_GetRandomNumber()` (truncated to 16 bits) for the S&H noise and the S&H LFO.
*Problem:* non-reproducible; no PRNG in the original.
*Adaptation:* seeded `xorshift32`; tests use fixed seeds; statistical equivalence (flat spectrum, uniform) is the criterion, not sample equality vs hardware.
*Reason:* determinism for null tests.

**9. Denormal handling via FPU flush-to-zero**
*Original:* `FPSCR.FZ` set at init; SVF loop guarded by a NaN scrub.
*Problem:* desktop CPUs do not flush by default.
*Adaptation:* `ScopedNoDenormals` in `processBlock`, plus `isfinite` scrub on SVF states.
*Reason:* real-time safety.

**10. Parameter side effects and UI coupling inside `ccHandler`**
*Original:* handler also updates menu sub-pages, UART front panel, sequencer mute.
*Adaptation:* removed (replaced by engine events: `mute`, none).
*Reason:* separation of UI from DSP.

**11. FX dry/wet `= p/100` with a 7-bit value**
*Original:* `dryWet = value/100`; the hardware UI presumably limits to 0…100 but the engine does not (values 101…127 → wet > 100 %).
*Adaptation:* keep the formula; the host parameter range maps `0…1 → 0…100` so over-range is not reachable from the plugin. Documented.
*Reason:* avoid a gratuitous reachable instability; no loss of reference behaviour for valid kits.

**12. Resonance discontinuity**
*Original:* `q = 1 − r; if (q < 0.1) q = 0.02` → a jump from 0.1 to 0.02 at `r ≥ 0.9` (unstable/self-oscillating region).
*Adaptation:* none; flag as "known character".

**13. Amp EG: `decay` increment 0 at parameter 127 → infinite sustain; EG can go to slightly negative `value`**
*Adaptation:* none; UI shows "∞". Add a safety `panic` (all voices reset) for the plugin shell.
*Reason:* infinite drone is a feature (acid-style) but the host needs a way to silence it.

**14. Per-voice behavioural inconsistencies**
Examples: only drum voices ramp gain across the block and smooth drive; only drum voices zero the SVF on trigger; snare/cymbal/hat apply one gain per block; `Snare_trigger` doesn't reset a mod osc (none exists); hat `transGen.waveform==0` replaces `pitchMod` (no pitch EG). *Adaptation:* none, keep per-type code paths intact; document them in `DEVIATIONS.md`/tests per voice type. Unifying them would be a redesign.

**15. Reverb compiled out; `PAR_FX_REVERB_TYPE` no-op**
*Adaptation:* omit from the plugin; do not port reverb in v1. Keep the table entry out of the host parameter list.

**16. `modTargets` (legal destination list) lives in `menu/Cc2Text.c`**
*Problem:* UI code defines which parameters are modulatable.
*Adaptation:* lift the list (≈228 rows, 34/voice) into the parameter table as a `modTarget` flag + order; generate the UI list from it.

**17. FM index depends on carrier type (4× deeper for table carriers) and on `fmModAmount²·pitchEG`**
*Adaptation:* none; the UI's FM-amount control should not claim a "percentage".

**18. Fader volume**
*Original:* hardware fader multiplier, not stored in kits.
*Adaptation:* separate host parameter per voice, stored in plugin state (not in the kit snapshot).

**19. Sequencer clock is wall-clock (0.25 ms ticks), polled once per audio block**
*Original:* 96 PPQ internal clock from `systick_ticks`; sub-ticks and steps fire at the next 1.45 ms block boundary; MIDI-clock slave upscaled by an internal clock.
*Problem:* host transport, tempo changes, loops/locates and sample accuracy.
*Adaptation:* host-PPQ sub-tick clock with sample offsets; step counters anchored to host position; free-run mode for hosts without transport; events then quantised to engine ticks (same as original).
*Reason:* musical correctness in a DAW without changing step/flam/shift logic (`lxr-sequencer.md` §4.2).

**20. Cross-track `chokeNext/chokeCurrent` in `seq_processFlam`**
*Original:* file-scope flags reset only at `idx == 0`, shared across tracks and the remaining sub-ticks of a step.
*Problem:* a shifted-back note on one track suppresses other tracks' current/previous triggers for the rest of the step — almost certainly unintended.
*Adaptation:* **reference mode keeps it**; a per-track option is a Phase-9 candidate after the harness confirms the behaviour.
*Reason:* it is the shipping behaviour; any "fix" must be a deliberate, tested change.

**21. P-locks written through the live parameter handler with restore-on-next-destination**
*Original:* `autoNode_updateValue` calls `ccHandler` with the stored original unchanged; `autoNode_setDestination` restores `midiParser_originalCcValues[dest]` of the previous destination on every trigger (verified, S0).
*Problem:* collides with modulation and host automation if implemented as direct writes (which value is "base"?).
*Adaptation:* engine **override** layer (`lxr_set_override`): effective = override ?? base, then modulation as before; clearing restores base. Order: base/override → velocity/LFO modulation → transform.
*Reason:* keeps host-visible parameters untouched and makes the interplay deterministic. **[verify]** the original's order (p-lock vs. modulation writes within a block) on the harness.

**22. Sequencer pattern RAM copy semantics**
*Original:* patterns live in a backup/edit buffer swapped on pattern change (`seq_copyBackupBufferToPattern` discards unsaved edits).
*Adaptation:* edits commit immediately to the pattern store; no "discard on switch" (deviation S6, to be confirmed with the user).
*Reason:* desktop state model; avoids silent data loss.

## 4. Unresolved questions

| # | Question | How to answer |
|---|---|---|
| 1 | Is the half-wave FM (negative → 0) behaviour real on the shipping firmware? | Build the original on the host harness with explicit saturating cast and compare to the wrapped variant; ideally compare to a hardware recording. |
| 2 | Is there a hardware LXR-02 (or recordings from one) available? | Ask the user. Without it, "sounds like the original" can only be tested against the *source*, not the device. |
| 3 | Licence of freesound #4102 (reported CC-BY 4.0): **decision — keep and attribute**; verify the licence page manually and whether other transient tables come from other sources. Provenance of `initKit` still unknown (do not ship as factory kit). | Manual check; ask Erica Synths if needed. |
| 4 | ~~Permission to use "LXR"/"Erica Synths" branding~~ **Resolved by decision: the product is named LynnDrum**; only truthful derivation/compatibility statements are used. (Revisit only if the name changes.) | — |
| 5 | Does the `NOTICE.md` marking requirement (modified versions) extend to a plugin UI, and in what form? | Ask upstream / counsel. |
| 6 | Kit file format of the SD card kits (for importing real kits) | Read `presetManager.c::preset_loadDrumsetSD` (not yet read). |
| 7 | How `VEL_DEST`/`TARGET_LFO` values map to destination params | Read `frontPanelParser.c` ~l.76–95 and `menu.c` mod-target handling. |
| 8 | Sequencer open items: cross-track `chokeNext/chokeCurrent` coupling, exact shuffle formula and "odd step" definition, 0.25 ms systick unit, recording quantiser, pattern-change commit semantics | Listed in `lxr-sequencer.md` §9; resolve with the sequencer harness (implementation plan, stage S0). The clock/flam/shift/probability/p-lock/roll code has been read. |
| 9 | Exact hardware sample rate (44 140 is the code's claim) | Measure from a hardware recording if available. |
| 10 | Whether `DISTORTION_CLIP`'s "RAT" model is intentional naming | Cosmetic; label in UI as "Clip (RAT-style)". |
