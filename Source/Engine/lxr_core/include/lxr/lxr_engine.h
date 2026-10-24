/* LynnDrum engine core: C API.
 *
 * The engine renders at the instrument's native rate (44 140 Hz) in blocks of 64 frames,
 * exactly like the firmware it is derived from; sample-rate adaptation lives outside.
 * One LxrEngine is fully independent of any other; a single instance must not be used from
 * two threads at once, but different instances may run on different threads. */
#ifndef LXR_ENGINE_H
#define LXR_ENGINE_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

#define LXR_BLOCK_FRAMES   64          /* frames per render block (the firmware's DMA unit) */
#define LXR_ENGINE_RATE    44140       /* the real I2S rate of the firmware */
#define LXR_KIT_BYTES      247         /* END_OF_SOUND_PARAMETERS: one byte per sound parameter (checked in lxr_engine.c) */
#define LXR_NUM_VOICES     7           /* 0..2 drums, 3 snare, 4 cymbal, 5 closed hat, 6 open hat */

typedef struct LxrEngine LxrEngine;

LxrEngine* lxr_create(uint32_t seed);
void       lxr_destroy(LxrEngine*);

void lxr_set_seed(LxrEngine*, uint32_t seed);          /* noise / sample&hold generator */
void lxr_set_tempo(LxrEngine*, unsigned bpm);          /* integer BPM, drives tempo-synced LFOs */
void lxr_set_fader(LxrEngine*, unsigned voice, float gain);

/* One sound-parameter write, 0..LXR_KIT_BYTES-1 = the PAR_* index, value 0..127.
 * Same path as a front-panel edit of the firmware (midiParser_ccHandler). */
void lxr_param(LxrEngine*, unsigned par, unsigned value);

/* Load a complete kit (LXR_KIT_BYTES parameter bytes): velocity/LFO targets first, then every
 * parameter in index order, as the firmware does. */
void lxr_load_kit(LxrEngine*, const uint8_t kit[LXR_KIT_BYTES]);

/* Raw parameter-handler write as a sequencer p-lock produces it: status 0xB0 = CC (data1 = PAR+1),
 * otherwise CC2 (data1 = PAR-128). update_original = 0 for p-locks (the stored original is kept). */
void lxr_cc(LxrEngine*, uint8_t status, uint8_t data1, uint8_t data2, uint8_t update_original);
/* the stored "original" CC values (index = data1 of the CC; CC2 params at 128+); p-lock restore reads these */
const uint8_t* lxr_original_cc_table(const LxrEngine*);

/* Modulation targets (the firmware's `modTargets[]` list, index = value of the PAR_VEL_DEST_n / PAR_TARGET_LFOn
 * parameters). kind 0 = velocity modulator n (0..5), kind 1 = LFO of voice n (0..5). */
unsigned lxr_num_mod_targets(void);
void lxr_set_mod_target(LxrEngine*, unsigned kind, unsigned n, unsigned target_index);

void lxr_trigger(LxrEngine*, unsigned voice, unsigned note, unsigned velocity);

/* Render one block. st1 = stereo pair of DAC1 (default routing), st2 = DAC2; interleaved L/R,
 * LXR_BLOCK_FRAMES*2 samples each. */
void lxr_render_block(LxrEngine*, int16_t* st1, int16_t* st2);

#ifdef __cplusplus
}
#endif
#endif
