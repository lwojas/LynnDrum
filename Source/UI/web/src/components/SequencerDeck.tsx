import React, { useEffect, useRef } from 'react'
import { useStore } from '../store'
import { getTelemetry, onTelemetryFrame, Telemetry } from '../telemetry'
import { PatternBar } from './PatternBar'
import { EuclidPanel, RollControl } from './EuclidRoll'
import { MOD_TARGETS, MOD_TARGET_PAR, SOUND_PARAMS } from '../params.generated'
import { formatValue, PARAM_BY_ID } from './controls'
import { FLAM_LABELS, NUM_STEPS, SHIFT_NONE, TRACKS, shiftOf } from '../model'

const noteName = (n: number) => ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'][n % 12] + (Math.floor(n / 12) - 1)

function VolBar({ vol, on, onChange }: { vol: number; on: boolean; onChange: (v: number) => void }) {
  const drag = useRef(false)
  const set = (e: React.PointerEvent, el: HTMLElement) => { const r = el.getBoundingClientRect(); onChange(Math.max(1, Math.min(127, Math.round(((e.clientX - r.left) / r.width) * 127)))) }
  return (
    <div className="h-2.5 w-full rounded-sm bg-black/50 relative cursor-ew-resize touch-none" title={`Volume ${vol}`}
      onPointerDown={(e) => { e.stopPropagation(); drag.current = true; (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); set(e, e.currentTarget as HTMLElement) }}
      onPointerMove={(e) => drag.current && set(e, e.currentTarget as HTMLElement)} onPointerUp={() => (drag.current = false)}
      onClick={(e) => e.stopPropagation()}>
      <div className={`h-full rounded-sm ${on ? 'bg-synth-amber' : 'bg-slate-600'}`} style={{ width: `${(vol / 127) * 100}%`, opacity: on ? 1 : 0.4 }} />
    </div>
  )
}

function Pad({ idx }: { idx: number }) {
  const { pattern, send, voice, selStep, setSelStep } = useStore()
  const tr = pattern.tracks[voice]
  const outside = idx >= tr.length
  const on = tr.on[idx] && !outside
  const sel = selStep === idx
  const flam = tr.flam[idx], shift = shiftOf(tr.shift[idx]), prob = tr.prob[idx]
  const tags: { t: string; c: string }[] = []
  if (on && flam) tags.push({ t: FLAM_LABELS[flam], c: 'bg-synth-violet/30 text-synth-violet' })
  if (on && shift) tags.push({ t: (shift > 0 ? '+' : '') + shift, c: 'bg-synth-cyan/20 text-synth-cyan' })
  if (on && prob < 100) tags.push({ t: prob + '%', c: 'bg-synth-emerald/20 text-synth-emerald' })
  if (on && (tr.lockPar1[idx] >= 0 || tr.lockPar2[idx] >= 0)) tags.push({ t: 'P-LCK', c: 'bg-synth-cyan/30 text-synth-cyan' })
  return (
    <div className={`relative flex flex-col justify-between rounded-md border-2 p-1 min-w-0 select-none transition-colors
        ${outside ? 'opacity-25 border-synth-border bg-synth-bg' : on ? 'border-synth-amber bg-synth-surface' : 'border-synth-border bg-synth-bg/80'}
        data-[playing=true]:ring-2 data-[playing=true]:ring-synth-cyan data-[playing=true]:shadow-glow-cyan ${sel && !outside ? 'outline outline-1 outline-slate-300' : ''}`}
      title="click: add / select / remove  ·  shift-click or right-click: select only"
      onContextMenu={(e) => { e.preventDefault(); if (!outside) setSelStep(idx) }}
      onClick={(e) => {
        if (outside) return
        if (e.shiftKey) { setSelStep(idx); return }                       // select only
        if (!on) { setSelStep(idx); send(['step', voice, idx, 1]) }       // empty step: turn on and select it
        else if (!sel) setSelStep(idx)                                    // active, not selected: select it first
        else send(['step', voice, idx, 0])                                // active and selected: turn off
      }}>
      <div className="flex items-center justify-between text-[9px] font-mono leading-none">
        <span className={on ? 'text-slate-200' : 'text-slate-500'}>{String(idx + 1).padStart(2, '0')}</span>
        <span className="text-slate-600">{sel ? "●" : ""}</span>
      </div>
      <div className={`flex-1 my-1 rounded flex flex-col items-center justify-center gap-0.5 min-h-[28px] ${on ? 'bg-synth-amber text-black shadow-glow-amber' : 'bg-black/40'}`}>
        {on && <span className="font-extrabold text-[11px] font-mono">TRIG</span>}
        <div className="flex gap-0.5 flex-wrap justify-center">{tags.map((g, i) => <span key={i} className={`px-1 rounded text-[8px] font-mono font-bold ${g.c}`}>{g.t}</span>)}</div>
      </div>
      <VolBar vol={tr.vol[idx]} on={on} onChange={(v) => { if (!outside) send(['stepVol', voice, idx, v]) }} />
    </div>
  )
}

