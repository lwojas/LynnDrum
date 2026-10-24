# LXR DSP — what the code actually does

Written for an audio programmer who has not seen the source. Facts are from the code at `a43cd4f` unless marked **[measured]** (I computed it from the
shipped tables or by running the same arithmetic in C/Python), **[inferred]** (follows from the code but I have not executed the firmware) or **[verify]**
(needs the reference build or hardware).

Conventions: `Fs = REAL_FS = 44140 Hz`. `B = 64` frames per engine block. Control rate `Fc = Fs/B = 689.69 Hz` (1.450 ms). Audio inside the voices is
**int16** (±32767); filters, envelopes, LFOs and effects maths are **float/double**; the int16 ↔ float conversions truncate toward zero. File references
are relative to `Reference/lxr-desktop-app/Core/Src/Soundengine/DSPAudio/` unless noted.

---

## 0. The two clocks inside the engine

Everything in the engine is built on a **two-rate scheme**:

| Rate | Where | What runs |
|---|---|---|
| **Audio rate**, per sample, in 64-sample loops | `calcDrumVoiceSyncBlock`, `Snare_calcSyncBlock`, … | oscillators, FM, noise, transient playback, SVF, distortion, voice gain ramp, panning, FX |
| **Control rate**, once per 64-sample block (`*_calcAsync`, `mixer_calcNextSampleBlock` preamble) | amp EG, pitch EG, snap EG, LFO, modulation writes, filter coefficient recompute (`SVF_recalcFreq`), `osc_setFreq` (phase increment & wavetable choice) | all "slow" state |

The control tick is **order-significant** (see `lxr-audio-flow.md` §3): reset modulation targets → velocity re-assert → LFO dispatch → filter coefficients →
per-voice `*_calcAsync` (EGs, pitch) → per-voice audio blocks.

Consequences that define the sound and that a port must keep:

- **Envelope and LFO time constants are expressed in "per-block increments"**, so they are bound to `B = 64` and `Fs = 44140`. Changing either changes decay times
  unless the constants are rescaled (§3.5).
- The oscillator frequency is **constant within a block** (pitch EG stepped at 690 Hz, no per-sample interpolation). The pitch sweep of a kick is a staircase of 1.45 ms steps.
- Parameter changes (including LFO modulation) land at block boundaries and cannot be smoother than that, except where the engine adds explicit smoothers (§3.6).

---

## 1. Oscillators (`Oscillator.c`, `wavetable.c`)

### 1.1 Phase and frequency

`OscInfo.phase` is a `uint32` accumulator (2³² = one cycle). `phaseInc` is set at control rate by `osc_setFreq`:

```
f      = osc.freq * osc.pitchMod * osc.modNodeValue
phaseInc = f / Fs * 2^32            (computed as (TABLESIZE*f/Fs) << 20, or (1024*f/Fs) << 22 — same value, float→uint32)
```

- `osc.freq` comes from `osc_setBaseNote`: `MidiNoteFrequencies[clamp(coarse + (note - 60), 0, 127)] * detune(fine)`. `coarse` and `fine` are the two bytes of `midiFreq`.
  `detune(v) = 1 + (v/127 - 0.5)·(1.0595 - 1)` — **linear** (not exponential) ±½-semitone factor, ≈ ±50 cents. The default coarse is 70 (it is a note index, not a frequency).
- `pitchMod` is `1 + pitchEG·amount (+ snap burst)` — a **linear-frequency multiplier**, not semitones (§3.2).
- `modNodeValue` is the multiplier that LFO/velocity modulation writes through the "coarse/fine" destination (`TYPE_SPECIAL_F`). It is **1.0 by default** and is multiplied into the frequency.
- Every voice's oscillator phase is **hard-reset on trigger** (§5.2).

### 1.2 Waveforms (`enum OscWaveforms`: SINE, TRI, SAW, REC, NOISE, PWM)

