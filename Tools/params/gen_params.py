#!/usr/bin/env python3
"""Generate the sound-parameter table of the plugin from the pinned upstream sources:

  * enumerator values      : compiled from Parameters.h (the compiler stays the source of truth)
  * datatype / menu per par: Src/menu/menu.c   parameter_dtypes[]  (the UI's own table => valid ranges)
  * menu entry lists       : Inc/menu/MenuText.h
  * voice grouping         : Inc/menu/menuPages.h (which voice page a parameter appears on)
  * mod-target list        : Src/menu/Cc2Text.c modTargets[]
  * default values         : the kit named by --kit (DEV: upstream initKit.c)

Outputs  Source/Plugin/GeneratedParams.h  (C++)  and  Source/UI/web/src/params.generated.ts  (UI).
Out-of-domain values are undefined behaviour in the original (see docs/ref-harness.md H7), hence ranges come
from the datatypes, not from "0..127 for everything"."""
import os, re, subprocess, sys, tempfile, json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
UP = os.path.join(ROOT, 'Reference/lxr-desktop-app/Core')
CORE = os.path.join(ROOT, 'Source/Engine/lxr_core')
rd = lambda p: open(p, newline='').read()

# ---- 1. enumerator values --------------------------------------------------------------------------------
hdr = rd(os.path.join(CORE, 'inc/Parameters.h'))
body = re.search(r'enum\s+ParamEnums\s*\{(.*?)\n\s*\}\s*;', hdr, re.S).group(1)
body = re.sub(r'/\*.*?\*/', '', body, flags=re.S); body = re.sub(r'//[^\n]*', '', body)
names = []
for item in body.split(','):
    m = re.match(r'\s*([A-Za-z_]\w*)', item)
    if m and m.group(1) not in names: names.append(m.group(1))
with tempfile.TemporaryDirectory() as t:
    c = os.path.join(t, 'e.c')
    open(c, 'w').write('#include <stdio.h>\n#include "Parameters.h"\nint main(void){\n' + ''.join('printf("%s %%d\\n", (int)%s);\n' % (n, n) for n in names) + 'return 0;}\n')
    subprocess.run(['cc', '-o', os.path.join(t, 'e'), c, '-I' + os.path.join(CORE, 'inc'), '-I' + os.path.join(CORE, 'platform')], check=True, capture_output=True)
    vals = {l.split()[0]: int(l.split()[1]) for l in subprocess.run([os.path.join(t, 'e')], capture_output=True, text=True, check=True).stdout.splitlines()}
END = vals['END_OF_SOUND_PARAMETERS']
by_idx = {}
for n, v in vals.items():
    if v < END and n not in ('PAR_MOD_WHEEL',): by_idx.setdefault(v, n)       # PAR_MOD_WHEEL aliases PAR_OSC_WAVE_DRUM1

# ---- 2. datatypes ------------------------------------------------------------------------------------------
menu_c = rd(os.path.join(UP, 'Src/menu/menu.c'))
a = menu_c.index('parameter_dtypes[NUM_PARAMS]'); b = menu_c.index('};', a)
body_d = re.sub(r'//[^\n]*', '', menu_c[a:b])
tokens = [(m.group(2), m.group(3)) for m in re.finditer(r'/\*.*?\*/|(DTYPE_\w+)(?:\s*\|\s*\(\s*(MENU_\w+)\s*<<\s*8\s*\))?', body_d, re.S) if m.group(1) for m in [m]] if False else []
for m in re.finditer(r'/\*.*?\*/|(DTYPE_\w+)(?:\s*\|\s*\(\s*(MENU_\w+)\s*<<\s*8\s*\))?', body_d, re.S):
    if m.group(1): tokens.append((m.group(1), m.group(2)))
assert len(tokens) == vals['NUM_PARAMS'], (len(tokens), vals['NUM_PARAMS'])      # the table is positional: row i = parameter i
dtypes = {n: tokens[v] for n, v in vals.items() if n.startswith('PAR_') and v < len(tokens) and n != 'PAR_MOD_WHEEL'}
# cross-check against the table's own (mostly right) comments
for n, d, m in re.findall(r'/\*\s*(PAR_\w+)\s*\*/\s*(DTYPE_\w+)(?:\s*\|\s*\(\s*(MENU_\w+)\s*<<8\s*\))?', menu_c[a:b]):
    if n in vals and n != 'PAR_MOD_WHEEL' and dtypes[n] != (d, m or None): sys.exit('dtype table misaligned at ' + n)

