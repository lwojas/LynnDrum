/* Phase-1 sequencer stubs (the S0 executable links the real sequencer instead). */
#include <stdint.h>
#include "Soundengine/DSPAudio/lfo.h"
#include "Soundengine/MIDI/MidiMessages.h"
#include "Soundengine/Sequencer/sequencer.h"
#include "Soundengine/Sequencer/clockSync.h"
#include "lxr_ref_api.h"

/* ---- sequencer (stubbed for Phase 1; S0 builds the real sequencer.c) ---- */
PatternSet seq_patternSet;
static uint16_t seq_tempo_host = 120;
uint16_t seq_getBpm(void) { return seq_tempo_host; }
void lxr_ref_set_bpm(unsigned bpm) { seq_tempo_host = (uint16_t)bpm; lfo_recalcSync(); }
uint8_t seq_getExtSync(void) { return 0; }
uint8_t seq_isRunning(void) { return 0; }
uint8_t seq_isTrackMuted(uint8_t trackNr) { (void)trackNr; return 0; }
void seq_setRunning(uint8_t isRunning) { (void)isRunning; }
void seq_setMute(uint8_t trackNr, uint8_t isMuted) { (void)trackNr; (void)isMuted; }
void seq_setNextPattern(const uint8_t patNr) { (void)patNr; }
void seq_addNote(uint8_t trackNr, uint8_t vel, uint8_t note) { (void)trackNr; (void)vel; (void)note; }
void seq_recordAutomation(uint8_t voice, uint8_t dest, uint8_t value) { (void)voice; (void)dest; (void)value; }
void seq_midiNoteOff(uint8_t chan) { (void)chan; }
void seq_sendMidiNoteOn(const uint8_t channel, const uint8_t note, const uint8_t veloc) { (void)channel; (void)note; (void)veloc; }
void seq_sync(void) { }
void sync_midiResetPosition(void) { }
void sync_midiStartStop(uint8_t isStart) { (void)isStart; }

uint8_t seq_prescaleCounter;
