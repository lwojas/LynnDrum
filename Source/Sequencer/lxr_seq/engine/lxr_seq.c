/* lxr_seq.c - LynnDrum sequencer entry points (ours; GPL-3.0-only). */
#include <stdlib.h>
#include <string.h>
#include "lxr/lxr_seq.h"
#define __attribute__(x)   /* only ITCM/DTCM section placement in the derived headers */
#include "lxrseq_state.h"

_Thread_local struct LxrSeq* lxrseq_cur;

uint32_t lxrseq_rng_next(void)
{
    uint32_t x = lxrseq_cur->rng;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    lxrseq_cur->rng = x;
    return x;
}

void lxrseq_cc(struct LxrSeq* s, uint8_t status, uint8_t d1, uint8_t d2, uint8_t upd)
{
    if (s->sink.cc) s->sink.cc(s->sink.ctx, status, d1, d2, upd);
}

#define ENTER(q) struct LxrSeq* const prev_ = lxrseq_cur; lxrseq_cur = (q)
#define LEAVE()  (lxrseq_cur = prev_)

LxrSeq* lxrseq_create(const LxrSeqSink* sink, uint32_t seed)
{
    struct LxrSeq* q = (struct LxrSeq*)calloc(1, sizeof *q);
    if (!q) return NULL;
    q->sink = *sink;
    q->rng = seed ? seed : 0x1234ABCDu;
    ENTER(q);
    /* initial values of the upstream definitions (stripped from the sources) */
    lxrseq_cur->m_seq_rollRate = 1;
    lxrseq_cur->m_seq_tempo = 120;
    lxrseq_cur->m_seq_quantisation = QUANT_16;
    lxrseq_cur->m_seq_armedArmedAutomationStep = -1;
    lxrseq_cur->m_seq_armedArmedAutomationTrack = -1;
    /* Soundengine.c::soundengine_init(): euklid_init(); then seq_init(); seq_setBpm(120) */
    euklid_init();
    seq_init();
    seq_setBpm(120);
    LEAVE();
    return q;
}

void lxrseq_destroy(LxrSeq* q) { free(q); }

void lxrseq_tick(LxrSeq* q, uint32_t systick)
{
    ENTER(q); lxrseq_cur->m_systick_ticks = systick; seq_tick(); LEAVE();
}

void lxrseq_set_tempo(LxrSeq* q, unsigned bpm) { ENTER(q); seq_setBpm((uint16_t)bpm); LEAVE(); }
void lxrseq_set_run(LxrSeq* q, int r) { ENTER(q); seq_setRunning((uint8_t)r); LEAVE(); }
int  lxrseq_is_running(const LxrSeq* q) { return q->m_seq_running; }
void lxrseq_set_mute(LxrSeq* q, unsigned t, int m) { ENTER(q); seq_setMute((uint8_t)t, (uint8_t)m); LEAVE(); }
void lxrseq_set_next_pattern(LxrSeq* q, unsigned p) { ENTER(q); seq_setNextPattern((uint8_t)p); LEAVE(); }
void lxrseq_set_song_mode(LxrSeq* q, int on) { ENTER(q); seq_setSongModeEnabled((uint8_t)on); LEAVE(); }
void lxrseq_set_song_entry(LxrSeq* q, unsigned pos, unsigned pat) { q->m_seq_songData[0][pos & 63] = (uint8_t)pat; }
void lxrseq_set_roll(LxrSeq* q, unsigned t, int on) { ENTER(q); seq_setRoll((uint8_t)t, (uint8_t)on); LEAVE(); }
void lxrseq_set_roll_rate(LxrSeq* q, unsigned r) { ENTER(q); seq_setRollRate((uint8_t)r); LEAVE(); }
void lxrseq_set_param(LxrSeq* q, unsigned par, unsigned v) { if (par < NUM_PARAMS) q->m_activeParameters[par] = (uint8_t)v; }
void lxrseq_set_edit_pattern(LxrSeq* q, unsigned p) { q->m_frontParser_shownPattern = (uint8_t)p; }