| Wave | Generation | Notes |
|---|---|---|
| **SINE** | 4097-entry int16 table (`sine_table`, one guard point). `idx = phase>>20` (12 bit), linear interpolation with a 20-bit fraction in **int64** arithmetic: `y = a + ((b-a)*frac >> 20)`. | **[measured]** Table starts at **−32767 at phase 0** (a −cos), crosses zero rising at index 1024 (= ¼ cycle), peaks at index 2048. The kick start-phase constants (§5.2) rely on this. |
| **TRI / SAW / REC** | **11 band-limited tables of 1024 samples** (`triTable/sawTable/recTable[11][1024]`), one table per octave, indexed `tableOffset`. 10-bit index (`phase>>22`) + 22-bit fraction, linear interpolation. | See §1.3 for how the table is chosen and what is in them. |
| **NOISE** | **Sample-and-hold white noise at a tunable rate**: each time the phase accumulator wraps, `output = GetRngValue()` (hardware TRNG, 32-bit, truncated to int16); hold between wraps. Not band-limited. | This is the "tuned digital noise" of the snare/cymbal/hat: noise pitch = hold rate. `NOISE` ignores FM (`TODO FM noise`). |
| **PWM** | Two interpolated reads of the **saw table**, second offset by `pwm·(2³²/2)` in phase, `out = sat16(saw(p) − saw(p+offset))`. | Classic difference-of-saws PWM (offset 0…½ cycle). Both variants (`calcPwmBlock`, `calcPwmFmBlock`) index their neighbours correctly. The FM variant adds the same `(uint32_t)` modulation term to the phase before computing both reads. The `pwm` parameter is `PWM` CC2 value/127. |

Waveform ≥ 6 ("samples") is a dead branch (`calcUserSample…` bodies are `#if 0`).

### 1.3 Band-limited tables and their selection **[measured]**

I parsed the three tables and measured their spectra:

| Table | Design f₀ (note) | Highest significant harmonic (saw / tri / rec, −50 dB re strongest) | Nyquist limit at 44.14 kHz |
|---|---|---|---|
| 4 | 130.8 Hz (48) | 61 / 17 / 69 | 168 |
| 5 | 261.6 Hz (60) | 34 / 15 / 45 | 84 |
| 6 | 523.3 Hz (72) | 18 / 11 / 32 | 42 |
| 7 | 1046.5 Hz (84) | 9 / 7 / 20 | 21 |
| 8 | 2093 Hz (96) | 5 / 6 / 12 | 10 |
| 9 | 4186 Hz (108) | 2 / 5 / 8 | 5 |
| 10 | 8372 Hz (120) | 1 / 3 / 7 | 2 |

Table choice is `osc_calcWavetableFreq`:

```c
fast_log2(v)        = 31 - clz(v)                       // uint8_t return
freqToMidiNote(f)   = 12*fast_log2((uint32_t)(f/440)) + 70
freqToTableIndex(f) = freqToMidiNote(f) / 12            // uint8_t return
tableOffset         = min(that, 10)
```

**[measured by running this arithmetic in C]** For `f < 440 Hz`, `(uint32_t)(f/440) = 0`, `clz(0) = 32`, so `fast_log2` returns `31−32 = −1 → 255` as `uint8_t`;
`12·255+70 = 3130; 3130/12 = 260 → uint8_t 4`. So **all frequencies below 440 Hz use table 4**, 440–880 → 5, 880–1760 → 6, 1760–3520 → 7, 3520–7040 → 8, 7040–14080 → 9, ≥14080 → 10.
Tables 0–3 are never used. (Whether the wrap was intentional is unknowable; the behaviour is deterministic and is the sound of the instrument.)

Two audible consequences:

1. **Slight aliasing near the top of each octave band**: the table in use has more harmonics than fit under Nyquist once the played frequency exceeds ≈ (Nyquist / highest harmonic): e.g. table 4 (saw, 61 harmonics) aliases above ≈ 360 Hz, table 5 above ≈ 650 Hz, table 6 above ≈ 1.2 kHz. Aliased partials are at the 1/h saw level (≈ −30…−40 dB), so they are quiet but present. This is part of the character; **preserve**.
2. **The "kick" range (< 440 Hz) is a fixed, relatively rich table.** The pitch envelope sweeps through frequencies, but the table never changes below 440 Hz, so there is no table-switch click in the lower register.

The interpolation reads `table[k][itg+1]` with `itg ≤ 1023` — **index 1024 is the first element of the next row** (row-major) and for `k = 10` it reads **past the array**. **[measured]** All saw rows start at 0, tri rows at −32767, so for saw/tri the next-row value equals the wrap value; for **rec** the first elements differ per row (0, 0, −1, 0, 3, 10, 38, 136, 396, 2879, 338), so the last-sample interpolation for rec at tables 8–9 heads toward a slightly wrong value (up to ≈ 7 % of full scale at the last 1/1024 of the cycle). Documented in `lxr-porting-notes.md` as an *original behaviour → problem → adaptation* item.

### 1.4 Frequency modulation

FM here is **phase modulation of a table oscillator by an int16 buffer**:

```
// carrier osc, modulator samples m[i] (int16, already scaled by the modulator's gain)
index   = phase + ((uint32_t)(m[i] * osc.fmMod)) << S      // S = 17 for sine carrier, 19 for table carriers
out     = interp(table, index)
phase  += phaseInc
```

