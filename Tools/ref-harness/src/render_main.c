/* lxr_ref_render - drives the UNMODIFIED upstream engine on the host.
 *
 * Reproduces the firmware's own call sequence:
 *   soundengine_init()           -> mixer_init, parameterArray_init, voices init
 *   preset_sendDrumsetParameters + preset_morph_tick  -> mod targets, then every
 *                                  kit parameter through midiParser_ccHandler
 *   voiceControl_noteOn           -> voice triggers
 *   mixer_calcNextSampleBlock     -> one 64-frame block (the firmware's DMA unit)
 *
 * Script grammar: see docs/ref-harness.md. One command per line, '#' comments. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdint.h>
#include <signal.h>
#include <execinfo.h>
#include <unistd.h>

#ifdef LXR_BACKEND_CORE
#include "lxr/lxr_engine.h"
#ifdef LXR_WITH_LXRSEQ
#include "lxr/lxr_seq.h"
#endif
#include "Parameters.h"                 /* lxr_core's copy: PAR_* enumerators */
extern const uint8_t initKit[254];      /* upstream initKit.c, used as a test fixture only */
#define END_OF_SOUND_PARAMETERS LXR_KIT_BYTES
#else
#include "Parameters.h"
#include "Preset/InitKit.h"
#include "Soundengine/DSPAudio/mixer.h"
#include "Soundengine/DSPAudio/DrumVoice.h"
#include "Soundengine/DSPAudio/Snare.h"
#include "Soundengine/DSPAudio/HiHat.h"
#include "Soundengine/DSPAudio/CymbalVoice.h"
#include "Soundengine/DSPAudio/modulationNode.h"
#include "Soundengine/MIDI/MidiParser.h"
#include "Soundengine/MIDI/MidiVoiceControl.h"
#include "Soundengine/MIDI/ParameterArray.h"
#include "Soundengine/MIDI/MidiMessages.h"
#include "menu/menu.h"
#include "menu/CcNr2Text.h"
#include "lxr_ref_api.h"
#endif
#ifdef LXR_WITH_SEQ
#include "Soundengine/Sequencer/sequencer.h"
#include "Soundengine/Sequencer/clockSync.h"
#include "Soundengine/Sequencer/EuklidGenerator.h"
#endif

#define BLOCK 64                 /* OUTPUT_DMA_SIZE */
#define ENGINE_FS 44140          /* REAL_FS: what the firmware actually runs at */

static const struct { const char* name; int value; } par_names[] = {
#include "par_names.inc"
};
#define NUM_PAR_NAMES (sizeof(par_names) / sizeof(par_names[0]))

/* ---------------------------------------------------------------- output */
typedef struct {
    int16_t* d;      /* interleaved L/R */
    size_t   frames, cap;
} Bus;

static Bus bus_dac1, bus_dac2;   /* dac1 = mixer `output2`, dac2 = mixer `output` */

static void bus_push(Bus* b, const int16_t* blk)
{
    if (b->frames + BLOCK > b->cap) {
        b->cap = b->cap ? b->cap * 2 : 1 << 16;
        b->d = (int16_t*)realloc(b->d, b->cap * 2 * sizeof(int16_t));
        if (!b->d) { fprintf(stderr, "out of memory\n"); exit(2); }
    }
    memcpy(b->d + b->frames * 2, blk, BLOCK * 2 * sizeof(int16_t));
    b->frames += BLOCK;
}

static void put16(FILE* f, uint16_t v) { fputc(v & 255, f); fputc(v >> 8, f); }
static void put32(FILE* f, uint32_t v) { put16(f, v & 0xFFFF); put16(f, v >> 16); }

static int write_wav(const char* path, const Bus* b, int as_float)
{
    FILE* f = fopen(path, "wb");
    if (!f) return -1;
    const uint32_t bytes = (uint32_t)(b->frames * 2 * (as_float ? 4 : 2));
    fwrite("RIFF", 1, 4, f); put32(f, 36 + bytes); fwrite("WAVEfmt ", 1, 8, f);
    put32(f, 16); put16(f, as_float ? 3 : 1); put16(f, 2);
    put32(f, ENGINE_FS); put32(f, ENGINE_FS * 2 * (as_float ? 4 : 2));
    put16(f, 2 * (as_float ? 4 : 2)); put16(f, as_float ? 32 : 16);
    fwrite("data", 1, 4, f); put32(f, bytes);
    for (size_t i = 0; i < b->frames * 2; i++) {
        if (as_float) {
            const float v = b->d[i] / 32768.0f;
            uint32_t u; memcpy(&u, &v, 4); put32(f, u);
        } else {
            put16(f, (uint16_t)b->d[i]);
        }
    }
    fclose(f);
    return 0;
}