# ---- 3. menu entry lists -------------------------------------------------------------------------------------
mt = rd(os.path.join(UP, 'Inc/menu/MenuText.h'))
arrays = {}
for name, blockbody in re.findall(r'const char (\w+)\[\]\[\d+\]\s*=\s*\{(.*?)\n\};', mt, re.S):
    ents = re.findall(r'\{\s*("(?:[^"]*)"|\d+)\s*\}', re.sub(r'//[^\n]*', '', blockbody))
    if ents and not ents[0].startswith('"'):
        arrays[name] = [e.strip('"') for e in ents[1:]]
MENU_ARRAY = {'MENU_AUDIO_OUT': 'outputNames', 'MENU_FILTER': 'filterTypes', 'MENU_WAVEFORM': 'waveformNames', 'MENU_SYNC_RATES': 'syncRateNames',
              'MENU_LFO_WAVES': 'lfoWaveNames', 'MENU_RETRIGGER': 'retriggerNames', 'MENU_TRANS': 'transientNames', 'MENU_MIX_FM': 'mixFmNames',
              'MENU_FX': 'fxNames', 'MENU_DIST': 'distNames', 'MENU_RATIO': 'ratioNames', 'MENU_DELAY': 'delayNames', 'MENU_REVERB': 'reverbNames',
              'MENU_AUDIO_OUT_FX': 'outputNamesFx'}
FRIENDLY = {
    'Sin': 'Sine', 'Tri': 'Triangle', 'Saw': 'Saw', 'Rec': 'Rectangle', 'Noi': 'Noise', 'PWM': 'PWM',
    'LP': 'Lowpass', 'HP': 'Highpass', 'BP': 'Bandpass', 'UBP': 'Bandpass (unity)', 'Nch': 'Notch', 'Pek': 'Peak', 'LP2': 'Lowpass (naive)',
    'St1': 'Stereo 1', 'St2': 'Stereo 2', 'L1': 'Left 1', 'R1': 'Right 1', 'L2': 'Left 2', 'R2': 'Right 2', 'FX': 'FX bus',
    'Snp': 'Snap', 'Ofs': 'Offset', 'Clk': 'Click', 'Ck2': 'Click 2', 'Tik': 'Tick', 'Kik': 'Kick', 'Kk2': 'Kick 2', 'Rim': 'Rim', 'Drp': 'Drop',
    'Hat': 'Hat', 'Clp': 'Clap', 'Snr': 'Snare', 'Tom': 'Tom', 'Sp2': 'Sp2',
    'sin': 'Sine', 'tri': 'Triangle', 'sup': 'Saw up', 'sdn': 'Saw down', 'sqr': 'Square', 'rnd': 'Random', 'xup': 'Exp up', 'xdn': 'Exp down',
    'off': 'Off', 'v1': 'Voice 1', 'v2': 'Voice 2', 'v3': 'Voice 3', 'v4': 'Voice 4', 'v5': 'Voice 5', 'v6': 'Voice 6',
    'FM': 'FM', 'Mix': 'Mix', 'drv': 'Drive', 'rng': 'Ring mod', 'cmp': 'Compressor', 'del': 'Delay', 'tub': 'Tube', 'fld': 'Fold', 'clp': 'Clip (RAT-style)',
    'Del': 'Delay', 'Pp': 'Ping-pong',
}
friendly = lambda s: FRIENDLY.get(s, s)

# ---- 4. voice grouping from the menu pages ---------------------------------------------------------------------
pages = rd(os.path.join(UP, 'Inc/menu/menuPages.h'))
voice_of = {}
VOICE_NAMES = ['Drum 1', 'Drum 2', 'Drum 3', 'Snare', 'Cymbal', 'Hi-hat']
marks = [(m.start(), int(m.group(1))) for m in re.finditer(r'//\s*page\s+(\d+)\s*-\s*Voice', pages, re.I)]
for k, (pos, num) in enumerate(marks):
    end = marks[k + 1][0] if k + 1 < len(marks) else len(pages)
    if num <= 7:                                          # pages 1..6 voices, 7 = open hat (same voice as 6)
        for p in re.findall(r'\bPAR_\w+', pages[pos:end]):
            voice_of.setdefault(p, min(num, 6) - 1)

