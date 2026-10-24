import React, { useEffect, useRef, useState } from 'react'
import { bridge } from '../bridge'
import { useStore } from '../store'
import { TRACKS } from '../model'

// roll rate (engine setting 0..5) -> label and retrigger interval in 16th steps
const RATES = [{ r: 5, label: '1/16' }, { r: 4, label: '1/8' }, { r: 3, label: '1/4' }, { r: 2, label: '1/2' }, { r: 1, label: '1 bar' }, { r: 0, label: 'one-shot' }]

export function RollControl() {
  const { voice, sendG } = useStore()
  const [rate, setRate] = useState(5)
  const [held, setHeld] = useState(false)
  const voiceRef = useRef(voice); voiceRef.current = voice
  const heldVoice = useRef<number | null>(null)
  useEffect(() => { sendG(['rollRate', rate]) }, [rate])
  const start = () => { heldVoice.current = voiceRef.current; setHeld(true); sendG(['roll', voiceRef.current, 1]) }
  const stop = () => { if (heldVoice.current !== null) { sendG(['roll', heldVoice.current, 0]); heldVoice.current = null; setHeld(false) } }
  useEffect(() => { window.addEventListener('pointerup', stop); window.addEventListener('blur', stop); return () => { window.removeEventListener('pointerup', stop); window.removeEventListener('blur', stop) } }, [])
  return (
    <div className="flex items-center gap-1">
      <button onPointerDown={start} title={`Hold: retrigger ${TRACKS[voice].short} at the roll rate (while the sequencer runs; one-shot or stopped: one hit per press)`}
        className={`px-3 py-0.5 rounded border font-bold ${held ? 'bg-synth-violet text-black border-synth-violet' : 'bg-synth-violet/15 border-synth-violet text-synth-violet'}`}>ROLL</button>
      <select value={rate} onChange={(e) => setRate(parseInt(e.target.value, 10))} className="bg-synth-surface border border-synth-border rounded px-1 py-0.5 text-synth-violet">
        {RATES.map(x => <option key={x.r} value={x.r}>{x.label}</option>)}
      </select>
    </div>
  )
}

export function EuclidPanel() {
  const { voice, viewPat, send, pattern } = useStore()
  const [open, setOpen] = useState(false)
  const cur = pattern.tracks[voice]
  const [len, setLen] = useState(16), [steps, setSteps] = useState(5), [rot, setRot] = useState(0)
  const [bits, setBits] = useState<number[]>(Array(64).fill(0))
  useEffect(() => { if (!open) return; const l = Math.max(1, len), s = Math.min(Math.max(1, steps), l), r = Math.min(rot, l - 1); bridge.euclid(l, s, r).then(setBits) }, [open, len, steps, rot])
  useEffect(() => { if (open) { setLen(cur.length); setSteps(Math.min(Math.max(1, cur.on.slice(0, cur.length).filter(Boolean).length || 4), cur.length)) } }, [open, voice])
  const btn = 'px-2 py-0.5 rounded bg-synth-surface hover:bg-synth-border border border-synth-border text-slate-300'
  const num = (label: string, v: number, set: (n: number) => void, lo: number, hi: number) => (
    <label className="flex items-center gap-1 text-slate-400">{label}
      <input type="number" min={lo} max={hi} value={v} onChange={(e) => set(Math.min(hi, Math.max(lo, parseInt(e.target.value || String(lo), 10))))} className="w-14 bg-synth-surface border border-synth-border rounded px-1 py-0.5 text-slate-100" /></label>)
  const l = Math.max(1, len)
  return (
    <div className="relative">
      <button className={btn + (open ? ' border-synth-emerald text-synth-emerald' : '')} onClick={() => setOpen(!open)}>EUCLID</button>
      {open && (
        <div className="absolute z-50 bottom-8 left-0 bg-synth-panel border border-synth-activeBorder rounded-lg p-3 shadow-xl w-[420px] max-w-[90vw] flex flex-col gap-2 text-[10px] font-mono">
          <div className="text-slate-200 font-bold">EUCLIDEAN RHYTHM → {TRACKS[voice].short}, pattern {viewPat + 1}</div>
          <div className="flex gap-3 flex-wrap">{num('LENGTH', len, setLen, 1, 64)}{num('STEPS', steps, setSteps, 1, l)}{num('ROTATE', rot, setRot, 0, l - 1)}</div>
          <div className="flex flex-wrap gap-0.5">{bits.slice(0, l).map((b, i) => <span key={i} className={`w-3.5 h-3.5 rounded-sm ${b ? 'bg-synth-emerald' : 'bg-synth-border'} ${i % 4 === 0 ? 'ml-1' : ''}`} />)}</div>
          <div className="flex justify-end gap-2">
            <span className="text-slate-500 mr-auto">replaces this track's steps and sets its length; volumes of kept steps stay</span>
            <button className={btn} onClick={() => setOpen(false)}>CLOSE</button>
            <button className={btn + ' bg-synth-emerald text-black border-synth-emerald font-bold'} onClick={() => send(['euclid', voice, l, Math.min(Math.max(1, steps), l), Math.min(rot, l - 1)])}>APPLY</button>
          </div>
        </div>)}
    </div>
  )
}