static uint64_t fnv1a(uint64_t h, const void* p, size_t n)
{
    const uint8_t* s = (const uint8_t*)p;
    for (size_t i = 0; i < n; i++) { h ^= s[i]; h *= 1099511628211ULL; }
    return h;
}

/* ---------------------------------------------------------------- engine */
static FILE* trace;
extern FILE* lxr_evlog;
static unsigned long block_index;

#ifdef LXR_BACKEND_CORE
static LxrEngine* eng;
#ifdef LXR_WITH_LXRSEQ
static LxrSeq* sq;
#endif
FILE* lxr_evlog;
#ifdef LXR_WITH_LXRSEQ
static void sq_init(void);
#endif
static void engine_init(void) { eng = lxr_create(0x1234ABCDu);
#ifdef LXR_WITH_LXRSEQ
    sq_init();
#endif
}
static void send_cc(unsigned par, unsigned val)
{
    lxr_param(eng, par, val);
#ifdef LXR_WITH_LXRSEQ
    lxrseq_set_param(sq, par, val);
#endif
    if (trace) fprintf(trace, "%lu par %u %u%s\n", block_index, par, val, par == 127 ? " (dropped, H4)" : "");
}
static void apply_kit(const uint8_t* kit)
{
    lxr_load_kit(eng, kit);
#ifdef LXR_WITH_LXRSEQ
    for (unsigned i = 0; i < END_OF_SOUND_PARAMETERS; i++) lxrseq_set_param(sq, i, kit[i]);
#endif
    if (trace) for (unsigned i = 0; i < END_OF_SOUND_PARAMETERS; i++) fprintf(trace, "%lu par %u %u%s\n", block_index, i, kit[i], i == 127 ? " (dropped, H4)" : "");
}
static void render_blocks(unsigned long n)
{
    static int16_t out1[BLOCK * 2], out2[BLOCK * 2];
    for (unsigned long i = 0; i < n; i++, block_index++) {
        lxr_render_block(eng, out1, out2);      /* out1 = DAC1 pair, out2 = DAC2 pair */
        bus_push(&bus_dac1, out1);
        bus_push(&bus_dac2, out2);
    }
}
#else
/* H3: parameterArray[0] (PAR_NONE) keeps a NULL pointer, and modNode_originalValueChanged
 * dereferences it when a modulator's destination is 0 and CC 1 (index 0) is written - a
 * harmless read of address 0 on Cortex-M, a segfault on the host. Point it at a zero byte. */
static uint8_t par_none_target;

static void engine_init(void)
{
    /* soundengine_init() minus codec / sequencer / UART */
    mixer_init();
    parameterArray_init();
    parameterArray[0].ptr  = &par_none_target;
    parameterArray[0].type = TYPE_UINT8;
    for (int i = 0; i < 6; i++) modNode_init(&velocityModulators[i]);
    memset(midi_MidiChannels, 0, 8);
#ifdef LXR_WITH_SEQ
    euklid_init();
    seq_init();
    seq_setBpm(120);
#endif
    initDrumVoice();
    Snare_init();
    HiHat_init();
    Cymbal_init();
}

static void send_cc(unsigned par, unsigned val)
{
    /* the firmware's kit-send path (preset_morph_tick) and front-panel edits
     * (CortexParser FRONT_CC / FRONT_CC_2) both reach the engine like this */
    MidiMsg msg; memset(&msg, 0, sizeof msg);
    if (par == 127) {
        /* H4: PAR index 127 reaches ccHandler as CC#0; its prologue then does
         * midiParser_originalCcValues[(uint16_t)(0 - 1) + 1], an out-of-bounds write 64 KiB
         * past a 255-byte array (silent RAM scribble on the MCU, undefined on the host).
         * CC#0 has no other effect (bank change: empty case), so the message is dropped. */
        activeParameters[par] = (uint8_t)val;
        if (trace) fprintf(trace, "%lu par %u %u (dropped, H4)\n", block_index, par, val);
        return;
    }
    if (par < 128) {
        msg.status = MIDI_CC;
        msg.data1  = (uint8_t)((par + 1) & 0x7f);   /* "stupid offset" */
    } else {
        msg.status = MIDI_CC2;
        msg.data1  = (uint8_t)((par - 128) & 0x7f);
    }
    msg.data2 = (uint8_t)val;
    midiParser_ccHandler(msg, 1, 0, 0.f);
    activeParameters[par] = (uint8_t)val;
    if (trace) fprintf(trace, "%lu par %u %u\n", block_index, par, val);
}