# ---- 5. mod targets -------------------------------------------------------------------------------------------------
cc2 = rd(os.path.join(UP, 'Src/menu/Cc2Text.c'))
mt0 = cc2.index('const ModTarg modTargets[]'); mt1 = cc2.index('};', mt0)
mod_targets = re.findall(r'\{\s*(TEXT_\w+)\s*,\s*(PAR_\w+)\s*\}', re.sub(r'//[^\n]*', '', cc2[mt0:mt1]))

# ---- 6. defaults: clean-room. Presets/factory/init.lynnpreset (our own "Init" kit) wins; otherwise generic rules ---------
init_path = os.path.join(ROOT, 'Presets/factory/init.lynnpreset')
init_kit = json.load(open(init_path))['kit'] if os.path.exists(init_path) else {}
RULES = [(r'^Volume$', 100), (r'^Pan$', 63), (r'^Filter Freq$', 127), (r'^Sample Rate Reducer', 127), (r'^Amp Slope$', 64), (r'^Pitch Slope$', 64),
         (r'^Decay', 40), (r'^Pitch Decay$', 20), (r'^Noise Freq$', 127), (r'^LFO Target Voice$', 1)]
def default_of(r_id, name, bipolar, lo):
    if r_id in init_kit: return init_kit[r_id]
    if bipolar: return 63
    for pat, v in RULES:
        if re.search(pat, name): return v
    return lo

# ---- 7. build the table ----------------------------------------------------------------------------------------------------
SKIP = ('PAR_NONE', 'PAR_NRPN_DATA_ENTRY_COARSE', 'PAR_BANK_CHANGE', 'PAR_FX_REVERB_TYPE', 'PAR_MORPH_KIT_DEST')   # reverb is compiled out upstream; morph arrives later
NAME_FIX = [   # (regex on the generated title, replacement) - friendly names for the UI
    (r'^Pwm$', 'PWM'), (r'^Fx Dry Wet$', 'FX Dry/Wet'), (r'^Fx Dist Type$', 'FX Distortion'), (r'^Osc Wave( Snare| Drum)?$', 'Waveform'), (r'^Noise Freq\d?$', 'Noise Freq'), (r'^Mix\d?$', 'Noise / Osc Mix'), (r'^Wave(\d)$', r'Wave \1'),
    (r'^Velod\d Closed$', 'Decay (closed)'), (r'^Velod\d Open$', 'Decay (open)'), (r'^Wave$', 'Waveform'), (r'^Mod Wave$', 'FM Waveform'), (r'^Veloa$', 'Attack'), (r'^Velod$', 'Decay'),
    (r'^Velod Closed$', 'Decay (closed)'), (r'^Velod Open$', 'Decay (open)'), (r'^Vol Slope$', 'Amp Slope'), (r'^Mod Eg$', 'Pitch Decay'),
    (r'^Modamnt$', 'Pitch Mod'), (r'^Fmamnt$', 'FM Amount'), (r'^Fm Freq$', 'FM Freq'), (r'^Vol$', 'Volume'), (r'^Reso$', 'Resonance'),
    (r'^Mix Mod$', 'FM / Mix Mode'), (r'^Velo Mod Amt$', 'Velocity Amount'), (r'^Vel Dest$', 'Velocity Target'),
    (r'^Volume Mod On Off$', 'Velocity > Volume'), (r'^Freq Lfo$', 'LFO Rate'), (r'^Amount Lfo$', 'LFO Amount'), (r'^Wave Lfo$', 'LFO Wave'),
    (r'^Voice Lfo$', 'LFO Target Voice'), (r'^Target Lfo$', 'LFO Target'), (r'^Retrigger Lfo$', 'LFO Retrigger'), (r'^Sync Lfo$', 'LFO Sync'),
    (r'^Offset Lfo$', 'LFO Phase'), (r'^Trans\d? Vol$', 'Click Level'), (r'^Trans\d? Wave$', 'Click Type'), (r'^Trans\d? Freq$', 'Click Pitch'),
    (r'^(Snare|Cymbal|Hat) Distortion$', 'Drive'), (r'^Drive$', 'Drive'), (r'^Mix$', 'Noise / Osc Mix'), (r'^Mod Osc F(\d)$', r'Mod Osc \1 Freq'),
    (r'^Mod Osc Gain(\d)$', r'Mod Osc \1 Gain'), (r'^Voice Decimation$', 'Sample Rate Reducer'), (r'^Voice Decimation All$', 'Sample Rate Reducer (all)'),
    (r'^Fx ', 'FX '), (r'^FX P(\d)$', r'FX Param \1'), (r'^Repeat$', 'Repeat Count'), (r'^Pitch Slope$', 'Pitch Slope'),
]
def pretty(n, voice):
    s = n[4:]
    s = re.sub(r'_(CYM|HH)$', '', s)
    if voice is not None and voice < 6:                    # drop the per-voice numbering, keep inner numbering (MOD_OSC_F1_CYM)
        k = voice + 1
        s = re.sub(r'_?(DRUM)?%d$' % k, '', s) if voice < 3 or True else s
    t = s.replace('_', ' ').strip().title()
    for pat, rep in NAME_FIX:
        t2 = re.sub(pat, rep, t)
        if t2 != t: t = t2; break
    return t or n

