# LXR-02 Modern Desktop VST Synthesizer — UI & Design Guidelines (`guideline.md`)

## 1. Executive Summary & Design Vision

The **LXR-02 Desktop VST Synthesizer** is a modern software instrument inspired by the Erica Synths × Sonic Potions LXR-02 digital drum machine. 

### Core Design Philosophy: "Functional Translation, Not Hardware Emulation"
Hardware instruments are constrained by physical dimensions, limited screen space, component costs, and shared multi-function controls (knobs/buttons multiplexed across layers). A modern digital audio workstation (DAW) plugin has no such physical limitations. 

- **Hardware Limitation Replaced:** Eliminates single-line alphanumeric LCD scrolling, shared data encoders, and blind parameter paging.
- **Software-Native Advantage:** Direct-access parameter decks, high-density yet readable information hierarchy, real-time graphical feedback (filter curves, envelope slopes, velocity meters), and simultaneous multi-voice mixing.
- **Aesthetic Stance:** Contemporary technical instrument. Avoids skeuomorphic photorealism (no fake screws, brushed metal reflections, or faux-3D knob shadows) while steering clear of overly flat or illegible "cyberpunk" tropes.

---

## 2. Layout & Spatial Architecture

The plugin window is built on a high-density, fixed-ratio desktop canvas (1440px+ base viewport, flexible down to standard 1280px DAW plugin windows). The architecture is divided into four distinct functional tiers:

```
+---------------------------------------------------------------------------------------+
|  1. GLOBAL HEADER BAR (Window controls, Preset/Kit Browser, BPM/Sync, Kit Morph, Meter)|
+-----------------------------+---------------------------------------------------------+
|                             |  3. SOUND DESIGN DECK (Central Workspace)               |
|  2. VOICE MATRIX & MIXER    |     - Sub-Header (Voice Engine, Algorithm, Global Tabs) |
|     (Left Panel)            |     - Module 1: OSC & FM Core (2-Op Sine + Click)       |
|     - 6 Voice Strips:       |     - Module 2: Filter (VCF Frequency Curve + Modes)    |
|       BD1, DRM2, DRM3,      |     - Module 3: Envelopes (Visual Curves, AEG/PEG)      |
|       SNARE, CLAP, H-HATS   |     - Module 4: LFO & Drive (Sync rate, fold clip)      |
|     - Faders, Pans, Solo,   +---------------------------------------------------------+
|       Mute, Send levels     |  Master FX Strip (Bus Compressor, Dotted Delay, P-Locks)|
+-----------------------------+---------------------------------------------------------+
|  4. TACTILE 16-STEP SEQUENCER DECK (Horizontal Full Width)                             |
|     - Transport, Voice Context, Bar Selectors (1-16, 17-32, 33-48, 49-64), Pattern Ops|
|     - 16 Horizontal Step Triggers (Tactile Pads, Accents, Rolls, P-Locks, Velocities) |
+---------------------------------------------------------------------------------------+
```

### Hierarchy Breakdown:
1. **Global Header (Top, ~56px):** 
   - Window controls (`● ● ●`), plugin name, firmware/engine branding (`Sonic Potions × Erica Synths`).
   - Kit Browser with quick stepper (`<`, `>`), Kit title (`Kit 07: Berlin Industrial Acid_909x`), and Dirty/Mod state indicator (`*MOD`).
   - Master Timing & Feel: BPM (`136.00` in amber), Sync/Internal toggle, Tap Tempo button, Swing parameter (`54%`).
   - LXR Signature Kit Morphing crossfader (A/B interpolation slider).
   - Master Output stereo VU meter (`-1.8 dB`) and VST3 / Settings cog.

2. **Voice Matrix & Mixer (Left Panel, ~260px width):**
   - 6 Dedicated vertical channel strips: `BD 1`, `DRUM 2`, `DRUM 3`, `SNARE`, `CLAP`, `H-HATS`.
   - Each strip contains:
     - Voice selector tab with active engine tag (`SUB FM`, `FM TOM`, `CLANG`, etc.).
     - Rotary balance/pan pot with numerical readouts (`C`, `L18`, `R22`).
     - High-precision vertical throw faders with calibrated level bars.
     - Individual peak dB readouts (`+0.2dB`, `-3.4dB`, etc.).
     - Tactile `M` (Mute) and `S` (Solo) toggles.
   - Channel send footers for Master Drive Send (`+4.5dB`) and Master Delay Send (`28%`).