void lxrseq_set_main_step(LxrSeq* q, unsigned pat, unsigned t, unsigned st, int on)
{ ENTER(q); seq_setMainStep((uint8_t)pat, (uint8_t)t, (uint8_t)st, (uint8_t)on); LEAVE(); }
void lxrseq_set_step(LxrSeq* q, unsigned pat, unsigned t, unsigned st, unsigned vol, unsigned prob, unsigned note)
{
    Step* s = &q->m_seq_patternSet.seq_subStepPattern[pat][t][st];
    s->volume = (uint8_t)vol; s->prob = (uint8_t)prob; s->note = (uint8_t)note;
}
void lxrseq_set_step_timing(LxrSeq* q, unsigned pat, unsigned t, unsigned st, unsigned flam, unsigned shift)
{
    q->m_seq_patternSet.seq_stepTiming[pat][t][st].flam = flam & 15;
    q->m_seq_patternSet.seq_stepTiming[pat][t][st].shift = shift & 15;
}
void lxrseq_set_plock(LxrSeq* q, unsigned pat, unsigned t, unsigned st, unsigned slot, unsigned dest, unsigned v)
{
    Step* s = &q->m_seq_patternSet.seq_subStepPattern[pat][t][st];
    if (slot == 1) { s->param1Nr = (uint8_t)dest; s->param1Val = (uint8_t)v; }
    else           { s->param2Nr = (uint8_t)dest; s->param2Val = (uint8_t)v; }
}
void lxrseq_set_track_length(LxrSeq* q, unsigned pat, unsigned t, unsigned n) { q->m_seq_patternSet.length[pat][t] = (uint8_t)n; }
void lxrseq_set_pattern_shuffle(LxrSeq* q, unsigned pat, unsigned v)
{
    ENTER(q);
    lxrseq_cur->m_seq_patternSet.shuffle[pat] = (uint8_t)v;
    lxrseq_cur->m_activeParameters[PAR_SHUFFLE] = (uint8_t)v;
    seq_setShuffle(v / 127.f);
    LEAVE();
}
void lxrseq_clear_pattern(LxrSeq* q, unsigned pat) { ENTER(q); seq_clearPattern((uint8_t)pat); LEAVE(); }
void lxrseq_euclid_length(LxrSeq* q, unsigned t, unsigned len) { ENTER(q); euklid_setLength((uint8_t)t, (uint8_t)len); LEAVE(); }
void lxrseq_euclid_steps(LxrSeq* q, unsigned t, unsigned steps, unsigned pat) { ENTER(q); euklid_setSteps((uint8_t)t, (uint8_t)steps, (uint8_t)pat); LEAVE(); }
void lxrseq_euclid_rotation(LxrSeq* q, unsigned t, unsigned rot, unsigned pat) { ENTER(q); euklid_setRotation((uint8_t)t, (uint8_t)rot, (uint8_t)pat); LEAVE(); }
void lxrseq_get_main_steps(const LxrSeq* q, unsigned pat, unsigned t, uint16_t out[4], unsigned* length)
{
    for (int i = 0; i < 4; i++) out[i] = q->m_seq_patternSet.seq_mainSteps[i][pat][t];
    if (length) *length = q->m_seq_patternSet.length[pat][t];
}
unsigned lxrseq_active_pattern(const LxrSeq* q) { return q->m_seq_activePattern; }
unsigned lxrseq_prescale_counter(const LxrSeq* q) { return q->m_seq_prescaleCounter; }
void lxrseq_set_seed(LxrSeq* q, uint32_t seed) { q->rng = seed ? seed : 0x1234ABCDu; }
int lxrseq_step_index(const LxrSeq* q, unsigned t) { return t < LXRSEQ_TRACKS ? q->m_seq_stepIndex[t] : -1; }

void lxrseq_start_at(LxrSeq* q, uint32_t absStep, unsigned sub, double remaining)
{
    ENTER(q);
    seq_setRunning(1);                                   /* resets the step indices (-1) and the sub-tick counter */
    if (sub > 23) sub = 23;
    if (remaining < 0.0) remaining = 0.0;
    if (remaining > 1.0) remaining = 1.0;
    const uint8_t pat = lxrseq_cur->m_seq_activePattern;
    for (int t = 0; t < LXRSEQ_TRACKS; ++t) {
        unsigned len = lxrseq_cur->m_seq_patternSet.length[pat][t]; if (!len) len = 16;
        /* seq_nextStep() increments first: sub == 0 -> the step is *about to start*, otherwise it is the current one */
        const uint32_t cur = (sub == 0) ? absStep + len - 1 : absStep;
        lxrseq_cur->m_seq_stepIndex[t] = (int8_t)(cur % len);
        lxrseq_cur->m_seq_lastMasterStep[t] = 0;
    }
    lxrseq_cur->m_seq_masterStepCnt = (uint8_t)(sub == 0 ? absStep : absStep + 1);      /* keeps the swing parity on the host grid */
    lxrseq_cur->m_seq_prescaleCounter = (uint8_t)sub;
    lxrseq_cur->m_seq_lastShuffle = 0;
    lxrseq_cur->m_isStepShuffled = 0;
    /* make the next poll fire after the remaining part of the current sub-tick period */
    const float period = lxrseq_cur->m_seq_deltaT > 1.f ? lxrseq_cur->m_seq_deltaT : 20.f;
    const uint32_t wait = (uint32_t)(period * remaining);
    lxrseq_cur->m_seq_lastTick = lxrseq_cur->m_systick_ticks - (uint32_t)period + wait;
    LEAVE();
}
unsigned lxrseq_pending_pattern(const LxrSeq* q) { return q->m_seq_pendingPattern; }
unsigned lxrseq_song_position(const LxrSeq* q) { return q->m_seq_songPositionPointer; }
int lxrseq_song_mode(const LxrSeq* q) { return q->m_seq_songModeEnabled; }
