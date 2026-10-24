# lxr_core

The LynnDrum sound engine: the DSP and parameter handler of the Erica Synths LXR firmware (GPL-3.0-only), made
instance-based and callable through `include/lxr/lxr_engine.h`.

- `src/`, `inc/` - **derived** files, produced from the pinned upstream by `Tools/port/make_core.py`
  (mechanical edits only; see `DEVIATIONS.md` L1-L6). Treat them as hand-maintainable source after generation, but
  keep changes mechanical and log them in `DEVIATIONS.md`.
- `platform/` - host replacements for the STM32 HAL/CMSIS surface and the `LxrEngine` state/macro layer (ours).
- `engine/lxr_engine.c`, `include/` - the C API (ours).
- Rule: nothing outside this directory includes upstream-derived code (clean GPL boundary).

Test: `cmake -S Tools/compare -B build-core && cmake --build build-core && python3 Tools/compare/null_test.py build/lxr_ref_render build-core/lxr_render build/scen && build-core/test_instances`.
