#!/usr/bin/env python3
"""Derive Source/Engine/lxr_core from the pinned upstream (+ the harness patches H1-H8).

This script documents *exactly* what differs from upstream; its output is committed and is the
source of truth afterwards (it is not a build step).  Every edit asserts its match count so a
different upstream pin fails loudly.

Edits are mechanical:
  * the file-scope mutable state moves into struct LxrEngine (platform/lxr_state.h); the original
    identifiers keep working through macros that resolve against the thread-local current engine,
    so function bodies stay textually identical to upstream;
  * the definitions / extern declarations of that state are removed;
  * ccHandler is extracted (unchanged apart from removing UART/menu/sequencer side effects).
"""
import os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
UP = os.path.join(ROOT, 'Reference/lxr-desktop-app/Core')
PATCHES = os.path.join(ROOT, 'Tools/ref-harness/patches')
DST = os.path.join(ROOT, 'Source/Engine/lxr_core')

def rd(p): return open(p, newline='').read()
def wr(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', newline='').write(s)

# ---------- 1. patched upstream tree (harness patches) ---------------------------------------
tmp = tempfile.mkdtemp()
touched = set()
for pf in sorted(os.listdir(PATCHES)):
    for line in rd(os.path.join(PATCHES, pf)).splitlines():
        if line.startswith('--- a/'):
            touched.add(line[6:].split('\t')[0].strip())
for rel in touched:
    os.makedirs(os.path.join(tmp, os.path.dirname(rel)), exist_ok=True)
    shutil.copy(os.path.join(UP, rel), os.path.join(tmp, rel))
for pf in sorted(os.listdir(PATCHES)):
    subprocess.run(['patch', '-p1', '-i', os.path.join(PATCHES, pf)], cwd=tmp, check=True, capture_output=True)

def src(rel):
    p = os.path.join(tmp, rel)
    return rd(p if os.path.exists(p) else os.path.join(UP, rel))

# ---------- 2. file lists --------------------------------------------------------------------
DSP = ['1PoleLp', 'BufferTools', 'CymbalVoice', 'Decay', 'distortion', 'dither', 'DrumVoice',
       'HiHat', 'lfo', 'mixer', 'modulationNode', 'Oscillator', 'random', 'ResonantFilter', 'Samples', 'SlopeEg2',
       'snapEg', 'Snare', 'squareRootLut', 'TiltEq', 'transientGenerator', 'transientTables', 'wavetable',
       'FX/Compressor', 'FX/Delay', 'FX/Distortion', 'FX/FxRamBuffer', 'FX/Reverb', 'FX/Ringmod',
       'FX/VerbTools/AllpassDelay', 'FX/VerbTools/sinCos', 'FX/VerbTools/VerbDelay', 'FX/VerbTools/VerbModDelay']
SOURCES = ['Src/Soundengine/DSPAudio/%s.c' % f for f in DSP] + [
    'Src/Soundengine/FxBus.c', 'Src/Soundengine/MIDI/MidiVoiceControl.c', 'Src/Soundengine/MIDI/ParameterArray.c',
    'Src/Soundengine/MIDI/MidiMessages.c', 'Src/menu/Cc2Text.c']
HEADERS = []
for d in ('Inc/Soundengine/DSPAudio', 'Inc/Soundengine/DSPAudio/FX', 'Inc/Soundengine/DSPAudio/FX/VerbTools'):
    for f in sorted(os.listdir(os.path.join(UP, d))):
        if f.endswith('.h'): HEADERS.append(d + '/' + f)
HEADERS += ['Inc/Soundengine/FxBus.h', 'Inc/Soundengine/config.h', 'Inc/Soundengine/globals.h', 'Inc/Soundengine/datatypes.h',
            'Inc/Soundengine/MIDI/MidiMessages.h', 'Inc/Soundengine/MIDI/MidiParser.h', 'Inc/Soundengine/MIDI/MidiVoiceControl.h',
            'Inc/Soundengine/MIDI/ParameterArray.h', 'Inc/Soundengine/MIDI/valueShaper.h', 'Inc/Soundengine/MIDI/MidiNoteNumbers.h',
            'Inc/Parameters.h', 'Inc/menu/CcNr2Text.h', 'Inc/config.h']

# ---------- 3. edits -------------------------------------------------------------------------
def sub(s, pat, rep, count=1, flags=0, what=''):
    s2, n = re.subn(pat, rep, s, flags=flags)
    if n != count:
        sys.exit('edit failed (%s): %r matched %d times, expected %d' % (what, pat, n, count))
    return s2

def drop_line(s, text, what, count=1):
    """remove whole lines that contain `text` (exact substring)"""
    lines = s.split('\n'); out = []; n = 0
    for l in lines:
        if text in l and not l.lstrip().startswith('//'):
            n += 1; continue
        out.append(l)
    if n != count:
        sys.exit('edit failed (%s): %r removed %d lines, expected %d' % (what, text, n, count))
    return '\n'.join(out)

EDITS = {}
def edit(rel):
    def deco(f): EDITS[rel] = f; return f
    return deco

# definitions that moved into LxrEngine
@edit('Src/Soundengine/DSPAudio/CymbalVoice.c')
def _(s): return drop_line(s, 'INDTCMZ CymbalVoice cymbalVoice;', 'cymbal def')
@edit('Src/Soundengine/DSPAudio/HiHat.c')
def _(s): return drop_line(s, 'INDTCMZ HiHatVoice hatVoice;', 'hat def')
@edit('Src/Soundengine/DSPAudio/Snare.c')
def _(s): return drop_line(s, 'INDTCMZ SnareVoice snareVoice;', 'snare def')
@edit('Src/Soundengine/DSPAudio/DrumVoice.c')
def _(s): return drop_line(s, 'INDTCMZ DrumVoice voiceArray[NUM_DRUM_VOICES];', 'drum def')
@edit('Src/Soundengine/DSPAudio/modulationNode.c')
def _(s): return drop_line(s, 'INDTCMZ ModulationNode velocityModulators[6];', 'velmod def')
@edit('Src/Soundengine/FxBus.c')
def _(s): return drop_line(s, 'INDTCMZ FxBus fxBus;', 'fxbus def')
@edit('Src/Soundengine/DSPAudio/FX/FxRamBuffer.c')
def _(s): return drop_line(s, 'INDTCMZ __fp16 FX_BUFFER[FX_BUFFER_SIZE+1];', 'fxbuf def')
@edit('Src/Soundengine/MIDI/ParameterArray.c')
def _(s): return drop_line(s, ' Parameter parameterArray[END_OF_SOUND_PARAMETERS];', 'paramarray def')
@edit('Src/Soundengine/MIDI/MidiVoiceControl.c')
def _(s):
    s = drop_line(s, 'static uint8_t active_voices=0;', 'active_voices def')
    return drop_line(s, 'uint8_t voiceStatus[NUM_DRUM_VOICES];', 'voiceStatus def')
@edit('Src/Soundengine/DSPAudio/mixer.c')
def _(s):
    for t in ('INDTCMZ uint8_t mixer_audioRouting[6];', 'INDTCMZ float mixer_decimation_rate[7];', 'INDTCMZ float mixer_decimation_cnt[6];',
              'INDTCMZ int16_t mixer_voice_samples[6];', '\tuint8_t r2_Available;', '\tuint8_t l1_Available;', '\tuint8_t l2_Available;', '\tuint8_t r1_Available;'):
        s = drop_line(s, t, 'mixer def ' + t)
    # jack detect: every jack is connected on the host (identity routing)
    for pin in ('r2', 'l1', 'l2', 'r1'):
        s = sub(s, r'\t%s_Available = \(switch_%s_GPIO_Port->IDR & switch_%s_Pin\)>0;\r?\n' % (pin, pin, pin),
                '\t%s_Available = 1;\n' % pin, 1, what='jack ' + pin)
    return s

# extern declarations removed from headers
HDR_EDITS = {
    'Inc/Soundengine/FxBus.h': ['extern INDTCMZ FxBus fxBus;'],
    'Inc/Soundengine/DSPAudio/HiHat.h': ['extern HiHatVoice hatVoice;'],
    'Inc/Soundengine/DSPAudio/modulationNode.h': ['extern ModulationNode velocityModulators[6];'],
    'Inc/Soundengine/DSPAudio/CymbalVoice.h': ['extern CymbalVoice cymbalVoice;'],
    'Inc/Soundengine/MIDI/MidiParser.h': ['extern uint8_t midiParser_originalCcValues[0xff];', 'extern uint8_t midi_MidiChannels[8];'],
    'Inc/Soundengine/DSPAudio/DrumVoice.h': ['extern DrumVoice voiceArray[NUM_DRUM_VOICES];'],
    'Inc/Soundengine/DSPAudio/mixer.h': ['extern float mixer_decimation_rate[7];', 'extern uint8_t mixer_audioRouting[6];'],
    'Inc/Soundengine/DSPAudio/Snare.h': ['extern SnareVoice snareVoice;'],
    'Inc/Soundengine/DSPAudio/FX/FxRamBuffer.h': ['extern INDTCMZ __fp16 FX_BUFFER[FX_BUFFER_SIZE+1];'],
    'Inc/Soundengine/MIDI/MidiVoiceControl.h': ['extern uint8_t voiceStatus[NUM_DRUM_VOICES];'],
    'Inc/Soundengine/MIDI/ParameterArray.h': ['extern Parameter parameterArray[END_OF_SOUND_PARAMETERS];'],
}
for rel, texts in HDR_EDITS.items():
    def mk(texts):
        def f(s):
            for t in texts: s = drop_line(s, t, 'hdr ' + t)
            return s
        return f
    EDITS[rel] = mk(texts)

# ---------- 4. ccHandler extraction (Src/Soundengine/MIDI/MidiParser.c -> lxr_param.c) --------
PARAM_HEAD = """/*
 * lxr_param.c - the parameter handler of the LXR firmware, extracted from MidiParser.c.
 *
 * Derived from Core/Src/Soundengine/MIDI/MidiParser.c (Copyright (C) 2012-2026 Erica Synths,
 * SPDX-License-Identifier: GPL-3.0-only; see LICENSE and NOTICE.md).  Modified for the LynnDrum
 * plugin: only the pieces the CC/NRPN parameter writes need are kept (constants, the pitch/detune
 * helpers, the NRPN forwarder and midiParser_ccHandler); the MIDI/UART/USB/MTC/routing parser is
 * omitted; the engine state lives in LxrEngine (see platform/lxr_state.h).  The handler body is
 * byte-identical to upstream.
 */
#include "Soundengine/MIDI/MidiParser.h"
#include "Soundengine/MIDI/MidiNoteNumbers.h"
#include "Soundengine/DSPAudio/DrumVoice.h"
#include "Soundengine/DSPAudio/Snare.h"
#include "Soundengine/DSPAudio/HiHat.h"
#include "Soundengine/DSPAudio/CymbalVoice.h"
#include "Soundengine/DSPAudio/mixer.h"
#include "Soundengine/DSPAudio/modulationNode.h"
#include "Soundengine/MIDI/valueShaper.h"
#include "Soundengine/FxBus.h"
#include "Soundengine/MIDI/MidiMessages.h"
#include "menu/menu.h"

"""

def make_param_c():
    lines = src('Src/Soundengine/MIDI/MidiParser.c').split('\n')
    def find(prefix, start=0):
        for i in range(start, len(lines)):
            if lines[i].startswith(prefix): return i
        sys.exit('not found: ' + prefix)
    a = find('#define SEMITONE_UP'); b = find('#define NUM_LFO')
    c0 = find('static inline float calcPitchModAmount'); c1 = find('}', c0)
    d0 = find('float midiParser_calcDetune') - 1           # includes the one-line comment above
    cc0 = find('void midiParser_ccHandler'); cc1 = find('void midiParser_checkMtc')
    while lines[cc1 - 1].strip().startswith('//') or lines[cc1 - 1].strip() == '': cc1 -= 1
    # sanity: the extracted ranges must not contain the parser-only state
    parts = lines[a:b] + [''] + lines[c0:c1 + 1] + [''] + lines[d0:cc1]
    text = '\n'.join(parts)
    for bad in ('parserState', 'midiParser_mtc', 'usb_', 'uart_sendMidi', 'seq_sync'):
        assert bad not in text, bad
    return PARAM_HEAD + text + '\n'

def make_text_ids():
    ids = sorted(set(re.findall(r'\bTEXT_[A-Z0-9_]+\b', src('Src/menu/Cc2Text.c'))))
    return '/* generated: UI text ids referenced by the mod-target table (values are irrelevant to the engine) */\n' \
           'enum { %s };\n' % ', '.join(ids)

# ---------- 5. write --------------------------------------------------------------------------
if os.path.exists(DST + '/src'): shutil.rmtree(DST + '/src')
if os.path.exists(DST + '/inc'): shutil.rmtree(DST + '/inc')
for rel in SOURCES:
    s = src(rel)
    if rel in EDITS: s = EDITS[rel](s)
    wr(os.path.join(DST, 'src', rel[len('Src/'):]), s)
for rel in HEADERS:
    s = src(rel)
    if rel in EDITS: s = EDITS[rel](s)
    wr(os.path.join(DST, 'inc', rel[len('Inc/'):]), s)
wr(os.path.join(DST, 'src/Soundengine/MIDI/lxr_param.c'), make_param_c())
wr(os.path.join(DST, 'platform/lxr_text_ids.h'), make_text_ids())
print('lxr_core regenerated:', len(SOURCES), 'sources,', len(HEADERS), 'headers')