static void apply_kit(const uint8_t* kit)
{
    memset(activeParameters, 0, sizeof activeParameters);
    memcpy(activeParameters, kit, END_OF_SOUND_PARAMETERS);

    /* preset_sendDrumsetParameters(): velocity / LFO mod targets first */
    const uint8_t nmt = getNumModTargets();
    for (int i = 0; i < 6; i++) {
        if (activeParameters[PAR_VEL_DEST_1 + i] >= nmt)  activeParameters[PAR_VEL_DEST_1 + i] = 0;
        if (activeParameters[PAR_TARGET_LFO1 + i] >= nmt) activeParameters[PAR_TARGET_LFO1 + i] = 0;
        if (activeParameters[PAR_VOICE_LFO1 + i] < 1 || activeParameters[PAR_VOICE_LFO1 + i] > 6)
            activeParameters[PAR_VOICE_LFO1 + i] = 1;
    }
    for (int i = 0; i < 6; i++) {
        modNode_setDestination(&velocityModulators[i], modTargets[activeParameters[PAR_VEL_DEST_1 + i]].param);
        const uint16_t t = modTargets[activeParameters[PAR_TARGET_LFO1 + i]].param;
        switch (i) {
        case 0: case 1: case 2: modNode_setDestination(&voiceArray[i].lfo.modTarget, t); break;
        case 3: modNode_setDestination(&snareVoice.lfo.modTarget, t);  break;
        case 4: modNode_setDestination(&cymbalVoice.lfo.modTarget, t); break;
        case 5: modNode_setDestination(&hatVoice.lfo.modTarget, t);    break;
        }
    }
    /* ... then preset_morph(): every sound parameter in index order (morph = 0) */
    uint8_t snapshot[END_OF_SOUND_PARAMETERS];
    memcpy(snapshot, activeParameters, sizeof snapshot);
    for (unsigned i = 0; i < END_OF_SOUND_PARAMETERS; i++) send_cc(i, snapshot[i]);
}

static void render_blocks(unsigned long n)
{
    static int16_t out1[BLOCK * 2], out2[BLOCK * 2];
    for (unsigned long i = 0; i < n; i++, block_index++) {
        mixer_calcNextSampleBlock(out1, out2);
        bus_push(&bus_dac2, out1);
        bus_push(&bus_dac1, out2);
    }
}

#endif


/* ---------------------------------------------------------------- sequencer backends */
static uint32_t sq_now;
#if defined(LXR_WITH_SEQ)          /* upstream sequencer (oracle) */
static void sq_init(void) { }
static void sq_poll(uint32_t t) { systick_ticks = t; seq_tick(); }
static void sq_ms(int p, int t, int st, int on) { seq_setMainStep((uint8_t)p, (uint8_t)t, (uint8_t)st, (uint8_t)on); }
static void sq_sd(int p, int t, int st, int vol, int prob, int note) {
    Step* s = &seq_patternSet.seq_subStepPattern[p][t][st]; s->volume = (uint8_t)vol; s->prob = (uint8_t)prob; s->note = (uint8_t)note; }
static void sq_st(int p, int t, int st, int flam, int shift) {
    seq_patternSet.seq_stepTiming[p][t][st].flam = (uint8_t)flam; seq_patternSet.seq_stepTiming[p][t][st].shift = (uint8_t)shift; }
static void sq_pl(int p, int t, int st, int slot, int dest, int v) {
    Step* s = &seq_patternSet.seq_subStepPattern[p][t][st];
    if (slot == 1) { s->param1Nr = (uint8_t)dest; s->param1Val = (uint8_t)v; } else { s->param2Nr = (uint8_t)dest; s->param2Val = (uint8_t)v; } }