- Units: for a **sine carrier** the peak phase offset is `m·fmMod/32768` cycles; for **table carriers** it is `m·fmMod/8192` cycles. **Table carriers see a 4× deeper FM index** for the same settings.
- **Negative modulator samples are cast `(uint32_t)` of a negative float** — undefined behaviour in C, but defined on the target (Cortex-M7 `VCVT.U32.F32` saturates to **0**; **[measured]** the same on this Apple-silicon host). The effect is that **only the positive half-cycle of the modulator contributes to the phase offset** (half-wave rectified FM). **[inferred; verify on reference build]**. On x86-64 the same expression would give a different (wrapped) result, so the port must implement this explicitly (`max(0, m*fmMod)` as a saturating convert) — see porting notes.
- The effective depth is `fmMod = fmModAmount · pitchEG` (updated per block in `calcDrumVoiceAsync`: `osc.fmMod = fmModAmount * egPitchVal`) **and** the modulator buffer was already scaled by `fmModAmount` (`calcNextOscSampleBlock(&modOsc, modBuf, …, gain=fmModAmount)`), so the index is **proportional to `fmModAmount²·pitchEG`** and decays with the pitch envelope. FM brightness is therefore a function of the pitch EG decay; there is no separate FM envelope.
- **Drum voices only** can choose between FM and "mix" mode (`CC2_MIX_MOD_n`, default on): in *mix* mode `out = osc·(1−fmModAmount) + modOsc·fmModAmount` (saturating `QADD16`) — an oscillator **cross-fade**, not FM.
- Hat/cymbal: `osc` is FM'd by `modOsc·g1 + modOsc2·g2` (saturating add of two int16 buffers), where `g1,g2 = fmModAmount1/2`, and `osc.fmMod = 1` (fixed; set at init). `modOsc2` defaults to **NOISE**, i.e. FM by sample-and-hold noise → inharmonic metallic/noisy spectrum.

### 1.5 Why this suits percussion

- A kick is `sine(+tri/saw/…)` whose frequency is `f·(1 + EG·32)` with the EG sampled at 690 Hz: a hard exponential-ish sweep with cheap state (one `phaseInc` per block).
- **Always restarting the phase at a known point** (§5.2) makes every hit identical (phase-coherent attack), which is what a drum needs.
- The oscillator can **start at a non-zero-crossing** ("offset" transient, §4) to put a controlled click in the first sample.
- Noise as an oscillator (S&H at tunable rate) gives snare/hat/cymbal timbres without filters.
- Table-lookup + 32-bit phase accumulator is about 10 instructions per sample on a Cortex-M7.

---

## 2. Filter (`ResonantFilter.c`) — the only filter in the voices

One topology: a **zero-delay-feedback (TPT) state-variable filter**, 2-pole (12 dB/oct), with several output taps. **No 24 dB mode exists.**

### 2.1 Coefficients (control rate)

```
cutoff param c ∈ [0,1]            // 7-bit param / 127
shaped = valueShaperF2F(c, -0.9)  // (1+k)c/(1+k|c|), k = 2s/(1.0001 - s) = -0.947
f      = shaped * 0.45            // normalised to Fs, so f_max = 0.45*Fs = 19.86 kHz
g      = fastTan(π f)             // Padé: (15x - x³)/(15 - 6x²) — not exact tan
Q param (reso) r ∈ [0,1]:  q = 1 - r;  if q < 0.1 → q = 0.02     // "damping" R
R      = (f >= 0.4499) ? 1 : q    // at max cutoff, resonance forced off
```

**[measured]** cutoff mapping: param 16 → 150 Hz, 32 → 346 Hz, 48 → 616 Hz, 64 → 1.0 kHz, 80 → 1.6 kHz, 96 → 2.8 kHz, 112 → 5.6 kHz, 127 → 19.9 kHz. Param 0 → 0 Hz (silent LP).
`fastTan` error is ~5 % at the top (6.0 vs 6.3 at `x = 1.414`), i.e. the top of the cutoff range is a few percent lower than nominal. A property of the filter's sound, to be preserved.
`SVF_setReso`: the resonance knob is *inverted damping*: `r = 0.9 → q = 0.1`, `r ≥ 0.9 → q jumps to 0.02` (self-oscillation territory). **Discontinuity at r = 0.9** (q 0.1 → 0.02).

### 2.2 Per-sample core (`SVF_calcBlockZDF`)

Input `x = softClipTwo(sample/32768 · drive)`, with `softClipTwo(x) = x·tanhXdX(x/2)`, `tanhXdX(x) = ((x²+105)x²+945)/((15x²+420)x²+945)` (a Padé of tanh(x)/x).
`drive = 0.4 + d²·6` (`SVF_setDrive`, `d` = filter-drive param/127; `USE_SHAPER_NONLINEARITY=0`, `UNIT_GAIN_DRIVE=0`).

