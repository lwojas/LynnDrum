# UI architecture recommendation

Inputs studied: `concept/stitch_lxr_02_vst_ui_design/screen.png` (2560×1768 render of the mockup) and `code.html` (54 kB, the generated Tailwind markup behind it).
`guidelines.md` (repo root) has now been read and is folded in as **§7**. Status of the two inputs: the mockup and the guideline are **inspiration for look, feel and interaction — not a spec for behaviour**. Where either conflicts with how the engine really works, the engine wins and the UI adapts (§2 for the mockup, §7.3 for the guideline).

## 1. What the mockup is

A single window designed at ≈1300 × 860 CSS px (the HTML hard-codes `max-w-[1300px] h-[860px]`; **the plugin will use that as the *design size* only — the layout must be fluid, §6**), dark synth styling (amber / cyan / emerald / violet accents on near-black blue-greys, monospace labels, glow shadows):

```
┌ header: kit browser (‹ KIT 07: name *MOD › ≡) · BPM/SYNC/TAP/SWING · MORPH A──●──B · output meter · VST3 · settings ─────────────┐
├ VOICE MATRIX & MIXER (6 strips) ─┬ MAIN WORKSPACE ───────────────────────────────────────────────────────────────────────────────┤
│ strip: voice button, role,       │ voice title + algorithm text │ tabs: MAIN SYNTH | MOD MATRIX | SAMPLE/CLICK | KIT ROUTING     │
│ pan knob, vertical fader, M / S  │ ┌ 1 OSC & FM CORE ┐┌ 2 FILTER (VCF) ┐┌ 3 ENVELOPES ┐┌ 4 LFO & DRIVE ┐                        │
│ "OUT: MULTI", DRIVE SEND, DELAY  │ │ 2 wave selects, ││ response graph ││ AEG|PEG graph││ dest/shape,   │                        │
│ SEND                             │ │ 4 knobs, click  ││ cutoff/reso    ││ A / D1 / D2  ││ rate/sat knobs│                        │
│                                  │ │ type/level      ││ LP24/BP12/HP24 ││ pitch curve  ││ drive type    │                        │
│                                  │ └─────────────────┘└────────────────┘└──────────────┘└───────────────┘                        │
│                                  │ GLOBAL MASTER FX: compressor · delay · P-LOCKS status                                          │
├ STEP SEQUENCER: voice, bar tabs (1–4), CLEAR/COPY/PASTE/RANDOM/ROLL-FLAM, SCALE, LENGTH; 16 pads (TRIG/ACC/ROLL/P-LCK/LOCK) ───────┤
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

The HTML is **static** apart from ~20 lines of JS (toggle step pad, select voice button). It uses the Tailwind CDN script (online, runtime compile), a Tailwind config with the colour tokens, `Inter` + system-mono fonts, inline SVG for graphs, and CSS gradients for knob caps/fader thumbs. It is a design artefact, not shippable code, but it is an unusually good starting point: the markup/tokens can be ported to components almost one-to-one.

## 2. Mockup vs the real LXR engine (must be settled before building the UI)

The mockup is *LXR-inspired*, not derived from the firmware. Several controls have **no engine counterpart** or mean something different. "The original implementation is the reference", so the UI either honestly reflects the engine, or the engine gets extended in a documented later phase. Decisions are the user's; recommendations below.

| Mockup element | Engine reality | Recommendation |
|---|---|---|
| **Filter "24dB LP / BP12 / HP24"**, response graph | One 2-pole (12 dB/oct) ZDF SVF with 7 modes: LP, HP, BP, unity-BP, notch, peak, "naive 2-pole LP". | Relabel to real modes; draw the response from the actual SVF transfer function (analytic, in JS). |
| **Voice names** BD 1 / DRUM 2 / DRUM 3 / SNARE / CLAP / H-HATS | 3 FM "drum" voices, snare (noise+osc), cymbal (3-osc FM with repeat EG; can sound like a clap), hi-hat (closed/open on one voice). | Name by engine role; "CLAP" is the cymbal/repeat voice. The mockup's role subtitles (SUB FM, FM TOM, CLANG, NOISE+, BURST, CH/OH) are fine as free text. |
| **FEEDBACK 12 %** (OSC & FM) | No operator feedback exists. | Remove, or reuse the slot for *Mix/FM mode* (`MIX_MOD`) or transient pitch. |
| **RATIO 1:2.00** | Modulator pitch is an independent coarse/fine note offset (`FMDTN`), not a ratio. | Show ratio as a *derived* readout from the two tunings; edit via coarse/fine. |
| **COARSE 48.2 Hz** | Coarse is a 0–127 *note offset* (default 70) + fine ±50 ct, relative to the played note (60 = nominal). | Show note/Hz derived from coarse+fine; edit coarse as semitones. |
| **Envelopes A / D1 / D2 / "AEG\|PEG"** | Amp EG: attack, decay, slope (+ repeat on snare/cymbal; open/closed decay on hat). Pitch EG: decay, slope, amount. **No filter EG.** | A = attack, D1 = amp decay, D2 = pitch decay; add slope controls; draw curves from the real EG functions. |
| **"Pitch mod +24 semi, EXP CURVE"** | `amount = (p/127)²·32` = linear *frequency multiplier* (up to +32×), curved by slope. | Display as "× freq" (and optionally approximate semitones of the initial sweep). |
| **LFO "DEST: VCF CUTOFF"**, shape, rate, sync 1/8 | ✓ Per-voice LFO with one destination (any parameter in `modTargets`), 8 waveforms, 11 sync divisions, retrigger source, phase offset, amount. | Faithful. Add "amount", "retrigger", "phase". Destination list from the generated modTargets table. |
| **SATURATION +8.2 dB, DRIVE TYPE fold/clip/tube** (in LFO & DRIVE) | Per-voice: a rational soft-clipper (`distortion shape`, not dB). Fold/clip/tube are the **global FX-bus** distortion types. | Split: per-voice "Drive" knob (shape); FX type selector in the FX area. Do not label in dB. |
| **Global master FX: compressor *and* delay together, delay "dotted 1/8"** | **One** FX slot at a time (Off/Drive/Ring/Comp/Delay); delay time is free (0.6 ms … 0.74 s), not tempo-synced; FX applies only to voices routed to it. | Faithful: single FX selector + 4 generic knobs relabelled per type. A chain or tempo-sync is a *post-reference extension*. |
| **DRIVE SEND +4.5 dB / DELAY SEND 28 %** | No send levels; per-voice binary routing (`AUDIO_OUT` = FX). | Per-strip "FX" routing toggle; remove send knobs for v1. |
| **MORPH A ↔ B** | ✓ exists in firmware (kit-to-kit parameter interpolation, skips audio routing). | Phase B (needs two kit snapshots + blend). |
| **Kit browser "KIT 07: Berlin Industrial Acid_909x *MOD"** | Kits live on the SD card. | Plugin preset browser with dirty flag. |
| **BPM / SYNC / TAP / SWING** | BPM, shuffle exist in the sequencer; ext-sync exists in firmware. | v1: BPM follows the host (display, editable only in Free-run); SYNC = Host-sync / Free-run switch (`lxr-sequencer.md` §4.2); TAP only in Free-run; SWING = sequencer shuffle (0…1). |
| **Step sequencer: bars 1–4, 16 pads, TRIG/ACC/ROLL/P-LCK, CLEAR/COPY/PASTE/RANDOM, scale, length** | ✓ 64 steps × 4 bars, per-step volume/prob/note/flam/shift, 2 automation slots per step (= P-locks), roll, euclid, copy/clear, per-track length. **No accent concept** (step volume instead), "RANDOM" ≈ probability/euclid. | **In scope for v1 (USP).** Full mapping in `lxr-sequencer.md` §4.4. ACC → map to high step volume or drop; LOCK → "trigger with p-lock" (a p-lock needs a trigger); add the controls the mockup omits (probability, shift, track length, rotation, pattern select). |
| **Fader in dB, pan "L18 / R22"** | Voice `vol` is linear 0…1 (7-bit); `pan` 0…127 constant-power; plus a hardware-fader gain. | UI-only taper/dB display; "L/R" display derived from pan. |
| **Header "LXR-02 … SONIC POTIONS × ERICA SYNTHS", window title "LXR-02 … VST3 Instrument"** | `NOTICE.md` §7(e): no use of the names "Erica Synths"/"LXR"/"LXR-02" in a way that suggests origin/approval/affiliation without written permission. | **Decision: product name is "LynnDrum"** (for now). Replace the header text and window title; keep a small credits/About line: "Derived from the open-source LXR firmware by Erica Synths (GPL-3.0). Not affiliated with or endorsed by Erica Synths." plus the CC-BY attribution for the transient samples. The mockup's logo mark/colour scheme is ours to keep; "VST3" badge fine. |
| macOS traffic-light buttons in the mockup | n/a in a plugin window | Drop. |

## 3. Technology decision

### Candidates

| | React (+Vite, TS, Tailwind) in JUCE WebView | JUCE native components (`Component`, `LookAndFeel`, custom `paint`) | Hybrid (native shell, WebView panels) |
|---|---|---|---|
| Fidelity to the mockup | **Very high** — the mockup *is* HTML/CSS; gradients, glows, SVG graphs, fonts port directly | Medium-low: every glow/gradient/knob cap/graph must be hand-painted (`juce::Graphics`, `DropShadow`, cached `Image`s); big custom C++ UI code base | Same as React but extra seams |
| Iteration speed | **Fastest**: Vite HMR in a normal browser with a mocked bridge; screenshot-diff against `screen.png` with Playwright | Slow: C++ rebuild + host reload per change | Medium |
| Parameter communication | JUCE 8 `WebBrowserComponent` **relays** (`WebSliderRelay`, `WebToggleButtonRelay`, `WebComboBoxRelay`) bound to APVTS params; JS side mirrors state, handles gestures | Native attachments (`SliderAttachment`…) — simplest and safest | Both |
| State sync | One C++ source of truth (APVTS + ValueTree); UI is a view | Same | Two stores to keep in sync |
| Performance | Fine for this UI (≈ 100 controls, 3 small graphs, meters at 30 Hz). WebView memory ≈ tens of MB per instance. | Lowest overhead, but custom painting of dense gradients is not free either | — |
| Risks | WebView2 runtime (Windows), webkit2gtk (Linux), host keyboard-focus quirks, per-instance process/memory, HiDPI scaling, startup latency; resource loading must be offline (no CDN) | Maintenance burden of a custom widget set; harder to reproduce the look | Complexity (the brief says avoid) |
| Team fit | Stated prior success with WebView/React | Unknown | |

### Recommendation: **React + Vite + TypeScript + Tailwind (compiled), served from the plugin binary into a JUCE 8 `WebBrowserComponent`**

*Not* because it is familiar but because the requirement that dominates here — reproducing a dense, effect-heavy, designer-made mockup closely and iterating on it — is exactly what HTML/CSS is for, while the decisive risk (WebView in plugin hosts) has a known mitigation (see below). The engine, parameters and state stay 100 % native C++; the UI is a replaceable *view*. If the guideline (not yet seen) turns out to be much simpler than the mockup, re-evaluate JUCE-native: the decision hinges on visual complexity.

Concrete choices:

- **Build, don't CDN.** Replace the Tailwind CDN script with a build step (`tailwindcss` via Vite). Self-host the font(s) (Inter, plus a bundled mono) as assets — no network access from a plugin. Output `dist/` → zipped/embedded by CMake (`juce_add_binary_data`) and served through `WebBrowserComponent::Options::withResourceProvider`.
- **React is justified** by ~100 repetitive controls (voice strips, knobs, pads) and shared state, but keep it light: one global store keyed by parameter id; no routing, no data libraries. (Preact would do equally well if bundle size matters.)
- **Components** (all stateless over a parameter id): `Knob`, `Fader`, `Segmented`, `Select`, `PadGrid`/`StepLane`, `StepInspector`, `TransportBar`, `EnvelopeGraph`, `FilterGraph`, `Meter`, `VoiceStrip`, panels. Graphs are SVG/canvas drawn from **JS ports of the engine's own functions** (EG time/slope mapping, SVF transfer function), so what is drawn is what plays.
- **Interaction rules:** drag = relative change (shift = fine), double-click = default, wheel; `beginGesture/endGesture` around drags (host automation write modes); 127 discrete steps to match the engine; text readouts from the generated display functions (Hz, ms, ×, dB).
- **Dev loop:** `npm run dev` with a mock bridge (same message shapes) so the entire UI runs in Chrome; Playwright script screenshots at 1300×860 and diffs against `screen.png`; plugin build embeds `dist/`.
- **Theming tokens** lifted from the Tailwind config in `code.html` (`synth.bg/panel/surface/border/amber/cyan/emerald/violet/red`).

### Mitigations for the WebView risks (to be proven in the first UI spike, before polishing)

1. Prototype a "hello knob" plugin in the target DAWs early (Windows WebView2 evergreen runtime presence, macOS WKWebView, one Linux host if relevant); check keyboard focus, resize, multiple instances, open/close/reopen, and project reload.
2. Keep the editor creation lazy and cheap; destroy the WebView with the editor; set a per-plugin WebView2 user-data folder in a writable location.
3. Never call into JS from the audio thread. The UI polls telemetry (§4).
4. Provide a fallback "no-UI" parameter view (host generic editor remains available because all parameters are real host parameters).

## 4. UI ↔ DSP communication boundary

Three channels, nothing else:

```
 (1) Parameters      JS  ⇄  JUCE relays  ⇄  APVTS  ⇄  host automation   — all sound params, fader/mute/mode flags
 (2) UI events       JS  ──►  native event handler  ──►  lock-free SPSC queue ──► audio thread   — audition pad, kit load, step edit (later)
 (3) Telemetry       audio thread ──► atomics snapshot ──► UI timer (30–60 Hz) ──► JS    — meters, voice activity, EG/LFO phase, step playhead
