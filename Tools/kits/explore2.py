from kitlib import *
D1 = V('Drum 1')
def kick(**kw):
    kit = defaults(); kit.update(D1(Waveform=0, Volume=127, **kw))
    return mono(render(par_lines(kit) + ['trig 0 60 120'], 400))
for desc, kw in [('c31 mod0', dict(Coarse=31)),
                 ('c31 mod60 pd8', dict(Coarse=31, Pitch_Mod=60, Pitch_Decay=8)),
                 ('c31 mod80 pd20', dict(Coarse=31, Pitch_Mod=80, Pitch_Decay=20)),
                 ('c28 mod100 pd10', dict(Coarse=28, Pitch_Mod=100, Pitch_Decay=10))]:
    for dec in (30, 45):
        x = kick(Decay=dec, **kw)
        print((desc + ' dec%d' % dec).ljust(24), 'peak %.2f dec40 %4d ms  f@5-15 %6.0f f@30-60 %6.0f f@100-200 %6.0f' % (peak(x), decay_ms(x), zc_hz(x, 5, 15), zc_hz(x, 30, 60), zc_hz(x, 100, 200)))
