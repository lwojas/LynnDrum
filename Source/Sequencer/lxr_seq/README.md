# lxr_seq

The LynnDrum step sequencer: the LXR sequencer (GPL-3.0-only) made instance-based, driven by the firmware's own
0.25 ms clock that the host injects (`lxrseq_tick`), emitting effects through a sink (`include/lxr/lxr_seq.h`).

- `src/`, `inc/` - derived, produced by `Tools/port/make_seq.py` (mechanical edits, `DEVIATIONS.md` Q1-Q8).
- `platform/` - host layer + `LxrSeq` state/macro layer (ours); `engine/lxr_seq.c`, `include/` - the C API (ours).
- Independent of `lxr_core`: connect them through `LxrSeqSink` (trigger -> `lxr_trigger`, cc -> `lxr_cc`, original CC
  table -> `lxr_original_cc_table`).

Gate: `build-core/lxr_render_seq` over `Tools/ref-harness/scripts/gen_seq_scenarios.py` scenarios must reproduce
`Tools/ref-harness/golden/seq/*.ev` exactly; `build-core/test_seq_instances` for isolation.
