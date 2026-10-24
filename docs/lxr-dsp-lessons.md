# What the LXR teaches us — observations for webdsp

**Observations only.** Nothing here modifies or is applied to webdsp, and nothing assumes the LXR architecture should become webdsp's. I have not read webdsp's source in this task,
so every "relevance" statement is a hypothesis to test against it. Evidence for each item points to `lxr-dsp.md` / `lxr-architecture.md`.

## 1. Useful architecture patterns

| Pattern in LXR | Why it works | Possible relevance to webdsp |
|---|---|---|
| **Two-rate engine: control tick (once per 64-sample block) + audio loop.** All envelopes/LFOs/coefficient maths happen at 690 Hz; the audio loop does only table lookups, an SVF, a soft-clipper and gain. | Predictable CPU independent of voice complexity; complex modulation is "free". | If webdsp recomputes slow state per sample or per ad-hoc event, a fixed control tick is a simple cap on cost. Cost: parameters are stair-stepped (see below). |
| **Statically allocated, monophonic voices with deterministic reset-on-trigger.** No pool, allocation, stealing; every hit starts from known state. | Dense percussion costs a constant; reproducible transients; no voice-lifecycle bugs. | For drum-type voices, "restart the voice" can be better than "allocate a new one". For tonal polyphony it does not apply. |
| **Event quantisation to the block boundary; single-threaded cooperative ordering** (MIDI → params → DSP). | No locks, no atomics, no races: everything that changes DSP state does so between blocks. | In a browser/AudioWorklet or plugin context the equivalent is "apply all queued events at the top of the render quantum", never mid-block. |
| **Modulation = rewriting parameters at block rate, with an "original value" restore each block.** | A *general* destination list (any parameter) with one tiny mechanism. | Simple and powerful; but LXR's implementation (re-entering the CC parser) is a cautionary tale: keep base and effective values separate (see porting notes §2.1). |
| **One kit = a flat array of 7-bit values.** Presets, morph, automation, modulation and the hardware protocol all use the same address space. | Trivial serialisation, interpolation (morph) and diffing. | A flat, indexable parameter space makes preset morphing and A/B testing trivial. The cost: resolution limited to the quantisation chosen. |
| **FX as a routable bus with exactly one active type**, per-voice binary routing. | Bounded CPU/memory (one shared 64 KB buffer for delay/reverb); tiny UI. | A single-slot FX bus is an acceptable constraint for a drum machine; a chain would multiply buffers. |

## 2. DSP techniques

