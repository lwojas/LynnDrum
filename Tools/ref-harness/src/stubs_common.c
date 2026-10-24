/* Host stubs for the hardware / UI / sequencer symbols that the engine files
 * (mixer, voices, MidiParser::ccHandler, MidiVoiceControl, lfo, ...) reference.
 * Every stub is inert unless noted. Phase-1 scope: sequencer.c is NOT built
 * (stage S0 replaces the seq_* stubs with the real file). */
#include <stdint.h>
#include <string.h>
#include "Soundengine/DSPAudio/lfo.h"
#include "Soundengine/MIDI/MidiMessages.h"
#include "Soundengine/Sequencer/sequencer.h"
#include "Soundengine/Sequencer/clockSync.h"
#include "Soundengine/MIDI/MidiParser.h"
#include "Soundengine/MIDI/CortexParser.h"
#include "menu/menu.h"
#include "IO/adcPots.h"
#include "lxr_ref_api.h"
#include "Soundengine/MIDI/MidiVoiceControl.h"
#include <stdio.h>

/* ---- globals ------------------------------------------------------------ */
GPIO_TypeDef lxr_host_gpio_all_high = { 0xFFFFFFFFu };
RNG_HandleTypeDef hrng;
volatile uint32_t systick_ticks;
float debugWatch;
void Error_Handler(void) { }

/* deterministic PRNG replacing the hardware TRNG (xorshift32) */
static uint32_t rng_state = 0x1234ABCDu;
void lxr_host_rng_seed(uint32_t seed) { rng_state = seed ? seed : 0x1234ABCDu; }
uint32_t lxr_host_rng_next(void)
{
    uint32_t x = rng_state;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    rng_state = x;
    return x;
}

/* ---- menu / UI: the kit "edit buffer" the firmware mirrors parameters into ---- */
uint8_t activeParameters[NUM_PARAMS];
uint8_t menu_activePage;
uint8_t frontParser_activeTrack;
uint8_t menu_getActiveVoice(void) { return 0; }
uint8_t menu_getSubPage(void) { return 0; }
uint8_t menu_getViewedPattern(void) { return 0; }
void menu_repaint(void) { }
void menu_switchSubPage(uint8_t subPageNr, uint8_t toggle) { (void)subPageNr; (void)toggle; }

/* ---- faders: host-settable, default full scale ---- */
static float faders[8] = { 1.f, 1.f, 1.f, 1.f, 1.f, 1.f, 1.f, 1.f };
void lxr_ref_set_fader(unsigned idx, float v) { if (idx < 8) faders[idx] = v; }
float adc_getFaderVolume(uint8_t idx) { return faders[idx & 7]; }

/* ---- UART / USB / MIDI out: swallowed ---- */
void uart_sendFrontpanelByte(uint8_t data) { (void)data; }
void uart_sendMidi(MidiMsg msg) { (void)msg; }
void usb_sendMidi(MidiMsg msg) { (void)msg; }


/* ---- event log: sequencer-visible effects, in firmware order ---------------- */
FILE* lxr_evlog;
extern uint8_t seq_prescaleCounter;
void lxr_hook_noteOn(uint8_t voice, uint8_t note, uint8_t vel)   /* sequencer.c: voiceControl_noteOn */
{
    if (lxr_evlog) fprintf(lxr_evlog, "%lu sub=%u trig %u %u %u\n", (unsigned long)systick_ticks, seq_prescaleCounter, voice, note, vel);
    voiceControl_noteOn(voice, note, vel);
}
void lxr_hook_cc(MidiMsg msg, uint8_t updateOriginalValue, uint8_t isFloatModulator, float v)  /* sequencer.c, automationNode.c */
{
    if (lxr_evlog) fprintf(lxr_evlog, "%lu sub=%u cc %02x %u %u%s\n", (unsigned long)systick_ticks, seq_prescaleCounter, msg.status, msg.data1, msg.data2, isFloatModulator ? " flt" : "");
    midiParser_ccHandler(msg, updateOriginalValue, isFloatModulator, v);
}
