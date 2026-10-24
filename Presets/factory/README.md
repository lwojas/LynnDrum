# Factory presets

Clean-room: authored for LynnDrum with `Tools/kits/make_factory.py` (formulas of `docs/lxr-dsp.md`, checked by measurement). **Nobody has auditioned these by ear yet** - they are plausible starting points, not finished sound design. Edit the recipe, run the script, rebuild.

| Preset | Kit idea | Pattern |
|---|---|---|
| Init | one plain voice each (sine kick with pitch drop, two toms, noise+triangle snare, metallic cymbal and hats); the default of every parameter | none |
| Tight 4/4 | short, punchy | four on the floor, backbeat snare, offbeat hats |
| Deep Backbeat | lower, longer | swung backbeat with ghost snares (probability) |
| Metal Broken | FM toms, bright metallic hats/cymbal | broken beat: polymetric cymbal (32) and tom (12) tracks, flam, shift, probability |

Measured with the reference renderer (`python3 Tools/kits/make_factory.py --measure`; level = peak of the summed buses, decay = time to -40 dB):

```
== Init
  Kick (D1)  peak 0.39 decay(-40dB)   470 ms dominant     48 Hz centroid    101 Hz
  Tom (D2)   peak 0.35 decay(-40dB)   400 ms dominant    108 Hz centroid    197 Hz
  Tom (D3)   peak 0.34 decay(-40dB)   330 ms dominant    194 Hz centroid    332 Hz
  Snare      peak 0.60 decay(-40dB)   230 ms dominant    221 Hz centroid   7525 Hz
  Cymbal     peak 0.49 decay(-40dB)  1200 ms dominant   2635 Hz centroid   7657 Hz
  CH         peak 0.24 decay(-40dB)    60 ms dominant   1870 Hz centroid   9131 Hz
  OH         peak 0.27 decay(-40dB)   440 ms dominant   2177 Hz centroid   9639 Hz
== Tight 4/4
  Kick (D1)  peak 0.39 decay(-40dB)   320 ms dominant     54 Hz centroid    123 Hz
  Tom (D2)   peak 0.34 decay(-40dB)   300 ms dominant    145 Hz centroid    263 Hz
  Tom (D3)   peak 0.34 decay(-40dB)   260 ms dominant    264 Hz centroid    448 Hz
  Snare      peak 0.54 decay(-40dB)   180 ms dominant    221 Hz centroid   7921 Hz
  Cymbal     peak 0.47 decay(-40dB)   920 ms dominant   3518 Hz centroid   8405 Hz
  CH         peak 0.21 decay(-40dB)    40 ms dominant   4666 Hz centroid  10815 Hz
  OH         peak 0.23 decay(-40dB)   290 ms dominant   3421 Hz centroid  10490 Hz
  pattern, 2 bars: peak 0.46, clipped samples 0
== Deep Backbeat
  Kick (D1)  peak 0.40 decay(-40dB)   650 ms dominant     38 Hz centroid     78 Hz
  Tom (D2)   peak 0.35 decay(-40dB)   520 ms dominant     75 Hz centroid    136 Hz
  Tom (D3)   peak 0.35 decay(-40dB)   440 ms dominant    129 Hz centroid    223 Hz
  Snare      peak 0.64 decay(-40dB)   280 ms dominant    145 Hz centroid   7228 Hz
  Cymbal     peak 0.57 decay(-40dB)  1290 ms dominant   1320 Hz centroid   6757 Hz
  CH         peak 0.28 decay(-40dB)    90 ms dominant   1870 Hz centroid   8202 Hz
  OH         peak 0.28 decay(-40dB)   520 ms dominant   2177 Hz centroid   8663 Hz
  pattern, 2 bars: peak 0.49, clipped samples 0
== Metal Broken
  Kick (D1)  peak 0.39 decay(-40dB)   440 ms dominant     48 Hz centroid    204 Hz
  Tom (D2)   peak 0.34 decay(-40dB)   330 ms dominant    129 Hz centroid    396 Hz
  Tom (D3)   peak 0.34 decay(-40dB)   290 ms dominant    372 Hz centroid    650 Hz
  Snare      peak 0.71 decay(-40dB)   200 ms dominant    329 Hz centroid   6440 Hz
  Cymbal     peak 0.57 decay(-40dB)  1290 ms dominant   1110 Hz centroid   9412 Hz
  CH         peak 0.15 decay(-40dB)    50 ms dominant   4354 Hz centroid  10032 Hz
  OH         peak 0.16 decay(-40dB)   390 ms dominant   2489 Hz centroid  11080 Hz
  pattern, 2 bars: peak 0.61, clipped samples 0
```
