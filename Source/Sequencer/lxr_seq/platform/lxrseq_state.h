/* LxrSeq: all mutable file-scope state of the derived sequencer, plus the macro layer that maps the
 * upstream identifiers onto the thread-local current sequencer and the firmware services onto the
 * host sink. Not derived from upstream (it only names upstream state). */
#ifndef LXRSEQ_STATE_H
#define LXRSEQ_STATE_H

#include "stm32f7xx_hal.h"
#include "Soundengine/config.h"
#include "Soundengine/Sequencer/sequencer.h"
#include "Soundengine/Sequencer/clockSync.h"
#include "Soundengine/Sequencer/EuklidGenerator.h"
#include "Soundengine/DSPAudio/automationNode.h"
#include "lxr/lxr_seq.h"

typedef struct { uint8_t prev, current, next; } LxrSeqRnd;
typedef struct { uint8_t fxType; } LxrSeqFxDummy;
/* UI constants the sequencer compares against (values only need to be distinct) */
enum { SEQ_PAGE, FX_MODE_PAGE, PATTERN_LOAD_PAGE, SONG_MODE_PAGE, MENU_MIDI_PAGE, PERF_PAGE, EUKLID_PAGE };
enum { SELECT_MODE_PERF = 1, SELECT_MODE_PAT_GEN, SELECT_MODE_PATTERN, SELECT_MODE_SONG };
enum { CURRENT_KIT, SAVE_TYPE_KIT = 0 };
#define LED_START_STOP 0
#define LED_STEP1 0
#define LED_STEP2 0
#define LED_STEP3 0
#define LED_STEP4 0
#define LED_STEP5 0
#define LED_STEP6 0
#define LED_STEP7 0
#define LED_STEP8 0
#define LED_STEP9 0
#define LED_STEP10 0
#define LED_STEP11 0
#define LED_STEP12 0
#define LED_STEP13 0
#define LED_STEP14 0
#define LED_STEP15 0
#define LED_STEP16 0
#define SKIP_NEXT_KIT_AUTOLOAD 2
#define FX_OFF 0

struct LxrSeq
{
    LxrSeqSink sink;
    PatternSet m_seq_patternSet;
    PatternBackupBuffer m_patternBackupBuffer;
    uint8_t m_seq_songData[NUM_KIT_SLOTS][MAX_SONG_LENGTH];
    uint8_t* m_seq_activeSong;
    uint8_t m_seq_songPositionPointer;
    AutomationNode m_seq_automationNodes[NUM_TRACKS][2];
    int8_t  m_seq_stepIndex[NUM_TRACKS];
    uint8_t m_seq_lastMasterStep[NUM_TRACKS];
    int8_t  m_seq_stepToSkip[NUM_TRACKS];
    LxrSeqRnd m_seq_rndValue[NUM_TRACKS];
    uint8_t m_lastWasNoteOn[NUM_TRACKS];
    uint8_t m_chokeCurrent, m_chokeNext;
    uint8_t m_seq_prescaleCounter, m_seq_masterStepCnt, m_seq_rollRate, m_seq_rollState;
    uint16_t m_seq_tempo;
    uint32_t m_seq_lastTick;
    float   m_seq_deltaT, m_seq_shuffle, m_seq_lastShuffle;
    uint8_t m_isStepShuffled, m_seq_activeAutomTrack, m_seq_delayedSyncStepFlag, m_seq_isSyncExternal;
    int8_t  m_seq_armedArmedAutomationStep, m_seq_armedArmedAutomationTrack;
    uint8_t m_seq_mutedTracks, m_seq_songModeEnabled, m_seq_running, m_seq_activePattern, m_seq_pendingPattern;
    uint8_t m_seq_selectedStep, m_seq_recordActive, m_seq_eraseActive, m_seq_quantisation, m_seq_loadPendigFlag, m_seq_resetBarOnPatternChange;
    uint8_t m_midi_chan_notes[16];
    uint16_t m_midi_notes_on;
    /* clockSync.c */
    float   m_sync_window[WINDOW_SIZE];
    float   m_sync_timeLast;
    uint8_t m_sync_writePos, m_sync_armed, m_sync_clockCnt;
    uint32_t m_sync_delayedStepTimer;
    /* EuklidGenerator.c */
    uint8_t m_euklid_length[NUM_TRACKS], m_euklid_steps[NUM_TRACKS], m_euklid_rotation[NUM_TRACKS];
    ActiveSteps m_euklid_patternBuffer;
    uint16_t m_euklid_nextCnt1, m_euklid_originalLength;
    /* environment the firmware kept elsewhere */
    uint32_t m_systick_ticks;                    /* TIM14 ticks, 0.25 ms units (injected) */
    uint32_t rng;
    uint8_t m_activeParameters[NUM_PARAMS];      /* only PAR_PATTERN_MODE / SHUFFLE / FOLLOW / MIDI_NOTE* are read */
    uint8_t m_frontParser_shownPattern;          /* the pattern being edited (seq_setTrackLength) */
    uint8_t m_frontParser_activeTrack;
    uint8_t m_menu_activePage, m_menu_songMenuPosition, m_menu_activeBar, m_menu_shownPattern, m_menu_playedPattern, m_menu_activePatternBank;
    uint8_t m_menu_selectedPresetNr[4], m_menu_loadedPresetNr[4];
    uint8_t m_trigger_clockReceived, m_midi_process_block;
    LxrSeqFxDummy fxBusDummy;                 /* sequencer.c sets fxBus.fxType = FX_OFF before a kit load */
};

extern _Thread_local struct LxrSeq* lxrseq_cur;

#endif