- **Rational "slope" curve** `(1+k)x/(1+k|x|)` is used for *everything*: envelope shaping (`slope`), time→increment mapping (K = 198 / 1998), filter cutoff taper (`k=−0.947`), decimation taper, LFO exp, per-voice soft clip. One cheap function, one division, symmetric, monotonic, no `exp/log`. A very compact way to give every knob a controllable taper.
- **Time mapping with a "time → increment" rational curve** (`inc = 2(1 − (1+K)v/(1+K v))`) gives ~1.4 ms to minutes (and infinity at max) over 0…127 with fine resolution at short times — a parameter law worth comparing with webdsp's.
- **Phase-modulation FM with a 32-bit phase accumulator**, modulator scaled by a *pitch-envelope-linked depth* so brightness decays with the pitch sweep for free (FM index ∝ `fmAmount²·pitchEG`). Very efficient "kick that gets duller as it falls" behaviour from one envelope.
- **"Offset" transient**: start the oscillator at a chosen phase (e.g. at the waveform's peak) to create a controlled first-sample click; **"snap" transient**: a very short, steep, squared pitch burst; **sample transients** played raw (no interpolation) as click layers. A tiny toolbox that gives hits their attack identity without extra oscillators.
- **Linear pitch sweep, not semitone sweep** (`f·(1 + EG·amount)`): a different sonic character from the usual exponential pitch envelope; cheap (one multiply per block).
- **ZDF/TPT state-variable filter with a soft-clipped state and tanh on the LP only**, ±input drive, 7 outputs from one core, `fastTan` Padé for coefficients, and an escape hatch ("naive 2-pole") for cases where the nonlinear one misbehaves on kick transients. Note that nonlinearity is limited to three cheap places — no per-sample `tanh` calls.
- **Tuned sample-and-hold noise** (`noise freq` = hold rate) as an *oscillator* — a controllable "colour of noise" with no filter, and usable as an FM source (metallic cymbal/hat).
- **Mipmapped band-limited tables** per octave (11 × 1024) — measured with the surprising result that actual in-use bands overlap Nyquist; the "accidental" `uint8_t` wrap pins everything below 440 Hz to one table. It teaches how forgiving percussion is of mild aliasing and how much character a "slightly wrong" table choice contributes.
- **Block-wise linear gain interpolation** to turn a control-rate EG into a smooth audio-rate gain, *skipped on hard attacks* to keep them snappy — an inexpensive, deliberate click/snap trade-off.
- **Repeat envelope** (attack time reused as the loop decay, N repeats) → claps/flams from a single EG.
- **Delay time changes by 10 ms crossfade between two read heads** (no pitch glide, no zipper), including a pending-request slot while a fade runs.
- **Compressor envelope in the dB domain** (one-pole on `overdB` with attack/release coefficients): a minimal log-domain compressor.
- **Diode/triode transfer tables** (257/129 entries) + slew limiter + band-limiting filters for "RAT"-style and tube distortion: character via tables rather than maths.

### Sequencer patterns worth noting (read after the scope decision)

- **Micro-timing as bit masks.** A step's flam (×2…×8) is a 24-bit mask over the step's 24 sub-ticks, and shift (−7…+7 in units of 3 sub-ticks) is a bit-shift of that mask into the previous/next step; the sequencer merges three neighbouring steps' masks each sub-tick with a fixed priority (*next > current > prev*). Tiny state, no event lists, and flam + shift compose by plain shifts.
- **Probability with a 3-slot random window** (prev/current/next draws) so a step that fires early or late (shifted) sees the same draw as when it fires in place.
- **Per-track independent lengths with the longest track as the master** for pattern switching — polymetric patterns for free.
- **P-locks as two per-track "automation nodes"** that write through the normal parameter path and restore the stored value when the destination changes — a very small mechanism for per-step parameter automation (but entangled with modulation in the original; keep base/override/effective separate).
- **Clock = 96 PPQ with 24 sub-ticks per 16th**, so flam ×2/×3/×4/×6/×8 and shift ±7 all land on integer sub-ticks.

## 3. Performance techniques

- Everything in the audio path is table lookups and multiply-adds; transcendental functions only at control rate (`sqrtf`, `expf` in setters), except the compressor's per-sample `logf/expf` (a desktop cost, trivial).
- Heavy use of 16-bit SIMD saturating add (`QADD16`) to sum stereo pairs — a hardware-specific trick that on desktop is irrelevant.
- **Placement of hot data/code in ITCM/DTCM** (`INDTCM`, `IN_ITCM_RAM`) — embedded-specific.
- Voice buffers are short VLAs on the stack (64 samples) — cache-resident by construction; the block is small enough for L1.
- `fp16` delay storage halves RAM for the FX buffer (an embedded trade-off: 10-bit mantissa).
- Interpolation: 64-bit multiply-shifts on integers instead of float interpolation.

## 4. Things specific to embedded hardware (do not carry over)

16-bit buses and saturation as "the master", fixed 44 140 Hz from a prescaler, ITCM/DTCM placement, DMA ping-pong and its one-block latency, hardware TRNG, ADC faders/pots, jack-detect routing, flush-to-zero set globally, FP-unit-specific float→uint casts, `-O0` pragmas around NaN scrubbing, 7-bit parameters (MIDI-bound), ms-timer sequencer.

## 5. Things that may not translate to webdsp (or deserve caution)

- **Block-rate stepping of pitch/filter/EG** gives the LXR its feel but is a quality compromise (staircase pitch sweeps, steppy filter modulation at 690 Hz, an LFO at 200 Hz aliasing against a 690 Hz sampler). A modern engine would interpolate; whether you want the stair is an aesthetic choice, not a technical necessity.
- **Per-type voice code paths with subtle inconsistencies** (ramped gain vs block-constant gain; reset filter vs not) are a maintenance trap; webdsp probably wants one voice abstraction.
- **Parameter layer fused with the MIDI parser** — the antipattern; keep a typed setter API.
- **Global singletons** — not viable for multi-instance plugins/web contexts.
- **Hard-coded rate constants** (RAT filter coefficients, `0.01` smoothers) — write time constants in seconds and derive per rate.
- **Infinite-sustain at max decay, resonance jump at 0.9, undefined casts** — surprises best avoided.
- **Resolution**: 128-step parameters are a hardware convenience.

## 6. Comparison experiments worth running (once webdsp is open to comparison)

1. Same patch (e.g. sine + pitch EG, same decay) rendered by both; compare pitch trajectory (linear-f vs exponential), spectrum over time, and amplitude envelope shape (rational slope vs webdsp's).
2. Filter step response and resonance sweep (LXR SVF vs webdsp's) with a kick transient input.
3. FM brightness decay (LXR's `fmAmount²·pitchEG` coupling vs independent FM envelope).
4. Time-to-sample conversion curves: LXR `K=1998` law vs webdsp's law, for 0…127.
5. Retrigger transients: always-reset vs reset-when-closed, with and without SVF zeroing (measure click energy).
6. CPU per voice and per-voice jitter (block-rate control vs per-sample).
