# LXR audio flow — complete signal path and routing

Derived from the source, not from the assumed template. Where the real structure differs from the textbook
`host/clock/MIDI → event handling → sequencer → voice allocation → voices → mix → FX → master`, the difference is called out.

## 1. The real pipeline

```
 ┌───────────────────────── event sources (all processed in the main loop / TIM2 ISR, never in parallel with DSP) ──────────────────────────┐
 │  DIN MIDI (uart_processMidi)   USB-MIDI (usb_getMidi)   Front-panel UART (frontPanelParser)   internal sequencer (seq_tick, ms clock)   │
 └──────────────┬──────────────────────┬───────────────────────────┬───────────────────────────────────────┬───────────────────────────────┘
                ▼                      ▼                           ▼                                       ▼
        midiParser_parseMidiMessage ──► note on → midiParser_noteOn → voiceControl_noteOn(voice,note,vel)    seq_triggerVoice → voiceControl_noteOn
                │                       CC/NRPN → midiParser_ccHandler (all parameter writes)                  (also parameter-automation nodes → ccHandler)
                │                       clock/start/stop → clockSync → seq_nextStep
                ▼
        *_trigger(): reset phases / EGs / filter, latch pan+velocity            (state changes only — no audio generated here)
                │
   ═════════════╪═══════════ block boundary (every 64 frames @ 44 140 Hz = 1.45 ms) ══════════════════════════════════════════════════════
                ▼
        mixer_calcNextSampleBlock(out[64 stereo], out2[64 stereo])
          1  read jack-detect GPIO (hardware routing fallback)                      ◄── hardware-only
          2  modNode_resetTargets()           re-apply original values of all modulated parameters (via ccHandler)
          3  modNode_reassignVeloMod()        re-apply latched velocity modulation (via ccHandler)
          4  lfo_dispatchNextValue × 6        advance each LFO one block; write modulated parameter (via ccHandler)
          5  SVF_recalcFreq × 6               g = tan(πf) from the (possibly modulated) cutoff
          6  *_calcAsync × 6                  amp EG, pitch EG, snap EG, osc_setFreq (phaseInc, table select)
          7  clear: out, out2, fxBus buffers (64 stereo frames each)
          8  for v in {Drum1, Drum2, Drum3, Snare, Cymbal, HiHat}:
                 voice block → int16[64] mono        (see lxr-dsp.md §5.1)
                 mixer_decimateBlock(v)              optional sample-rate reducer
                 mixer_addDataToOutput(route[v], panL, panR, …)    pan + saturating add into the chosen destination
          9  FxBus_process(fxBus, out…)             FX processor, result saturating-added into fxBus.audioRouting's output
        │
        ▼
   int16 stereo ping-pong buffers (dma_buffer, dma_buffer2) ──► I2S DMA ──► two CS4344 DACs (DAC1 = out2 pair, DAC2 = out pair)
```

Differences from the textbook model:

1. **No voice-allocation stage.** The mapping event → voice is static (voice number from MIDI channel/track).
2. **Parameter changes and modulation run through the same handler as external MIDI CC** (steps 2–4).
3. **No master processing**: no master volume, no limiter, no master EQ. The "master" is `QADD16` saturation.
4. **The FX is a single send-only bus**, not a master insert (see §3).
5. **The sequencer is not part of the audio callback's timing** — it is polled just before the block, on a wall clock (0.25 ms `systick_ticks`, 96 PPQ internal, 24 sub-ticks per 16th). In the plugin it becomes a host-PPQ-driven event source feeding the same trigger path (`lxr-sequencer.md`).

## 2. Stage inventory (classes, ownership, timing, state)

| Stage | Functions / data | Owner & lifetime | Timing | Allocation | Thread assumption | Update mechanism |
|---|---|---|---|---|---|---|
| MIDI in | `uart_processMidi`, `usb_getMidi`, `midiParser_parseUartData` (state machine) | static FIFO buffers (`FIFO.c`) | polled, per main-loop pass | none | main loop (also TIM2 ISR calls `uart_processMidi`) | n/a |
| Note routing | `midiParser_noteOn`, `voiceControl_noteOn/Off` | `active_voices` bitmask, `voiceStatus[]` | immediate (between blocks) | none | cooperative | direct call |
| Sequencer | `seq_tick`, `seq_processFlam`, `seq_triggerVoice`, `clockSync` | `seq_patternSet` (large static), `seq_stepIndex[7]` … | **wall clock** (0.25 ms ticks), evaluated each block; 96 PPQ, 24 sub-ticks/step | none | cooperative (called with TIM2 IRQ masked) | → `seq_triggerVoice` → `voiceControl_noteOn`; automation nodes → ccHandler |
| Parameters | `midiParser_ccHandler`, `activeParameters[]`, `parameterArray[]` | statics; live in the voice structs | block-quantised | none | cooperative | the switch statement |
| Voice DSP | `calcDrumVoiceAsync/SyncBlock`, `Snare_*`, `HiHat_*`, `Cymbal_*` | `INDTCMZ DrumVoice voiceArray[3]`, `snareVoice`, `hatVoice`, `cymbalVoice` (DTCM) | control tick + 64-sample audio loop | none (VLAs of 64 int16 on stack) | cooperative | direct field writes |
| Mixing | `mixer_addDataToOutput`, `__QADD16`/`__PKHBT` SIMD | out buffers (DMA) | per block | none | cooperative | `mixer_audioRouting[6]` |
| FX | `FxBus_process`, `Delay`, `Compressor`, `Ringmod`, `Distortion_process` | `fxBus` (DTCM), `FX_BUFFER[32768]` fp16 (DTCM) | audio rate in the block | none | cooperative | `FxBus_setParameter` |
| Output | `HAL_I2S_TxCpltCallback`/DMA ISR, `bCurrentSampleValid` | `dma_buffer`, `dma_buffer2` ping-pong | one 64-frame buffer per DMA period (1.45 ms) | none | ISR | flag flip |

