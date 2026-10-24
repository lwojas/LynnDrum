/* Dumps the engine's own parameter->physical-value mappings (computed by the derived engine code, not re-derived) as JSON.
 * Used as the golden reference for the UI's readout formulas (Source/UI/web/src/readout.test.ts).
 * build: see Tools/params/readout_tables.sh */
#include <stdio.h>
#include "Soundengine/DSPAudio/SlopeEg2.h"
#include "Soundengine/DSPAudio/Decay.h"
#include "Soundengine/DSPAudio/ResonantFilter.h"
#include "Soundengine/DSPAudio/lfo.h"
#include "Soundengine/MIDI/MidiParser.h"
#include "Soundengine/MIDI/valueShaper.h"

static void row(const char* name, double (*f)(int), int last)
{
    printf("  \"%s\": [", name);
    for (int d = 0; d < 128; d++) printf("%s%.9g", d ? "," : "", f(d));
    printf("]%s\n", last ? "" : ",");
}
static double t_attack(int d)  { SlopeEg2 e; slopeEg2_setAttack(&e, (uint8_t)d, 0); return e.attack; }
static double t_decay(int d)   { return slopeEg2_calcDecay((uint8_t)d); }
static double t_pitch(int d)   { DecayEg e; DecayEg_setDecay(&e, (uint8_t)d); return e.decay; }
static double t_slope(int d)   { SlopeEg2 e; slopeEg2_setSlope(&e, (uint8_t)d); return e.slope; }
static double t_cutoff(int d)  { ResonantFilter f; SVF_directSetFilterValue(&f, valueShaperF2F(d / 127.f, FILTER_SHAPER)); return f.f * REAL_FS; }
static double t_q(int d)       { ResonantFilter f; SVF_setReso(&f, d / 127.f); return f.q; }
static double t_lfo(int d)     { Lfo l; l.sync = 0; lfo_setFreq(&l, d / 127.f); return l.freq; }
static double t_decim(int d)   { return valueShaperF2F(d / 127.f, -0.7f) * REAL_FS; }
static double t_detune(int d)  { return midiParser_calcDetune((uint8_t)d); }
static double t_click(int d)   { return 1.f + ((d / 33.9f) - 0.75f); }

int main(void)
{
    printf("{\n  \"blockMs\": %.9g,\n", 1000.0 * OUTPUT_DMA_SIZE / REAL_FS);
    row("attack", t_attack, 0); row("decay", t_decay, 0); row("pitchDecay", t_pitch, 0); row("slope", t_slope, 0);
    row("cutoffHz", t_cutoff, 0); row("filterQ", t_q, 0); row("lfoHz", t_lfo, 0); row("decimHz", t_decim, 0);
    row("detune", t_detune, 0); row("clickPitch", t_click, 1);
    printf("}\n");
    return 0;
}