static void sq_len(int p, int t, int n) { seq_patternSet.length[p][t] = (uint8_t)n; }
static void sq_shuf(int p, int v) { seq_patternSet.shuffle[p] = (uint8_t)v; activeParameters[PAR_SHUFFLE] = (uint8_t)v; seq_setShuffle(v / 127.f); }
static void sq_euk_len(int t, int n) { euklid_setLength((uint8_t)t, (uint8_t)n); }
static void sq_euk_steps(int t, int n, int p) { euklid_setSteps((uint8_t)t, (uint8_t)n, (uint8_t)p); }
static void sq_euk_rot(int t, int n, int p) { euklid_setRotation((uint8_t)t, (uint8_t)n, (uint8_t)p); }
static void sq_dump(int p, int t) {
    if (lxr_evlog) fprintf(lxr_evlog, "%lu mainsteps pat=%d trk=%d %04x %04x %04x %04x len=%u\n", (unsigned long)systick_ticks, p, t,
        seq_patternSet.seq_mainSteps[0][p][t], seq_patternSet.seq_mainSteps[1][p][t],
        seq_patternSet.seq_mainSteps[2][p][t], seq_patternSet.seq_mainSteps[3][p][t], seq_patternSet.length[p][t]); }
static void sq_mute(int t, int m) { seq_setMute((uint8_t)t, (uint8_t)m); }
static void sq_run(int r) { seq_setRunning((uint8_t)r); }
static void sq_pattern(int p) { seq_setNextPattern((uint8_t)p); }
static void sq_roll(int t, int on) { seq_setRoll((uint8_t)t, (uint8_t)on); }
static void sq_rollrate(int r) { seq_setRollRate((uint8_t)r); }
static void sq_song(int on) { seq_setSongModeEnabled((uint8_t)on); }
static void sq_songset(int pos, int pat) { seq_songData[0][pos & 63] = (uint8_t)pat; }
#elif defined(LXR_WITH_LXRSEQ)     /* lxr_seq driving lxr_core */
extern FILE* lxr_evlog;
static void sq_trigger(void* c, unsigned t, unsigned n, unsigned v) {
    (void)c; if (lxr_evlog) fprintf(lxr_evlog, "%lu sub=%u trig %u %u %u\n", (unsigned long)sq_now, lxrseq_prescale_counter(sq), t, n, v);
    lxr_trigger(eng, t, n, v); }
static void sq_cc(void* c, uint8_t st, uint8_t d1, uint8_t d2, uint8_t upd) {
    (void)c; if (lxr_evlog) fprintf(lxr_evlog, "%lu sub=%u cc %02x %u %u\n", (unsigned long)sq_now, lxrseq_prescale_counter(sq), st, d1, d2);
    lxr_cc(eng, st, d1, d2, upd); }
static void sq_kit(void* c, unsigned k) { (void)c; if (lxr_evlog) fprintf(lxr_evlog, "%lu kit %u\n", (unsigned long)sq_now, k); }
static void sq_tempo(void* c, unsigned bpm) { (void)c; lxr_set_tempo(eng, bpm); }
static void sq_init(void) {
    LxrSeqSink sink = { 0, sq_trigger, sq_cc, lxr_original_cc_table(eng), sq_kit, sq_tempo };
    sq = lxrseq_create(&sink, 0x1234ABCDu);
}
static void sq_poll(uint32_t t) { lxrseq_tick(sq, t); }
static void sq_ms(int p, int t, int st, int on) { lxrseq_set_main_step(sq, p, t, st, on); }
static void sq_sd(int p, int t, int st, int vol, int prob, int note) { lxrseq_set_step(sq, p, t, st, vol, prob, note); }
static void sq_st(int p, int t, int st, int flam, int shift) { lxrseq_set_step_timing(sq, p, t, st, flam, shift); }
static void sq_pl(int p, int t, int st, int slot, int dest, int v) { lxrseq_set_plock(sq, p, t, st, slot, dest, v); }
static void sq_len(int p, int t, int n) { lxrseq_set_track_length(sq, p, t, n); }
static void sq_shuf(int p, int v) { lxrseq_set_pattern_shuffle(sq, p, v); }
static void sq_euk_len(int t, int n) { lxrseq_euclid_length(sq, t, n); }
static void sq_euk_steps(int t, int n, int p) { lxrseq_euclid_steps(sq, t, n, p); }
static void sq_euk_rot(int t, int n, int p) { lxrseq_euclid_rotation(sq, t, n, p); }
static void sq_dump(int p, int t) {
    uint16_t m[4]; unsigned len; lxrseq_get_main_steps(sq, p, t, m, &len);
    if (lxr_evlog) fprintf(lxr_evlog, "%lu mainsteps pat=%d trk=%d %04x %04x %04x %04x len=%u\n", (unsigned long)sq_now, p, t, m[0], m[1], m[2], m[3], len); }
