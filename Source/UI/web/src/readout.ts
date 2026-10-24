// Parameter -> physical-unit text. Time/frequency curves come from readout.golden.json, which is dumped from the
// derived engine itself (Tools/params/readout_tables.sh), so the UI cannot drift from the DSP. Closed forms are used
// only where they are trivial (note->Hz, dB, pan, pitch-mod multiplier).
import T from './readout.golden.json'

const NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

export const noteName = (n: number) => NOTES[((n % 12) + 12) % 12] + (Math.floor(n / 12) - 1)
export const mtof = (n: number) => 440 * Math.pow(2, (n - 69) / 12)

export function fmtHz(hz: number): string {
  if (hz < 10) return hz.toFixed(2) + ' Hz'
  if (hz < 100) return hz.toFixed(1) + ' Hz'
  if (hz < 1000) return Math.round(hz) + ' Hz'
  return (hz / 1000).toFixed(hz < 10000 ? 2 : 1) + ' kHz'
}
export function fmtMs(ms: number): string {
  if (!isFinite(ms)) return '∞'
  if (ms < 10) return ms.toFixed(1) + ' ms'
  if (ms < 1000) return Math.round(ms) + ' ms'
  return (ms / 1000).toFixed(ms < 10000 ? 2 : 1) + ' s'
}
const signed = (v: number, s: string) => (v > 0 ? '+' : '') + s

/** time of an envelope whose table holds the per-block increment (0 = never) */
const envMs = (tab: number[], d: number) => (tab[d] > 0 ? T.blockMs / tab[d] : Infinity)

type Fmt = (d: number) => string
const fmtNote: Fmt = d => `${noteName(d)} ${fmtHz(mtof(d))}`
const fmtPct: Fmt = (d) => Math.round((d / 127) * 100) + '%'

/** formatter keyed by parameter id (family prefix); undefined = plain value */
export function readoutFor(id: string): Fmt | undefined {
  if (/^(coarse|mod_osc_f\d|fm_freq)/.test(id)) return fmtNote
  if (/^fine/.test(id)) return d => { const c = Math.round(1200 * Math.log2(T.detune[d])) || 0; return signed(c, String(c)) + ' ct' }
  if (/^veloa/.test(id)) return d => fmtMs(envMs(T.attack, d))
  if (/^velod/.test(id)) return d => fmtMs(envMs(T.decay, d))
  if (/^mod_eg/.test(id)) return d => fmtMs(envMs(T.pitchDecay, d))
  if (/^modamnt/.test(id)) return d => '×' + (1 + Math.pow(d / 127, 2) * 32).toFixed(1)
  if (/^filter_freq/.test(id)) return d => fmtHz(T.cutoffHz[d])
  if (/^reso_/.test(id)) return fmtPct
  if (/^freq_lfo/.test(id)) return d => fmtHz(T.lfoHz[d])
  if (/^voice_decimation/.test(id)) return d => fmtHz(T.decimHz[d])
  if (/^trans\d_freq/.test(id)) return d => '×' + T.clickPitch[d].toFixed(2)
  if (/^vol\d/.test(id)) return d => d === 0 ? '-∞ dB' : (20 * Math.log10(d / 127)).toFixed(1) + ' dB'
  if (/^pan\d/.test(id)) return d => { const p = Math.round(((d - 63.5) / 63.5) * 100); return p === 0 ? 'C' : (p < 0 ? 'L' : 'R') + Math.abs(p) }
  if (/^(vol|pitch)_slope/.test(id)) return d => { const p = Math.round(((d - 63.5) / 63.5) * 100); return Math.abs(p) <= 1 ? 'lin' : signed(p, String(p)) + '%' }
  if (/^repeat/.test(id)) return d => d === 0 ? 'off' : d + '×'
  if (/^offset_lfo/.test(id)) return d => Math.round((d / 127) * 360) + '°'
  if (/^fx_dry_wet/.test(id)) return d => d + '%'
  if (/^(mod_osc_gain|fmamnt|amount_lfo|drive|snare_dist|cymbal_dist|hat_dist|filter_drive|velo_mod|trans\d_vol|pwm|noise_freq|mix|fx_p\d)/.test(id)) return fmtPct
  return undefined
}