rows = []
for idx in sorted(by_idx):
    n = by_idx[idx]
    if n in SKIP or 'UNUSED' in n or n.startswith('PAR_NRPN') or n not in dtypes: continue
    d, m = dtypes[n]
    voice = None if n.startswith('PAR_FX') or n == 'PAR_VOICE_DECIMATION_ALL' else voice_of.get(n)
    if voice is None and not (n.startswith('PAR_FX') or n == 'PAR_VOICE_DECIMATION_ALL'):
        mm = re.search(r'(?:_|WAVE|COARSE|FINE)(\d)$|(\d)$', n)
        if mm and n.startswith(('PAR_',)) and 'FX' not in n and 'LFO' not in n: voice = int(mm.group(1) or mm.group(2)) - 1 if 0 < int(mm.group(1) or mm.group(2)) <= 6 else None
    group = VOICE_NAMES[voice] if voice is not None and 0 <= voice < 6 else ('FX' if n.startswith('PAR_FX') else 'Global')
    kind, lo, hi, choices = 'int', 0, 127, None
    if d == 'DTYPE_MENU':
        arr = arrays[MENU_ARRAY[m]]; kind, hi, choices = 'choice', len(arr) - 1, [friendly(x) for x in arr]
    elif d == 'DTYPE_ON_OFF': kind, hi = 'bool', 1
    elif d == 'DTYPE_VOICE_LFO': lo, hi = 1, 6
    elif d in ('DTYPE_TARGET_SELECTION_VELO', 'DTYPE_TARGET_SELECTION_LFO'): kind, hi = 'target', len(mod_targets) - 1
    elif d == 'DTYPE_0B100': hi = 100
    elif d not in ('DTYPE_0B127', 'DTYPE_PM63'): continue          # not a 7-bit sound parameter
    de = min(max(default_of(n[4:].lower(), pretty(n, voice), d == 'DTYPE_PM63', lo), lo), hi)
    rows.append(dict(par=idx, enum=n, id=n[4:].lower(), name=pretty(n, voice), group=group, kind=kind, min=lo, max=hi, default=de,
                     bipolar=(d == 'DTYPE_PM63'), choices=choices,
                     tkind=('vel' if d == 'DTYPE_TARGET_SELECTION_VELO' else 'lfo' if d == 'DTYPE_TARGET_SELECTION_LFO' else None),
                     tindex=int(re.search(r'(\d)$', n).group(1)) - 1 if d.startswith('DTYPE_TARGET') else None))

