# LynnDrum - notices

LynnDrum is free software under the **GNU General Public License v3.0 only** (see `LICENSE`).

## Derivation (truthful statement, per the upstream NOTICE section 7)

The sound engine (`Source/Engine/lxr_core/src`, `.../inc`) and the sequencer (`Source/Sequencer/lxr_seq`, when
added) are **modified versions of the open-source firmware of the Erica Synths LXR-02 drum synthesizer**
(`github.com/erica-synths/lxr-desktop-app`, Copyright (C) 2012-2026 Erica Synths, GPL-3.0-only with the additional
permission and terms in its `NOTICE.md`). They have been changed to run as a software instrument; the exact edits
are reproducible with `Tools/port/make_core.py` and recorded in `DEVIATIONS.md`.

LynnDrum is **not** an Erica Synths product, is not approved by or affiliated with Erica Synths, and is not
official LXR firmware. "Erica Synths", "LXR" and "LXR-02" are trademarks of Erica Synths and are used here only
to state compatibility/derivation.

Per-file policy: derived files keep their upstream copyright/SPDX header; files written for LynnDrum say so in
their header and carry `SPDX-License-Identifier: GPL-3.0-only`.

## Third-party material

- Transient sample tables (`transientTables.c`): reported as CC BY 4.0 (freesound #4102) - attribution text to be
  confirmed against the licence page before release (see `docs/implementation-plan.md` D6).
- `Reference/` holds the unmodified upstream source as a git submodule for study and for the reference harness;
  it is not part of the shipped product.

## Factory content

The factory presets in `Presets/factory/` are original work written for LynnDrum (parameter values chosen with the published DSP behaviour and checked by measurement); no kit or pattern data of the LXR firmware (including its `initKit`) is shipped or used as a default. They are released under GPL-3.0-only with the rest of the project.
