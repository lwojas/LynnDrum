# LXR parameter map

```
LXR parameter → source representation → DSP destination → timing/rate → proposed VST parameter
```

The full per-parameter table is in **Appendix A** (generated from `Inc/Soundengine/MIDI/MidiMessages.h` and cross-checked against the
`midiParser_ccHandler` switch in `Src/Soundengine/MIDI/MidiParser.c`). This front section explains the conventions and the cross-cutting rules the table cannot
express.

## 1. Numbering

| Concept | Value |
|---|---|
| Sound parameters (saved in a kit) | **228**: `PAR_*` indices 0…227. One byte each. (`INIT_KIT_SIZE` = 254 bytes; the extra 26 bytes are not itemised — layout not read.) |
| Bank 1 (CC) | `PAR` 1…126 ↔ MIDI CC **n = PAR + 1** (CC 2…127). `PAR_NONE`=0 and `PAR_BANK_CHANGE`=127 are the "stupid offset" wrap (`data1 += 1; data1 &= 0x7f`). |
| Bank 2 (CC2 / NRPN) | `PAR` 128…227 ↔ CC2/NRPN index `PAR − 128`. |
| Beyond 228 | UI/global values (`PAR_MORPH`, `PAR_BPM`, step edit values, MIDI channels, …). Not sound parameters; mutes live at CC2 118…124. |

Source of truth for a port: **`Inc/Parameters.h` (`enum ParamEnums`) + the `ccHandler` switch**. The two numbering systems are bridged by the offset above; the port should
index by `PAR` and never by CC.

## 2. Value representation

- **Every parameter is a 7-bit integer 0…127** (`activeParameters[idx]`). Floats are `v/127`. Parameters handled as floats (`value.flt`) lose nothing beyond the 7-bit quantisation; integer-handled ones (EG times, slopes, pan, coarse/fine, enums, LFO sync) receive `itg`.
- When *modulated*, the destination receives the unquantised float (`isFloatModulator`) and `itg = trunc(v·127)`. So **modulated continuous parameters are smoother than the stored ones, modulated integer parameters step in 1/127 units.**
- Enumerations (`waveform`, `filterType`, LFO wave, retrigger, sync, transient wave, audio out, FX type…) are plain 0…N−1 integers. Under modulation they are mapped as `floor(N·v)` (clamped to N−1), except filter type (`floor(7·v)+1`, clamped to 7) and the retrigger source (`7·v`).
- The "type" column of `parameterArray[]` (`TYPE_UINT8/FLT/SPECIAL_F/UINT32/SPECIAL_P`) is used **only** by modulators to read/restore the original value. It does not define the parameter's range or unit.

## 3. Transform recipes referenced by the table

| Name | Transform | Notes |
|---|---|---|
| Filter cutoff | `f = shaper(p, −0.9)·0.45`, `g = fastTan(πf)` | exponential-ish; see `lxr-dsp.md` §2. |
| Reso | `q = 1 − p`; `q < 0.1 → 0.02` | jump at p ≥ 0.9 (0.1 → 0.02). |
| Filter drive | `drive = 0.4 + p²·6` | CC2. |
| Amp attack/decay | `inc = min(1, 2(1 − (1+K)v/(1+K v)))`, `K=198` (attack) / `1998` (decay) | per-block increment; **127 ⇒ ∞**. |
| Slope | `a = (p/127 − 0.5)·1.999; slope = 2a/(1−a)`; attack uses the mirror | 64 ≈ linear. |
| Pitch EG amount | `(p/127)²·32` | linear-frequency multiplier. |
| Coarse / Fine | `note = clamp(coarse + (played − 60), 0..127)`; `freq = MidiNoteFrequencies[note]·(1 + (fine/127 − ½)·0.0595)` | The table `MidiNoteFrequencies` is in `MidiNoteNumbers.h`. |
| LFO rate | `(0.0078125 + p(1 − 0.0078125))³·200 Hz` | sync overrides with BPM-based division (11 steps). |
| Decimation | `shaper(p, −0.7)`; per-voice × global | 1.0 = off. |
| Transient pitch | `1 + (p/33.9 − 0.75)` (0.25 … 4.0) | sample-index increment, not Hz. |
| Pan | `L = √((127 − p)/127)`, `R = √(p/127)`, **latched at trigger** | constant-power (centre = −3 dB each). |
| FX dry/wet | `dryWet = p/100` | **7-bit value / 100**: p ∈ (100…127] gives wet > 100 % (overdrive of the blend). The UI presumably caps at 100; the engine does not. |
| FX P1…P4 | meaning depends on `fxType` (see §5) | |

## 4. Timing / rate classes

| Class | Meaning | Examples |
|---|---|---|
| **trigger** | latched when a note triggers | pan, velocity, osc start phase, LFO phase reset, hat open/closed decay |
| **block** | takes effect at the next 64-frame block start; DSP state derived at control rate | waveforms, tuning, EG times, slopes, filter cutoff/Q/drive/type, FM/mix amounts, LFO rate/wave/sync/amount, transient settings, volume (then smoothed) |
| **block + smoothed** | block-quantised then one-pole smoothed at audio rate | voice `vol` (+ fader), drum-voice distortion drive (voices 0–2 only) |
| **event** | affects a selector, not a DSP value | FX type, routing, delay type, modulation destinations, mute |
| **modulated (block)** | rewritten each block by LFO/velocity (§6 of `lxr-dsp.md`) | any parameter chosen as destination |

## 5. FX parameters (`PAR_FX_P1…P4`)

`FxBus_setParameter(idx, p)` stores `parameter[idx]` then re-pushes all four to the active FX:

| fxType | P1 | P2 | P3 | P4 | Extra |
|---|---|---|---|---|---|
| 1 Drive | drive (`FX_P1`→`setDrive`; gain `1+4d` / `1+2304d` for RAT) | `p1` (type-specific: tube output trim / fold DC offset / RAT feedback) | `p2` (tone LP coef) | `p3` (output level) | `FX_DIST_TYPE` Tube/Fold/Clip |
| 2 Ring | carrier freq (`p·880 Hz`) | — | — | — | `FX_WAVE` |
| 3 Comp | attack (0.03–100 ms) | release (25–200 ms) | threshold (−96…0 dB) | makeup (1…3×) | `FX_RATIO` |
| 4 Delay | time | range | tone (LP coef = p²) | feedback | `FX_DELAY_TYPE` |

## 6. Proposed VST parameter strategy (summary — design in `lxr-vst-architecture.md`)