def target_label(t, p):
    if p == 'PAR_NONE': return 'None'
    v = vals.get(p, -1); vo = None if p.startswith('PAR_FX') or p == 'PAR_VOICE_DECIMATION_ALL' else voice_of.get(p)
    if p.startswith('PAR_FX'): return 'FX: ' + pretty(p, None)
    g = VOICE_NAMES[vo] if vo is not None else 'Global'
    return '%s: %s' % (g, pretty(p, vo))
targets = [dict(par=vals.get(p, 0), label=target_label(t, p)) for t, p in mod_targets]

# ---- 8. emit ---------------------------------------------------------------------------------------------------------------------
cq = lambda s: '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
with open(os.path.join(ROOT, 'Source/Plugin/GeneratedParams.h'), 'w') as f:
    f.write('// SPDX-License-Identifier: GPL-3.0-only\n// GENERATED by Tools/params/gen_params.py from the pinned upstream - do not edit.\n#pragma once\n#include <cstdint>\n\n')
    f.write('namespace lynn::params\n{\nenum class Kind : std::uint8_t { Int, Choice, Bool, Target };\n')
    f.write('struct Def { const char* id; const char* name; const char* group; std::uint16_t par; Kind kind; std::uint8_t min, max, def; bool bipolar; std::int8_t targetKind /*-1, 0 velocity, 1 lfo*/; std::int8_t targetIndex; const char* choices /* \'|\' separated */; };\n')
    f.write('inline constexpr Def kSound[] = {\n')
    for r in rows:
        f.write('    { %s, %s, %s, %d, Kind::%s, %d, %d, %d, %s, %d, %d, %s },\n' % (
            cq(r['id']), cq(r['name']), cq(r['group']), r['par'], {'int': 'Int', 'choice': 'Choice', 'bool': 'Bool', 'target': 'Target'}[r['kind']],
            r['min'], r['max'], r['default'], 'true' if r['bipolar'] else 'false',
            {None: -1, 'vel': 0, 'lfo': 1}[r['tkind']], r['tindex'] if r['tindex'] is not None else -1,
            cq('|'.join(r['choices'])) if r['choices'] else 'nullptr'))
    f.write('};\ninline constexpr int kNumSound = %d;\n' % len(rows))
    f.write('/* the clean-room Init kit: every exposed parameter at its default, the rest zero (END_OF_SOUND_PARAMETERS = 247 bytes) */\ninline void fillDefaultKit (std::uint8_t* kit247) { for (int i = 0; i < 247; ++i) kit247[i] = 0; for (const auto& d : kSound) kit247[d.par] = d.def; }\n')
    f.write('inline constexpr const char* kModTargets[] = {\n' + ''.join('    %s,\n' % cq(t['label']) for t in targets) + '};\n')
    f.write('inline constexpr std::uint16_t kModTargetPar[] = { %s };\n}\n' % ', '.join(str(t['par']) for t in targets))
with open(os.path.join(ROOT, 'Source/UI/web/src/params.generated.ts'), 'w') as f:
    f.write('// GENERATED by Tools/params/gen_params.py - do not edit.\nexport interface ParamDef { id: string; name: string; group: string; par: number; kind: "int" | "choice" | "bool" | "target"; min: number; max: number; def: number; bipolar: boolean; choices?: string[]; targetKind?: "vel" | "lfo"; targetIndex?: number }\n')
    out = []
    for r in rows:
        o = {'id': r['id'], 'name': r['name'], 'group': r['group'], 'par': r['par'], 'kind': r['kind'], 'min': r['min'], 'max': r['max'], 'def': r['default'], 'bipolar': r['bipolar']}
        if r['choices']: o['choices'] = r['choices']
        if r['tkind']: o['targetKind'] = r['tkind']; o['targetIndex'] = r['tindex']
        out.append(o)
    f.write('export const SOUND_PARAMS: ParamDef[] = ' + json.dumps(out, indent=0) + '\n')
    f.write('export const MOD_TARGETS: string[] = ' + json.dumps([t['label'] for t in targets]) + '\n')
import collections
json.dump({'params': rows, 'targets': targets}, open(os.path.join(ROOT, 'Tools/params/params.json'), 'w'), indent=1)
print(len(rows), 'sound parameters;', collections.Counter(r['group'] for r in rows), ';', len(targets), 'mod targets')
