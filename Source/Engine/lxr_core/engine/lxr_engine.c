/* lxr_engine.c - LynnDrum engine entry points.  Not derived from upstream code except that the
 * kit-loading order and initialisation sequence reproduce what the firmware does
 * (Soundengine.c::soundengine_init, presetManager.c::preset_sendDrumsetParameters/preset_morph_tick). */
#include <stdlib.h>
#include <string.h>
#include "lxr/lxr_engine.h"
#include "lxr_state.h"
#include "Soundengine/DSPAudio/mixer.h"
#include "Soundengine/DSPAudio/lfo.h"
#include "Soundengine/DSPAudio/DrumVoice.h"
#include "Soundengine/DSPAudio/Snare.h"
#include "Soundengine/DSPAudio/HiHat.h"
#include "Soundengine/DSPAudio/CymbalVoice.h"
#include "Soundengine/DSPAudio/modulationNode.h"
#include "Soundengine/MIDI/MidiParser.h"
#include "Soundengine/MIDI/MidiVoiceControl.h"
#include "Soundengine/MIDI/MidiMessages.h"
#include "Soundengine/MIDI/ParameterArray.h"
#include "menu/menu.h"
#include "menu/CcNr2Text.h"
#include "Soundengine/DSPAudio/random.h"

_Thread_local LxrEngine* lxr_cur;
_Static_assert(LXR_KIT_BYTES == END_OF_SOUND_PARAMETERS, "public kit size must equal END_OF_SOUND_PARAMETERS");
RNG_HandleTypeDef hrng;            /* referenced by random.h; unused (see lxr_rng_next) */

uint32_t lxr_rng_next(void)
{
    uint32_t x = lxr_cur->rng;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    lxr_cur->rng = x;
    return x;
}

/* scoped "current engine": keeps nested use and calls on different engines correct */
#define ENTER(e) LxrEngine* const lxr_prev_ = lxr_cur; lxr_cur = (e)
#define LEAVE()  (lxr_cur = lxr_prev_)

LxrEngine* lxr_create(uint32_t seed)
{
    LxrEngine* e = (LxrEngine*)calloc(1, sizeof(LxrEngine));
    if (!e) return NULL;
    ENTER(e);
    e->rng = seed ? seed : 0x1234ABCDu;
    e->tempo = 120;
    for (int i = 0; i < 8; i++) e->fader[i] = 1.f;

    /* Soundengine.c::soundengine_init() minus codec / sequencer / UART */
    mixer_init();
    parameterArray_init();
    /* H3: parameterArray[0] (PAR_NONE) is NULL upstream; the MCU reads address 0 harmlessly */
    parameterArray[0].ptr  = &e->par_none_target;
    parameterArray[0].type = TYPE_UINT8;
    for (int i = 0; i < 6; i++) modNode_init(&velocityModulators[i]);
    initDrumVoice();
    Snare_init();
    HiHat_init();
    Cymbal_init();
    LEAVE();
    return e;
}

void lxr_destroy(LxrEngine* e) { free(e); }

void lxr_set_seed(LxrEngine* e, uint32_t seed) { e->rng = seed ? seed : 0x1234ABCDu; }
void lxr_set_fader(LxrEngine* e, unsigned voice, float gain) { if (voice < 8) e->fader[voice] = gain; }

void lxr_set_tempo(LxrEngine* e, unsigned bpm)
{
    ENTER(e);
    e->tempo = (uint16_t)bpm;
    lfo_recalcSync();
    LEAVE();
}

void lxr_param(LxrEngine* e, unsigned par, unsigned value)
{
    if (par >= NUM_PARAMS) return;
    ENTER(e);
    if (par == 127) {
        /* H4: PAR_BANK_CHANGE arrives as CC#0, whose upstream prologue writes 64 KiB past
         * midiParser_originalCcValues; the case itself is empty. Dropped. */
        activeParameters[par] = (uint8_t)value;
        LEAVE();
        return;
    }
    MidiMsg msg; memset(&msg, 0, sizeof msg);
    if (par < 128) {
        msg.status = MIDI_CC;
        msg.data1  = (uint8_t)((par + 1) & 0x7f);        /* the firmware's "stupid offset" */
    } else {
        msg.status = MIDI_CC2;
        msg.data1  = (uint8_t)((par - 128) & 0x7f);
    }
    msg.data2 = (uint8_t)(value & 0x7f);
    midiParser_ccHandler(msg, 1, 0, 0.f);
    activeParameters[par] = msg.data2;
    LEAVE();
}