With `ENABLE_NONLINEAR_INTEGRATORS=0` (this build) `t0 = t1 = 1`, so the loop is the **linear** TPT SVF:

```
g0  = 1/(1 + 2 R g)
f1  = g² g0
y1  = (f1·x + s2 + g g0 s1) / (f1 + 1)          // lowpass
xx  = x - y1
y0  = (softClipTwo(s1) + g·xx) · g0             // bandpass
s1' = softClipTwo(s1) + 2g(xx - 2R·y0)          // state 1 (nonlinear: soft-clipped before the update)
s2' = s2 + 2g·y0
```

Outputs by `filterType` (stored as `param+1`): **1 LP** `= tanh(y1)` (via `fastTanh` rational `4.15x/(4.29+x²)`, hard ±1 beyond ±1.95), **2 HP** `x − 2R·y0 − y1`, **3 BP** `y0`, **4 unity-gain BP** `2R·y0`, **5 notch** `x − 2R·y0`, **6 peak** `y1 − h`, **7 "naive 2-pole"** (a different LP: two cascaded one-pole integrators with a feedback term, ± clamping at ±1 — "added to fix the kick transient problems with the nonlinear ZDF LP"), 8 off (no-op). Output: `sat16(out·0x7fff)`.

So the filter's only nonlinearities are the **input soft-clipper (drive)**, **soft-clipped s1 state feedback**, and the **tanh on the LP output**. The HP/BP/notch outputs are *not* tanh'd.

Design notes:
- **State is zeroed on every trigger** (`SVF_reset`: `s1 = s2 = a = b = 0`) "to prevent wrong transient". This guarantees identical transients per hit and is a deliberate click-ish reset.
- `removeMaliciousSample` (compiled at `-O0`) replaces NaN states with 0 before each block — a firmware-safety hack for unstable settings.
- Coefficients are **recomputed once per block** and **not interpolated**: LFO/velocity modulated cutoff therefore steps at 690 Hz (the LFO itself is a stair).
- There is a "Cheap" variant (`SVF_calcBlockCheapZDF`) selected only when reverb is active — dead in this build (`USE_REVERB=0`).
- `USE_PEAK` (snare peak filter) is 0.

---

## 3. Envelopes, smoothing and click control

### 3.1 Amp EG: `SlopeEg2` (double precision)

State: `value` (linear ramp 0–1, stepped **per block**), `attack`, `decay` (per-block increments), `slope`/`invSlope` (shape), `repeat/repeatCnt`, `state ∈ {STOPPED, A, D, REPEAT}`.

```
trigger():   if repeat==0:  state = A            // value NOT reset: attack continues from the current level
             else:          state = REPEAT; value = 1; repeatCnt = repeat
calc():      A:      value += attack; if ≥1 → value=1, state=D; return shape(value, invSlope)
             D:      if value>0: value -= decay; return shape(value, slope)   else return 0   (value is NOT clamped at 0: it can go slightly negative once)
             REPEAT: if value>0: value -= attack  (attack time is reused as the loop decay)
                     else: repeatCnt--; if >0: value=1 else {state=D; value=1}
                     return shape(value, slope)
shape(v, s) = (1+s)·v / (1+s·|v|)      // rational "slope" curve, s = 2a/(1-a), a ∈ (-1,1)
```

- `slope` parameter `d` (0–127): `a = ((d/127) − 0.5)·1.999`, so the curve goes from strongly concave to strongly convex through linear at 64. Decay uses `slope`; attack uses the mirrored `invSlope`.
- Time mapping (`slopeEg2_calcTime`): `inc = min(1, 2·(1 − (1+K)v/(1+K|v|)))` with `v = d/127` and `K = 1998` (decay) or `198` (attack); the `·2, cap 1` came with the 64-sample block (`USE_BIG_SAMPLE_BUFFER`).
  **[measured]** *time of the linear ramp 1→0* (the output is then reshaped by `slope`): decay param 0 → 1.4 ms (one block), 5 → 60 ms, 10 → 125 ms, 20 → 270 ms, 32 → 490 ms, 64 → 1.47 s, 96 → 4.5 s, 110 → 9.4 s, 120 → 25 s, 126 → 183 s, **127 → increment 0 = never decays** (infinite sustain). Attack param 0 → 1.4 ms, 5 → 6.6 ms, 20 → 28 ms, 64 → 147 ms, 100 → 535 ms, 127 → never reaches 1.
- `isSync` divides by 16 (`AMP_EG_SYNC` build option, off).

### 3.2 Pitch EG: `DecayEg` and the snap EG

