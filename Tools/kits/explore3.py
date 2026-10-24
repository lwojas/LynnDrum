from kitlib import *
D1 = V('Drum 1')
def kick(**kw):
    kit = defaults(); kit.update(D1(Waveform=0, Volume=127, Coarse=31, Decay=32, **kw))
    return mono(render(par_lines(kit) + ['trig 0 60 120'], 300))
print('mod  pd  slope | f5-15  f20-40  f50-90  f120-220 | peak')
for mod in (45, 60, 75):
    for pd in (30, 40, 50):
        for sl in (64, 90):
            x = kick(Pitch_Mod=mod, Pitch_Decay=pd, Pitch_Slope=sl)
            print('%3d %3d %3d | %5.0f %6.0f %6.0f %8.0f | %.2f' % (mod, pd, sl, zc_hz(x, 5, 15), zc_hz(x, 20, 40), zc_hz(x, 50, 90), zc_hz(x, 120, 220), peak(x)))