static void sq_mute(int t, int m) { lxrseq_set_mute(sq, t, m); }
static void sq_run(int r) { lxrseq_set_run(sq, r); }
static void sq_pattern(int p) { lxrseq_set_next_pattern(sq, p); }
static void sq_roll(int t, int on) { lxrseq_set_roll(sq, t, on); }
static void sq_rollrate(int r) { lxrseq_set_roll_rate(sq, r); }
static void sq_song(int on) { lxrseq_set_song_mode(sq, on); }
static void sq_songset(int pos, int pat) { lxrseq_set_song_entry(sq, pos, pat); }
#endif

/* ---------------------------------------------------------------- script */
static int lookup_par(const char* s)
{
    if (isdigit((unsigned char)s[0])) return atoi(s);
    for (size_t i = 0; i < NUM_PAR_NAMES; i++)
        if (!strcmp(par_names[i].name, s)) return par_names[i].value;
    return -1;
}

/* "init": preset_init() copies initKit[8..END_OF_SOUND_PARAMETERS) (the first 8 bytes
 * are the kit name) into the parameter block; the tail stays zero.
 * file: raw END_OF_SOUND_PARAMETERS parameter bytes, as preset_readDrumsetData() reads them. */
static int load_kit_bytes(const char* spec, uint8_t* kit)
{
    memset(kit, 0, END_OF_SOUND_PARAMETERS);
    if (!strcmp(spec, "init")) {
        for (int i = 8; i < END_OF_SOUND_PARAMETERS; i++) kit[i - 8] = initKit[i];
        return 0;
    }
    FILE* f = fopen(spec, "rb");
    if (!f) return -1;
    size_t n = fread(kit, 1, END_OF_SOUND_PARAMETERS, f);
    fclose(f);
    return n ? 0 : -1;
}

