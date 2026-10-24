import sys; sys.path.insert(0, '.')
from measure import *
base = ['kit init']
for coarse in (20, 31, 40, 50, 63, 75, 90):
    lines = base + ['par PAR_OSC_WAVE_DRUM1 0', f'par PAR_COARSE1 {coarse}', 'par PAR_FINE1 63', 'par PAR_MODAMNT1 0', 'par PAR_FMAMNT1 0', 'par PAR_VELOD1 60', 'par PAR_VOL1 127', 'trig 0 60 127']
    x = mono(render(lines, 120))
    print('coarse', coarse, end=' '); report('drum1', x)
