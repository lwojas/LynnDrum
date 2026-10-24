import React, { useRef } from 'react'
import { useParam } from '../store'
import { commitSoundEdit } from '../audition'
import { MOD_TARGETS, ParamDef, SOUND_PARAMS } from '../params.generated'

export const PARAM_BY_ID = new Map<string, ParamDef>(SOUND_PARAMS.map(p => [p.id, p]))

/** value text for a raw (engine-domain) value */
export function formatValue(d: ParamDef, raw: number): string {
  if (d.kind === 'choice') return d.choices?.[raw] ?? String(raw)
  if (d.kind === 'target') return MOD_TARGETS[raw] ?? String(raw)
  if (d.kind === 'bool') return raw ? 'ON' : 'OFF'
  if (d.bipolar) return (raw - 63 > 0 ? '+' : '') + (raw - 63)
  return String(raw)
}

const R = 17, C = 22                       // knob geometry (viewBox 44)
const polar = (a: number, r = R) => [C + r * Math.cos(a), C + r * Math.sin(a)]
const arc = (a0: number, a1: number) => {
  const [x0, y0] = polar(a0), [x1, y1] = polar(a1)
  return `M ${x0} ${y0} A ${R} ${R} 0 ${Math.abs(a1 - a0) > Math.PI ? 1 : 0} ${a1 > a0 ? 1 : 0} ${x1} ${y1}`
}

export function Knob({ id, label, accent = '#ff7728', size = 40 }: { id: string; label?: string; accent?: string; size?: number }) {
  const d = PARAM_BY_ID.get(id)!
  const [n, setN, h] = useParam(id, 'slider')
  const drag = useRef<{ y: number; n: number } | null>(null)
  const raw = Math.round(d.min + n * (d.max - d.min))
  const a0 = Math.PI * 0.75, a1 = Math.PI * 2.25
  const at = (v: number) => a0 + (a1 - a0) * v
  const from = d.bipolar ? at(0.5) : a0
  const to = at(n)
  const def = (d.def - d.min) / (d.max - d.min)
  return (
    <div className="flex flex-col items-center gap-0.5 select-none" style={{ width: Math.max(size + 14, 50) }} title={`${d.name}: ${formatValue(d, raw)}  (double-click: default, shift: fine)`}>
      <svg width={size} height={size} viewBox="0 0 44 44" className="touch-none cursor-ns-resize"
        onPointerDown={(e) => { (e.target as Element).setPointerCapture?.(e.pointerId); drag.current = { y: e.clientY, n }; h.begin() }}
        onPointerMove={(e) => { const s = drag.current; if (!s) return; const k = e.shiftKey ? 1200 : 180; setN(Math.min(1, Math.max(0, s.n + (s.y - e.clientY) / k))) }}
        onPointerUp={() => { if (drag.current) commitSoundEdit(); drag.current = null; h.end() }}
        onDoubleClick={() => { h.begin(); setN(def); h.end(); commitSoundEdit() }}>
        <path d={arc(a0, a1)} stroke="#242a3a" strokeWidth={3.5} fill="none" strokeLinecap="round" />
        {Math.abs(to - from) > 0.01 && <path d={arc(Math.min(from, to), Math.max(from, to))} stroke={accent} strokeWidth={3.5} fill="none" strokeLinecap="round" />}
        <circle cx={C} cy={C} r={13} fill="#171b26" stroke="#0b0d12" strokeWidth={1} />
        <line x1={C} y1={C} x2={polar(to, 11)[0]} y2={polar(to, 11)[1]} stroke="#e2e8f0" strokeWidth={2} strokeLinecap="round" />
      </svg>
      <div className="text-[9px] font-mono text-slate-400 leading-none truncate max-w-full">{label ?? d.name}</div>
      <div className="text-[10px] font-mono leading-none" style={{ color: accent }}>{formatValue(d, raw)}</div>
    </div>
  )
}

export function Select({ id, label, wide }: { id: string; label?: string; wide?: boolean }) {
  const d = PARAM_BY_ID.get(id)!
  const [v, set] = useParam(id, 'combo')
  const items = d.kind === 'target' ? MOD_TARGETS : d.choices ?? []
  return (
    <label className={`flex flex-col gap-0.5 min-w-0 ${wide ? 'flex-1' : ''}`}>
      <span className="text-[9px] font-mono text-slate-400 leading-none truncate">{label ?? d.name}</span>
      <select value={v} onChange={(e) => { set(parseInt(e.target.value, 10)); setTimeout(commitSoundEdit, 60) }}
        className="bg-synth-surface border border-synth-border rounded px-1 py-0.5 text-[10px] font-mono text-synth-cyan min-w-0 w-full">
        {items.map((t, i) => <option key={i} value={i}>{t}</option>)}
      </select>
    </label>
  )
}

export function Switch({ id, label }: { id: string; label?: string }) {
  const d = PARAM_BY_ID.get(id)!
  const [v, set] = useParam(id, 'toggle')
  return (
    <button onClick={() => { set(v ? 0 : 1); setTimeout(commitSoundEdit, 60) }} title={d.name}
      className={`px-2 py-1 rounded border text-[9px] font-mono font-bold ${v ? 'bg-synth-cyan/20 border-synth-cyan text-synth-cyan' : 'border-synth-border text-slate-400'}`}>{label ?? d.name}</button>
  )
}

/** generic control for any parameter id */
export function Ctl({ id, label, accent }: { id: string; label?: string; accent?: string }) {
  const d = PARAM_BY_ID.get(id)
  if (!d) return null
  if (d.kind === 'int') return <Knob id={id} label={label} accent={accent} />
  if (d.kind === 'bool') return <Switch id={id} label={label} />
  return <Select id={id} label={label} />
}