`DecayEg`: `value = 1` on trigger (hard reset), `value −= decay` per block (floor 0), output `shape(value, slope)`. Pitch amount (`MODAMNT`): `amount = (d/127)²·32` and the oscillator multiplier is `pitchMod = 1 + EG·amount` → at full amount the start frequency is **33× the base**, falling back to 1× — a **linear-frequency** sweep curved by `slope`, not a semitone sweep. **[measured]** `amount` at d = 32/64/96/127 → 2.0 / 8.1 / 18.3 / 32.0.
`calcTime` for the decay uses `K = 0.99` mapping: `K = 198`.

`SnapEg` (transient type 0, "Snp"): `value = 1` on trigger, per block `out = value²·24; value −= 0.2·transientPitch`. At `pitch = 1` it lasts 5 blocks (7 ms). The output is **added to the oscillator pitch multiplier** (`pitchMod += snap · transientVolume`, up to +24×). It is a very short, steep pitch snap, not a sample. The drum voice adds it on top of the pitch EG. For hat/cymbal it **replaces** `pitchMod` (`pitchMod = 1 + snap·vol`, they have no pitch EG; the snap EG is only evaluated when transient type is 0).

### 3.3 How the engine avoids clicks (and where it does not)

| Mechanism | Where | Effect |
|---|---|---|
| **Linear gain ramp across the block** | `bufferTool_addGainInterpolated(buf, gain, lastGain, 64)`: `g(i) = last + (i/63)(gain − last)`, in double (drum voices only) | Turns the 690 Hz stepped amp EG into a piecewise-linear gain — removes zipper noise on decays. **Skipped when attack == 1 and in attack/repeat state**: `ampFilterInput = lastGain = EG` (no ramp) so attacks and repeat re-hits stay hard (snappy clap/kick). |
| **EG retrigger does not reset `value`** | `slopeEg2_trigger` | Amp EG attacks *from the current level* — no gain discontinuity from the EG itself. |
| **Phase always reset to a fixed start phase** | `Drum_trigger` (see §5.2) | Reproducible transient but **creates a waveform discontinuity** if the voice is still sounding. The click is partially masked by the EG restart. The original has a commented guard "reset only if the envelope is closed" (`USE_AMP_FILTER`, compiled out). |
| **SVF state zeroed on trigger** | `SVF_reset` | Deterministic filter transient; also a discontinuity on retrigger. |
| **One-pole smoothers (coef 0.01 per sample ≈ 70 Hz)** | per-voice `MixerPageFilter[0]` (voice `vol`), `FaderVolumeFilter` (fader), `distortion.DriveParamFilter` (drive; drum voices 0–2 only) | Smooth stepped parameter changes. Snare/cymbal/hat `FaderVolumeFilter` uses 0.1 (~700 Hz). Their `vol`, drive (`calcDistBlock`, unfiltered) are **not** smoothed. |
| **Delay-time change = 10 ms crossfade between read pointers** | `Delay_setDelayTime`, `fadeSeconds = 0.01` | No zipper/pitch artefacts; delay-time changes while a fade runs are queued (`timePending`). |
| **Trigger-time pan latch** | `triggeredPanL/R` | Pan cannot change within a note. |
| **No dither** in the active path (dither exists but `USE_AMP_FILTER` is off) | — | 16-bit truncation noise is present, unshaped. |

Non-click-safe on purpose or by omission: hat/cymbal/snare amp is applied at **one gain value per block** (`combinedVolume` constant over 64 samples, no ramp) → EG decays are staircase-stepped at 690 Hz on those voices (a −60 dB/second decay moves ≈ −0.09 dB per step, inaudible; fast decays/attacks are stair-stepped).

### 3.4 Retrigger/reset behaviour summary

| State | On trigger |
|---|---|
| Osc phase (main + mod) | **Reset** to a fixed phase (offset-dependent) — drum voices; hat/cymbal reset main and mod oscs (`modOsc.phase = 0`); snare resets main osc only (noise osc free-runs) |
| Amp EG | state → A (or REPEAT), value kept |
| Pitch EG | value ← 1 |
| Snap EG | value ← 1 |
| Transient phase | ← 0 |
| SVF state | **zeroed** (drum voices only!). Snare/cymbal/hat **do not** call `SVF_reset`, so their filters keep ringing across triggers |
| LFO | phase ← `phaseOffset` for each LFO whose `retrigger` source = this voice |
| Velocity | `velo = vel/127` stored; velocity modulator updated |
| Pan | `triggeredPan{L,R}` recomputed |

### 3.5 Time-base dependencies to rescale in any rate/block change