3. **Sound Design Deck (Central / Right Area):**
   - Active Voice Banner: Displays current voice (`VOICE 1: BASSDRUM`), engine algorithm description (`2-OP SINE FM + TRANSIENT CLICK`), and workspace navigation tabs (`MAIN SYNTH`, `MOD MATRIX`, `SAMPLE / CLICK`, `KIT ROUTING`).
   - **4 Modular Parameter Sections:**
     - **OSC & FM Core:** Waveform selectors (`PURE SINE`, `TRIANGLE`), FM Amount knob, Coarse Frequency readout (`48.2 Hz`), Ratio (`1:2.00`), and Feedback (`12%`). Dedicated Click generator sub-panel.
     - **Filter (VCF):** Interactive 2D Frequency Response Curve visualizer showing cutoff slope and resonance peak. Rotary cutoff (`1.48 kHz`) and Resonance (`Q: 4.8`) controls. Stepped filter topologies (`LP24`, `BP12`, `HP24`).
     - **Envelopes (AEG / PEG):** Real-time mathematical attack/decay curvature display (`420 ms` total decay), rotary knobs for Attack (`1.2ms`), Decay 1 (`180ms`), Decay 2 (`420ms`), and Pitch Modulation envelope curve toggle.
     - **LFO & Drive:** Host-synced modulation rate (`1/8D`), Saw Down / Triangle wave selector, dynamic destination router (`VCF CUTOFF`), and saturation amount with Tube Fold Clip drive mode.
   - **Master FX Strip:** Unified readouts for Global Bus Compressor (`VCA 4:1`, `GR: -2.4dB`), Global Delay (`DOTTED 1/8`, `FB: 42%`), and P-Lock activity status (`ACTIVE 24 MODS`).

4. **16-Step Horizontal Performance Sequencer (Bottom Deck):**
   - **Full-width horizontal layout** honoring electronic music 16-step sequencing conventions.
   - Organized into 4 distinct bars/beats (`01–04`, `05–08`, `09–12`, `13–16`) using subtle vertical dividers.
   - Navigation strip: Voice target badge (`VOICE 1: BD`), Bar selection tabs (`BAR 1 [1-16]`, `BAR 2`, `BAR 3`, `BAR 4`), Pattern utility buttons (`CLEAR`, `COPY`, `PASTE`, `RANDOM`, `ROLL / FLAM`), and Grid resolution (`1/16th`, `16 / 16`).
   - Tactile step pads featuring active triggers, playhead position halo, P-Lock badges, flam/roll tags, accent flags, and dedicated velocity level micro-bars.

---

## 3. Color System & Theming Tokens

Built upon the **"Sonic Precision"** dark instrumentation theme, calibrated for low eye strain in dim studio environments while providing rapid visual feedback.

| Token Role | Hex Code | Purpose & Application |
|---|---|---|
| `surface-lowest` | `#0c0e15` | Sequencer step wells, deep inset fader troughs, background base. |
| `surface` | `#11131a` | Main chassis background, master panel base. |
| `surface-container-low` | `#191b22` | Card/module backgrounds (Filter, OSC, Sequencer deck). |
| `surface-bright` | `#373941` | Inactive step buttons, inactive borders, slider thumb tracks. |
| **Primary Accent (LXR Amber)** | `#ff6b2b` | Active selected voice, trigger step illumination, tempo values, primary focus borders. |
| **Secondary Accent (Cyan/Teal)** | `#00d4e5` / `#00b4d8` | Filter frequency response curve, P-Locks (`P-LCK`), playhead cursor, active modes (`LP24`). |
| **Tertiary Accent (Acid Lime)** | `#10b981` / `#00e676` | Envelope generator curve (AEG/PEG), audio signal peak presence. |
| **Auxiliary Accent (Violet/Purple)** | `#a855f7` | Sub-step rolls / flams, modulation matrix routing. |
| `text-primary` | `#f1f3f9` | Parameter headers, active numerical readouts, step numbers. |
| `text-secondary` | `#8b90a0` | Inactive parameter labels, sub-headers, utility actions. |
| `text-dim` | `#4b5063` | Units of measurement (dB, Hz, ms, %), inactive step numbers. |

---

## 4. Typography Hierarchy

The type system prioritizes monospaced rhythm and technical clarity.