```

- **No callbacks from the UI into engine objects.** The engine API has no UI-facing symbols; the UI never holds a pointer to DSP state.
- **State loads/preset changes** originate in C++ (StateManager / preset browser) and update APVTS; the UI re-reads via the relays.
- **Menus with generated content** (LFO/velocity destination lists, transient names, waveform names) come from the same generated table as the parameters (`params.ts`), so UI, DSP and docs cannot drift.
- **Thread safety:** UI thread = JUCE message thread (relay callbacks). Audio thread touches only atomics and the SPSC queue.

## 5. Staging

1. **Spike:** WebView + one knob + meter, load in 2 DAWs. (Go/no-go on WebView.)
2. Mixer rack + synth panels (the four modules) + header (kit name, meter, host BPM). This covers the full v1 engine.
3. Mod-matrix and Kit-routing tabs (LFO/velocity destinations, audio routing, FX selector).
4. Sample/Click tab (transient wave/level/pitch).
5. **Sequencer deck (v1)** — starts as soon as `lxr_seq` emits a stream (it can be developed against a mock bridge with a simulated playhead long before audio exists): pad grid, bar tabs, per-step inspector (volume/prob/note/flam/shift/p-locks), track length/rotation, pattern select, transport/sync controls, playhead. **Morph** stays post-v1 (needs a second kit snapshot).
6. Fluid-layout pass (§6), then pixel pass against the mockup, then the guideline pass (§7: tokens, type, interaction rules, accessibility).

## 6. Open questions (after reading the guideline)

Decided: sequencer is in v1; window may start fixed but the layout is fluid (§6); product name LynnDrum. Answered by the guideline: base canvas 1440 px+, usable down to 1280 (§7.1), tokens/type/interaction rules (§7.2–7.4). Still open: minimum size below 1280 (we keep the tiers of §6.2 as a superset); whether the plugin remembers its size (recommended: yes); which of the mockup/guideline-only controls (feedback, sends, 24 dB filter, dual FX, accents, Hold/Decay 2 envelope) are *wanted additions* (engine extension in Phase 9) rather than to-be-removed placeholders; how the sequencer deck should use extra width (see §6.3).

## 6. Fluid layout (decision 2026-10-24: start fixed if convenient, but never paint ourselves into a corner)

React + Tailwind makes fluid layout cheap *if it is a rule from the first component*. The rule: **the guideline's 1440 px-wide canvas is the design size (the mockup render is 1300×860); neither is a layout constraint.**

### 6.1 Rules for every component

1. **No fixed pixel heights/widths on structural containers.** The mockup's `h-[860px] max-w-[1300px]` becomes `h-full w-full`; regions are CSS Grid with `minmax()`/`fr` tracks; the window is the viewport.
2. **Scale type and controls from one variable.** Set the root font size from the viewport (`clamp(11px, calc(0.55vw + 6px), 16px)`, tuned so the design size gives the mockup's 12 px base); size everything in `rem`/`em`. Knobs, faders, pads, meters are **SVG/CSS** (vector, `viewBox`), graphs use `viewBox` + `vector-effect: non-scaling-stroke`, so a larger window enlarges controls crisply and a smaller one shrinks them.
3. **Container queries instead of global breakpoints** (`@container` via Tailwind's container-queries plugin, which the mockup already loads): each panel decides its own layout from its width.
4. **Touch/pointer targets have a minimum size** (≥ 24 px) independent of the scale variable; at the minimum window size controls stop shrinking and the panel scrolls rather than collapsing.
5. **No layout logic in JS** except the root-font-size effect and the mixer/sequencer virtualisation (below).

### 6.2 Layout tiers (indicative; tune against the guideline)

| Window width | Layout |
|---|---|
| ≥ 1500 | Design layout + extra space goes to the sequencer deck (§6.3) and larger graphs |
| 1100 – 1500 | Design layout (mixer rack | 4 synth modules in one row | master FX | sequencer) |
| 900 – 1100 | Synth modules wrap to a 2×2 grid; mixer strips narrow (fader + M/S, pan knob moves under the name) |
| < 900 (minimum ≈ 800×560) | Mixer collapses to an icon rail with a selected-voice strip; synth modules become tabs (OSC/FM · Filter · Env · LFO/Drive); sequencer deck shows one bar at a time |

### 6.3 Sequencer deck behaviour with width

16 pads/bar at the design size; with more width show 32 or 64 steps (several bars as rows or in one long lane); with less, one bar at a time with the bar tabs. The step inspector (volume, probability, note, flam, shift, p-locks) docks below or beside depending on height. Pad geometry is derived from available width/height, never fixed.

### 6.4 Plugin window plumbing

- JUCE: `setResizable(true, true)` with a `ComponentBoundsConstrainer` (min ≈ 800×560; optional aspect-ratio lock, off by default), WebView fills the editor; resize events are debounced; the last size is stored in the plugin state (non-parameter `ValueTree` node) and restored.
- If a host cannot resize plugin windows, the fixed design size still works unchanged (the layout simply runs at one tier). That keeps "start fixed" as a legitimate first milestone.
- Test matrix: Playwright screenshots at 800×560, 960×640, 1100×720, 1280×800 (guideline's minimum "standard" window), 1300×860 (mockup size, diffed against `screen.png`), 1440×900 (guideline base), 1600×1000, 1920×1080; assertions for no horizontal scroll, no overlapping/clipped text, minimum control sizes, sequencer geometry.

## 7. Design guideline (`guidelines.md`) — adopted, adapted, and where it conflicts

The guideline is a visual/interaction brief (philosophy: *functional translation, not hardware emulation* — direct-access decks, real-time graphics, simultaneous multi-voice mixing; flat, non-skeuomorphic). It agrees with the mockup on structure (header · voice mixer · sound-design deck · master FX strip · sequencer deck) and adds tokens, typography, component rules and a checklist. It describes some behaviour the engine does not have; per the instruction that it is inspiration only, **§7.3 lists each conflict and its resolution so the UI never promises something the DSP cannot do.**

### 7.1 Adopted as is

| Guideline | How we use it |
|---|---|
| Four-tier layout, left mixer ≈ 260 px, central deck with four modules, bottom sequencer deck full width | Layout skeleton (§1), made fluid (§6). Header height ~56 px (the mockup renders ~40 px; follow the guideline). |
| Canvas "1440 px+ base, flexible down to 1280" | **Design size = 1440 wide**; 1280 is the smallest *standard* window we must look right in; the §6.2 tiers extend below that. |
| Bars as pages of 16 (`1-16, 17-32, 33-48, 49-64`), steps grouped 4+4+4+4 with dividers | Exactly matches the engine's 64 steps × 4 bars (`lxr-sequencer.md`). |
| Step pad states: inactive / TRIG / playhead / P-LCK / flam-roll badge / **velocity micro-bar (0–127, drag vertically)** | Direct fit: velocity = step volume (7-bit), P-LCK = p-lock slots, `2x` = flam ×2…×8, playhead from telemetry. |
| Selecting a voice by clicking its strip header without interrupting playback | Pure UI state (selected voice), no engine effect. |
| Colour roles: amber = selection/trigger/tempo, cyan = filter/P-locks/playhead, green = envelopes, violet = rolls/modulation | Used as semantic tokens (§7.2). |
| Interaction: vertical drag (100 px = full sweep), Shift+drag fine, double-click / Alt+click = reset to default, wheel steps | Implemented in `Knob`/`Fader`; semantics adapted to 127 discrete steps (§7.3 #12). |
| Vector-only controls (SVG/CSS), no raster knobs; HiDPI ready | Same as §3/§6. |
| Responsive rule: shrinking width must collapse padding, never clip the sequencer steps | Rule 1 of §6.1 + sequencer geometry test. |
| Colour-coded modules; section headers `1. OSC & FM CORE` etc. | Kept as visual structure. |
| Flat dial anatomy (dark inset base + 2 px pip or radial sweep gauge); no faux-3D | **Preferred over the mockup's radial-gradient knob caps**, which the guideline itself rules out. |
| Tests use structural selectors (`#step-sequencer`, `.channel-strip:nth-child(n)`), no text-matching selectors | Adopted for Playwright (plus `data-testid` where structure is ambiguous). |

