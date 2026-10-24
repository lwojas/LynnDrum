import React from 'react'
import { useParam, useStore } from '../store'
import { TRACKS } from '../model'
import { Fader } from './Fader'
import { audition } from '../audition'

const dbOf = (v: number) => (v <= 0.0005 ? '-inf' : (20 * Math.log10(v)).toFixed(1) + 'dB')

function Strip({ t }: { t: number }) {
  const { voice, setVoice, pattern, send } = useStore()
  const info = TRACKS[t]
  const [val, set, handle] = useParam('fader' + (t + 1))
  const sel = voice === t
  const muted = pattern.tracks[t].muted
  return (
    <div className={`flex flex-col items-stretch min-w-0 flex-1 rounded-lg border p-1.5 gap-1.5 bg-synth-surface/60 ${sel ? 'border-synth-amber shadow-glow-amber' : 'border-synth-border'}`}>
      <button onClick={() => { setVoice(t); audition(t) }}
        className={`rounded px-0 py-1 text-[10px] font-extrabold font-mono text-center ${sel ? 'bg-synth-amber text-black' : 'bg-synth-border text-slate-200'}`}>{info.tag}</button>
      <div className="text-center text-[9px] font-mono text-slate-400 truncate">{info.role}</div>
      <div className="flex-1 flex justify-center min-h-0"><Fader value={val} handle={handle} onChange={set} color={sel ? '#ff7728' : '#00e5ff'} /></div>
      <div className={`text-center text-[10px] font-mono ${sel ? 'text-synth-amber' : 'text-slate-400'}`}>{dbOf(val)}</div>
      <div className="flex gap-1 justify-center">
        <button title={`Audition ${info.name} (key ${t + 1})`} onPointerDown={() => audition(t)}
          className="w-7 h-5 rounded text-[10px] border bg-synth-panel text-synth-emerald border-synth-border hover:bg-synth-emerald hover:text-black">▶</button>
        <button title="Mute (stops this track's sequencer triggers)" onClick={() => send(['mute', t, muted ? 0 : 1])}
          className={`w-7 h-5 rounded text-[10px] font-mono border ${muted ? 'bg-synth-red text-black border-synth-red' : 'bg-synth-panel text-slate-300 border-synth-border'}`}>M</button>
      </div>
    </div>
  )
}

export function Mixer() {
  return (
    <section className="flex flex-col min-h-0 min-w-0 p-3 gap-2 border-r border-synth-border bg-synth-panel/60" style={{ flex: '0 0 clamp(330px, 29%, 420px)' }}>
      <div className="flex items-center justify-between border-b border-synth-border/70 pb-1.5">
        <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-synth-amber" /><span className="font-extrabold text-sm tracking-wider font-mono">VOICE MATRIX &amp; MIXER</span></div>
        <span className="text-[10px] font-mono text-slate-400">OUT: <span className="text-synth-cyan">STEREO (DAC1+2)</span></span>
      </div>
      <div className="flex gap-1.5 flex-1 min-h-0">{TRACKS.map(t => <Strip key={t.id} t={t.id} />)}</div>
      <div className="text-[10px] font-mono text-slate-500">Pan, drive and output routing: sound deck, top right.</div>
    </section>
  )
}