## 3. Routing and mixing in detail

### 3.1 Per-voice routing (`mixer_audioRouting[v]`, parameter `PAR_AUDIO_OUT1…6`)

Seven destinations: `St1` (stereo pair on DAC 1), `St2` (stereo pair on DAC 2), `L1`, `R1`, `L2`, `R2` (mono jacks), **`FX`** (the FX bus). Default routing in a fresh kit is whatever the kit says. The router also contains **hardware fallbacks**: if a destination jack has no cable inserted (`switch_*` GPIO), the mixer re-routes to the next available jack (`mixer_checkOutJackAvailable`). In a plugin the jack state is "always connected".

Panning is applied only for the stereo and FX destinations. Mono destinations take the voice at unity. Pan law is **constant-power** `√((127−p)/127)`, `√(p/127)`, computed with `p` **latched at trigger** (`triggeredPanL/R`).

### 3.2 Summation

Voices are added into 16-bit stereo output with **saturating SIMD adds** (`__QADD16` on packed L/R halfwords; `__PKHBT` packs `(int16)(sample·panL)` and `(int16)(sample·panR)`). Six voices at full scale will hard-clip the output. There is no gain compensation, so **the headroom policy is "the kit designer's ears"**.

### 3.3 FX bus

```
 voice (route == FX) ──pan──► fxBusData[64 stereo] (int16, saturating sum)
                                   │
                                   ▼   FxBus_process
                    type = OFF       : out += bus                                  (just an extra "stereo sum")
                    type = DRIVE     : out += bus + (drive(bus) − bus)·dryWet
                    type = RING      : out += bus + (bus·carrier>>16 − bus)·dryWet
                    type = COMP      : out += bus + (comp(bus) − bus)·dryWet
                    type = DELAY     : out += bus + (delay(bus_mono_or_stereo) − bus)·dryWet     (normal = L+R mono-summed; ping-pong = stereo)
                                   │
                                   ▼   written (saturating add) into the output chosen by fxBus.audioRouting
```

Consequences worth noting:
- The FX processes **only voices explicitly routed to it**. Non-FX voices bypass it entirely. There is no "send level": it is a binary routing per voice.
- `dryWet` is "how much of the *bus* is replaced by the effect": at 0 the bus is passed dry, at 1 pure wet. So the FX bus acts as a **routable insert** for the chosen voices.
- Exactly **one** effect type is active at a time. There is no FX chain. (The mockup shows a compressor and a delay simultaneously — see `lxr-ui-architecture.md`.)
- When the FX bus is routed to a mono output (`channels == 1`) most effects (all except the normal delay, which sums L+R) take only the left channel of the bus.

### 3.4 Block-structure facts that matter for the port

- All "stereo" buffers are interleaved L/R int16, 64 frames. Mixer code addresses `outL`/`outR` as `+2` strides and relies on 32-bit aliasing for SIMD. That is pure presentation and does not need to be preserved, but the *saturation points* (per voice sum, bus sum, output) do.
- FX blocks use VLAs sized by `size` (≤ 64) — no persistent per-block state.
- The ping-pong double buffer implies **one block (1.45 ms) of output latency** on top of the one-block event quantisation.

## 4. Timing model and sample-rate assumptions

| Quantity | Value | Where baked in |
|---|---|---|
| Sample rate | **44 140 Hz** (`REAL_FS`) | phase increments, SVF coefficient domain (normalised), LFO rate, EG increments (per block), delay samples, compressor time constants, one-pole coefficients, RAT-distortion filter constants, transient sample lengths, Fc for sync |
| Block | **64 frames** | control tick, EG/LFO rate, gain ramp length, DMA size |
| Output word | 16-bit int | saturation, truncation, no dither |
| Control rate | 689.7 Hz | EGs, LFOs, filter coefficients, pitch |
| Event granularity | 1 block (1.45 ms) | triggers & parameter writes |
| Sequencer clock | `systick_ticks` (0.25 ms units, inferred) via `seq_calcDeltaT(bpm)`: 96 PPQ internal, 24 sub-ticks per 16th; MIDI-clock slave: 24 PPQN / 6 pulses per 16th, BPM from a moving average of inter-pulse time | |

**The engine fundamentally assumes a fixed sample rate and a fixed block size.** Neither is a runtime variable; both are `#define`s used in dozens of places and in precomputed constants.

## 5. Mapping to a plugin (headline only; full discussion in `lxr-vst-architecture.md`)

| Original stage | Plugin equivalent |
|---|---|
| DMA ping-pong + ISR | `processBlock`; an internal 64-frame "engine tick" loop fed from the host buffer |
| `systick_ticks` / `seq_tick` | host PPQ → sub-tick boundaries with sample offsets (`SeqClock`), or an internal sample counter in free-run mode |
| `seq_triggerVoice` + p-lock automation nodes | sequencer trigger → `EventScheduler` → `lxr_set_override` + `lxr_trigger` |
| MIDI parse + note routing | JUCE `MidiBuffer` → note map → `lxr_trigger(voice, note, vel)` events with timestamps |
| `ccHandler` | `lxr_set_param(PAR, 0..127)` setter generated from the parameter table |
| Modulation write-back through `ccHandler` | engine-internal base/modulated parameter pair |
| Jack detect / routing fallback | removed; all outputs "connected" |
| Faders | `fader[v]` parameters |
| `QADD16` summing | float sum with an explicit ±1.0 clip in *reference mode* |
| DAC1/DAC2 | main stereo out + optional aux busses (St2, mono outs) |
