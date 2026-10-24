#!/usr/bin/env python3
"""Derive Source/Sequencer/lxr_seq from the pinned upstream (+ harness patches H8).
Same technique as make_core.py: file-scope state moves into struct LxrSeq, upstream identifiers
resolve through macros against the thread-local current sequencer; definitions are stripped;
MIDI-out / LED / menu code is shimmed away. Function bodies stay textually identical."""
import os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
UP = os.path.join(ROOT, 'Reference/lxr-desktop-app/Core')
PATCHES = os.path.join(ROOT, 'Tools/ref-harness/patches')
DST = os.path.join(ROOT, 'Source/Sequencer/lxr_seq')

def rd(p): return open(p, newline='').read()
def wr(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True); open(p, 'w', newline='').write(s)

tmp = tempfile.mkdtemp(); touched = set()
for pf in sorted(os.listdir(PATCHES)):
    for line in rd(os.path.join(PATCHES, pf)).splitlines():
        if line.startswith('--- a/'): touched.add(line[6:].split('\t')[0].strip())
for rel in touched:
    os.makedirs(os.path.join(tmp, os.path.dirname(rel)), exist_ok=True); shutil.copy(os.path.join(UP, rel), os.path.join(tmp, rel))
for pf in sorted(os.listdir(PATCHES)):
    subprocess.run(['patch', '-p1', '-i', os.path.join(PATCHES, pf)], cwd=tmp, check=True, capture_output=True)
def src(rel):
    p = os.path.join(tmp, rel); return rd(p if os.path.exists(p) else os.path.join(UP, rel))

SOURCES = ['Src/Soundengine/Sequencer/sequencer.c', 'Src/Soundengine/Sequencer/clockSync.c',
           'Src/Soundengine/Sequencer/EuklidGenerator.c', 'Src/Soundengine/DSPAudio/automationNode.c']
HEADERS = ['Inc/Soundengine/Sequencer/sequencer.h', 'Inc/Soundengine/Sequencer/clockSync.h', 'Inc/Soundengine/Sequencer/EuklidGenerator.h',
           'Inc/Soundengine/DSPAudio/automationNode.h', 'Inc/Preset/SeqStep.h', 'Inc/Parameters.h', 'Inc/Soundengine/MIDI/MidiMessages.h',
           'Inc/Soundengine/globals.h', 'Inc/Soundengine/config.h']

def strip_decl(s, decl, count=1):
    """remove a (whole-statement) declaration, whitespace-insensitive; keeps surrounding comments"""
    pat = r'\s+'.join(re.escape(t) for t in decl.split())
    s2, n = re.subn(pat, '', s)
    if n != count: sys.exit('strip failed: %r matched %d times (expected %d)' % (decl, n, count))
    return s2

def strip_func(s, header_regex):
    """remove a whole function definition (header + balanced braces)"""
    m = re.search(header_regex, s)
    if not m: sys.exit('function not found: ' + header_regex)
    i = s.index('{', m.end()); depth = 0; j = i
    while True:
        if s[j] == '{': depth += 1
        elif s[j] == '}':
            depth -= 1
            if depth == 0: break
        j += 1
    return s[:m.start()] + s[j + 1:]

def rename_local(s, pairs):
    for old, new, cnt in pairs:
        if s.count(old) != cnt: sys.exit('local rename: %r found %d, expected %d' % (old, s.count(old), cnt))
        s = s.replace(old, new)
    return s