`decay`, `attack`, `snap` decay (`0.2·pitch` per block), `LFO_SR = Fs/B`, `LOW/HI` delay constants (`SECONDS_TO_SAMPLES`), compressor `exp(−1000/(ms·Fs))`, `Delay` fade, the one-pole coefficients that are *fixed numbers* (0.01, 0.1, `DITHER`), the RAT-distortion filter constants (hard-coded for 44 140 Hz, see §6), the sample-rate-reducer rate, and transient playback (a sample-index counter incremented by `pitch·2²⁰` per **sample**, so transient length scales with `Fs`).

### 3.6 Smoothing inventory

Per-voice smoothing is limited to volume/fader/drive (above). **Filter cutoff, resonance, oscillator pitch, FM amount, EG times are not smoothed** (block-stepped). 7-bit parameter resolution makes cutoff sweeps steppy by design (the hardware pots are 7-bit).

---

## 4. Transient generator (`transientGenerator.c`, `snapEg.c`)

`transGen.waveform`: **0 = Snap** (pitch burst, §3.2), **1 = Offset** (start-phase offset, §5.2), **2…13 → samples `transientData[w−2]`** (12 click/hit one-shots, `int8`, 2205 samples ≈ 50 ms at 44.1 k). Names (`MenuText.h`): `Snp, Ofs, Clk, Ck2, Tik, Kik, Rim, Drp, Hat, Clp, Kk2, Snr, Tom, Sp2`.

Sample playback (`transient_calcBlock`): phase counter `p += pitch·2²⁰` per sample, index `p>>20`, `out = volume · int8 · 256` (no interpolation → aliasing, intentionally lo-fi; the "pitch" is just index increment, range 0.25…4: `pitch = 1 + (param/33.9 − 0.75)`), plays once (`p ≥ 2204<<20` → silent), restarts at trigger. Stops contributing after the sample ends. `transientVolumeTable` (a linear 1→0 envelope) exists but is **unused** in the block path (`* transientVolumeTable[phase>>5]` is commented out) — the one-shots play un-enveloped.

Placement in the chain differs per voice: **drum voices add the transient before the SVF** (so it is filtered and part of the amp envelope); **hat/cymbal add it after the SVF** (unfiltered; scaled by `combinedVolume`); **snare** adds it to the osc/noise mix after the (noise-only) filter.

---

## 5. Voice structure details

### 5.1 Per-type signal path (block of 64)

```
DrumVoice (0..2)
  modOsc  ──(gain = fmModAmount)──► modBuf
  if mixOscs:  osc(gain = 1-fmModAmount) ──► buf;  buf += modBuf (sat16)
  else:        buf = osc FM'd by modBuf (gain 1.0)
  buf += transient (sat16)
  buf  = SVF(type, buf)                                  // float inside, int16 out
  buf *= ramp(lastGain → ampEG)                          // double ramp across block (or hard step in attack/repeat)
  if volumeMod: buf *= velo
  buf  = softclip(buf)                                   // calcDistBlockFiltered (drive smoothed)
  buf *= vol(smoothed) * fader(smoothed)                 // int16 truncation here
SnareVoice (3)
  noise = S&H noise osc (×0.9) → SVF                     // filter acts on noise only
  tone  = osc (×(1−mix));  tr = transient
  buf   = (noise·mix + tone + tr) · [vol · (volumeMod? velo:1) · ampEG(block const)] · fader(smoothed)
  buf   = softclip(buf)                                  // calcDistBlock (unsmoothed)
CymbalVoice (4) / HiHatVoice (5)
  mod = modOsc(×g1) + modOsc2(×g2)  (sat16)
  buf = osc FM'd by mod (gain 1.0 cymbal / 0.5 hat) → SVF
  buf += transient (sat16, unfiltered)
  buf *= [vol · (volumeMod? velo:1) · ampEG(block const)] · fader(smoothed)
  buf  = softclip(buf)
```

### 5.2 Start phase and the "offset" transient

`Drum_trigger` (always executed — the guard is compiled out):

```
offset = 1;  if (transGen.waveform == 1) offset -= transGen.volume          // "Ofs" mode: volume = how far from the safe phase
osc.phase  = SINE : 1024 + ((0x3ff<<20) − 1024)·offset     // sine_table[0]=-1 .. [1023]≈zero-cross rising; offset=1 ⇒ zero-cross start, 0 ⇒ trough start (full-scale click)
             TRI/SAW/REC : (0xff<<22)·offset              // ≈ quarter cycle for offset = 1
             else: 0
modOsc.phase = same as osc but with offset = 1 (always the safe phase)
```