const PAR_DEF = new Map(SOUND_PARAMS.map(d => [d.par, d]))
const VOICE_PREFIX = ['Drum 1', 'Drum 2', 'Drum 3', 'Snare', 'Cymbal', 'Hi-hat', 'Hi-hat']
// p-lockable destinations: every mod target that is a plain parameter (not another target selector); grouped by voice
const LOCKABLE = MOD_TARGETS.map((label, i) => ({ label, par: MOD_TARGET_PAR[i] })).filter(t => t.par !== 0 && PAR_DEF.get(t.par) && PAR_DEF.get(t.par)!.kind !== 'target')

function LockRow({ slot, voice, step }: { slot: 1 | 2; voice: number; step: number }) {
  const { pattern, send } = useStore()
  const tr = pattern.tracks[voice], on = tr.on[step]
  const par = slot === 1 ? tr.lockPar1[step] : tr.lockPar2[step]
  const val = slot === 1 ? tr.lockVal1[step] : tr.lockVal2[step]
  const def = par >= 0 ? PAR_DEF.get(par) : undefined
  const own = VOICE_PREFIX[voice]
  const groups = Array.from(new Set(LOCKABLE.map(t => t.label.split(':')[0])))
  groups.sort((a, b) => (a === own ? -1 : b === own ? 1 : 0))
  const setPar = (p: number) => { const d = p >= 0 ? PAR_DEF.get(p) : undefined; send(['stepLock', voice, step, slot, p, d ? Math.min(Math.max(d.def, d.min), d.max) : 0]) }
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-synth-cyan font-bold">LOCK {slot}</span>
      <select disabled={!on} value={par} onChange={(e) => setPar(parseInt(e.target.value, 10))}
        className="bg-synth-surface border border-synth-border rounded px-1 py-0.5 disabled:opacity-40 max-w-[190px]">
        <option value={-1}>none</option>
        {groups.map(g => <optgroup key={g} label={g}>{LOCKABLE.filter((t, i, a) => t.label.split(':')[0] === g && a.findIndex(u => u.par === t.par) === i).map(t => <option key={t.par} value={t.par}>{t.label.replace(/^[^:]*:\s*/, '')}</option>)}</optgroup>)}
      </select>
      {def && def.kind === 'int' && <input type="range" min={def.min} max={def.max} value={val} className="w-28 accent-synth-cyan" onChange={(e) => send(['stepLock', voice, step, slot, par, parseInt(e.target.value, 10)])} />}
      {def && def.kind === 'int' && <span className="w-16 text-synth-cyan font-mono">{formatValue(def, val)}</span>}
      {def && def.kind !== 'int' && (
        <select value={val} onChange={(e) => send(['stepLock', voice, step, slot, par, parseInt(e.target.value, 10)])} className="bg-synth-surface border border-synth-border rounded px-1 py-0.5 text-synth-cyan">
          {Array.from({ length: def.max - def.min + 1 }, (_, k) => def.min + k).map(v => <option key={v} value={v}>{formatValue(def, v)}</option>)}
        </select>)}
      {def && <span className="text-synth-cyan w-16">{formatValue(def, val)}</span>}
    </div>
  )
}