def edit_sequencer(s):
    # locals that would be hijacked by the isStepShuffled state macro
    s = rename_local(s, [('uint8_t isStepShuffled = isShuffled;', 'uint8_t isStepShuffledLocal = isShuffled;', 1),
                         ('const float shuffleFactor = isStepShuffled * seq_shuffle;', 'const float shuffleFactor = isStepShuffledLocal * seq_shuffle;', 1),
                         ('uint8_t isStepShuffled = seq_getMasterStepCnt()%2 == 1;', 'uint8_t isStepShuffledLocal = seq_getMasterStepCnt()%2 == 1;', 1),
                         ('if(isStepShuffled)\r\n\t\t\t\t\t{', 'if(isStepShuffledLocal)\r\n\t\t\t\t\t{', 1)])
    for d in ['uint8_t seq_prescaleCounter = 0;', 'uint8_t seq_masterStepCnt=0;', 'uint8_t seq_rollRate = 1;', 'uint8_t seq_rollState = 0;',
              'static int8_t seq_stepIndex[NUM_TRACKS];', 'static uint16_t seq_tempo = 120;', 'static uint32_t seq_lastTick = 0;',
              'uint8_t isStepShuffled=0;', 'static float seq_deltaT;', 'uint8_t seq_activeAutomTrack=0;', 'uint8_t seq_delayedSyncStepFlag = 0;',
              'uint8_t seq_isSyncExternal = 0;', 'uint8_t seq_lastMasterStep[NUM_TRACKS];', 'float seq_shuffle = 0;', 'int8_t seq_stepToSkip[NUM_TRACKS];',
              'static int8_t seq_armedArmedAutomationStep = -1;', 'static int8_t seq_armedArmedAutomationTrack = -1;', 'static uint8_t seq_mutedTracks=0;',
              'uint8_t seq_songModeEnabled=0;', 'uint8_t seq_running = 0;', 'uint8_t seq_activePattern = 0;', 'uint8_t seq_pendingPattern = 0;',
              'uint8_t seq_selectedStep = 0;', 'uint8_t seq_recordActive = 0;', 'uint8_t seq_eraseActive=0;', 'uint8_t seq_quantisation = QUANT_16;',
              'static uint8_t seq_loadPendigFlag = 0;', 'uint8_t seq_resetBarOnPatternChange=0;', 'static uint8_t midi_chan_notes[16];',
              'static uint16_t midi_notes_on=0;', 'float seq_lastShuffle = 0;', 'PatternSet seq_patternSet;', 'PatternBackupBuffer patternBackupBuffer;',
              'uint8_t seq_songData[NUM_KIT_SLOTS][MAX_SONG_LENGTH];', 'uint8_t *seq_activeSong;', 'uint8_t seq_songPositionPointer = 0;',
              'static AutomationNode seq_automationNodes[NUM_TRACKS][2];', 'uint8_t lastWasNoteOn[NUM_TRACKS];', 'uint8_t chokeCurrent=0;', 'uint8_t chokeNext=0;']:
        s = strip_decl(s, d)
    # seq_rndValue is an anonymous struct definition
    s, n = re.subn(r'struct\s*\{\s*uint8_t prev;\s*uint8_t current;\s*uint8_t next;\s*\}\s*seq_rndValue\[NUM_TRACKS\];', '', s)
    if n != 1: sys.exit('seq_rndValue')
    # PatternSet under USE_PATTERN_EDIT_BUFFER: the other branch
    s = strip_decl(s, 'PatternSet seq_patterns;')
    # MIDI-out helpers: removed (macros in lxrseq_state.h make every call a no-op)
    for fn in [r'static\s+void\s+seq_sendMidi\s*\(MidiMsg msg\)\s*(?=\{)', r'void\s+seq_midiNoteOff\s*\(uint8_t chan\)\s*(?=\{)',
               r'static\s+void\s+seq_sendRealtime\s*\(const uint8_t status\)\s*(?=\{)',
               r'void\s+seq_sendMidiNoteOn\s*\(const uint8_t channel, const uint8_t note, const uint8_t veloc\)\s*(?=\{)',
               r'static\s+void\s+seq_sendProgChg\s*\(const uint8_t ptn\)\s*(?=\{)']:
        s = strip_func(s, fn)
    # S6: upstream copies a "backup buffer" (the pattern as it was loaded from the SD card) over the pattern being left,
    # discarding every edit made since. The plugin edits patterns in place and keeps all 64 in memory.
    s = strip_decl(s, 'seq_copyBackupBufferToPattern(seq_activePattern);')
    for d in ['static void seq_sendMidi(MidiMsg msg);', 'static void seq_sendRealtime(const uint8_t status);', 'static void seq_sendProgChg(const uint8_t ptn);']:
        s = strip_decl(s, d)
    return s

EDITS = {'Src/Soundengine/Sequencer/sequencer.c': edit_sequencer}
def edit_clock(s):
    return rename_local(s, [('uint8_t isStepShuffled = seq_getMasterStepCnt()%2 == 1;', 'uint8_t isStepShuffledLocal = seq_getMasterStepCnt()%2 == 1;', 1),
                            ('if(isStepShuffled)', 'if(isStepShuffledLocal)', 1)])
EDITS['Src/Soundengine/Sequencer/clockSync.c'] = lambda s: edit_clock([s := strip_decl(s, d) for d in
    ['static float sync_window[WINDOW_SIZE];', 'float sync_timeLast = 0;', 'uint8_t sync_writePos = 0;', 'uint8_t sync_armed = 0;',
     'uint8_t sync_clockCnt = 0;', 'uint32_t sync_delayedStepTimer = 0;']][-1])
EDITS['Src/Soundengine/Sequencer/EuklidGenerator.c'] = lambda s: [s := strip_decl(s, d) for d in
    ['static uint8_t euklid_length[NUM_TRACKS];', 'static uint8_t euklid_steps[NUM_TRACKS];', 'static uint8_t euklid_rotation[NUM_TRACKS];',
     'static ActiveSteps euklid_patternBuffer;', 'static uint16_t euklid_nextCnt1=0;', 'static uint16_t euklid_originalLength=0;']][-1]

HDR_STRIP = {
    'Inc/Soundengine/globals.h': ['extern INDTCMZ volatile uint32_t systick_ticks;'],
    'Inc/Soundengine/Sequencer/sequencer.h': ['extern uint8_t seq_activePattern;', 'extern uint8_t seq_pendingPattern;', 'extern uint8_t seq_newPatternAvailable;',
        'extern uint8_t seq_prescaleCounter;', 'extern PatternSet seq_patternSet;', 'extern PatternBackupBuffer patternBackupBuffer;',
        'extern uint8_t seq_songData[NUM_KIT_SLOTS][MAX_SONG_LENGTH];', 'extern uint8_t *seq_activeSong;', 'extern uint8_t seq_songPositionPointer;',
        'extern uint8_t seq_selectedStep;', 'extern uint8_t seq_resetBarOnPatternChange;', 'extern PatternSet seq_patterns;'],
}

if os.path.exists(DST + '/src'): shutil.rmtree(DST + '/src')
if os.path.exists(DST + '/inc'): shutil.rmtree(DST + '/inc')
for rel in SOURCES:
    s = src(rel)
    if rel in EDITS: s = EDITS[rel](s)
    wr(os.path.join(DST, 'src', os.path.basename(rel)), s)
for rel in HEADERS:
    s = src(rel)
    for d in HDR_STRIP.get(rel, []): s = strip_decl(s, d)
    wr(os.path.join(DST, 'inc', rel.split('/', 1)[1]), s)
print('lxr_seq regenerated')
