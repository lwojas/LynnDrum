# Reference harness (Phase 1)

`Tools/ref-harness/` builds the **unmodified upstream** DSP, parameter handler (`midiParser_ccHandler`), voice trigger path (`voiceControl_noteOn`) and mixer on the host, and renders audio from a script, deterministically. It is the oracle for the later bit-exact (T0) tests. Upstream (`Reference/lxr-desktop-app`, a read-only submodule) is never written to; the few edits it needs are `.patch` files applied to a copy in the build tree.

Status: **Phase 1 implemented on macOS arm64**; **Linux/x86-64 support is deliberately dropped for now** (decision 2026-10-24; port later — libm reproducibility is the known risk, §5). See §5.

## 1. Build and run

```sh
cmake -S Tools/ref-harness -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build
build/lxr_ref_render Tools/ref-harness/scripts/smoke_kick.lxr -o out [--float] [--trace]
# -> out.dac1.wav out.dac2.wav (int16, 44 140 Hz, stereo) [+ .f32.wav] [+ out.trace.txt]
#    stdout: blocks=360 frames=23040 dac1=<fnv1a64> dac2=<fnv1a64>
python3 Tools/ref-harness/scripts/gen_scenarios.py build/scen Reference/lxr-desktop-app/Core/Inc/Parameters.h
sh Tools/ref-harness/scripts/run_scenarios.sh build/lxr_ref_render build/scen build/manifest.txt
diff Tools/ref-harness/golden/manifest.txt build/manifest.txt        # T0 gate
python3 Tools/ref-harness/scripts/wavstat.py out.dac1.wav 50         # peak/RMS per 50 blocks
```

Output buses: the mixer writes two stereo buffers. `St1` (default routing) lands in `dac1` (= mixer `output2`), `St2` in `dac2` (= `output`). Both are saved; the FX bus is added to whichever the FX routing selects. The sample rate in the WAV header is the engine's real `REAL_FS = 44 140`.

## 2. Script grammar (`.lxr`, one command per line, `#` comments)

| Command | Meaning (firmware path it reproduces) |
|---|---|
| `seed N` | seed the deterministic xorshift32 that replaces the hardware TRNG |
| `bpm N` | tempo seen by tempo-synced LFOs (`seq_getBpm` stub + `lfo_recalcSync`) |
| `kit init` / `kit <file>` | `preset_init`: copy `initKit[8..228)` (first 8 bytes = name) / raw 228 parameter bytes; then `preset_sendDrumsetParameters` (velocity + LFO mod targets via `modTargets[]`) followed by `preset_morph` order (every parameter 0…227 through `midiParser_ccHandler`, "+1 offset" for <128, CC2 for ≥128). Applied atomically before the next block (the firmware trickles one parameter per main-loop pass). |
| `par NAME\|idx v` | one front-panel parameter write (same path as above); names are the `PAR_*` enumerators, generated from the upstream header |
| `trig voice note vel` | `voiceControl_noteOn`; voice 0‑2 drum, 3 snare, 4 cymbal, 5 closed hat, 6 open hat |
| `fader i x` | stub for `adc_getFaderVolume(i)` (default 1.0) |
| `render N` | N × `mixer_calcNextSampleBlock` (64 frames each) |

Triggers and parameter writes take effect at the next block boundary, exactly as in the firmware.

## 3. What is built, what is stubbed

Built unmodified (apart from §4): all of `DSPAudio/` incl. FX, `FxBus.c`, `MidiParser.c`, `MidiVoiceControl.c`, `ParameterArray.c`, `MidiMessages.c`, `menu/Cc2Text.c` (data only: `modTargets[]`), `Preset/initKit.c`.
Not built in `lxr_ref_render` (built in `lxr_ref_seq`, §5b): `sequencer.c`, `clockSync.c`, `EuklidGenerator.c`; `Uart.c`, `CortexParser.c`, USB, SD/preset manager, LCD/menu, codec, `Soundengine.c`.

`src/stubs.c` provides ≈30 inert symbols: menu/front-panel (`menu_*`, `frontParser_activeTrack`, `activeParameters[]` as the kit edit buffer), UART/USB MIDI out, jack-detect GPIO (all jacks "connected" ⇒ routing fallback is the identity), `adc_getFaderVolume`, and the sequencer API used by `MidiParser`/`lfo` (`seq_getBpm` is real, the rest no-ops). Shims (`shim/`) implement the CMSIS intrinsics (`__QADD16`, `__QSUB16`, `__SADD16`, `__PKHBT`, `__SSAT`, `__SMLALD`, `__QADD/__QSUB`, `__CLZ`) with ARMv7E‑M semantics; `__attribute__` (all remaining uses are ITCM/DTCM section placement) is defined away; `char` is unsigned as on ARM (`-funsigned-char`); FP contraction is off.

## 4. Edits and deviations from the firmware (H‑series register)

Each has a reason; none changes the result on a Cortex‑M7 except where stated.