function Inspector() {
  const { pattern, send, voice, selStep } = useStore()
  const tr = pattern.tracks[voice], i = selStep
  const on = tr.on[i]
  const Row = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <label className="flex items-center gap-1.5"><span className="text-slate-400">{label}</span>{children}</label>)
  const num = (v: number, min: number, max: number, cmd: 'stepVol' | 'stepProb' | 'stepNote') => (
    <input type="number" min={min} max={max} value={v} disabled={!on}
      className="w-14 bg-synth-surface border border-synth-border rounded px-1 py-0.5 text-slate-100 disabled:opacity-40"
      onChange={(e) => send([cmd, voice, i, Math.max(min, Math.min(max, parseInt(e.target.value || String(min), 10)))])} />)
  return (
    <div className="flex flex-col gap-1 text-[10px] font-mono text-slate-300 border-t border-synth-border/60 pt-1.5">
      <div className="flex items-center gap-4 flex-wrap">
        <span className={`font-bold ${on ? 'text-synth-amber' : 'text-slate-500'}`}>STEP {String(i + 1).padStart(2, '0')}{on ? '' : ' (off)'}</span>
        <Row label="VOL">{num(tr.vol[i], 1, 127, 'stepVol')}</Row>
        <Row label="PROB %">{num(tr.prob[i], 1, 100, 'stepProb')}</Row>
        <Row label={`NOTE ${noteName(tr.note[i])}`}>{num(tr.note[i], 0, 127, 'stepNote')}</Row>
        <Row label="FLAM">
          <select disabled={!on} value={tr.flam[i]} onChange={(e) => send(['stepFlam', voice, i, parseInt(e.target.value, 10)])}
            className="bg-synth-surface border border-synth-border rounded px-1 py-0.5 disabled:opacity-40">{FLAM_LABELS.map((l, k) => <option key={k} value={k}>{l}</option>)}</select>
        </Row>
        <Row label="SHIFT">
          <select disabled={!on} value={tr.shift[i]} onChange={(e) => send(['stepShift', voice, i, parseInt(e.target.value, 10)])}
            className="bg-synth-surface border border-synth-border rounded px-1 py-0.5 disabled:opacity-40">
            {Array.from({ length: 15 }, (_, k) => <option key={k} value={k}>{k === SHIFT_NONE ? '0' : (shiftOf(k) > 0 ? '+' : '') + shiftOf(k)}</option>)}
          </select>
          <span className="text-slate-500">× 1/8 step</span>
        </Row>
        <span className="text-slate-500 ml-auto">click a step: add → select → remove · shift/right-click: select only</span>
      </div>
      <div className="flex items-center gap-6 flex-wrap">
        <LockRow slot={1} voice={voice} step={i} /><LockRow slot={2} voice={voice} step={i} />
        <span className="text-slate-600" title="A p-lock sets a parameter when this step triggers and keeps it until the track's next trigger restores it">p-lock: set on this trigger, restored on the track's next</span>
      </div>
    </div>
  )
}

