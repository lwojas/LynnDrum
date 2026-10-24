/* Instance isolation test for lxr_core.
 * A: reference run - each of two differently configured engines rendered alone.
 * B: the same two engines interleaved block by block in one thread.
 * C: the same two engines rendered concurrently on two threads.
 * All three must produce identical samples (no shared mutable state, TLS current-engine correct). */
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "lxr/lxr_engine.h"
#include "Parameters.h"

extern const uint8_t initKit[254];
#define NBLK 400

static LxrEngine* make(int variant)
{
    uint8_t kit[LXR_KIT_BYTES] = {0};
    for (int i = 8; i < LXR_KIT_BYTES; i++) kit[i - 8] = initKit[i];
    LxrEngine* e = lxr_create(variant == 0 ? 11 : 99);
    lxr_set_tempo(e, variant == 0 ? 120 : 173);
    lxr_load_kit(e, kit);
    if (variant == 1) {
        lxr_param(e, PAR_FILTER_FREQ_1, 30);
        lxr_param(e, PAR_OSC_WAVE_DRUM1, 2);
        lxr_param(e, PAR_FM_FREQ1, 90);
        lxr_param(e, PAR_FMAMNT1, 60);
    }
    return e;
}

static void step(LxrEngine* e, int variant, int blk, int16_t* out)
{
    static const int voices[2][4] = {{0, 3, 5, 6}, {1, 0, 4, 5}};
    if (blk % 50 == 0) lxr_trigger(e, voices[variant][(blk / 50) % 4], 48 + variant * 7, 100);
    int16_t a[128], b[128];
    lxr_render_block(e, a, b);
    memcpy(out, a, sizeof a); memcpy(out + 128, b, sizeof b);
}

static int16_t ref[2][NBLK][256], got[2][NBLK][256];

typedef struct { int variant; } Job;
static void* run(void* p)
{
    const int v = ((Job*)p)->variant;
    LxrEngine* e = make(v);
    for (int i = 0; i < NBLK; i++) step(e, v, i, got[v][i]);
    lxr_destroy(e);
    return NULL;
}

static int same(const char* what)
{
    if (memcmp(ref, got, sizeof ref)) { printf("FAIL: %s differs\n", what); return 1; }
    printf("ok:   %s\n", what); return 0;
}

int main(void)
{
    int fail = 0;
    for (int v = 0; v < 2; v++) { LxrEngine* e = make(v); for (int i = 0; i < NBLK; i++) step(e, v, i, ref[v][i]); lxr_destroy(e); }
    long energy = 0; for (int i = 0; i < NBLK; i++) for (int k = 0; k < 256; k++) energy += abs(ref[0][i][k]) + abs(ref[1][i][k]);
    if (!energy) { puts("FAIL: reference is silent"); return 1; }
    if (!memcmp(ref[0], ref[1], sizeof ref[0])) { puts("FAIL: variants identical (test is vacuous)"); return 1; }

    LxrEngine* e0 = make(0); LxrEngine* e1 = make(1);                 /* B: interleaved */
    for (int i = 0; i < NBLK; i++) { step(e0, 0, i, got[0][i]); step(e1, 1, i, got[1][i]); }
    lxr_destroy(e0); lxr_destroy(e1);
    fail |= same("interleaved engines");

    memset(got, 0, sizeof got);                                       /* C: two threads */
    pthread_t t[2]; Job j[2] = {{0}, {1}};
    for (int v = 0; v < 2; v++) pthread_create(&t[v], NULL, run, &j[v]);
    for (int v = 0; v < 2; v++) pthread_join(t[v], NULL);
    fail |= same("concurrent threads");
    return fail;
}
