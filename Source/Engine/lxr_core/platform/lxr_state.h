/* LxrEngine: every piece of mutable file-scope state of the derived DSP / parameter code.
 *
 * Upstream keeps ~25 globals. They are members of this struct; the upstream identifiers keep
 * working through the macros below, which resolve against the *current engine* (thread-local,
 * set by every public lxr_* entry point). Function bodies therefore stay textually identical
 * to upstream, and any number of engines can coexist (also on concurrent audio threads).
 * Not derived from upstream (it only names upstream state). */
#ifndef LXR_STATE_H
#define LXR_STATE_H

#include "stm32f7xx_hal.h"
#include "Soundengine/config.h"
#include "Parameters.h"
#include "Soundengine/DSPAudio/DrumVoice.h"
#include "Soundengine/DSPAudio/Snare.h"
#include "Soundengine/DSPAudio/CymbalVoice.h"
#include "Soundengine/DSPAudio/HiHat.h"
#include "Soundengine/DSPAudio/modulationNode.h"
#include "Soundengine/DSPAudio/FX/FxRamBuffer.h"
#include "Soundengine/FxBus.h"
#include "Soundengine/MIDI/ParameterArray.h"

typedef struct LxrEngine
{
    /* voices */
    DrumVoice   voiceArray[NUM_DRUM_VOICES];
    SnareVoice  snareVoice;
    CymbalVoice cymbalVoice;
    HiHatVoice  hatVoice;
    /* FX */
    FxBus       fxBus;
    __fp16      FX_BUFFER[FX_BUFFER_SIZE + 1];
    /* modulation / parameters */
    ModulationNode velocityModulators[6];
    Parameter   parameterArray[END_OF_SOUND_PARAMETERS];
    uint8_t     midiParser_originalCcValues[0xff];
    uint16_t    midiParser_activeNrpnNumber;
    uint8_t     midi_MidiChannels[8];
    uint8_t     activeParameters[NUM_PARAMS];      /* the kit "edit buffer" the firmware mirrors parameters into */
    /* mixer */
    uint8_t     mixer_audioRouting[6];
    float       mixer_decimation_rate[7];
    float       mixer_decimation_cnt[6];
    int16_t     mixer_voice_samples[6];
    uint8_t     r1_Available, l1_Available, r2_Available, l2_Available;
    /* voice control */
    uint8_t     voiceStatus[NUM_DRUM_VOICES];
    uint8_t     active_voices;
    /* host-facing */
    float       fader[8];                          /* adc_getFaderVolume() */
    uint16_t    tempo;                             /* seq_getBpm() (integer BPM, see deviation S8) */
    uint8_t     mutedTracks;                       /* CC2_MUTE_n -> seq_setMute() */
    uint32_t    rng;                               /* xorshift32 replacing the hardware TRNG */
    uint8_t     par_none_target;                   /* H3: target of parameterArray[0] */
} LxrEngine;

extern _Thread_local LxrEngine* lxr_cur;

/* upstream identifiers -> current engine */
#define voiceArray                  (lxr_cur->voiceArray)
#define snareVoice                  (lxr_cur->snareVoice)
#define cymbalVoice                 (lxr_cur->cymbalVoice)
#define hatVoice                    (lxr_cur->hatVoice)
#define fxBus                       (lxr_cur->fxBus)
#define FX_BUFFER                   (lxr_cur->FX_BUFFER)
#define velocityModulators          (lxr_cur->velocityModulators)
#define parameterArray              (lxr_cur->parameterArray)
#define midiParser_originalCcValues (lxr_cur->midiParser_originalCcValues)
#define midiParser_activeNrpnNumber (lxr_cur->midiParser_activeNrpnNumber)
#define midi_MidiChannels           (lxr_cur->midi_MidiChannels)
#define activeParameters            (lxr_cur->activeParameters)
#define mixer_audioRouting          (lxr_cur->mixer_audioRouting)
#define mixer_decimation_rate       (lxr_cur->mixer_decimation_rate)
#define mixer_decimation_cnt        (lxr_cur->mixer_decimation_cnt)
#define mixer_voice_samples         (lxr_cur->mixer_voice_samples)
#define r1_Available                (lxr_cur->r1_Available)
#define l1_Available                (lxr_cur->l1_Available)
#define r2_Available                (lxr_cur->r2_Available)
#define l2_Available                (lxr_cur->l2_Available)
#define voiceStatus                 (lxr_cur->voiceStatus)
#define active_voices               (lxr_cur->active_voices)

/* hardware / firmware services the derived code calls */
#define adc_getFaderVolume(idx)     (lxr_cur->fader[(idx) & 7])
#define seq_getBpm()                (lxr_cur->tempo)
#define seq_setMute(trk, on)        ((on) ? (void)(lxr_cur->mutedTracks |= (uint8_t)(1u << (trk))) : (void)(lxr_cur->mutedTracks &= (uint8_t)~(1u << (trk))))
#define HAL_RNG_GetRandomNumber(h)  (lxr_rng_next())
#define uart_sendFrontpanelByte(x)  ((void)(x))
#define seq_sendMidiNoteOn(c, n, v) ((void)0)
#define seq_midiNoteOff(c)          ((void)0)
uint32_t lxr_rng_next(void);

/* UI hooks referenced by dead branches of the parameter handler */
#define menu_activePage             0
#define menu_getSubPage()           0
#define menu_switchSubPage(a, b)    ((void)0)
#define FX_MODE_PAGE                1
#endif