export function SequencerDeck() {
  const { pattern, send, voice, bar, setBar, clipboard } = useStore()
  const tr = pattern.tracks[voice]
  // Playhead: no React re-render per frame. The pad under the playhead gets a data-playing attribute (styled by CSS variants),
  // set directly on the DOM node; the bar tab follows the playhead through the (rare) setBar.
  const grid = useRef<HTMLDivElement>(null)
  const live = useRef({ voice, bar, length: tr.length }); live.current = { voice, bar, length: tr.length }
  const lit = useRef<Element | null>(null)
  const place = useRef((t: Telemetry) => {})
  place.current = (t: Telemetry) => {
    const { voice: v, bar: b, length } = live.current
    const idx = t.running ? t.steps[v] : -1
    const local = idx - b * 16
    const el = idx >= 0 && idx < length && local >= 0 && local < 16 ? grid.current?.children[local] ?? null : null
    if (el !== lit.current) { lit.current?.removeAttribute('data-playing'); el?.setAttribute('data-playing', 'true'); lit.current = el }
    if (t.running && length > 16 && idx >= 0) { const nb = Math.floor(idx / 16); if (nb !== b) setBar(nb) }
  }
  useEffect(() => onTelemetryFrame(t => place.current(t)), [])
  useEffect(() => { lit.current = null; place.current(getTelemetry()) }, [voice, bar, tr.length, pattern])
  const bars = Math.max(1, Math.min(4, Math.ceil(tr.length / 16)))
  const random = () => { for (let s = 0; s < NUM_STEPS; s++) send(['step', voice, s, s < tr.length && Math.random() < 0.3 ? 1 : 0]) }
  const btn = 'px-2 py-0.5 rounded bg-synth-surface hover:bg-synth-border border border-synth-border text-slate-300 disabled:opacity-40'
  return (
    <footer className="shrink-0 bg-synth-panel border-t-2 border-synth-border p-3 flex flex-col gap-2" style={{ height: 'clamp(330px, 44%, 440px)' }}>
      <PatternBar />
      <div className="flex items-center justify-between gap-3 flex-wrap pb-1.5 border-b border-synth-border/70 text-[10px] font-mono">
        <div className="flex items-center gap-3">
          <span className="font-extrabold text-xs tracking-wider">STEP SEQUENCER</span>
          <span className="bg-synth-surface text-synth-amber px-1.5 py-0.5 rounded border border-synth-border">VOICE {voice + 1}: {TRACKS[voice].short}</span>
          <div className="flex bg-synth-surface p-0.5 rounded border border-synth-border">
            {[0, 1, 2, 3].map(b => (
              <button key={b} disabled={b >= bars} onClick={() => setBar(b)}
                className={`px-2.5 py-0.5 rounded font-bold ${bar === b ? 'bg-synth-amber text-black' : 'text-slate-400'} disabled:opacity-30`}>BAR {b + 1} [{b * 16 + 1}-{b * 16 + 16}]</button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button className={btn} onClick={() => send(['clearTrack', voice])}>CLEAR</button>
          <button className={btn} onClick={() => { clipboard.current = voice }}>COPY</button>
          <button className={btn} disabled={clipboard.current === null} onClick={() => clipboard.current !== null && send(['copyTrack', clipboard.current, voice])}>PASTE</button>
          <button className={btn} onClick={random}>RANDOM</button>
          <EuclidPanel />
        </div>
        <RollControl />
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1 text-slate-400">SWING
            <input type="range" min={0} max={127} value={pattern.shuffle} className="w-20 accent-synth-amber" onChange={(e) => send(['shuffle', parseInt(e.target.value, 10)])} />
            <span className="text-slate-200 w-8">{Math.round((pattern.shuffle / 127) * 100)}%</span></label>
          <label className="flex items-center gap-1 text-slate-400">LENGTH
            <select value={tr.length} onChange={(e) => { send(['trackLength', voice, parseInt(e.target.value, 10)]); setBar(0) }}
              className="bg-synth-surface border border-synth-border rounded px-1 py-0.5 text-synth-amber font-bold">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 24, 32, 48, 64].map(n => <option key={n} value={n}>{n}</option>)}
            </select></label>
        </div>
      </div>
      <div ref={grid} className="grid gap-1.5 flex-1 min-h-0" style={{ gridTemplateColumns: 'repeat(16, minmax(0, 1fr))' }}>
        {Array.from({ length: 16 }, (_, k) => <Pad key={bar * 16 + k} idx={bar * 16 + k} />)}
      </div>
      <Inspector />
    </footer>
  )
}
