from kitlib import *
H = V('Hi-hat')
def hat(open_, **kw):
    kit = defaults(); kit.update(H(Volume=110, **kw))
    return mono(render(par_lines(kit) + ['trig %d 60 110' % (6 if open_ else 5)], 250))
def rep(tag, x):
    st = next((i for i, v in enumerate(x) if abs(v) > 0.01), 0)
    print(tag.ljust(34), 'peak %.2f dec40 %4d ms centroid %6.0f Hz  >5k-vs-<5k %5.1f dB' % (peak(x), decay_ms(x), centroid_hz(x, st), band_db(x, st, 5000, 20000) - band_db(x, st, 100, 5000)))
base = dict(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=63, Fine=63, Mod_Osc_1_Freq=63, Mod_Osc_2_Freq=63, Mod_Osc_1_Gain=100, Mod_Osc_2_Gain=100, Filter_Type=1, Filter_Freq=60, Resonance=20)
for tag, kw in [('base', {}), ('coarse 80', dict(Coarse=80)), ('coarse 100', dict(Coarse=100)), ('hp f90', dict(Filter_Freq=90)),
                ('hp f100 gains 127', dict(Filter_Freq=100, Mod_Osc_1_Gain=127, Mod_Osc_2_Gain=127)), ('waves noise', dict(Wave_1=4, Wave_2=4, Wave_3=4, Filter_Freq=90))]:
    k = dict(base); k.update(kw)
    for o, dk in ((False, dict(Decay_closed=12)), (True, dict(Decay_open=30))):
        rep(('OPEN ' if o else 'CLOSED ') + tag, hat(o, **k, **dk))