1. **One generated parameter table** (JSON/X-macro) is the single source of truth: id, name, voice, group, PAR index, kind (`int7`/`float7`/`enum`/`bool`), enum labels, default, display function, engine setter, rate class, UI binding. It drives APVTS creation, the engine setter switch, kit save/load, docs and the UI metadata.
2. Expose all **sound parameters (≈ 200 meaningful, excluding the `UNUSED`/NRPN/protocol slots)** as host parameters. Continuous: `AudioParameterFloat` with **127 steps** (interval 1/127) so the host quantises exactly as the hardware does; enums as `AudioParameterChoice`; bools as `AudioParameterBool`.
   *Rationale:* automation and DAW presets must reproduce kits bit-exactly; extra resolution would silently diverge from the reference.
3. Do **not** expose the modulation-destination selectors (`VEL_DEST`, `LFO TARGET/VOICE`) as plain numeric parameters. Expose them as choice parameters generated from the `modTargets` table (the engine's legal-destination list lives in UI code, `menu/Cc2Text.c`, and must be lifted into the table).
4. The **hardware faders** (`adc_getFaderVolume`) are *not* kit parameters. They map to a separate per-voice `fader` host parameter (the mixer strips in the mockup) multiplying `vol`.
5. Sequencer values (`PAR_STEP_*`, `PAR_ROLL`, `PAR_BPM`, euclid…) are **not** sound parameters. They belong to the **sequencer module** (in scope for v1 — see `lxr-sequencer.md` §4.3 for its parameter set: global/per-track/per-step values, a small host-automatable subset, per-step data in plugin state), not to this table. The only link between the two is the **p-lock destination list**: a step's `param1Nr/param2Nr` index the same `modTarget`-flagged rows of this table.
6. Modulation must write to an **engine-internal modulated copy**, never back into the host parameter (see the porting note on the `resetTargets`/`ccHandler` loop).

## 7. Items needing the reference build to resolve

- The conversion from `VEL_DEST` / `TARGET_LFO` / `VOICE_LFO` values to a destination `PAR` index (`modNode_setDestination`) is done in the front-panel/menu path (`frontPanelParser.c` ≈ lines 76–95, `menu.c`, `Cc2Text.c`). I identified the call sites but did not trace them to the end.
- Exact kit-file layout (`presetManager.c`, 3.2 k lines) — only needed for importing real LXR kits.
- 7-bit value → display strings (`Cc2Text.c`, `menu.c`) for matching the hardware's displayed units.

---

## Appendix A — full parameter table (generated)

Rows with `—` in the first column are protocol slots / non-DSP / outside the 228-parameter sound space. Voice names: BD/Drum1, Drum2, Drum3 = `DrumVoice[0..2]`; Snare, Cymbal, HiHat = the single instances. Rate classes as in §4.

| PAR idx | CC / CC2 | Name | Voice | DSP destination (as implemented) | Type | Rate | Proposed VST param |
|---|---|---|---|---|---|---|---|
| — | 0 | CC_BANK_CHANGE | — | protocol / unused (kit-select, mod wheel, NRPN framing) | — | — | not a parameter |
| — | 1 | CC_MODWHEEL | — | protocol / unused (kit-select, mod wheel, NRPN framing) | — | — | not a parameter |
| 1 | 2 | OSC_WAVE_DRUM1 | BD/Drum1 | drumVoice[0].osc.waveform (0..5) | enum | block | choice Sin/Tri/Saw/Rec/Noise/PWM |
| 2 | 3 | OSC_WAVE_DRUM2 | Drum2 | drumVoice[1].osc.waveform (0..5) | enum | block | choice Sin/Tri/Saw/Rec/Noise/PWM |
| 3 | 4 | OSC_WAVE_DRUM3 | Drum3 | drumVoice[2].osc.waveform (0..5) | enum | block | choice Sin/Tri/Saw/Rec/Noise/PWM |
| 4 | 5 | OSC_WAVE_SNARE | Snare | snareVoice.osc.waveform | enum | block | choice |
| — | 6 | NRPN_DATA_ENTRY_COARSE | — | protocol / unused (kit-select, mod wheel, NRPN framing) | — | — | not a parameter |
| 6 | 7 | CYM_WAVE1 | Cymbal | cymbalVoice.osc.waveform | enum | block | choice |
| 7 | 8 | WAVE1_HH | HiHat | hatVoice.osc.waveform | enum | block | choice |
| 8 | 9 | F_OSC1_COARSE | BD/Drum1 | drumVoice[0].osc.midiFreq[15:8] → osc_recalcFreq → osc.freq → phaseInc | u7 | block | int 0..127 (note offset; default 70) |
| 9 | 10 | F_OSC1_FINE | BD/Drum1 | drumVoice[0].osc.midiFreq[7:0] → osc.freq (±½ semitone, linear) | u7 | block | int 0..127 (±50 ct) |
| 10 | 11 | F_OSC2_COARSE | Drum2 | drumVoice[1].osc.midiFreq[15:8] → osc_recalcFreq → osc.freq → phaseInc | u7 | block | int 0..127 (note offset; default 70) |
| 11 | 12 | F_OSC2_FINE | Drum2 | drumVoice[1].osc.midiFreq[7:0] → osc.freq (±½ semitone, linear) | u7 | block | int 0..127 (±50 ct) |
| 12 | 13 | F_OSC3_COARSE | Drum3 | drumVoice[2].osc.midiFreq[15:8] → osc_recalcFreq → osc.freq → phaseInc | u7 | block | int 0..127 (note offset; default 70) |
| 13 | 14 | F_OSC3_FINE | Drum3 | drumVoice[2].osc.midiFreq[7:0] → osc.freq (±½ semitone, linear) | u7 | block | int 0..127 (±50 ct) |
| 14 | 15 | F_OSC4_COARSE | Snare | snareVoice.osc.midiFreq[15:8] → osc_recalcFreq → osc.freq → phaseInc | u7 | block | int 0..127 (note offset; default 70) |
| 15 | 16 | F_OSC4_FINE | Snare | snareVoice.osc.midiFreq[7:0] → osc.freq (±½ semitone, linear) | u7 | block | int 0..127 (±50 ct) |
| 16 | 17 | F_OSC5_COARSE | Cymbal | cymbalVoice.osc.midiFreq[15:8] → osc_recalcFreq → osc.freq → phaseInc | u7 | block | int 0..127 (note offset; default 70) |
| 17 | 18 | F_OSC5_FINE | Cymbal | cymbalVoice.osc.midiFreq[7:0] → osc.freq (±½ semitone, linear) | u7 | block | int 0..127 (±50 ct) |
| 18 | 19 | F_OSC6_COARSE | HiHat | hatVoice.osc.midiFreq[15:8] → osc_recalcFreq → osc.freq → phaseInc | u7 | block | int 0..127 (note offset; default 70) |
| 19 | 20 | F_OSC6_FINE | HiHat | hatVoice.osc.midiFreq[7:0] → osc.freq (±½ semitone, linear) | u7 | block | int 0..127 (±50 ct) |
| 20 | 21 | MOD_WAVE_DRUM1 | BD/Drum1 | drumVoice[0].modOsc.waveform | enum | block | choice |
| 21 | 22 | MOD_WAVE_DRUM2 | Drum2 | drumVoice[1].modOsc.waveform | enum | block | choice |
| 22 | 23 | MOD_WAVE_DRUM3 | Drum3 | drumVoice[2].modOsc.waveform | enum | block | choice |
| 23 | 24 | CYM_WAVE2 | Cymbal | cymbalVoice.modOsc.waveform | enum | block | choice |
| 24 | 25 | CYM_WAVE3 | Cymbal | cymbalVoice.modOsc2.waveform (default NOISE) | enum | block | choice |
| 25 | 26 | WAVE2_HH | HiHat | hatVoice.modOsc.waveform | enum | block | choice |
| 26 | 27 | WAVE3_HH | HiHat | hatVoice.modOsc2.waveform (default NOISE) | enum | block | choice |
| 27 | 28 | SNARE_NOISE_F | Snare | snareVoice.noiseOsc.freq = p·22000 Hz (× modNodeValue) | f32 | block | float 0..1 (display Hz) |
| 28 | 29 | SNARE_MIX | Snare | snareVoice.mix (noise vs tone crossfade) | f32 | block | float |
| 29 | 30 | CYM_MOD_OSC_F1 | Cymbal | cymbalVoice.modOsc.midiFreq coarse | u7 | block | int |
| 30 | 31 | CYM_MOD_OSC_F2 | Cymbal | cymbalVoice.modOsc2.midiFreq coarse | u7 | block | int |
| 31 | 32 | CYM_MOD_OSC_GAIN1 | Cymbal | cymbalVoice.fmModAmount1 | f32 | block | float |
| 32 | 33 | CYM_MOD_OSC_GAIN2 | Cymbal | cymbalVoice.fmModAmount2 | f32 | block | float |
| 33 | 34 | MOD_OSC_F1 | HiHat | hatVoice.modOsc.midiFreq coarse | u7 | block | int |
| 34 | 35 | MOD_OSC_F2 | HiHat | hatVoice.modOsc2.midiFreq coarse | u7 | block | int |
| 35 | 36 | MOD_OSC_GAIN1 | HiHat | hatVoice.fmModAmount1 | f32 | block | float |
| 36 | 37 | MOD_OSC_GAIN2 | HiHat | hatVoice.fmModAmount2 | f32 | block | float |
| 37 | 38 | FILTER_FREQ_DRUM1 | BD/Drum1 | drumVoice[0].filter: SVF_directSetFilterValue(shaper(p,-0.9)) → f=0.45·shaped; g=tan(πf) recalculated per block | f32 | block | float (display Hz) |
| 38 | 39 | FILTER_FREQ_DRUM2 | Drum2 | drumVoice[1].filter: SVF_directSetFilterValue(shaper(p,-0.9)) → f=0.45·shaped; g=tan(πf) recalculated per block | f32 | block | float (display Hz) |
| 39 | 40 | FILTER_FREQ_DRUM3 | Drum3 | drumVoice[2].filter: SVF_directSetFilterValue(shaper(p,-0.9)) → f=0.45·shaped; g=tan(πf) recalculated per block | f32 | block | float (display Hz) |
| 40 | 41 | SNARE_FILTER_F | Snare | snareVoice.filter cutoff (same mapping) | f32 | block | float |
| 41 | 42 | CYM_FIL_FREQ | Cymbal | cymbalVoice.filter cutoff | f32 | block | float |
| 42 | 43 | HAT_FILTER_F | HiHat | hatVoice.filter cutoff | f32 | block | float |
| 43 | 44 | RESO_DRUM1 | BD/Drum1 | drumVoice[0].filter.q = 1−p (q<0.1 → 0.02) | f32 | block | float |
| 44 | 45 | RESO_DRUM2 | Drum2 | drumVoice[1].filter.q = 1−p (q<0.1 → 0.02) | f32 | block | float |
| 45 | 46 | RESO_DRUM3 | Drum3 | drumVoice[2].filter.q = 1−p (q<0.1 → 0.02) | f32 | block | float |
| 46 | 47 | SNARE_RESO | Snare | snareVoice.filter.q | f32 | block | float |
| 47 | 48 | CYM_RESO | Cymbal | cymbalVoice.filter.q | f32 | block | float |
| 48 | 49 | HAT_RESO | HiHat | hatVoice.filter.q | f32 | block | float |
| 49 | 50 | VELOA1 | BD/Drum1 | drumVoice[0].oscVolEg.attack (per-block increment, K=198) | u7 | block | int 0..127 (display ms) |
| 50 | 51 | VELOD1 | BD/Drum1 | drumVoice[0].oscVolEg.decay (per-block increment, K=1998; 127 = ∞) | u7 | block | int 0..127 (display time) |
| 51 | 52 | VELOA2 | Drum2 | drumVoice[1].oscVolEg.attack (per-block increment, K=198) | u7 | block | int 0..127 (display ms) |
| 52 | 53 | VELOD2 | Drum2 | drumVoice[1].oscVolEg.decay (per-block increment, K=1998; 127 = ∞) | u7 | block | int 0..127 (display time) |
| 53 | 54 | VELOA3 | Drum3 | drumVoice[2].oscVolEg.attack (per-block increment, K=198) | u7 | block | int 0..127 (display ms) |
| 54 | 55 | VELOD3 | Drum3 | drumVoice[2].oscVolEg.decay (per-block increment, K=1998; 127 = ∞) | u7 | block | int 0..127 (display time) |
| 55 | 56 | VELOA4 | Snare | snareVoice.oscVolEg.attack (per-block increment, K=198) | u7 | block | int 0..127 (display ms) |
| 56 | 57 | VELOD4 | Snare | snareVoice.oscVolEg.decay (per-block increment, K=1998; 127 = ∞) | u7 | block | int 0..127 (display time) |
| 57 | 58 | VELOA5 | Cymbal | cymbalVoice.oscVolEg.attack (per-block increment, K=198) | u7 | block | int 0..127 (display ms) |
| 58 | 59 | VELOD5 | Cymbal | cymbalVoice.oscVolEg.decay (per-block increment, K=1998; 127 = ∞) | u7 | block | int 0..127 (display time) |
| 59 | 60 | VELOA6 | HiHat | hatVoice.oscVolEg.attack (per-block increment, K=198) | u7 | block | int 0..127 (display ms) |
| 60 | 61 | VELOD6 | HiHat | hatVoice.decayClosed (copied into oscVolEg.decay at trigger) | u7 | block | int 0..127 (display time) |
| 61 | 62 | VELOD6_OPEN | HiHat | hatVoice.decayOpen | u7 | block | int |
| 62 | 63 | VOL_SLOPE1 | BD/Drum1 | drumVoice[0].oscVolEg.slope/invSlope | u7 | block | int 0..127 (64 = linear) |
| 63 | 64 | VOL_SLOPE2 | Drum2 | drumVoice[1].oscVolEg.slope/invSlope | u7 | block | int 0..127 (64 = linear) |
| 64 | 65 | VOL_SLOPE3 | Drum3 | drumVoice[2].oscVolEg.slope/invSlope | u7 | block | int 0..127 (64 = linear) |
| 65 | 66 | EG_SNARE1_SLOPE | Snare | snareVoice.oscVolEg.slope | u7 | block | int |
| 66 | 67 | CYM_SLOPE | Cymbal | cymbalVoice.oscVolEg.slope | u7 | block | int |
| 67 | 68 | VOL_SLOPE6 | HiHat | hatVoice.oscVolEg.slope/invSlope | u7 | block | int 0..127 (64 = linear) |
| 68 | 69 | REPEAT1 | Snare | snareVoice.oscVolEg.repeat (clap re-hits) | u7 | block | int 0..127 (repeat count) |
| 69 | 70 | CYM_REPEAT | Cymbal | cymbalVoice.oscVolEg.repeat | u7 | block | int |
| 70 | 71 | PITCHD1 | BD/Drum1 | drumVoice[0].oscPitchEg.decay | u7 | block | int 0..127 |
| 71 | 72 | PITCHD2 | Drum2 | drumVoice[1].oscPitchEg.decay | u7 | block | int 0..127 |
| 72 | 73 | PITCHD3 | Drum3 | drumVoice[2].oscPitchEg.decay | u7 | block | int 0..127 |
| 73 | 74 | PITCHD4 | Snare | snareVoice.oscPitchEg.decay | u7 | block | int 0..127 |
| 74 | 75 | MODAMNT1 | BD/Drum1 | drumVoice[0].egPitchModAmount = (p/127)²·32 (linear-frequency multiplier) | u7 | block | int 0..127 |
| 75 | 76 | MODAMNT2 | Drum2 | drumVoice[1].egPitchModAmount = (p/127)²·32 (linear-frequency multiplier) | u7 | block | int 0..127 |
| 76 | 77 | MODAMNT3 | Drum3 | drumVoice[2].egPitchModAmount = (p/127)²·32 (linear-frequency multiplier) | u7 | block | int 0..127 |
| 77 | 78 | MODAMNT4 | Snare | snareVoice.egPitchModAmount = (p/127)²·32 (linear-frequency multiplier) | u7 | block | int 0..127 |
| 78 | 79 | PITCH_SLOPE1 | BD/Drum1 | drumVoice[0].oscPitchEg.slope | u7 | block | int |
| 79 | 80 | PITCH_SLOPE2 | Drum2 | drumVoice[1].oscPitchEg.slope | u7 | block | int |
| 80 | 81 | PITCH_SLOPE3 | Drum3 | drumVoice[2].oscPitchEg.slope | u7 | block | int |
| 81 | 82 | PITCH_SLOPE4 | Snare | snareVoice.oscPitchEg.slope | u7 | block | int |
| 82 | 83 | FMAMNT1 | BD/Drum1 | drumVoice[0].fmModAmount (FM depth / mix crossfade) | f32 | block | float |
| 83 | 84 | FMDTN1 | BD/Drum1 | drumVoice[0].modOsc.midiFreq coarse (modulator pitch) | u7 | block | int |
| 84 | 85 | FMAMNT2 | Drum2 | drumVoice[1].fmModAmount (FM depth / mix crossfade) | f32 | block | float |
| 85 | 86 | FMDTN2 | Drum2 | drumVoice[1].modOsc.midiFreq coarse (modulator pitch) | u7 | block | int |
| 86 | 87 | FMAMNT3 | Drum3 | drumVoice[2].fmModAmount (FM depth / mix crossfade) | f32 | block | float |
| 87 | 88 | FMDTN3 | Drum3 | drumVoice[2].modOsc.midiFreq coarse (modulator pitch) | u7 | block | int |
| 88 | 89 | VOL1 | BD/Drum1 | drumVoice[0].vol (× fader, smoothed one-pole 0.01 drum voices) | f32 | block | float |
| 89 | 90 | VOL2 | Drum2 | drumVoice[1].vol (× fader, smoothed one-pole 0.01 drum voices) | f32 | block | float |
| 90 | 91 | VOL3 | Drum3 | drumVoice[2].vol (× fader, smoothed one-pole 0.01 drum voices) | f32 | block | float |
| 91 | 92 | VOL4 | Snare | snareVoice.vol (× fader, smoothed one-pole 0.01 drum voices) | f32 | block | float |
| 92 | 93 | VOL5 | Cymbal | cymbalVoice.vol (× fader, smoothed one-pole 0.01 drum voices) | f32 | block | float |
| 93 | 94 | VOL6 | HiHat | hatVoice.vol (× fader, smoothed one-pole 0.01 drum voices) | f32 | block | float |
| 94 | 95 | PAN1 | BD/Drum1 | drumVoice[0].pan latched at trigger → triggeredPanL/R = √((127−p)/127), √(p/127) | u7 | trigger | int 0..127 (L..R) |
| 95 | 96 | PAN2 | Drum2 | drumVoice[1].pan latched at trigger → triggeredPanL/R = √((127−p)/127), √(p/127) | u7 | trigger | int 0..127 (L..R) |
| 96 | 97 | PAN3 | Drum3 | drumVoice[2].pan latched at trigger → triggeredPanL/R = √((127−p)/127), √(p/127) | u7 | trigger | int 0..127 (L..R) |
| — | 98 | NRPN_FINE | — | protocol / unused (kit-select, mod wheel, NRPN framing) | — | — | not a parameter |
| — | 99 | NRPN_COARSE | — | protocol / unused (kit-select, mod wheel, NRPN framing) | — | — | not a parameter |
| 99 | 100 | PAN4 | Snare | snareVoice.pan latched at trigger → triggeredPanL/R = √((127−p)/127), √(p/127) | u7 | trigger | int 0..127 (L..R) |
| 100 | 101 | PAN5 | Cymbal | cymbalVoice.pan latched at trigger → triggeredPanL/R = √((127−p)/127), √(p/127) | u7 | trigger | int 0..127 (L..R) |
| 101 | 102 | PAN6 | HiHat | hatVoice.pan latched at trigger → triggeredPanL/R = √((127−p)/127), √(p/127) | u7 | trigger | int 0..127 (L..R) |
| 102 | 103 | OSC1_DIST | BD/Drum1 | drumVoice[0].distortion.shape = 2s/(1−s), s=p−1/128 | f32 | block | float |
| 103 | 104 | OSC2_DIST | Drum2 | drumVoice[1].distortion.shape = 2s/(1−s), s=p−1/128 | f32 | block | float |
| 104 | 105 | OSC3_DIST | Drum3 | drumVoice[2].distortion.shape = 2s/(1−s), s=p−1/128 | f32 | block | float |
| 105 | 106 | SNARE_DISTORTION | Snare | snareVoice.distortion.shape | f32 | block | float |
| 106 | 107 | CYMBAL_DISTORTION | Cymbal | cymbalVoice.distortion.shape | f32 | block | float |
| 107 | 108 | HAT_DISTORTION | HiHat | hatVoice.distortion.shape | f32 | block | float |
| 108 | 109 | VOICE_DECIMATION1 | BD/Drum1 | mixer_decimation_rate[0] = shaper(p,−0.7) | f32 | block | float |
| 109 | 110 | VOICE_DECIMATION2 | Drum2 | mixer_decimation_rate[1] = shaper(p,−0.7) | f32 | block | float |
| 110 | 111 | VOICE_DECIMATION3 | Drum3 | mixer_decimation_rate[2] = shaper(p,−0.7) | f32 | block | float |
| 111 | 112 | VOICE_DECIMATION4 | Snare | mixer_decimation_rate[3] = shaper(p,−0.7) | f32 | block | float |
| 112 | 113 | VOICE_DECIMATION5 | Cymbal | mixer_decimation_rate[4] = shaper(p,−0.7) | f32 | block | float |
| 113 | 114 | VOICE_DECIMATION6 | HiHat | mixer_decimation_rate[5] = shaper(p,−0.7) | f32 | block | float |
| 114 | 115 | VOICE_DECIMATION_ALL | all | mixer_decimation_rate[6] (global factor) | f32 | block | float |
| 115 | 116 | FREQ_LFO1 | BD/Drum1 | drumVoice[0].lfo.freq = (0.0078+p·0.992)³·200 Hz (or sync division base) | f32 | block | float |
| 116 | 117 | FREQ_LFO2 | Drum2 | drumVoice[1].lfo.freq = (0.0078+p·0.992)³·200 Hz (or sync division base) | f32 | block | float |
| 117 | 118 | FREQ_LFO3 | Drum3 | drumVoice[2].lfo.freq = (0.0078+p·0.992)³·200 Hz (or sync division base) | f32 | block | float |
| 118 | 119 | FREQ_LFO4 | Snare | snareVoice.lfo.freq = (0.0078+p·0.992)³·200 Hz (or sync division base) | f32 | block | float |
| 119 | 120 | FREQ_LFO5 | Cymbal | cymbalVoice.lfo.freq = (0.0078+p·0.992)³·200 Hz (or sync division base) | f32 | block | float |
| 120 | 121 | FREQ_LFO6 | HiHat | hatVoice.lfo.freq = (0.0078+p·0.992)³·200 Hz (or sync division base) | f32 | block | float |
| 121 | 122 | AMOUNT_LFO1 | BD/Drum1 | drumVoice[0].lfo.modTarget.amount | f32 | block | float |
| 122 | 123 | AMOUNT_LFO2 | Drum2 | drumVoice[1].lfo.modTarget.amount | f32 | block | float |
| 123 | 124 | AMOUNT_LFO3 | Drum3 | drumVoice[2].lfo.modTarget.amount | f32 | block | float |
| 124 | 125 | AMOUNT_LFO4 | Snare | snareVoice.lfo.modTarget.amount | f32 | block | float |
| 125 | 126 | AMOUNT_LFO5 | Cymbal | cymbalVoice.lfo.modTarget.amount | f32 | block | float |
| 126 | 127 | AMOUNT_LFO6 | HiHat | hatVoice.lfo.modTarget.amount | f32 | block | float |
| — | 128 | RESERVED4 | — | protocol / unused (kit-select, mod wheel, NRPN framing) | — | — | not a parameter |
| 128 | CC2:0 | CC2_FILTER_DRIVE_1 | BD/Drum1 | drumVoice[0].filter.drive = 0.4+(p)²·6 (input soft-clip gain) | f32 | block | float |
| 129 | CC2:1 | CC2_FILTER_DRIVE_2 | Drum2 | drumVoice[1].filter.drive = 0.4+(p)²·6 (input soft-clip gain) | f32 | block | float |
| 130 | CC2:2 | CC2_FILTER_DRIVE_3 | Drum3 | drumVoice[2].filter.drive = 0.4+(p)²·6 (input soft-clip gain) | f32 | block | float |
| 131 | CC2:3 | CC2_FILTER_DRIVE_4 | Snare | snareVoice.filter.drive = 0.4+(p)²·6 (input soft-clip gain) | f32 | block | float |
| 132 | CC2:4 | CC2_FILTER_DRIVE_5 | Cymbal | cymbalVoice.filter.drive = 0.4+(p)²·6 (input soft-clip gain) | f32 | block | float |
| 133 | CC2:5 | CC2_FILTER_DRIVE_6 | HiHat | hatVoice.filter.drive = 0.4+(p)²·6 (input soft-clip gain) | f32 | block | float |
| 134 | CC2:6 | CC2_MIX_MOD_1 | BD/Drum1 | drumVoice[0].mixOscs (1 = cross-fade, 0 = FM) | bool | block | choice FM/Mix |
| 135 | CC2:7 | CC2_MIX_MOD_2 | Drum2 | drumVoice[1].mixOscs (1 = cross-fade, 0 = FM) | bool | block | choice FM/Mix |
| 136 | CC2:8 | CC2_MIX_MOD_3 | Drum3 | drumVoice[2].mixOscs (1 = cross-fade, 0 = FM) | bool | block | choice FM/Mix |
| 137 | CC2:9 | CC2_VOLUME_MOD_ON_OFF1 | BD/Drum1 | drumVoice[0].volumeMod (velocity → gain) | bool | block | toggle |
| 138 | CC2:10 | CC2_VOLUME_MOD_ON_OFF2 | Drum2 | drumVoice[1].volumeMod (velocity → gain) | bool | block | toggle |
| 139 | CC2:11 | CC2_VOLUME_MOD_ON_OFF3 | Drum3 | drumVoice[2].volumeMod (velocity → gain) | bool | block | toggle |
| 140 | CC2:12 | CC2_VOLUME_MOD_ON_OFF4 | Snare | snareVoice.volumeMod (velocity → gain) | bool | block | toggle |
| 141 | CC2:13 | CC2_VOLUME_MOD_ON_OFF5 | Cymbal | cymbalVoice.volumeMod (velocity → gain) | bool | block | toggle |
| 142 | CC2:14 | CC2_VOLUME_MOD_ON_OFF6 | HiHat | hatVoice.volumeMod (velocity → gain) | bool | block | toggle |
| 143 | CC2:15 | CC2_VELO_MOD_AMT_1 | BD/Drum1 | velocityModulators[i].amount | f32 | block | float |
| 144 | CC2:16 | CC2_VELO_MOD_AMT_2 | Drum2 | velocityModulators[i].amount | f32 | block | float |
| 145 | CC2:17 | CC2_VELO_MOD_AMT_3 | Drum3 | velocityModulators[i].amount | f32 | block | float |
| 146 | CC2:18 | CC2_VELO_MOD_AMT_4 | Snare | velocityModulators[i].amount | f32 | block | float |
| 147 | CC2:19 | CC2_VELO_MOD_AMT_5 | Cymbal | velocityModulators[i].amount | f32 | block | float |
| 148 | CC2:20 | CC2_VELO_MOD_AMT_6 | HiHat | velocityModulators[i].amount | f32 | block | float |
| 149 | CC2:21 | CC2_VEL_DEST_1 | BD/Drum1 | velocity modulator destination (index into modTargets[] in menu/Cc2Text.c → param idx) [setter path not read] | index | event | choice (generated list) |
| 150 | CC2:22 | CC2_VEL_DEST_2 | Drum2 | velocity modulator destination (index into modTargets[] in menu/Cc2Text.c → param idx) [setter path not read] | index | event | choice (generated list) |
| 151 | CC2:23 | CC2_VEL_DEST_3 | Drum3 | velocity modulator destination (index into modTargets[] in menu/Cc2Text.c → param idx) [setter path not read] | index | event | choice (generated list) |
| 152 | CC2:24 | CC2_VEL_DEST_4 | Snare | velocity modulator destination (index into modTargets[] in menu/Cc2Text.c → param idx) [setter path not read] | index | event | choice (generated list) |
| 153 | CC2:25 | CC2_VEL_DEST_5 | Cymbal | velocity modulator destination (index into modTargets[] in menu/Cc2Text.c → param idx) [setter path not read] | index | event | choice (generated list) |
| 154 | CC2:26 | CC2_VEL_DEST_6 | HiHat | velocity modulator destination (index into modTargets[] in menu/Cc2Text.c → param idx) [setter path not read] | index | event | choice (generated list) |
| 155 | CC2:27 | CC2_WAVE_LFO1 | BD/Drum1 | drumVoice[0].lfo.waveform (8) | enum | block | choice |
| 156 | CC2:28 | CC2_WAVE_LFO2 | Drum2 | drumVoice[1].lfo.waveform (8) | enum | block | choice |
| 157 | CC2:29 | CC2_WAVE_LFO3 | Drum3 | drumVoice[2].lfo.waveform (8) | enum | block | choice |
| 158 | CC2:30 | CC2_WAVE_LFO4 | Snare | snareVoice.lfo.waveform (8) | enum | block | choice |
| 159 | CC2:31 | CC2_WAVE_LFO5 | Cymbal | cymbalVoice.lfo.waveform (8) | enum | block | choice |
| 160 | CC2:32 | CC2_WAVE_LFO6 | HiHat | hatVoice.lfo.waveform (8) | enum | block | choice |
| 161 | CC2:33 | CC2_VOICE_LFO1 | BD/Drum1 | LFO destination: voice selector (UI-level; ccHandler ignores) [setter path not read] | index | event | choice |
| 162 | CC2:34 | CC2_VOICE_LFO2 | Drum2 | LFO destination: voice selector (UI-level; ccHandler ignores) [setter path not read] | index | event | choice |
| 163 | CC2:35 | CC2_VOICE_LFO3 | Drum3 | LFO destination: voice selector (UI-level; ccHandler ignores) [setter path not read] | index | event | choice |
| 164 | CC2:36 | CC2_VOICE_LFO4 | Snare | LFO destination: voice selector (UI-level; ccHandler ignores) [setter path not read] | index | event | choice |
| 165 | CC2:37 | CC2_VOICE_LFO5 | Cymbal | LFO destination: voice selector (UI-level; ccHandler ignores) [setter path not read] | index | event | choice |
| 166 | CC2:38 | CC2_VOICE_LFO6 | HiHat | LFO destination: voice selector (UI-level; ccHandler ignores) [setter path not read] | index | event | choice |
| 167 | CC2:39 | CC2_TARGET_LFO1 | BD/Drum1 | LFO destination: parameter selector within the voice (UI-level) [setter path not read] | index | event | choice (generated list) |
| 168 | CC2:40 | CC2_TARGET_LFO2 | Drum2 | LFO destination: parameter selector within the voice (UI-level) [setter path not read] | index | event | choice (generated list) |
| 169 | CC2:41 | CC2_TARGET_LFO3 | Drum3 | LFO destination: parameter selector within the voice (UI-level) [setter path not read] | index | event | choice (generated list) |
| 170 | CC2:42 | CC2_TARGET_LFO4 | Snare | LFO destination: parameter selector within the voice (UI-level) [setter path not read] | index | event | choice (generated list) |
| 171 | CC2:43 | CC2_TARGET_LFO5 | Cymbal | LFO destination: parameter selector within the voice (UI-level) [setter path not read] | index | event | choice (generated list) |
| 172 | CC2:44 | CC2_TARGET_LFO6 | HiHat | LFO destination: parameter selector within the voice (UI-level) [setter path not read] | index | event | choice (generated list) |
| 173 | CC2:45 | CC2_RETRIGGER_LFO1 | BD/Drum1 | drumVoice[0].lfo.retrigger (0=off, 1..6 = source voice) | enum | block | choice |
| 174 | CC2:46 | CC2_RETRIGGER_LFO2 | Drum2 | drumVoice[1].lfo.retrigger (0=off, 1..6 = source voice) | enum | block | choice |
| 175 | CC2:47 | CC2_RETRIGGER_LFO3 | Drum3 | drumVoice[2].lfo.retrigger (0=off, 1..6 = source voice) | enum | block | choice |
| 176 | CC2:48 | CC2_RETRIGGER_LFO4 | Snare | snareVoice.lfo.retrigger (0=off, 1..6 = source voice) | enum | block | choice |
| 177 | CC2:49 | CC2_RETRIGGER_LFO5 | Cymbal | cymbalVoice.lfo.retrigger (0=off, 1..6 = source voice) | enum | block | choice |
| 178 | CC2:50 | CC2_RETRIGGER_LFO6 | HiHat | hatVoice.lfo.retrigger (0=off, 1..6 = source voice) | enum | block | choice |
| 179 | CC2:51 | CC2_SYNC_LFO1 | BD/Drum1 | drumVoice[0].lfo.sync (0=free, 1..11 = 4/1…1/32) → phaseInc | enum | block | choice |
| 180 | CC2:52 | CC2_SYNC_LFO2 | Drum2 | drumVoice[1].lfo.sync (0=free, 1..11 = 4/1…1/32) → phaseInc | enum | block | choice |
| 181 | CC2:53 | CC2_SYNC_LFO3 | Drum3 | drumVoice[2].lfo.sync (0=free, 1..11 = 4/1…1/32) → phaseInc | enum | block | choice |
| 182 | CC2:54 | CC2_SYNC_LFO4 | Snare | snareVoice.lfo.sync (0=free, 1..11 = 4/1…1/32) → phaseInc | enum | block | choice |
| 183 | CC2:55 | CC2_SYNC_LFO5 | Cymbal | cymbalVoice.lfo.sync (0=free, 1..11 = 4/1…1/32) → phaseInc | enum | block | choice |
| 184 | CC2:56 | CC2_SYNC_LFO6 | HiHat | hatVoice.lfo.sync (0=free, 1..11 = 4/1…1/32) → phaseInc | enum | block | choice |
| 185 | CC2:57 | CC2_OFFSET_LFO1 | BD/Drum1 | drumVoice[0].lfo.phaseOffset = p·2³² | f32 | block | float |
| 186 | CC2:58 | CC2_OFFSET_LFO2 | Drum2 | drumVoice[1].lfo.phaseOffset = p·2³² | f32 | block | float |
| 187 | CC2:59 | CC2_OFFSET_LFO3 | Drum3 | drumVoice[2].lfo.phaseOffset = p·2³² | f32 | block | float |
| 188 | CC2:60 | CC2_OFFSET_LFO4 | Snare | snareVoice.lfo.phaseOffset = p·2³² | f32 | block | float |
| 189 | CC2:61 | CC2_OFFSET_LFO5 | Cymbal | cymbalVoice.lfo.phaseOffset = p·2³² | f32 | block | float |
| 190 | CC2:62 | CC2_OFFSET_LFO6 | HiHat | hatVoice.lfo.phaseOffset = p·2³² | f32 | block | float |
| 191 | CC2:63 | CC2_FILTER_TYPE_1 | BD/Drum1 | drumVoice[0].filterType = p+1 (LP,HP,BP,UBP,Notch,Peak,Naive2P) | enum | block | choice |
| 192 | CC2:64 | CC2_FILTER_TYPE_2 | Drum2 | drumVoice[1].filterType = p+1 (LP,HP,BP,UBP,Notch,Peak,Naive2P) | enum | block | choice |
| 193 | CC2:65 | CC2_FILTER_TYPE_3 | Drum3 | drumVoice[2].filterType = p+1 (LP,HP,BP,UBP,Notch,Peak,Naive2P) | enum | block | choice |
| 194 | CC2:66 | CC2_FILTER_TYPE_4 | Snare | snareVoice.filterType = p+1 (LP,HP,BP,UBP,Notch,Peak,Naive2P) | enum | block | choice |
| 195 | CC2:67 | CC2_FILTER_TYPE_5 | Cymbal | cymbalVoice.filterType = p+1 (LP,HP,BP,UBP,Notch,Peak,Naive2P) | enum | block | choice |
| 196 | CC2:68 | CC2_FILTER_TYPE_6 | HiHat | hatVoice.filterType = p+1 (LP,HP,BP,UBP,Notch,Peak,Naive2P) | enum | block | choice |
| 197 | CC2:69 | CC2_TRANS1_VOL | BD/Drum1 | drumVoice[0].transGen.volume | f32 | block | float |
| 198 | CC2:70 | CC2_TRANS2_VOL | Drum2 | drumVoice[1].transGen.volume | f32 | block | float |
| 199 | CC2:71 | CC2_TRANS3_VOL | Drum3 | drumVoice[2].transGen.volume | f32 | block | float |
| 200 | CC2:72 | CC2_TRANS4_VOL | Snare | snareVoice.transGen.volume | f32 | block | float |
| 201 | CC2:73 | CC2_TRANS5_VOL | Cymbal | cymbalVoice.transGen.volume | f32 | block | float |
| 202 | CC2:74 | CC2_TRANS6_VOL | HiHat | hatVoice.transGen.volume | f32 | block | float |
| 203 | CC2:75 | CC2_TRANS1_WAVE | BD/Drum1 | drumVoice[0].transGen.waveform (0 snap,1 offset,2+ samples) | enum | block | choice |
| 204 | CC2:76 | CC2_TRANS2_WAVE | Drum2 | drumVoice[1].transGen.waveform (0 snap,1 offset,2+ samples) | enum | block | choice |
| 205 | CC2:77 | CC2_TRANS3_WAVE | Drum3 | drumVoice[2].transGen.waveform (0 snap,1 offset,2+ samples) | enum | block | choice |
| 206 | CC2:78 | CC2_TRANS4_WAVE | Snare | snareVoice.transGen.waveform (0 snap,1 offset,2+ samples) | enum | block | choice |
| 207 | CC2:79 | CC2_TRANS5_WAVE | Cymbal | cymbalVoice.transGen.waveform (0 snap,1 offset,2+ samples) | enum | block | choice |
| 208 | CC2:80 | CC2_TRANS6_WAVE | HiHat | hatVoice.transGen.waveform (0 snap,1 offset,2+ samples) | enum | block | choice |
| 209 | CC2:81 | CC2_TRANS1_FREQ | BD/Drum1 | drumVoice[0].transGen.pitch = 1+(p/33.9−0.75)  (0.25…4.0) | u7 | block | int |
| 210 | CC2:82 | CC2_TRANS2_FREQ | Drum2 | drumVoice[1].transGen.pitch = 1+(p/33.9−0.75)  (0.25…4.0) | u7 | block | int |
| 211 | CC2:83 | CC2_TRANS3_FREQ | Drum3 | drumVoice[2].transGen.pitch = 1+(p/33.9−0.75)  (0.25…4.0) | u7 | block | int |
| 212 | CC2:84 | CC2_TRANS4_FREQ | Snare | snareVoice.transGen.pitch = 1+(p/33.9−0.75)  (0.25…4.0) | u7 | block | int |
| 213 | CC2:85 | CC2_TRANS5_FREQ | Cymbal | cymbalVoice.transGen.pitch = 1+(p/33.9−0.75)  (0.25…4.0) | u7 | block | int |
| 214 | CC2:86 | CC2_TRANS6_FREQ | HiHat | hatVoice.transGen.pitch = 1+(p/33.9−0.75)  (0.25…4.0) | u7 | block | int |
| 215 | CC2:87 | CC2_AUDIO_OUT1 | BD/Drum1 | mixer_audioRouting[i] (St1,St2,L1,R1,L2,R2,FX) | enum | block | choice (Main / FX bus / aux outs) |
| 216 | CC2:88 | CC2_AUDIO_OUT2 | Drum2 | mixer_audioRouting[i] (St1,St2,L1,R1,L2,R2,FX) | enum | block | choice (Main / FX bus / aux outs) |
| 217 | CC2:89 | CC2_AUDIO_OUT3 | Drum3 | mixer_audioRouting[i] (St1,St2,L1,R1,L2,R2,FX) | enum | block | choice (Main / FX bus / aux outs) |
| 218 | CC2:90 | CC2_AUDIO_OUT4 | Snare | mixer_audioRouting[i] (St1,St2,L1,R1,L2,R2,FX) | enum | block | choice (Main / FX bus / aux outs) |
| 219 | CC2:91 | CC2_AUDIO_OUT5 | Cymbal | mixer_audioRouting[i] (St1,St2,L1,R1,L2,R2,FX) | enum | block | choice (Main / FX bus / aux outs) |
| 220 | CC2:92 | CC2_AUDIO_OUT6 | HiHat | mixer_audioRouting[i] (St1,St2,L1,R1,L2,R2,FX) | enum | block | choice (Main / FX bus / aux outs) |
| — | 93 | CC2_UNUSED1 | — | legacy MIDI-note override (PAR_MIDI_NOTE n lives elsewhere; dummy slots) | — | — | not a DSP parameter |
| — | 94 | CC2_UNUSED2 | — | legacy MIDI-note override (PAR_MIDI_NOTE n lives elsewhere; dummy slots) | — | — | not a DSP parameter |
| — | 95 | CC2_UNUSED3 | — | legacy MIDI-note override (PAR_MIDI_NOTE n lives elsewhere; dummy slots) | — | — | not a DSP parameter |
| — | 96 | CC2_UNUSED4 | — | legacy MIDI-note override (PAR_MIDI_NOTE n lives elsewhere; dummy slots) | — | — | not a DSP parameter |
| — | 97 | CC2_UNUSED5 | — | legacy MIDI-note override (PAR_MIDI_NOTE n lives elsewhere; dummy slots) | — | — | not a DSP parameter |
| — | 98 | CC2_UNUSED6 | — | legacy MIDI-note override (PAR_MIDI_NOTE n lives elsewhere; dummy slots) | — | — | not a DSP parameter |
| — | 99 | CC2_UNUSED7 | — | legacy MIDI-note override (PAR_MIDI_NOTE n lives elsewhere; dummy slots) | — | — | not a DSP parameter |
| 228 | CC2:100 | CC2_PWM_1 | BD/Drum1 | drumVoice[0].pwm (PWM duty offset) | f32 | block | float |
| 229 | CC2:101 | CC2_PWM_2 | Drum2 | drumVoice[1].pwm (PWM duty offset) | f32 | block | float |
| 230 | CC2:102 | CC2_PWM_3 | Drum3 | drumVoice[2].pwm (PWM duty offset) | f32 | block | float |
| 231 | CC2:103 | CC2_PWM_4 | Snare | snareVoice.pwm (PWM duty offset) | f32 | block | float |
| 232 | CC2:104 | CC2_PWM_5 | Cymbal | cymbalVoice.pwm (PWM duty offset) | f32 | block | float |
| 233 | CC2:105 | CC2_PWM_6 | HiHat | hatVoice.pwm (PWM duty offset) | f32 | block | float |
| 234 | CC2:106 | CC2_FX_TYPE | — | fxBus.fxType (Off/Drive/Ring/Comp/Delay) + FxBus_updateParameter | enum | block | choice |
| 235 | CC2:107 | CC2_FX_ROUTING | — | fxBus.audioRouting (output for the FX bus return) | enum | block | choice |
| 236 | CC2:108 | CC2_FX_AMOUNT | — | fxBus.dryWet = p/100 (!) (see note) | u7 | block | float 0..1 (see porting notes) |
| 237 | CC2:109 | CC2_FX_DIST_TYPE | — | fxBus.distortion.distortionType (Tube/Fold/Clip-RAT) | enum | block | choice |
| 238 | CC2:110 | CC2_FX_P1 | — | fxBus.parameter[0] → FxBus_updateParameter (meaning depends on fxType) | f32 | block | float ×4 (relabel per FX) |
| 239 | CC2:111 | CC2_FX_P2 | — | fxBus.parameter[1] → FxBus_updateParameter (meaning depends on fxType) | f32 | block | float ×4 (relabel per FX) |
| 240 | CC2:112 | CC2_FX_P3 | — | fxBus.parameter[2] → FxBus_updateParameter (meaning depends on fxType) | f32 | block | float ×4 (relabel per FX) |
| 241 | CC2:113 | CC2_FX_P4 | — | fxBus.parameter[3] → FxBus_updateParameter (meaning depends on fxType) | f32 | block | float ×4 (relabel per FX) |
| 242 | CC2:114 | CC2_FX_RATIO | — | Compressor_setRatio (1,2,3,4,6,8) | enum | block | choice |
| 243 | CC2:115 | CC2_FX_WAVE | — | Ringmod_setWave (osc waveform) | enum | block | choice |
| 244 | CC2:116 | CC2_FX_REVERB_TYPE | — | no-op (reverb compiled out) | — | block | omit |
| 245 | CC2:117 | CC2_FX_DELAY_TYPE | — | fxBus.delay.delayType (Normal / Ping-pong) | enum | block | choice |
| —(246+) | CC2:118 | CC2_MUTE_1 | BD/Drum1 | seq_setMute(track) — sequencer mute flag (also blocks MIDI notes) | bool | event | toggle (plugin-level mute) |
| —(246+) | CC2:119 | CC2_MUTE_2 | Drum2 | seq_setMute(track) — sequencer mute flag (also blocks MIDI notes) | bool | event | toggle (plugin-level mute) |
| —(246+) | CC2:120 | CC2_MUTE_3 | Drum3 | seq_setMute(track) — sequencer mute flag (also blocks MIDI notes) | bool | event | toggle (plugin-level mute) |
| —(246+) | CC2:121 | CC2_MUTE_4 | Snare | seq_setMute(track) — sequencer mute flag (also blocks MIDI notes) | bool | event | toggle (plugin-level mute) |
| —(246+) | CC2:122 | CC2_MUTE_5 | Cymbal | seq_setMute(track) — sequencer mute flag (also blocks MIDI notes) | bool | event | toggle (plugin-level mute) |
| —(246+) | CC2:123 | CC2_MUTE_6 | HiHat | seq_setMute(track) — sequencer mute flag (also blocks MIDI notes) | bool | event | toggle (plugin-level mute) |
| —(246+) | CC2:124 | CC2_MUTE_7 | Open HH | seq_setMute(track) — sequencer mute flag (also blocks MIDI notes) | bool | event | toggle (plugin-level mute) |