static int run_script(FILE* in, const char* name)
{
    char line[512];
    int lineno = 0;
    while (fgets(line, sizeof line, in)) {
        lineno++;
        char* h = strchr(line, '#'); if (h) *h = 0;
        char cmd[32] = {0}, a[256] = {0}, b[64] = {0}, c[64] = {0};
        int n = sscanf(line, "%31s %255s %63s %63s", cmd, a, b, c);
        if (n < 1) continue;
#define NEED(k) do { if (n < (k) + 1) { fprintf(stderr, "%s:%d: '%s' needs %d args\n", name, lineno, cmd, (k)); return -1; } } while (0)
        if (!strcmp(cmd, "seed"))        { NEED(1); 
#ifdef LXR_BACKEND_CORE
            lxr_set_seed(eng, (uint32_t)strtoul(a, 0, 0));
#ifdef LXR_WITH_LXRSEQ
            lxrseq_set_seed(sq, (uint32_t)strtoul(a, 0, 0));
#endif
#else
            lxr_host_rng_seed((uint32_t)strtoul(a, 0, 0));
#endif
        }
        else if (!strcmp(cmd, "bpm"))    {
            NEED(1);
#if defined(LXR_WITH_SEQ)
            seq_setBpm((uint16_t)atoi(a));
#elif defined(LXR_WITH_LXRSEQ)
            lxrseq_set_tempo(sq, (unsigned)atoi(a));
#else
#ifdef LXR_BACKEND_CORE
            lxr_set_tempo(eng, (unsigned)atoi(a));
#else
            lxr_ref_set_bpm((unsigned)atoi(a));
#endif
#endif
        }
#if defined(LXR_WITH_SEQ) || defined(LXR_WITH_LXRSEQ)
        else if (!strcmp(cmd, "ms"))   { /* ms pat track step on */
            int pat, trk, stp, on;
            if (sscanf(line, "%*s %d %d %d %d", &pat, &trk, &stp, &on) != 4) goto bad;
            sq_ms(pat, trk, stp, on);
        }
        else if (!strcmp(cmd, "sd"))   { /* sd pat track step vol prob note */
            int pat, trk, stp, vol, prob, note;
            if (sscanf(line, "%*s %d %d %d %d %d %d", &pat, &trk, &stp, &vol, &prob, &note) != 6) goto bad;
            sq_sd(pat, trk, stp, vol, prob, note);
        }
        else if (!strcmp(cmd, "st"))   { /* st pat track step flam shift(0..14, 7 = none) */
            int pat, trk, stp, flam, shift;
            if (sscanf(line, "%*s %d %d %d %d %d", &pat, &trk, &stp, &flam, &shift) != 5) goto bad;
            sq_st(pat, trk, stp, flam, shift);
        }
        else if (!strcmp(cmd, "pl"))   { /* pl pat track step slot(1|2) NAME|none value : NAME -> cortex destination number (PAR+1 below 127), a plain number is used raw */
            int pat, trk, stp, slot, pv; char nm[96];
            if (sscanf(line, "%*s %d %d %d %d %95s %d", &pat, &trk, &stp, &slot, nm, &pv) != 6) goto bad;
            int dest = 0xff;
            if (strcmp(nm, "none")) {
                const int pr = lookup_par(nm);
                if (pr < 0) { fprintf(stderr, "%s:%d: unknown parameter '%s'\n", name, lineno, nm); return -1; }
                dest = isdigit((unsigned char)nm[0]) ? pr : (pr < 127 ? pr + 1 : pr);
            }
            sq_pl(pat, trk, stp, slot, dest, pv);
        }
        else if (!strcmp(cmd, "len"))  { /* len pat track steps */
            int pat, trk, n;
            if (sscanf(line, "%*s %d %d %d", &pat, &trk, &n) != 3) goto bad;
            sq_len(pat, trk, n);
        }
        else if (!strcmp(cmd, "shuf")) { /* shuf pat 0..127 : pattern shuffle, applied like a pattern switch does */
            int pat, v;
            if (sscanf(line, "%*s %d %d", &pat, &v) != 2) goto bad;
            sq_shuf(pat, v);
        }
        else if (!strcmp(cmd, "euk_len"))   { NEED(2); sq_euk_len(atoi(a), atoi(b)); }
        else if (!strcmp(cmd, "euk_steps")) { NEED(3); sq_euk_steps(atoi(a), atoi(b), atoi(c)); }
        else if (!strcmp(cmd, "euk_rot"))   { NEED(3); sq_euk_rot(atoi(a), atoi(b), atoi(c)); }
        else if (!strcmp(cmd, "dump")) { NEED(2); sq_dump(atoi(a), atoi(b)); }
        else if (!strcmp(cmd, "mute")) { NEED(2); sq_mute(atoi(a), atoi(b)); }
        else if (!strcmp(cmd, "run"))  { NEED(1); sq_run(atoi(a)); }
        else if (!strcmp(cmd, "pattern")) { NEED(1); sq_pattern(atoi(a)); }
        else if (!strcmp(cmd, "roll")) { NEED(2); sq_roll(atoi(a), atoi(b)); }
        else if (!strcmp(cmd, "rollrate")) { NEED(1); sq_rollrate(atoi(a)); }
        else if (!strcmp(cmd, "song")) { NEED(1); sq_song(atoi(a)); }
        else if (!strcmp(cmd, "songset")) { NEED(2); sq_songset(atoi(a), atoi(b)); }
        else if (!strcmp(cmd, "ticks")) { /* ticks N [poll]: advance the 0.25 ms clock, polling the sequencer every `poll` ticks */
            NEED(1);
            const unsigned long n = strtoul(a, 0, 10); const unsigned poll = n >= 1 && b[0] ? (unsigned)atoi(b) : 1;
            for (unsigned long i = 0; i < n; i++) {
                sq_now++;
                if (poll <= 1 || (sq_now % poll) == 0) sq_poll(sq_now);
            }
        }
        else if (!strcmp(cmd, "play")) { /* play N : N audio blocks; the clock advances by the real block duration, one poll per block */
            NEED(1);
            const unsigned long n = strtoul(a, 0, 10);
            static double acc;
            for (unsigned long i = 0; i < n; i++) {
                acc += (double)BLOCK / (double)ENGINE_FS / 0.00025;
                sq_now = (uint32_t)acc;
                sq_poll(sq_now);
                render_blocks(1);
            }
        }
#endif
        else if (!strcmp(cmd, "kit"))    {
            NEED(1);
            uint8_t kit[END_OF_SOUND_PARAMETERS];
            if (load_kit_bytes(a, kit)) { fprintf(stderr, "%s:%d: cannot load kit '%s'\n", name, lineno, a); return -1; }
            apply_kit(kit);
        }
        else if (!strcmp(cmd, "par"))    {
            NEED(2);
            int p = lookup_par(a);
            if (p < 0 || p >= NUM_PARAMS) { fprintf(stderr, "%s:%d: unknown parameter '%s'\n", name, lineno, a); return -1; }
            send_cc((unsigned)p, (unsigned)atoi(b) & 0x7f);
        }
        else if (!strcmp(cmd, "trig"))   {
            NEED(3);
            const int v = atoi(a);
            if (v < 0 || v > 6) { fprintf(stderr, "%s:%d: voice 0..6\n", name, lineno); return -1; }
#ifdef LXR_BACKEND_CORE
            lxr_trigger(eng, (unsigned)v, (unsigned)atoi(b), (unsigned)atoi(c));
#else
            voiceControl_noteOn((uint8_t)v, (uint8_t)atoi(b), (uint8_t)atoi(c));
#endif
            if (trace) fprintf(trace, "%lu trig %d %d %d\n", block_index, v, atoi(b), atoi(c));
        }
        else if (!strcmp(cmd, "fader"))  {
            NEED(2);
#ifdef LXR_BACKEND_CORE
            lxr_set_fader(eng, (unsigned)atoi(a), (float)atof(b));
#else
            lxr_ref_set_fader((unsigned)atoi(a), (float)atof(b));
#endif
        }
        else if (!strcmp(cmd, "render")) { NEED(1); render_blocks(strtoul(a, 0, 10)); }
        else { fprintf(stderr, "%s:%d: unknown command '%s'\n", name, lineno, cmd); return -1; }
        continue;
#if defined(LXR_WITH_SEQ) || defined(LXR_WITH_LXRSEQ)
    bad:
        fprintf(stderr, "%s:%d: bad arguments for '%s'\n", name, lineno, cmd);
        return -1;
#endif
    }
    return 0;
}

