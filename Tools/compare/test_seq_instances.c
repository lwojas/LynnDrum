/* Instance isolation test for lxr_seq: two differently programmed sequencers produce the same
 * event streams alone, interleaved tick by tick, and concurrently on two threads. */
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "lxr/lxr_seq.h"

#define TICKS 40000
#define MAXEV 20000
typedef struct { unsigned long t; unsigned track, note, vel; } Ev;
typedef struct { Ev ev[MAXEV]; int n; uint32_t now; } Log;

static void on_trigger(void* c, unsigned tr, unsigned note, unsigned vel)
{
    Log* l = (Log*)c;
    if (l->n < MAXEV) l->ev[l->n++] = (Ev){ l->now, tr, note, vel };
}

static LxrSeq* make(int v, Log* log)
{
    LxrSeqSink sink = { log, on_trigger, 0, 0, 0, 0 };
    static uint8_t zeros[256];
    sink.originalCc = zeros;
    LxrSeq* q = lxrseq_create(&sink, v ? 77 : 5);
    lxrseq_set_tempo(q, v ? 147 : 120);
    for (int s = 0; s < 16; s++) {
        if ((v == 0 && s % 4 == 0) || (v == 1 && s % 3 != 2)) {
            lxrseq_set_main_step(q, 0, v, s, 1);
            lxrseq_set_step(q, 0, v, s, 100, v ? 60 : 100, 60 + s);
            lxrseq_set_step_timing(q, 0, v, s, v ? 2 : 0, v ? 9 : 7);
        }
    }
    if (v) lxrseq_set_track_length(q, 0, v, 12);
    lxrseq_set_pattern_shuffle(q, 0, v ? 80 : 0);
    lxrseq_set_run(q, 1);
    return q;
}

static Log ref[2], got[2];

static void* run(void* p)
{
    int v = *(int*)p; Log* l = &got[v];
    LxrSeq* q = make(v, l);
    for (uint32_t t = 1; t <= TICKS; t += 6) { l->now = t; lxrseq_tick(q, t); }
    lxrseq_destroy(q);
    return NULL;
}

static int same(const char* what)
{
    for (int v = 0; v < 2; v++)
        if (ref[v].n != got[v].n || memcmp(ref[v].ev, got[v].ev, sizeof(Ev) * ref[v].n)) { printf("FAIL: %s differs (variant %d)\n", what, v); return 1; }
    printf("ok:   %s\n", what); return 0;
}

int main(void)
{
    int fail = 0, ids[2] = {0, 1};
    for (int v = 0; v < 2; v++) { memset(&got[v], 0, sizeof got[v]); run(&ids[v]); ref[v] = got[v]; }
    if (ref[0].n < 20 || ref[1].n < 20 || ref[0].n == ref[1].n) { puts("FAIL: vacuous test"); return 1; }

    memset(got, 0, sizeof got);
    Log* l0 = &got[0]; Log* l1 = &got[1];
    LxrSeq* a = make(0, l0); LxrSeq* b = make(1, l1);
    for (uint32_t t = 1; t <= TICKS; t += 6) { l0->now = t; lxrseq_tick(a, t); l1->now = t; lxrseq_tick(b, t); }
    lxrseq_destroy(a); lxrseq_destroy(b);
    fail |= same("interleaved sequencers");

    memset(got, 0, sizeof got);
    pthread_t th[2];
    for (int v = 0; v < 2; v++) pthread_create(&th[v], NULL, run, &ids[v]);
    for (int v = 0; v < 2; v++) pthread_join(th[v], NULL);
    fail |= same("concurrent threads");
    return fail;
}