### 7.2 Tokens and typography

Use the guideline's palette as the single source of truth, exposed as CSS variables and mapped in Tailwind (`surface-lowest #0c0e15`, `surface #11131a`, `surface-container-low #191b22`, `surface-bright #373941`, amber `#ff6b2b`, cyan `#00d4e5` (`#00b4d8` alt), green `#10b981` (`#00e676` alt), violet `#a855f7`, `text-primary #f1f3f9`, `text-secondary #8b90a0`, `text-dim #4b5063`). The mockup's own Tailwind config uses slightly different values (`#090b10`, `#ff7728`, `#00e5ff`, `#2fe278`); **the guideline wins** and, since everything is a variable, switching is a one-line change.

Fonts: **Space Grotesk** (UI) and **JetBrains Mono** (tabular readouts), both SIL OFL — bundle them locally (no Google Fonts request from a plugin) and ship their licence texts in the credits. Type scale as specified (brand 14 px/+0.12em/700; section 12 px/+0.08em/600; readouts 13 px/500 mono; control labels 9–10 px; micro 8 px) **expressed in `rem` relative to the fluid root size (§6.1)** so the scale holds at 1440 and shrinks/grows with the window.

**Contrast check (computed, WCAG relative luminance):**

| Pair | Ratio on `surface` / `surface-container-low` | Verdict |
|---|---|---|
| text-primary | 16.7 / 15.5 | pass |
| text-secondary `#8b90a0` | 5.8 / 5.4 | pass (AA) |
| amber, cyan, green | 6.5 / 6.1, 10.2 / 9.5, 7.3 / 6.8 | pass |
| violet `#a855f7` | 4.7 / **4.35** | borderline: fails AA for small text on cards → use only for graphics/large text or lighten to ≈ `#b878fa` |
| **text-dim `#4b5063`** | **2.3 / 2.15** | **fails AA** (the guideline's own §6 item 4 requires AA). Restrict to non-essential decoration (grid lines, inactive step numbers' *glyph outlines*), or lighten text uses to ≥ `#7a8196` (4.8 / 4.4). Units (dB, Hz, ms) are essential information → use `text-secondary`. |

