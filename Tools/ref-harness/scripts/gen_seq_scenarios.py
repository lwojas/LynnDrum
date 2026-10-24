#!/usr/bin/env python3
"""Generate the stage-S0 sequencer scenarios (.lxr for lxr_ref_seq) into <outdir>.
Time: `ticks N` advances the 0.25 ms systick; one 16th step = 60000/bpm ticks, one 16-step bar = 16x that."""
import os, random, sys
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
SH = lambda s: 7 + s            # shift index for -7..+7

class Sc:
    def __init__(self, name, bpm=120, seed=1):
        self.name = name; self.bpm = bpm
        self.l = [f'seed {seed}', 'kit init', f'bpm {bpm}']
    def step(self, trk, n, vol=100, prob=100, note=60, flam=0, shift=0, pat=0):
        self.l += [f'ms {pat} {trk} {n} 1', f'sd {pat} {trk} {n} {vol} {prob} {note}', f'st {pat} {trk} {n} {flam} {SH(shift)}']
    def off(self, trk, n, pat=0): self.l.append(f'ms {pat} {trk} {n} 0')
    def length(self, trk, n, pat=0): self.l.append(f'len {pat} {trk} {n}')
    def plock(self, trk, n, slot, par, val, pat=0): self.l.append(f'pl {pat} {trk} {n} {slot} {par} {val}')
    def raw(self, *c): self.l += list(c)
    def run(self): self.l.append('run 1')
    def steps(self, n): self.l.append(f'ticks {int(n * 60000 / self.bpm)}')
    def bars(self, n): self.steps(16 * n)
    def save(self):
        open(os.path.join(out, self.name + '.lxr'), 'w').write('\n'.join(self.l) + '\n')

def new(name, **kw): return Sc(name, **kw)

# --- basics -------------------------------------------------------------------------
s = new('floor4'); [s.step(0, n) for n in (0, 4, 8, 12)]; s.run(); s.bars(3); s.save()
s = new('volume_note'); [s.step(1, n, vol=8 * n + 1, note=36 + 3 * n) for n in range(16)]; s.run(); s.bars(2); s.save()
s = new('all_tracks'); [s.step(t, 2 * t, note=40 + t) for t in range(7)]; s.run(); s.bars(2); s.save()
s = new('hats_5_6'); [s.step(5, n) for n in (0, 2, 4, 6, 8, 10, 12, 14)]; s.step(6, 7); s.step(6, 15); s.run(); s.bars(2); s.save()
# --- flam / shift ---------------------------------------------------------------------
for f in range(1, 6):
    s = new(f'flam_{f}'); s.step(0, 0, flam=f); s.step(0, 8, flam=f, shift=0); s.run(); s.bars(2); s.save()
for sh in (-7, -4, -1, 1, 3, 7):
    s = new(f'shift_{sh:+d}'); [s.step(0, n, shift=sh) for n in (0, 4, 8, 12)]; s.run(); s.bars(2); s.save()
s = new('flam5_shift-7'); s.step(0, 3, flam=5, shift=-7); s.step(0, 9, flam=5, shift=7); s.run(); s.bars(2); s.save()
s = new('flam4_shift+5_overlap'); s.step(0, 2, flam=4, shift=5); s.step(0, 3, flam=4, shift=5); s.run(); s.bars(2); s.save()
s = new('shift+7_last_step_wrap'); s.step(0, 15, shift=7); s.run(); s.bars(3); s.save()
s = new('shift-7_first_step_wrap'); s.step(0, 0, shift=-7); s.run(); s.bars(3); s.save()
# --- probability ----------------------------------------------------------------------
for p in (1, 50, 100):
    for sd in (1, 2):
        s = new(f'prob_{p}_seed{sd}', seed=sd); [s.step(0, n, prob=p) for n in range(16)]; s.run(); s.bars(4); s.save()
s = new('prob_flam_shift', seed=3); [s.step(0, n, prob=50, flam=2, shift=-3) for n in range(0, 16, 2)]; s.run(); s.bars(4); s.save()
# --- track lengths --------------------------------------------------------------------
for ln in (1, 3, 5, 17, 32, 64):
    s = new(f'len_{ln}'); s.length(0, ln); [s.step(0, n) for n in range(0, min(ln, 64), 2)] + ([s.step(0, 0)] if ln == 1 else []); s.run(); s.steps(ln * 3 + 5); s.save()
