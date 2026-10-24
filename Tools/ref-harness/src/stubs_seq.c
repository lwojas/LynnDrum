/* Hardware/UI stubs the real sequencer.c / clockSync.c / EuklidGenerator.c reference (stage S0). */
#include <stdint.h>
#include <stdio.h>
#include "menu/menu.h"
#include "Preset/PresetManager.h"
#include "Soundengine/TriggerOut.h"
#include "ledHandler.h"
#include "buttonHandler.h"
#include "Soundengine/MIDI/CortexParser.h"
#include "Soundengine/MIDI/Uart.h"

extern FILE* lxr_evlog;
extern volatile uint32_t systick_ticks;

uint8_t frontParser_shownPattern;          /* the "edited" pattern: seq_setTrackLength uses it */
uint8_t menu_activeBar, menu_playedPattern, menu_shownPattern, menu_songMenuPosition;
uint8_t menu_loadedPresetNr[NUM_CURRENT];
uint8_t menu_selectedPresetNr[NUM_PRESET_LOCATIONS];
uint8_t midi_process_block;
uint8_t trigger_clockReceived;

void menu_repaintAll(void) { }
void menu_setShownPattern(uint8_t patternNr) { (void)patternNr; }
uint8_t buttonHandler_getMode(void) { return 0; }

void led_blinkHandler(void) { }
void led_clearActive_step(void) { }
void led_clearAllBlinkLeds(void) { }
void led_clearSequencerLeds(void) { }
uint8_t led_idx2StepLed(uint8_t idx) { return idx; }
void led_initPatternSelectLeds(void) { }
void led_resetBlinkTimer(void) { }
void led_setActive_step(uint8_t stepNr) { (void)stepNr; }
void led_setBlinkLed(const uint8_t ledNr, const uint8_t onOff) { (void)ledNr; (void)onOff; }
void led_setValue(uint8_t val, uint8_t ledNr) { (void)val; (void)ledNr; }
void led_updateSeqLeds(void) { }

void trigger_clockTick(uint8_t onOff, uint8_t cnt) { (void)onOff; (void)cnt; }
void trigger_reset(uint8_t value) { (void)value; }
void uart_sendFrontpanelSysExByte(uint8_t data) { (void)data; }

void preset_touchTimer(PresetTimer type) { (void)type; }
void preset_loadDrumsetRam(uint8_t presetNr, uint8_t isMorph, uint8_t sendImmediate)
{
    /* pattern change with PAR_PATTERN_MODE == 1 loads the pattern's kit; logged only */
    (void)isMorph; (void)sendImmediate;
    if (lxr_evlog) fprintf(lxr_evlog, "%lu kit %u\n", (unsigned long)systick_ticks, presetNr);
}
