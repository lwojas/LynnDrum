from kitlib import *
def one(group, voice, kw, blocks=400, vel=115, note=60):
    kit = defaults(); kit.update(V(group)(Volume=110, **kw))
    return mono(render(par_lines(kit) + ['trig %d %d %d' % (voice, note, vel)], blocks))
def rep(tag, x):
    st = next((i for i, v in enumerate(x) if abs(v) > 0.01), 0)
    print(tag.ljust(38), 'peak %.2f dec40 %5d ms dom %6.0f cen %6.0f hi-lo %5.1f dB' % (peak(x), decay_ms(x), dominant_hz(x, st), centroid_hz(x, st), band_db(x, st, 4000, 20000) - band_db(x, st, 80, 4000)))
print('--- snare')
for tag, kw in [('osc tri c57 noise mix61 dec28', dict(Waveform=1, Coarse=57, Noise_Freq=127, Noise_Osc_Mix=61, Decay=28, Pitch_Mod=30, Pitch_Decay=20)),
                ('osc sine c52 mix 80 dec24 hp', dict(Waveform=0, Coarse=52, Noise_Osc_Mix=80, Decay=24, Filter_Type=1, Filter_Freq=20, Pitch_Mod=40, Pitch_Decay=18)),
                ('osc tri c60 mix 100 dec32 hp40', dict(Waveform=1, Coarse=60, Noise_Osc_Mix=100, Decay=32, Filter_Type=1, Filter_Freq=40)),
                ('clap-ish repeat', dict(Waveform=1, Coarse=57, Noise_Osc_Mix=127, Decay=22, Repeat_Count=3, Filter_Type=2, Filter_Freq=60))]:
    rep(tag, one('Snare', 3, kw))
print('--- cymbal')
for tag, kw in [('rec/rec/noise c100 dec58', dict(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=100, Mod_Osc_1_Gain=110, Mod_Osc_2_Gain=110, Decay=58, Filter_Type=1, Filter_Freq=50)),
                ('rec c85 dec64', dict(Wave_1=3, Wave_2=2, Wave_3=3, Coarse=85, Mod_Osc_1_Gain=127, Mod_Osc_2_Gain=100, Decay=64, Filter_Type=1, Filter_Freq=70, Mod_Osc_1_Freq=80, Mod_Osc_2_Freq=40)),
                ('crash dec72', dict(Wave_1=3, Wave_2=3, Wave_3=4, Coarse=95, Mod_Osc_1_Gain=127, Mod_Osc_2_Gain=127, Decay=72, Filter_Type=1, Filter_Freq=40, Attack=2))]:
    rep(tag, one('Cymbal', 4, kw, 800))
print('--- toms')
for tag, kw, g, v in [('D2 tom c45', dict(Waveform=0, Coarse=45, Decay=30, Pitch_Mod=50, Pitch_Decay=28, Pitch_Slope=64), 'Drum 2', 1),
                      ('D3 tom c55', dict(Waveform=0, Coarse=55, Decay=26, Pitch_Mod=50, Pitch_Decay=26), 'Drum 3', 2),
                      ('D3 fm perc c70', dict(Waveform=0, Coarse=70, Decay=20, FM_Amount=60, FM_Freq=70, FM_Waveform=0, Pitch_Mod=30, Pitch_Decay=20), 'Drum 3', 2)]:
    rep(tag, one(g, v, kw, 300))
