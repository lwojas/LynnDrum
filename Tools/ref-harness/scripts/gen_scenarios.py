#!/usr/bin/env python3
"""Generate the Phase-1 scenario scripts into <outdir>/ (one .lxr per scenario).
Scenarios:
  musical_*   hand-written sequences on the init kit (all 7 triggers, velocities, retrigger)
  sweep_<PAR>_<v>   every sound parameter at 0 / 64 / 127 then all voices triggered
"""
import os, re, sys
out = sys.argv[1]; params_h = sys.argv[2]
os.makedirs(out, exist_ok=True)

src = open(params_h, newline='').read()
body = re.search(r'enum\s+ParamEnums\s*\{(.*?)\n\s*\}\s*;', src, re.S).group(1)
body = re.sub(r'/\*.*?\*/', '', body, flags=re.S); body = re.sub(r'//[^\n]*', '', body)
names = []
for item in body.split(','):
    m = re.match(r'\s*([A-Za-z_]\w*)', item)
    if m and m.group(1) not in names: names.append(m.group(1))
end = names.index('END_OF_SOUND_PARAMETERS')
sound = names[:end]

def w(name, text):
    open(os.path.join(out, name + '.lxr'), 'w').write(text)

ALL = ''.join(f'trig {v} 60 110\nrender 6\n' for v in range(7))
w('musical_all_voices', 'seed 1\nbpm 120\nkit init\n' + ALL + 'render 200\n')
w('musical_velocity', 'seed 2\nkit init\n' + ''.join(f'trig {v} 60 {vel}\nrender 100\n' for v in (0,3,5) for vel in (1,32,64,100,127)))
w('musical_retrigger', 'seed 3\nkit init\n' + ''.join('trig 0 60 100\nrender 5\n' for _ in range(20)) + 'render 100\n')
w('musical_notes', 'seed 4\nkit init\n' + ''.join(f'trig {v} {n} 100\nrender 60\n' for v in (0,1,2,3,4) for n in (24,36,48,60,72,84,96,108)))
w('musical_hat_choke', 'seed 5\nkit init\ntrig 6 60 100\nrender 20\ntrig 5 60 100\nrender 100\ntrig 6 60 100\nrender 20\ntrig 6 60 100\nrender 100\n')
# Out-of-domain enum values (e.g. oscillator waveform 64) are undefined in the original:
# -O0 and -O2 builds disagree, so they are not part of the reference catalogue.
for p in sound[1:]:                      # PAR_NONE skipped
    if p in ('PAR_BANK_CHANGE', 'PAR_MOD_WHEEL'): continue   # CC#0 dropped (H4); MOD_WHEEL aliases PAR_OSC_WAVE_DRUM1
    values = (0, 1, 2, 3, 4, 5) if 'WAVE' in p else (0, 64, 127)
    for v in values:
        w(f'sweep_{p}_{v}', f'seed 7\nbpm 120\nkit init\npar {p} {v}\n' + ALL + 'render 60\n')
print(len(os.listdir(out)), 'scenarios')
