import React from 'react'
import { useStore } from '../store'
import { TRACKS } from '../model'
import { SOUND_PARAMS, ParamDef } from '../params.generated'
import { Ctl, Knob, Select, Switch } from './controls'
import { audition, isAuto, onAutoChange, setAuto } from '../audition'

const VOICE_GROUP = ['Drum 1', 'Drum 2', 'Drum 3', 'Snare', 'Cymbal', 'Hi-hat', 'Hi-hat']

type Module = 'osc' | 'filter' | 'env' | 'lfo' | 'out'
const MODULES: { key: Module; title: string; accent: string }[] = [
  { key: 'osc', title: '1. OSC & FM CORE', accent: '#ff7728' },
  { key: 'filter', title: '2. FILTER (SVF)', accent: '#00e5ff' },
  { key: 'env', title: '3. ENVELOPES', accent: '#2fe278' },
  { key: 'lfo', title: '4. LFO & VELOCITY', accent: '#a855f7' },
]
function moduleOf(d: ParamDef): Module {
  const n = d.name
  if (/^(Filter|Resonance)/.test(n)) return 'filter'
  if (/^(Attack|Decay|Amp Slope|Repeat|Pitch)/.test(n)) return 'env'
  if (/^(LFO|Velocity)/.test(n)) return 'lfo'
  if (/^(Volume|Pan|Drive|Sample Rate|Audio Out)/.test(n)) return 'out'
  return 'osc'
}

// the open hat shares the hat voice but has its own decay; the closed hat does not use the "open" decay
const hidden = (voice: number, d: ParamDef) => (voice === 5 && d.name === 'Decay (open)') || (voice === 6 && d.name === 'Decay (closed)')

function Panel({ title, accent, children }: { title: string; accent: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-synth-border bg-synth-panel/70 p-3 flex flex-col min-h-0 min-w-0 overflow-auto">
      <div className="font-extrabold font-mono text-xs tracking-wider border-b border-synth-border/70 pb-1.5 mb-2" style={{ color: accent }}>{title}</div>
      {children}
    </div>
  )
}

function Group({ defs, accent }: { defs: ParamDef[]; accent: string }) {
  const knobs = defs.filter(d => d.kind === 'int'), others = defs.filter(d => d.kind !== 'int')
  return (
    <div className="flex flex-col gap-2">
      {others.length > 0 && <div className="grid gap-x-2 gap-y-1.5" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(88px, 1fr))' }}>
        {others.map(d => d.kind === 'bool' ? <Switch key={d.id} id={d.id} /> : <Select key={d.id} id={d.id} />)}</div>}
      <div className="flex flex-wrap gap-x-1 gap-y-2">{knobs.map(d => <Knob key={d.id} id={d.id} accent={accent} />)}</div>
    </div>
  )
}

function FxStrip() {
  const fx = (n: string) => SOUND_PARAMS.find(p => p.group === 'FX' && p.name === n)!
  const Sel = ({ n, label, w }: { n: string; label: string; w: number }) => <div style={{ width: w }}><Select id={fx(n).id} label={label} /></div>
  return (
    <div className="shrink-0 rounded-xl border border-synth-border bg-synth-panel/70 px-3 py-1 flex items-end gap-2 flex-wrap" title="Only voices routed to the FX bus are processed; what P1-P4 mean depends on the effect type">
      <span className="font-extrabold font-mono text-[11px] tracking-wider text-slate-300 self-center">FX BUS</span>
      <Sel n="FX Type" label="TYPE" w={84} /><Sel n="FX Routing" label="OUTPUT" w={80} />
      <Knob id={fx('FX Dry/Wet').id} label="DRY/WET" accent="#00e5ff" size={32} />
      <Sel n="FX Distortion" label="DIST" w={72} /><Sel n="FX Ratio" label="RATIO" w={56} /><Sel n="FX Wave" label="WAVE" w={72} /><Sel n="FX Delay Type" label="DELAY" w={76} />
      {[1, 2, 3, 4].map(i => <Knob key={i} id={fx('FX P' + i).id} label={'P' + i} accent="#00e5ff" size={32} />)}
    </div>
  )
}

function AuditionBar({ voice }: { voice: number }) {
  const [auto, setA] = React.useState(isAuto())
  React.useEffect(() => onAutoChange(() => setA(isAuto())), [])
  return (
    <div className="flex items-center gap-1.5">
      <button onPointerDown={() => audition(voice)} className="px-4 py-2 rounded-lg bg-synth-emerald text-black font-extrabold font-mono text-xs tracking-wider shadow active:brightness-90" title="Play the selected voice (or press 1-7)">▶ AUDITION</button>
      <button onClick={() => setAuto(!auto)} className={`px-2 py-2 rounded-lg border text-[10px] font-mono font-bold ${auto ? 'bg-synth-cyan/20 border-synth-cyan text-synth-cyan' : 'border-synth-border text-slate-400'}`} title="Re-trigger the voice whenever you release a sound control">AUTO</button>
    </div>
  )
}

export function SoundDeck() {
  const { voice } = useStore()
  const t = TRACKS[voice]
  const defs = SOUND_PARAMS.filter(d => d.group === VOICE_GROUP[voice] && !hidden(voice, d))
  const by = (m: Module) => defs.filter(d => moduleOf(d) === m)
  return (
    <section className="flex-1 min-w-0 min-h-0 p-3 flex flex-col gap-3">
      <div className="flex items-center gap-4 flex-wrap shrink-0">
        <div className="rounded-lg border-2 border-synth-amber bg-synth-amber/10 px-4 py-2 font-extrabold font-mono text-synth-amber tracking-wider text-sm">
          ● VOICE {voice + 1}: {t.name} ({t.role})
        </div>
        <span className="font-mono text-xs text-slate-400">ALGORITHM: {t.algo}</span>
        <AuditionBar voice={voice} />
        <div className="flex-1" />
        <div className="flex gap-3 items-end">
          {by('out').map(d => <Ctl key={d.id} id={d.id} accent="#ff7728" />)}
        </div>
      </div>
      <div className="grid gap-3 flex-1 min-h-0" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gridAutoRows: 'minmax(0, 1fr)' }}>
        {MODULES.map(m => <Panel key={m.key} title={m.title} accent={m.accent}><Group defs={by(m.key)} accent={m.accent} /></Panel>)}
      </div>
      <FxStrip />
    </section>
  )
}