void lxr_cc(LxrEngine* e, uint8_t status, uint8_t data1, uint8_t data2, uint8_t update_original)
{
    ENTER(e);
    MidiMsg msg; memset(&msg, 0, sizeof msg);
    msg.status = status; msg.data1 = data1; msg.data2 = data2;
    midiParser_ccHandler(msg, update_original, 0, 0.f);
    LEAVE();
}

#pragma push_macro("midiParser_originalCcValues")
#undef midiParser_originalCcValues
const uint8_t* lxr_original_cc_table(const LxrEngine* e) { return e->midiParser_originalCcValues; }
#pragma pop_macro("midiParser_originalCcValues")

static void set_mod_target_(unsigned kind, unsigned n, unsigned idx)
{
    /* CortexParser FRONT_CC_VELO_TARGET / FRONT_CC_LFO_TARGET: the table index becomes a parameter number */
    if (idx >= getNumModTargets() || n > 5) return;
    const uint16_t t = modTargets[idx].param;
    if (kind == 0) { modNode_setDestination(&velocityModulators[n], t); return; }
    switch (n) {
    case 0: case 1: case 2: modNode_setDestination(&voiceArray[n].lfo.modTarget, t); break;
    case 3: modNode_setDestination(&snareVoice.lfo.modTarget, t);  break;
    case 4: modNode_setDestination(&cymbalVoice.lfo.modTarget, t); break;
    case 5: modNode_setDestination(&hatVoice.lfo.modTarget, t);    break;
    }
}

unsigned lxr_num_mod_targets(void) { return getNumModTargets(); }

void lxr_set_mod_target(LxrEngine* e, unsigned kind, unsigned n, unsigned idx)
{
    ENTER(e);
    set_mod_target_(kind, n, idx);
    LEAVE();
}

void lxr_load_kit(LxrEngine* e, const uint8_t kit[LXR_KIT_BYTES])
{
    ENTER(e);
    memset(activeParameters, 0, sizeof(uint8_t) * NUM_PARAMS);
    memcpy(activeParameters, kit, LXR_KIT_BYTES);

    const uint8_t nmt = getNumModTargets();
    for (int i = 0; i < 6; i++) {
        if (activeParameters[PAR_VEL_DEST_1 + i] >= nmt)  activeParameters[PAR_VEL_DEST_1 + i] = 0;
        if (activeParameters[PAR_TARGET_LFO1 + i] >= nmt) activeParameters[PAR_TARGET_LFO1 + i] = 0;
        if (activeParameters[PAR_VOICE_LFO1 + i] < 1 || activeParameters[PAR_VOICE_LFO1 + i] > 6)
            activeParameters[PAR_VOICE_LFO1 + i] = 1;
    }
    for (int i = 0; i < 6; i++) {
        set_mod_target_(0, (unsigned)i, activeParameters[PAR_VEL_DEST_1 + i]);
        set_mod_target_(1, (unsigned)i, activeParameters[PAR_TARGET_LFO1 + i]);
    }
    uint8_t snapshot[LXR_KIT_BYTES];
    memcpy(snapshot, activeParameters, sizeof snapshot);
    LEAVE();
    for (unsigned i = 0; i < LXR_KIT_BYTES; i++) lxr_param(e, i, snapshot[i]);
}

void lxr_trigger(LxrEngine* e, unsigned voice, unsigned note, unsigned velocity)
{
    if (voice >= LXR_NUM_VOICES) return;
    ENTER(e);
    voiceControl_noteOn((uint8_t)voice, (uint8_t)note, (uint8_t)velocity);
    LEAVE();
}

void lxr_render_block(LxrEngine* e, int16_t* st1, int16_t* st2)
{
    ENTER(e);
    /* mixer_calcNextSampleBlock(output, output2): DAC1 stereo lands in output2, DAC2 in output */
    mixer_calcNextSampleBlock(st2, st1);
    LEAVE();
}