The 8 px micro-labels are below comfortable legibility on 1× displays; keep them for redundant information only (never the sole carrier of a state) and let the fluid root size lift them at larger windows.

### 7.3 Conflicts with the implementation — resolved in favour of the engine

| # | Guideline says | Engine reality | UI resolution |
|---|---|---|---|
| 1 | Filter modes `LP24`, `BP12`, `HP24`; response curve as "SVG cubic bezier" | One 2-pole (12 dB/oct) ZDF SVF, 7 modes (LP, HP, BP, unity-BP, notch, peak, naive 2-pole LP); cutoff ≤ 19.9 kHz | Show the real modes; draw the **exact analytic magnitude response** of the TPT SVF (log 20 Hz–20 kHz) instead of a bezier approximation, so the picture is what plays. Resonance readout "Q" is derived (`Q = 1/(2·(1−r))`, jumping at r ≥ 0.9). |
| 2 | Envelopes: Attack, **Hold**, **Decay 1 corner, Decay 2 tail**, "420 ms total decay" | Amp EG: attack + decay + slope (+ repeat on snare/cymbal; open/closed decay on hat); separate pitch EG: decay + slope + amount. No hold, no second decay segment | Draw the real amp curve (rational slope) with the pitch EG as a second overlay curve ("AEG / PEG" tabs or overlay); knobs: Attack, Decay, Slope, Pitch Decay, Pitch Amount, Pitch Slope. "Total decay" = time to −60 dB computed from the real mapping (decay 127 = ∞ shown as "∞"). Live dot = per-voice EG phase from telemetry. |
| 3 | OSC panel: Feedback (12 %), Ratio (1:2.00), "2-op sine FM", dedicated Click sub-panel | No operator feedback; modulator pitch is independent coarse/fine; drum voices FM *or* mix of two selectable-wave oscillators; transient generator = Click (snap / offset / 12 samples) | Drop Feedback (or reuse the slot for FM/Mix mode); Ratio becomes a read-only derived readout; "algorithm" banner text is generated per **voice type** (drum / snare / cymbal / hat) from the engine's real topology. Click sub-panel = transient wave/volume/pitch ✓ (exists). |
| 4 | LFO "host-synced rate `1/8D`" (dotted) | Sync divisions are 4/1, 2/1, 1/1, 1/2, 1/3, 1/4, 1/6, 1/8, 1/12, 1/16, 1/32 (no dotted values); one destination per LFO, 8 waveforms | Offer exactly those 11 divisions + free rate (Hz, cubic mapping up to 200 Hz); waveform list = the engine's 8 (guideline's "Saw Down / Triangle" ✓ both exist). |
| 5 | "Tube Fold Clip" drive mode inside the LFO & Drive module; saturation in dB | Per-voice drive is a rational soft-clipper (`shape`); Tube/Fold/Clip(RAT-style) are the **global FX-bus** distortion types | Per-voice "Drive" knob (shape, no dB); Tube/Fold/Clip live in the FX area as the Drive effect's type. |
| 6 | Master FX strip shows bus compressor **and** delay concurrently; "GR: −2.4 dB" | One FX slot active at a time; compressor GR is internal (`env` in dB) | Single FX selector (Off/Drive/Ring/Comp/Delay) with a 4-knob row relabelled per type; GR meter only when Comp is selected (needs a small telemetry value from the engine); delay shown in time (ms/s) — no "dotted 1/8" (no tempo sync in the engine). |
| 7 | Per-strip **Drive Send (+4.5 dB)** and **Delay Send (28 %)** footers | No send levels: a voice is routed to the FX bus or not (`AUDIO_OUT = FX`) | Per-strip "FX" routing toggle (and the full output choice in the Kit Routing tab); footer shows the bus's active type and how many voices feed it. |
| 8 | Fader peak readouts like `+0.2 dB` | Voice level = linear `vol` (≤ 1) × fader (≤ 1): no boost; peaks can exceed full scale only by summing | Fader scale tops out at 0 dB (centre notch at 0 dB as the guideline wants); the numeric readout next to it is the **post-fader peak** from telemetry (can read > 0 dBFS when the voice clips internally). |
| 9 | Exclusive Solo with Ctrl+Click, latching Mute | LXR has mute only (it blocks new triggers; sounding tails continue), no solo | **Solo is a shell feature** implemented as mute of the others (same engine mute flag, so tails ring out — consistent with hardware mute); a separate "cut" gain mute can be added later. Exclusive-solo semantics as specified. |
| 10 | Header: BPM `136.00` amber, **Sync/Internal**, **Tap**, **Swing 54 %** | Original tempo is an integer BPM; swing = `shuffle` 0…1 | Host-sync shows the host tempo (two decimals, read-only); Internal = Free-run (editable, Tap enabled); Swing = shuffle. Note deviation S8 in `lxr-sequencer.md` (float tempo vs the original's integer). |
| 11 | **Kit Morph A/B crossfader** in the header | Exists in the firmware (kit interpolation) but needs a second kit snapshot | Present the control but **disabled/hidden until Phase B**; reserve the space so layout does not shift later. |
| 12 | Drag = 100 px full sweep; **Shift = 0.1 increments**; wheel stepped | Parameters are 7-bit (127 steps) | Normal drag ≈ 0.8 px per step; Shift = ¼ speed but still **1-step granularity** (no sub-step values exist; fractional readouts such as "48.2 Hz" are derived display only). |
| 13 | Step pad badges **ACC** (accent) and "LOCK" | No accent concept; p-locks apply only at triggers | ACC → drop or show "high-velocity" marker; LOCK → "trigger with p-lock". (Same as the mockup row in §2.) |
| 14 | "16-Step Sequencer" title, `1/16th` grid, `16 / 16` length | 64 steps in 4 bars, per-track length 1–64, steps fixed at 1/16 (no other scales) | Title "Step sequencer"; **grid resolution fixed 1/16** (show as a label, not a selector); `n / 16`-style length becomes per-track length 1–64; the extra engine features (probability, shift, rotation, pattern/song, Euclid, shuffle) get controls the guideline does not mention. |
| 15 | Header: "Sonic Potions × Erica Synths", "LXR-02 DIGITAL DRUM SYNTH", window-control dots | Trademark term; DAW supplies window chrome | Replace with **LynnDrum**; truthful derivation line in About; drop the dots. |
| 16 | "Coarse frequency readout (48.2 Hz)" | Coarse is a note offset relative to the played note (60 = nominal) | Readout shows note name + Hz derived for the nominal note; edit in semitones/cents. |
| 17 | Header/engine tag per strip (`SUB FM`, `FM TOM`, `CLANG`) | Voices are generic engine types; tags are descriptive | Free-text role tag stored with the kit (clean-room factory kits define them); not engine data. |

### 7.4 What the guideline adds that the engine can support (new UI work)

- **Real-time graphics** (filter curve, envelope curves, velocity/peak meters, EG playback dot, playhead halo): all derived from parameters (JS ports of the engine's EG/SVF functions) plus a small telemetry set: per-voice post-fader peak, per-voice EG phase, compressor GR, sequencer step/sub-tick position, active-voice flags.
- **Direct-access decks** instead of hardware paging: every one of the ≈200 parameters is reachable without paging; tabs `MAIN SYNTH / MOD MATRIX / SAMPLE-CLICK / KIT ROUTING` map to: synth modules; LFO/velocity destinations + p-lock destination lists; transient generator; audio routing + FX selector.
- **Simultaneous multi-voice mixing**: six strips always visible (collapsing to the icon rail only in the smallest tier, §6.2).

### 7.5 Implementation checklist additions

1. Tokens as CSS variables; Tailwind theme reads them; dark theme only for v1.
2. Fonts self-hosted; OFL texts in credits.
3. Contrast: fix `text-dim`/violet usage per §7.2; automated axe/contrast check in the Playwright run.
4. Keyboard accessibility for knobs/faders (arrow keys = ±1 step, PageUp/PageDown = ±8, Home = default) — not in the guideline, cheap, and hosts forward keys unpredictably so it must be tested.
5. Selectors for tests follow the guideline (structural ids/classes), no text matching.