| ID | Where | What | Effect vs hardware |
|---|---|---|---|
| H1 | patch 0001, `Oscillator.c::calcNoise` | `APSR.V` read after an unspecified instruction → signed overflow of the preceding `phase += phaseInc` | **Unknown**: on the MCU the flag is whatever the compiler left. Affects only single‑sample noise (noise as FM modulator/carrier). Pinned by golden hashes; revisit if a build of the firmware can be inspected. |
| H2 | patch 0002, `wavetable.[ch]` | `rec/tri/saw` tables get a 12th (zero) row so the interpolator's `[k][1024]` read is in bounds | For k<10: identical to the MCU's accidental read of the next row. For k=10 (≥ 8.37 kHz band): MCU reads an unspecified neighbour, harness reads 0. |
| H3 | `render_main.c` | `parameterArray[0]` (PAR_NONE) pointed at a zero byte | `modNode_originalValueChanged` derefs it when a modulator's destination is 0 and CC 1 is written; address 0 is readable on Cortex‑M, a segfault on the host. Value unused. |
| H4 | `render_main.c::send_cc` | kit parameter 127 (`PAR_BANK_CHANGE`, CC#0) is dropped | `ccHandler` does `midiParser_originalCcValues[(uint16_t)(0-1)+1]` = write **65 536 bytes past a 255‑byte array** (silent RAM scribble on the MCU) and nothing else (empty `case`). **Upstream bug, reported here.** |
| H5 | patches 0003/0004, `lxr_f2u32` | every float→`uint32_t` conversion that can see a negative/NaN/≥2³² value (FM index, `freq2PhaseIncr*`, LFO phase/offset, drum start phase) | Identical on ARM (`VCVT.U32.F32` saturates; negative → 0) and arm64; makes x86‑64 match. **Confirms the half‑wave FM behaviour (assumption 2) architecturally**: negative modulator → 0. Found by UBSan; the catalogue is clean. |
| H6 | `lxr_host_rng_next` | xorshift32 instead of the TRNG | Statistically equivalent (noise/S&H); by design. |
| H8 | patch 0005, `EuklidGenerator.c` | `if(length < 64)` around the leftover mask | restores the ARM result for 64-step Euclid tracks |
| H7 | scenarios | out‑of‑domain enum values (e.g. oscillator waveform 64) are not in the catalogue | They are undefined in the original (uninitialised sample; `-O0` ≠ `-O2`). The Phase‑5 parameter table must carry valid ranges. |

Also noted (no change needed): the kit‑apply order and timing differ from the firmware only in being atomic; `mixer.c` casts `int16_t*` to `int32_t*` (misaligned on some stack layouts: fine on arm64/x86‑64, UBSan alignment check disabled).

## 5. Exit-criterion status

| Criterion | Status |
|---|---|
| Deterministic build + script → WAV, no hardware | ✔ |
| Same results for repeated runs, `-O0`, `-O2`, UBSan build (float‑cast‑overflow on, alignment/bounds off) | ✔ 818 scenarios, identical hashes |
| UBSan clean over the catalogue | ✔ (after H4, H5) |
| Catalogue: 5 musical + every sound parameter at 0/64/127 (waveforms 0–5) | ✔ 818 scenarios, `golden/manifest.txt` |
| Identical on macOS arm64 and Linux x86‑64 | ➖ **Dropped for now (macOS arm64 only).** Notes for a later port: Authoring machine has no Rosetta/Docker; `.github/workflows/ref-harness.yml` runs the gate on ubuntu + macos. The x86‑64 binary compiles. **Main risk: libm.** The engine calls `expf`, `exp`, `logf`, `sinf` (and `fmod`, exact); glibc and Apple libm may differ in the last ulp. If CI diverges, bundle one deterministic implementation of those four in the harness *and* in `lxr_core` (T0 then holds across hosts; it also won't equal the firmware's newlib, which cannot be tested here anyway). |
| ASan | ✘ the ASan runtime hangs at start‑up on this OS build; UBSan used instead |

## 5b. Stage S0 — sequencer oracle (`lxr_ref_seq`)

`lxr_ref_seq` is the same CLI/engine built with the **real** `sequencer.c`, `clockSync.c`, `EuklidGenerator.c` (+ `automationNode.c`), `LXR_WITH_SEQ` defined. The sequencer is driven by an injected `systick_ticks` (0.25 ms units) and calls the real `seq_tick()`. Two compile-time renames (no source edits) route `voiceControl_noteOn` and `midiParser_ccHandler` calls made by `sequencer.c`/`automationNode.c` through `lxr_hook_*`, which append to the **event log** and then forward to the real function.

Extra script commands: `ms pat trk step on` · `sd pat trk step vol prob note` · `st pat trk step flam shift(7=none)` · `pl pat trk step slot NAME|none val` (name → cortex destination, PAR+1 below 127) · `len pat trk n` · `shuf pat 0..127` · `mute trk on` · `run 0|1` · `pattern n` · `roll trk on` · `rollrate 0..5` · `song 0|1` · `songset pos pat` · `euk_len|euk_steps|euk_rot` · `dump pat trk` · `ticks N [poll]` (advance the clock; `seq_tick` every `poll` ticks, default 1 = finest resolution) · `play N` (N audio blocks, clock advanced by the real 1.4499 ms per block, one `seq_tick` per block = the firmware's polling, **audio rendered**). `--events file` writes the stream, one line per effect: `<tick> sub=<prescaleCounter> trig <track> <note> <vol>` | `cc <status> <data1> <data2>` | `kit <n>` | `mainsteps …`.

Catalogue: `scripts/gen_seq_scenarios.py` → 75 scenarios (flam ×2–×8, shifts −7…+7, flam+shift overlaps, wraps, probability, lengths 1…64, polymetric, tempo 60–300, shuffle, mute, stop/start, p-locks, pattern switch (also polymetric), song mode, kit-per-pattern, roll rates 0–5, cross-track choke, Euclid, firmware-like 6-tick polling, 8 seeded random patterns). Golden streams: `golden/seq/*.ev` (diffed in CI). UBSan (all checks except alignment) is clean and gives identical streams.

### Findings (answers to `lxr-sequencer.md` §9)

1. **Cross-track `chokeNext/chokeCurrent` coupling is real** (`choke_cross_track2`): a shifted-back note fired by track 0 at sub-tick 12 suppresses track 1/2's later *current* notes (sub 21/15) in the same step; track 3's earlier note (sub 6) still plays. Reference mode keeps it; per-track fix stays a Phase‑9 option.
2. **Shuffle**: odd-indexed steps (1, 3, …; `masterStepCnt` parity evaluated when sub-tick 23 is reached) start `shuffle·16/24` of a step late (`shuf 64` → +168 ticks of a 500-tick step). **But only the lengthening of one sub-tick period is applied; the next period is shortened by the same amount, and `seq_tick` processes one sub-tick per call**, so the remaining sub-ticks of the delayed step play *back-to-back* until the clock catches up (flam ×2 in an odd step at `shuf 127`: sub 0 at +334, sub 12 only +12 ticks later at 1 tick polling; with one `seq_tick` per audio block it is ~6 ticks per sub-tick). Plain triggers (sub 0) behave like "odd steps start later"; **flams/shifts inside odd steps are compressed**, not delayed. Deviation S5 must say which behaviour the plugin reproduces (see decision D8).
3. **systick = 0.25 ms** is consistent with the code (`60000/bpm` ticks per 16th; 120 BPM → 500). Not independently verifiable without hardware; the oracle assumes it.
4. **Roll**: `seq_setRollRate(0..5)` → every 16 / 8 / 4 / 2 / 1 steps retrigger at step boundaries (rate 0 = one-shot on press, no retrigger); fixed volume 100, the step's note; an extra `cc`-free trigger.
5. **P-lock restore is unconditional**: `autoNode_setDestination` re-applies the stored original value of the *previous* destination on **every** trigger (even if unchanged), then `updateValue` writes the new value; a step without p-lock restores and writes nothing. Order within a trigger: restore(s) → set(s) → `trig`. (`lxr-sequencer.md` §3 said "if the destination differs": corrected.)
6. **Pattern switching**: a queued pattern becomes active at the next master-track wrap (longest track), `seq_setRunning(0)`→`(1)` restarts at step 0; song mode advances one entry per master wrap, `SONG_END` stops after the last bar; `PAR_PATTERN_MODE == 1` loads the pattern's kit (`kit n` event).
7. **Euclid** length 16 is stored as 0 (= "16" in `seq_nextStep`), but `seq_processFlam` divides by `length` unguarded → `% 0` and `prev = 0xFF` (reads `seq_mainSteps[15]`, out of bounds). **Upstream bug**; the scenarios normalise with `len … 16` after generation; `lxr_seq` must treat 0 as 16 (new deviation S9).
8. **Patch H8** (0005): `euklid_rotatePattern` shifts a 64-bit value by `length` = 64 (undefined; ARM EABI gives 0 ⇒ mask = all ones, arm64 wraps the shift ⇒ pattern erased). Guarded with `if(length < 64)`.

## 6. Findings worth carrying forward

1. **Upstream OOB write (H4)** in `ccHandler` for CC#0 / kit parameter 127 — `lxr_apply_param` must not reproduce it.
2. `initKit` layout: bytes 0‑7 are the kit name; parameters start at offset 8; `preset_init` copies only `initKit[8..228)` so the last 8 parameters are not initialised from it.
3. The reference voice sound comes out of `dac1` with default routing; both buses must be mixed in the plugin's main output.
4. Out‑of‑range enum values are UB: the Phase‑5 table needs per‑parameter valid ranges, and the plugin must clamp.
5. `calcNoise` depends on a CPU flag (H1): an unresolved fidelity question for noise‑as‑FM.