- **Primary Typeface:** `Space Grotesk` (Google Fonts) — modern geometric grotesque with distinct technical quirks.
- **Secondary / Monospaced Values:** `JetBrains Mono` or `Roboto Mono` — for strictly tabular data (tempo, frequency, dB, millisecond time codes).

### Type Scales:
- **Display / Brand:** `14px` / `Tracking +0.12em` / `Bold (700)` — All-caps (`LXR-02 DIGITAL DRUM SYNTH`).
- **Section Headers:** `12px` / `Tracking +0.08em` / `Semi-Bold (600)` — (`1. OSC & FM CORE`, `VOICE MATRIX & MIXER`).
- **Parameter Readouts:** `13px` / `Medium (500)` — (`1.48 kHz`, `136.00 BPM`, `+0.2 dB`).
- **Control Labels:** `9px – 10px` / `Tracking +0.05em` / `Medium (500)` — All-caps (`CUTOFF`, `RESONANCE`, `ATTACK`).
- **Micro / Sub-Labels:** `8px` — (`STICK 02`, `POLY: 1`, `48.2 Hz`).

---

## 5. Component Specifications & Interaction Rules

### 5.1 Knobs & Continuous Rotary Controllers
- **Visual Anatomy:** Flat cylindrical dial with dark inset base, contrasting 2px indicator pip or radial sweep gauge.
- **Color Coding:** Dials adopt the color of their respective sub-module:
  - Amber (`#ff6b2b`) for Pitch, FM amount, Drive, and Tempo.
  - Cyan (`#00d4e5`) for Filter Cutoff, Resonance, and Modulation.
  - Mint/Green (`#10b981`) for Envelope times and dynamics.
- **Interaction Conventions:**
  - Vertical click-and-drag for linear adjustment (100px travel = full 0–100% sweep).
  - `Shift + Drag` for fine micro-tuning (0.1 increments).
  - `Double Click` or `Alt + Click` resets to default factory parameter value.
  - Mouse wheel scrolling supports stepped increments.

### 5.2 Vertical Faders & Channel Strips
- **Track Length:** 120px travel with center-notched zero-dB indicator.
- **Thumb:** Flat illuminated capsule with horizontal neon indicator line.
- **Channel Header/Selector:** Clicking anywhere on the voice header selects that voice into the central sound design deck without interrupting playback.
- **Solo & Mute:** Exclusive Solo with `Ctrl + Click`; standard latching behavior.

### 5.3 Filter & Envelope Visualizers
- **Filter Curve (VCF):** Real-time SVG cubic bezier path representing the filter pole slope. Cutoff shifts the curve vertex horizontally (20 Hz – 20 kHz log scale); Resonance raises the bell peak amplitude.
- **Envelope Curve (AEG):** Vector polygon illustrating Attack slope, Hold, Decay 1 corner, and Decay 2 tail, with live playback position dot during note triggers.

### 5.4 16-Step Horizontal Sequencer Pads
Each step pad measures approximately `56px × 84px` and encapsulates multi-state status:
- **Inactive Step:** Dark muted container (`#191b22`), dim step number, empty velocity trench.
- **Active Trigger (TRIG):** Radiant amber border, glowing `TRIG` badge, filled velocity bar.
- **Current Playhead:** Vibrant cyan border with pulsating play dot and `PLAY` badge.
- **Parameter Locked (P-LCK):** Dedicated teal tag indicating voice-specific parameter offsets stored on that specific step.
- **Accent / Flam / Roll:** Badges positioned in the top-right corner (`ACC`, `2x`).
- **Velocity Micro-Bar:** Located at the bottom of each pad; click-and-drag vertically on the bar to adjust step velocity (0–127).

---

## 6. Implementation & Code Quality Checklist

When building or updating front-end screens for the LXR-02 VST:
1. **Responsive Constraints:** Maintain flex-grow and grid-template properties such that reducing plugin width collapses non-essential padding rather than clipping the 16 sequencer steps.
2. **Standard Valid CSS Selectors:** Use structural identifiers (e.g., `#step-sequencer`, `.channel-strip:nth-child(1)`) without text-matching selectors (`:contains`, `:has-text`).
3. **High DPI / Retina Readiness:** Use pure CSS and vector SVGs for all rotary gauges, filter curves, envelope lines, and icons. Avoid raster bitmapped knobs.
4. **Accessible Contrast:** Maintain minimum WCAG AA contrast for text labels against the dark chassis (`#11131a`).