s = new('poly_3_5_16')
for t, ln in ((0, 3), (1, 5), (2, 16)):
    s.length(t, ln); s.step(t, 0, note=40 + t); s.step(t, ln // 2, note=50 + t)
s.run(); s.bars(4); s.save()
s = new('poly_flam_across_wrap'); s.length(0, 5); s.step(0, 4, flam=3, shift=3); s.step(0, 0, shift=-2); s.run(); s.steps(30); s.save()
# --- tempo / shuffle ---------------------------------------------------------------------
for b in (60, 137, 200, 300):
    s = new(f'tempo_{b}', bpm=b); [s.step(0, n) for n in (0, 4, 8, 12)]; s.step(1, 2, flam=2); s.run(); s.bars(3); s.save()
for sv in (32, 64, 127):
    s = new(f'shuffle_{sv}'); [s.step(0, n) for n in range(16)]; s.raw(f'shuf 0 {sv}'); s.run(); s.bars(3); s.save()
s = new('shuffle_flam'); [s.step(0, n, flam=1) for n in range(4)]; s.step(1, 1, shift=-3); s.step(1, 3, shift=3); s.raw('shuf 0 127'); s.run(); s.bars(2); s.save()
# --- mute / run -----------------------------------------------------------------------
s = new('mute_mid'); [s.step(t, n) for t in (0, 1) for n in range(0, 16, 2)]; s.run(); s.bars(1); s.raw('mute 0 1'); s.bars(1); s.raw('mute 0 0'); s.bars(1); s.save()
s = new('stop_start'); [s.step(0, n) for n in (0, 5, 10)]; s.run(); s.steps(7); s.raw('run 0'); s.steps(8); s.run(); s.bars(1); s.save()
# --- p-locks -------------------------------------------------------------------------
s = new('plock_basic'); [s.step(0, n) for n in (0, 4, 8, 12)]
s.plock(0, 0, 1, 'PAR_FILTER_FREQ_1', 20); s.plock(0, 8, 1, 'PAR_FILTER_FREQ_1', 100); s.plock(0, 4, 1, 'PAR_RESO_1', 90)
s.run(); s.bars(2); s.save()
s = new('plock_two_slots'); s.step(0, 0); s.step(0, 8)
s.plock(0, 0, 1, 'PAR_FILTER_FREQ_1', 10); s.plock(0, 0, 2, 'PAR_VOL_SLOPE1', 33); s.plock(0, 8, 2, 'PAR_VOL_SLOPE1', 99)
s.run(); s.bars(2); s.save()
s = new('plock_hi_param'); s.step(0, 0); s.step(0, 8); s.plock(0, 0, 1, 'PAR_TRANS1_VOL', 50); s.run(); s.bars(2); s.save()
# --- patterns / song -------------------------------------------------------------------
s = new('pattern_switch'); [s.step(0, n) for n in (0, 8)]; [s.step(1, n, pat=1) for n in (0, 4, 8, 12)]
s.run(); s.steps(21); s.raw('pattern 1'); s.bars(3); s.save()
s = new('pattern_switch_poly'); s.length(0, 5); s.step(0, 0); s.step(0, 3); s.step(1, 0, pat=1)
s.run(); s.steps(7); s.raw('pattern 1'); s.steps(40); s.save()
s = new('song_mode'); [s.step(0, 0) for _ in (0,)]; s.step(1, 0, pat=1); s.step(2, 0, pat=2)
s.raw('songset 0 0', 'songset 1 1', 'songset 2 2', 'songset 3 64', 'song 1'); s.run(); s.bars(5); s.save()
s = new('pattern_kit_change'); s.step(0, 0); s.step(0, 0, pat=1); s.raw('par PAR_PATTERN_MODE 1'); s.run(); s.steps(5); s.raw('pattern 1'); s.bars(2); s.save()
for (ln, st, rot) in ((16, 5, 0), (16, 7, 3), (13, 5, 0), (32, 9, 0), (64, 17, 5), (8, 3, 0)):
    s = new(f'euclid_{ln}_{st}_{rot}'); s.raw(f'euk_len 0 {ln}', f'euk_steps 0 {st} 0', f'euk_rot 0 {rot} 0', 'dump 0 0'); ln == 16 and s.raw('len 0 0 16'); s.run(); s.steps(ln * 2 + 2); s.save()
# --- roll -----------------------------------------------------------------------------
for rr in (0, 1, 2, 3, 4, 5):
    s = new(f'roll_rate{rr}'); s.step(1, 0, note=64); s.raw(f'rollrate {rr}'); s.run(); s.steps(4); s.raw('roll 0 1'); s.bars(1); s.raw('roll 0 0'); s.steps(8); s.save()
# --- cross-track choke coupling (open item 1) ------------------------------------------
s = new('choke_cross_track'); s.step(0, 4, shift=-4); s.step(1, 3, note=61); s.step(1, 4, note=62); s.step(2, 3, note=63, shift=2); s.step(2, 4, note=64); s.run(); s.bars(2); s.save()
s = new('choke_cross_track2'); s.step(0, 4, shift=-4); s.step(1, 3, note=61, shift=7); s.step(2, 3, note=62, shift=5); s.step(3, 3, note=63, shift=2); s.run(); s.bars(2); s.save()
s = new('choke_same_track'); s.step(0, 4, shift=-4); s.step(0, 3, shift=0, note=61); s.run(); s.bars(2); s.save()
# --- firmware-like polling (one seq_tick per 1.45 ms block ~ 6 systicks) --------------------
s = new('poll6'); [s.step(0, n, flam=2) for n in (0, 4, 8, 12)]; s.run(); s.raw(f'ticks {int(3 * 16 * 60000 / 120)} 6'); s.save()
# --- seeded random patterns ------------------------------------------------------------------
for sd in range(1, 9):
    r = random.Random(sd); s = new(f'fuzz_{sd}', seed=sd, bpm=r.choice((90, 120, 133, 174)))
    for t in range(7):
        ln = r.choice((16, 16, 16, 12, 7, 24, 32, 64)); s.length(t, ln)
        for n in range(ln):
            if r.random() < 0.3:
                s.step(t, n, vol=r.randint(20, 127), prob=r.choice((100, 100, 75, 50)), note=r.randint(30, 90),
                       flam=r.choice((0, 0, 0, 1, 2, 3, 4, 5)), shift=r.choice((0, 0, 0, -7, -3, -1, 1, 2, 5, 7)))
    if sd % 2 == 0:
        s.raw(f'shuf 0 {r.randint(10, 100)}')
    if sd % 3 == 0:
        s.plock(0, 0, 1, 'PAR_FILTER_FREQ_1', 30); s.plock(1, 0, 2, 'PAR_FILTER_FREQ_2', 70)
    s.run(); s.bars(4); s.save()
print(len(os.listdir(out)), 'sequencer scenarios')