**[measured]** `sine_table[0] = −32767`, `[1024] = 12`, `[2048] = 32766`: with `offset=1` the kick's sine starts at its **zero crossing** (no step), with `offset→0` it starts at the **negative peak** (an immediate full-amplitude step — the "click").

### 5.3 Voice count, ownership, stealing

Six statically allocated voices. `voiceControl_noteOn` calls the voice's `*_trigger()`; it first calls `voiceControl_noteOff(voice)` (only MIDI-out bookkeeping — the DSP has no release stage). **No stealing, no allocation, no priority**: a trigger on a sounding voice **re-uses it with the resets in §3.4**. The open and closed hat are **one voice** (`HiHat_trigger(vel, isOpen, note)` sets `oscVolEg.decay = isOpen ? decayOpen : decayClosed`), so a closed-hat track hit *chokes* the open hat's tail simply by restarting the shared EG (and vice-versa). There is no separate choke logic in the DSP.

Why dense percussion is cheap: no polyphony → fixed CPU; one table lookup per oscillator sample; one filter per voice; the only per-sample float code is the SVF and the soft-clipper; everything else is int16 or per-block; the heavy tables live in ITCM/DTCM.

---

## 6. Modulation system

### 6.1 Sources and destinations

| Source | Count | Rate | Output |
|---|---|---|---|
| **Per-voice LFO** | 6 (one per voice) | **control rate** (once per block; `LFO_SR = Fs/64`) | unipolar 0…1 |
| **Velocity modulator** | 6 (one per voice) | set at **trigger**, re-asserted every block | `vel/127` (0…1) |
| Pitch EG, snap EG, amp EG | per voice | control rate | feed fixed destinations (pitch, FM depth, gain), **not routable** |

**There is no filter envelope and no general modulation matrix.** Each LFO has **one destination**; each velocity modulator has **one destination**. Destinations are *any parameter index with a non-null `parameterArray[].ptr`* (the list is in `mod_targ_lineup.ods` / `modTargets` in the menu code).

LFO (`lfo.c`): `uint32` phase, per-block increment `freq/Fc · 2³²` (or tempo-synced: 11 divisions from 4/1 to 1/32 relative to BPM), freq param mapping `f = (0.0078 + p(1−0.0078))³ · 200 Hz` **[measured]** (p=32/127: 3.4 Hz, 64/127: 26 Hz, 96/127: 87 Hz, 127/127: 200 Hz). Note that an "LFO" at 200 Hz is sampled at 690 Hz (aliases, staircases). Waveforms: sine, triangle, saw up, saw down, square, **S&H random** (new value on phase wrap), exp-up (x³), exp-down. Phase retrigger from a chosen voice (or none) to `phaseOffset`. Sine LFO output is `(sine_table[phase>>20]/32767 + 1)/2` and **starts at the minimum** (sine_table[0] = −1).

Modulation write (`modNode_updateValue(node, v)`):

```
orig  = activeParameters[dest] / 127                 // the *stored* 7-bit value
new   = clamp(orig + amount·(2v − 1), 0, 1)          // bipolar, centred on the stored value, amount ∈ 0..1
midiParser_ccHandler(CC(dest), isFloatModulator=1, new)   // → float for float params, itg = new·127 for int params
```

Every block `modNode_resetTargets()` first re-writes the original value of every modulated target (the "undo"), so destinations always return to base when the modulator changes target or amount goes to 0. Velocity destinations **latch** until the next trigger, since the value is re-applied each block. Multiple modulators on one destination: the last writer in the order `LFO(0..5)` (after velocity) wins. `modNode_originalValueChanged` keeps the stored "original" in sync with front-panel edits.

### 6.2 Where modulation is evaluated

**Hybrid, strictly per block/event**: LFO per block, velocity per trigger, EGs per block, parameter-to-DSP conversions at write time, audio-rate smoothing only for volume/fader/drive. Nothing is per-sample except the smoothers and the oscillators' own phase accumulation.

### 6.3 Conceptual graph

```
 vel(trigger) ─► velMod[v] ──(amount)──► ANY param p ◄─(amount)── LFO[v] ◄─retrigger─ trigger of voice r
                                     │ (via ccHandler, 7-bit/float)
 trigger ─► ampEG ──► gain               pitchEG ──► osc.pitchMod ──► phaseInc
              │                              └──► osc.fmMod (FM depth)  snapEG ──► pitchMod (+burst)
 params ─► SVF(f,q,drive,type)   osc waves/coarse/fine   transient{wave,vol,pitch}   dist   pan   routing   fx
```

---

## 7. FX processors (`FX/*`, `FxBus.c`)

