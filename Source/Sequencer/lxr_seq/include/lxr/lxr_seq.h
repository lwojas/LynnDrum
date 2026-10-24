/* LynnDrum sequencer core: C API.
 *
 * Instance-based port of the LXR step sequencer (7 tracks x 64 steps x 64 patterns, flam, shift,
 * probability, p-locks, Euclid, roll, pattern/song chaining, shuffle). Time is the firmware's own:
 * a 0.25 ms "systick" that the host injects with lxrseq_tick(); polling it once per engine block
 * (64 frames at 44 140 Hz = 5.8 ticks) reproduces the firmware's timing, including its shuffle. */
#ifndef LXR_SEQ_H
#define LXR_SEQ_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

#define LXRSEQ_TRACKS    7
#define LXRSEQ_STEPS     64
#define LXRSEQ_PATTERNS  64

typedef struct LxrSeq LxrSeq;

/* Where the sequencer's effects go. All callbacks are called synchronously from lxrseq_tick() and
 * from the edit calls that can trigger (roll). */
typedef struct LxrSeqSink {
    void* ctx;
    void (*trigger)(void* ctx, unsigned track, unsigned note, unsigned velocity);
    /* parameter write of a p-lock (status 0xB0 = CC, else CC2; data1/data2 as the firmware's ccHandler takes them) */
    void (*cc)(void* ctx, uint8_t status, uint8_t data1, uint8_t data2, uint8_t update_original);
    const uint8_t* originalCc;                       /* the engine's stored "original" CC values (restore source of p-locks) */
    void (*kit_change)(void* ctx, unsigned kit);     /* pattern change with PAR_PATTERN_MODE == 1 */
    void (*tempo)(void* ctx, unsigned bpm);          /* tempo changed (LFO sync recalculation) */
} LxrSeqSink;

LxrSeq* lxrseq_create(const LxrSeqSink* sink, uint32_t rng_seed);
void    lxrseq_destroy(LxrSeq*);

/* clock: advance to `systick` (0.25 ms units, monotonic) and process what is due - exactly one
 * sub-tick per call, like the firmware's once-per-block poll */
void    lxrseq_tick(LxrSeq*, uint32_t systick);

void    lxrseq_set_seed(LxrSeq*, uint32_t seed);               /* probability generator (xorshift32) */
void    lxrseq_set_tempo(LxrSeq*, unsigned bpm);
void    lxrseq_set_run(LxrSeq*, int running);
/* Start (or re-position) playback at an absolute host position: `abs_step` 16th notes from the host's zero, `sub` = sub-tick
 * (0..23) inside that step, `remaining` = fraction (0..1) of the current sub-tick still to wait. Every track plays step
 * abs_step % length, so polymetric tracks stay phase-correct across locates and loops. */
void    lxrseq_start_at(LxrSeq*, uint32_t abs_step, unsigned sub, double remaining);
int     lxrseq_is_running(const LxrSeq*);
void    lxrseq_set_mute(LxrSeq*, unsigned track, int muted);
void    lxrseq_set_next_pattern(LxrSeq*, unsigned pattern);
void    lxrseq_set_song_mode(LxrSeq*, int on);
void    lxrseq_set_song_entry(LxrSeq*, unsigned position, unsigned pattern);   /* 64 = end, 65 = loop */
void    lxrseq_set_roll(LxrSeq*, unsigned track, int on);
void    lxrseq_set_roll_rate(LxrSeq*, unsigned rate);                          /* 0 one-shot, 1..5 = 1/1..1/16 */
void    lxrseq_set_param(LxrSeq*, unsigned par, unsigned value);               /* PAR_PATTERN_MODE, PAR_FOLLOW, ... */
void    lxrseq_set_edit_pattern(LxrSeq*, unsigned pattern);                    /* pattern addressed by track-length edits */

/* pattern data */
void    lxrseq_set_main_step(LxrSeq*, unsigned pat, unsigned track, unsigned step, int on);
void    lxrseq_set_step(LxrSeq*, unsigned pat, unsigned track, unsigned step, unsigned vol, unsigned prob, unsigned note);
void    lxrseq_set_step_timing(LxrSeq*, unsigned pat, unsigned track, unsigned step, unsigned flam, unsigned shift_index);
void    lxrseq_set_plock(LxrSeq*, unsigned pat, unsigned track, unsigned step, unsigned slot, unsigned dest, unsigned value);
void    lxrseq_set_track_length(LxrSeq*, unsigned pat, unsigned track, unsigned length);
void    lxrseq_set_pattern_shuffle(LxrSeq*, unsigned pat, unsigned value);     /* 0..127, also applied now (as a pattern switch does) */
void    lxrseq_clear_pattern(LxrSeq*, unsigned pat);
void    lxrseq_euclid_length(LxrSeq*, unsigned track, unsigned length);
void    lxrseq_euclid_steps(LxrSeq*, unsigned track, unsigned steps, unsigned pat);      /* generates into `pat` */
void    lxrseq_euclid_rotation(LxrSeq*, unsigned track, unsigned rotation, unsigned pat);
void    lxrseq_get_main_steps(const LxrSeq*, unsigned pat, unsigned track, uint16_t out[4], unsigned* length);
unsigned lxrseq_active_pattern(const LxrSeq*);
int      lxrseq_step_index(const LxrSeq*, unsigned track);                  /* step the track last played (-1 before the first step) */
unsigned lxrseq_prescale_counter(const LxrSeq*);          /* sub-tick (0..23) within the current step */

#ifdef __cplusplus
}
#endif
#endif