static void crash_handler(int sig)
{
    void* frames[40];
    int n = backtrace(frames, 40);
    fprintf(stderr, "fatal signal %d at block %lu\n", sig, block_index);
    backtrace_symbols_fd(frames, n, 2);
    _exit(139);
}

int main(int argc, char** argv)
{
    signal(SIGSEGV, crash_handler); signal(SIGBUS, crash_handler);
    const char* script = NULL; const char* prefix = "out"; int as_float = 0, want_trace = 0;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-o") && i + 1 < argc) prefix = argv[++i];
        else if (!strcmp(argv[i], "--float")) as_float = 1;
        else if (!strcmp(argv[i], "--trace")) want_trace = 1;
        else if (!strcmp(argv[i], "--events") && i + 1 < argc) { lxr_evlog = fopen(argv[++i], "w"); }
        else if (!script) script = argv[i];
        else { fprintf(stderr, "usage: %s script [-o prefix] [--float] [--trace]\n", argv[0]); return 2; }
    }
    if (!script) { fprintf(stderr, "usage: %s script [-o prefix] [--float] [--trace]\n", argv[0]); return 2; }
    FILE* in = strcmp(script, "-") ? fopen(script, "r") : stdin;
    if (!in) { perror(script); return 2; }

    char path[1024];
    if (want_trace) { snprintf(path, sizeof path, "%s.trace.txt", prefix); trace = fopen(path, "w"); }

    engine_init();
    if (run_script(in, script)) return 1;

    uint64_t h1 = 1469598103934665603ULL, h2 = h1;
    h1 = fnv1a(h1, bus_dac1.d, bus_dac1.frames * 4);
    h2 = fnv1a(h2, bus_dac2.d, bus_dac2.frames * 4);
    snprintf(path, sizeof path, "%s.dac1.wav", prefix); write_wav(path, &bus_dac1, 0);
    snprintf(path, sizeof path, "%s.dac2.wav", prefix); write_wav(path, &bus_dac2, 0);
    if (as_float) {
        snprintf(path, sizeof path, "%s.dac1.f32.wav", prefix); write_wav(path, &bus_dac1, 1);
        snprintf(path, sizeof path, "%s.dac2.f32.wav", prefix); write_wav(path, &bus_dac2, 1);
    }
    if (trace) fclose(trace);
    if (lxr_evlog) fclose(lxr_evlog);
    printf("blocks=%lu frames=%zu dac1=%016llx dac2=%016llx\n", block_index, bus_dac1.frames,
           (unsigned long long)h1, (unsigned long long)h2);
    return 0;
}