A **single** FX slot (`fxBus.fxType`) fed by the **FX bus** (stereo, int16). Which voices feed it is the per-voice output routing parameter (`FX` destination). The bus output is added to the output chosen by `fxBus.audioRouting`. `dryWet` (0…1) mixes *within the bus*: `out = dry + (wet − dry)·dryWet` where `dry` is the bus content (voices routed to the bus). Voices not routed to the FX bus never touch the FX.

| FX | Algorithm (as implemented) | Params (P1…P4) |
|---|---|---|
| **Distortion** (3 types) | **Tube**: input·(1+4·drive) → 128-entry **ECC83 triode transfer table** (linear interp, `(sat16(x)>>9)+64`) → one-pole LP (`coff = 0.0654 + p2·0.924`) → ×`(1.1+0.55·p1)`·p3. **Fold**: `x·(1+4drive)+p1` → LP → **wavefolder** (`|‖mod(x−t, 4t)| − 2t| − t`, t=1) ·p3. **"Clip"** (code: `else // DISTORTION_RAT`): a **RAT pedal model**: input + 0.125·p1·lastOut → HP (7.2 Hz) → LP → HP → LP (hard-coded one-pole coefficients **for Fs = 44140**) → gain `1 + drive·2304` → **slew limiter (6.8/sample)** → ±4.2 clamp → **1N914 diode table** (257 entries) → LP → ·p3. | drive, p1, p2, p3 |
| **Ring mod** | Table oscillator (`osc`, REC by default; wave selectable), freq `p·880 Hz`, `y = (x·carrier) >> 16` (**halves the level**) | freq (P1); wave is a separate CC2 |
| **Compressor** | Feed-forward, detector = |0.5L + 0.5R| (mid, signed-average then abs), level in dB (`20/ln10·ln`), `over = max(0, dB − thresh)`, one-pole envelope in dB with attack/release `exp(−1000/(ms·Fs))` (`attack = 0.03+100a ms`, `release = 25+175r ms`, `thresh = −96…0 dB`), `GR = dB2lin(env·(ratio−1))`, ratios 1/2/3/4/6/8:1, makeup `1+2g`. Hard knee. | attack, release, threshold, makeup; ratio separate CC2 |
| **Delay** | Mono-summed (normal) or stereo ping-pong; **fp16 circular buffer** (`__fp16 FX_BUFFER[32768]`, ≈ 0.742 s max, shared with the dead reverb), linear-interpolated read, one-pole "tone" filter in the loop (`coef = f²`), feedback applied as `(int16)(out·fb)`, 10 ms crossfade on time changes, `range` selects 0.6–20 ms (comb/flange) vs 20 ms–0.74 s (echo) windows. The write value (input + feedback) is clamped to ±1 before storing, so runaway feedback saturates instead of exploding. | time, range, tone, feedback |
| Reverb | **Not built** (`USE_REVERB 0`). Source present: preDelay, 4 input allpasses, 2 plain + 2 mod allpasses, 4 delay lines, LFO 1.31 Hz, TiltEq, early taps 12/24/38/50. Mono-out. | — |

Per-voice **sample-rate reducer** (mixer): S&H counter `cnt += rate_v · rate_all; if ≥ 1 → latch`. Rate = `valueShaper(param, −0.7)`. Off at 1.0 (=param 127).

Master stage: **none**. The summed int16 stereo is `QADD16` saturating (hard clip at ±32767) and goes to the DAC. The commented `mixer_saturateOutputs` (ECC83) is dead code.

---

## 8. Numeric format summary and known quirks of the original

| Stage | Format |
|---|---|
| Oscillators, transients | int16 (table interpolation in int64/int32) |
| Mod buffers | int16, saturating add (`__QADD16`) |
| SVF internals | float32; I/O int16 (`sat16`) |
| Amp EG | **double**; gain ramp in **double**; applied to int16 with truncation |
| Voice volume/pan | float32; pan applied while summing, `data·panL/R` truncated to int16 |
| Bus summing | **int16 saturating SIMD** (`QADD16`) per stereo pair |
| FX | mixed: int16 in/out, float32/double inside; delay storage fp16 |

Quirks worth knowing: `Drum_trigger`'s dead guard; table interpolation read-ahead (§1.3); `(uint32_t)negative` in FM (§1.4); `SVF_reset` only on drum voices; `distortion` `shape−0.0078` makes shape 0 slightly *expanding* (k = −0.0155); `slopeEg2_calcTime` returns an increment of 0 at param 127 (never ends); hard-coded 44140-Hz coefficients in the RAT distortion; Tube FX fraction taken from the *unsaturated* input (`input&0x1FF`) while the index uses the saturated one; delay `FX_BUFFER_SIZE = 0x7FFF` used as a mask; compressor detector on the signed mid signal (anti-phase content is invisible).
