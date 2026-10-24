import React from 'react'
import { useParam, useStore } from '../store'
import { PresetBar } from './PresetBar'

function Meter() {
  const { playhead } = useStore()
  const [hold, setHold] = React.useState({ l: 0, r: 0 })
  React.useEffect(() => { setHold(h => ({ l: Math.max(playhead.peakL ?? 0, h.l * 0.85), r: Math.max(playhead.peakR ?? 0, h.r * 0.85) })) }, [playhead])
  const bar = (v: number) => Math.max(0, Math.min(1, (20 * Math.log10(Math.max(v, 1e-4)) + 60) / 66))      // -60 dB .. +6 dB
  const db = (v: number) => (v < 1e-4 ? '-inf' : (20 * Math.log10(v)).toFixed(1))
  const col = (v: number) => (v > 1 ? '#ff3b5c' : v > 0.7 ? '#ff7728' : '#2fe278')
  return (
    <div className="flex flex-col gap-0.5 w-28" title="Output peak">
      {[hold.l, hold.r].map((v, i) => <div key={i} className="h-1.5 rounded-sm bg-black/60 overflow-hidden"><div className="h-full" style={{ width: `${bar(v) * 100}%`, background: col(v) }} /></div>)}
      <span className="text-[9px] font-mono text-slate-400 text-right leading-none">{db(Math.max(hold.l, hold.r))} dB</span>
    </div>)
}

export function Header() {
  const { playhead } = useStore()
  const [sync, setSync] = useParam('seqSync', 'combo')
  const [run, setRun] = useParam('seqRun', 'toggle')
  const [tempo, setTempo, tempoH] = useParam('tempo')
  const [master, setMaster, masterH] = useParam('master')
  const free = sync === 1
  const freeBpm = 30 + tempo * 270
  const bpm = free ? freeBpm : playhead.bpm
  return (
    <header className="h-14 shrink-0 flex items-center gap-4 px-4 border-b-2 border-synth-border bg-synth-panel">
      <div className="flex items-baseline gap-2">
        <span className="font-extrabold text-xl tracking-widest">LYNN<span className="text-synth-amber">DRUM</span></span>
        <span className="text-[10px] font-mono text-slate-400 hidden md:inline">DIGITAL DRUM SYNTH</span>
      </div>
      <div className="flex-1" />
      <PresetBar />
      <div className="flex-1" />
      <div className="flex items-center gap-1 text-[10px] font-mono">
        <span className="text-slate-400 mr-1">SYNC</span>
        <div className="flex bg-synth-surface p-0.5 rounded border border-synth-border">
          {['HOST', 'FREE'].map((l, i) => (
            <button key={l} onClick={() => setSync(i)} className={`px-2 py-0.5 rounded font-bold ${sync === i ? 'bg-synth-amber text-black' : 'text-slate-400'}`}>{l}</button>
          ))}
        </div>
        <button disabled={!free} onClick={() => setRun(run ? 0 : 1)}
          className={`ml-1 px-3 py-1 rounded font-bold border ${!free ? 'opacity-40 border-synth-border text-slate-400' : run ? 'bg-synth-emerald text-black border-synth-emerald' : 'border-synth-border text-slate-200'}`}>
          {free ? (run ? '■ STOP' : '▶ RUN') : playhead.running ? '▶ HOST' : '■ HOST'}
        </button>
      </div>
      <div className="flex flex-col items-end leading-none">
        <span className="text-[9px] font-mono text-slate-400">BPM</span>
        <span className="text-xl font-mono font-bold text-synth-amber w-24 text-right">{bpm.toFixed(2)}</span>
      </div>
      {free && (
        <input type="range" min={0} max={1} step={0.0005} value={tempo} className="w-28 accent-synth-amber"
          onPointerDown={() => tempoH.begin()} onPointerUp={() => tempoH.end()} onChange={e => setTempo(parseFloat(e.target.value))} />
      )}
      <Meter />
      <div className="flex items-center gap-2">
        <span className="text-[9px] font-mono text-slate-400">MASTER</span>
        <div className="h-9 flex"><MasterBar value={master} onChange={setMaster} handle={masterH} /></div>
        <span className="text-[10px] font-mono text-slate-300 w-14">{master <= 0.001 ? '-inf' : (20 * Math.log10(Math.pow(master, 1 / 0.6) * 2)).toFixed(1) + 'dB'}</span>
      </div>
    </header>
  )
}

function MasterBar({ value, onChange, handle }: { value: number; onChange: (v: number) => void; handle: any }) {
  return (
    <input type="range" min={0} max={1} step={0.001} value={value} className="w-28 accent-synth-cyan self-center"
      onPointerDown={() => handle.begin()} onPointerUp={() => handle.end()} onChange={e => onChange(parseFloat(e.target.value))} />
  )
}
