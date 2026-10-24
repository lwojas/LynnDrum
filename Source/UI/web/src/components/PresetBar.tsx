import React, { useEffect, useState } from 'react'
import { bridge, PresetInfo, PresetState } from '../bridge'

const LEVELS: Record<number, string> = { 1: 'IMMEDIATE', 2: 'PRODUCTION', 3: 'LESSON' }
const LEVEL_COLOR: Record<number, string> = { 1: 'text-synth-emerald border-synth-emerald/60', 2: 'text-synth-cyan border-synth-cyan/60', 3: 'text-synth-amber border-synth-amber/60' }
const category = (i: PresetInfo) => i.meta?.category ?? 'Starter'

/** the library presets' documentation: what the preset is, and above all what it demonstrates */
function PresetInfoPanel({ item, onClose }: { item: PresetInfo; onClose: () => void }) {
  const m = item.meta!
  const row = (k: string, v?: string | number) => v ? <div className="grid grid-cols-[84px_1fr] gap-2"><span className="text-slate-500">{k}</span><span className="text-slate-200">{v}</span></div> : null
  return (
    <div className="absolute top-9 left-0 z-50 w-[460px] max-w-[92vw] max-h-[70vh] overflow-y-auto bg-synth-panel border border-synth-activeBorder rounded-lg p-3 shadow-xl flex flex-col gap-2 text-[10px] font-mono">
      <div className="flex items-center gap-2">
        <span className="text-xs font-bold text-synth-cyan">{item.name}</span>
        {m.level && <span className={`border rounded px-1 ${LEVEL_COLOR[m.level]}`}>{LEVELS[m.level]}</span>}
        <span className="text-slate-400">{m.category}</span>
        <button className="ml-auto text-slate-400 hover:text-white text-xs" onClick={onClose}>✕</button>
      </div>
      {m.character && <div className="text-slate-400 italic">{m.character}</div>}
      {m.demonstrates && <div className="border-l-2 border-synth-amber pl-2"><div className="text-synth-amber font-bold">WHAT THIS DEMONSTRATES</div><div className="text-slate-100 leading-snug">{m.demonstrates}</div></div>}
      {row('TECHNIQUE', m.technique)}
      {m.secondary?.length ? row('ALSO', m.secondary.join(' · ')) : null}
      {row('VOICES', m.voices)}
      {row('KEY', m.key)}
      {row('TEMPO', m.bpm ? `${m.bpm} bpm (the plugin follows the host tempo)` : undefined)}
      {row('SWING', m.swing)}
      {row('LENGTH', m.length)}
      {m.patterns?.length ? (
        <div><div className="text-slate-500 mb-0.5">PATTERNS (the song button plays them in order)</div>
          {m.patterns.map((t, i) => <div key={i} className="text-slate-200"><span className="text-synth-amber">{i + 1}</span> {t.replace(/^[A-H]: /, '')}</div>)}</div>) : null}
    </div>
  )
}

export function PresetBar() {
  const [items, setItems] = useState<PresetInfo[]>([])
  const [cur, setCur] = useState<PresetState>({ current: '', factory: true, dirty: false })
  const [dialog, setDialog] = useState<null | { name: string }>(null)
  const [info, setInfo] = useState(false)
  const refresh = () => bridge.presets().then(p => { setItems(p.items ?? []); setCur({ current: p.current, factory: p.factory, dirty: p.dirty }) })
  useEffect(() => { refresh(); return bridge.onPreset(p => setCur(c => ({ ...c, ...p }))) }, [])

  const index = items.findIndex(i => i.name === cur.current && i.factory === cur.factory)
  const step = (d: number) => { if (!items.length) return; const n = items[(Math.max(index, 0) + d + items.length) % items.length]; bridge.loadPreset(n.name, n.factory) }
  const commit = async (name: string) => { if (name.trim() && await bridge.savePreset(name.trim())) { await refresh(); setDialog(null) } }
  const isUser = !cur.factory
  const curItem = index >= 0 ? items[index] : undefined
  const cats = Array.from(new Set(items.filter(i => i.factory).map(category)))
  const btn = 'px-2 py-1 rounded border border-synth-border bg-synth-surface text-slate-300 hover:bg-synth-border text-[10px] font-mono'

  return (
    <div className="flex items-center gap-1.5 relative">
      <button className={btn} title="Previous preset" onClick={() => step(-1)}>‹</button>
      <select value={index >= 0 ? `${cur.factory ? 'f' : 'u'}:${cur.current}` : ''} className="bg-synth-surface border border-synth-border rounded px-2 py-1 text-xs font-mono text-synth-cyan max-w-[210px]"
        onChange={(e) => { const [k, ...n] = e.target.value.split(':'); bridge.loadPreset(n.join(':'), k === 'f') }}>
        {cats.map(c => <optgroup key={c} label={c}>{items.filter(i => i.factory && category(i) === c).map(i => <option key={'f' + i.name} value={`f:${i.name}`}>{i.name}</option>)}</optgroup>)}
        {items.some(i => !i.factory) && <optgroup label="User">{items.filter(i => !i.factory).map(i => <option key={'u' + i.name} value={`u:${i.name}`}>{i.name}</option>)}</optgroup>}
      </select>
      <button className={btn} title="Next preset" onClick={() => step(1)}>›</button>
      {curItem?.meta && <button className={btn + (info ? ' bg-synth-border' : '')} title="What this preset is and what it demonstrates" onClick={() => setInfo(v => !v)}>i</button>}
      {cur.dirty && <span className="text-[10px] font-mono text-synth-amber border border-synth-amber/60 rounded px-1">*MOD</span>}
      <button className={btn} title={isUser ? 'Overwrite this user preset' : 'Save as a new user preset'} onClick={() => (isUser ? commit(cur.current) : setDialog({ name: '' }))}>SAVE</button>
      <button className={btn} title="Save a copy under a new name" onClick={() => setDialog({ name: isUser ? cur.current + ' 2' : '' })}>SAVE AS</button>
      {isUser && <button className={btn + ' text-synth-red'} title="Delete this user preset" onClick={async () => { await bridge.deletePreset(cur.current); await refresh(); step(0) }}>DEL</button>}
      {info && curItem?.meta && <PresetInfoPanel item={curItem} onClose={() => setInfo(false)} />}
      {dialog && (
        <div className="absolute top-9 left-0 z-50 bg-synth-panel border border-synth-activeBorder rounded-lg p-3 shadow-xl flex flex-col gap-2 w-64">
          <span className="text-[10px] font-mono text-slate-300">PRESET NAME</span>
          <input autoFocus value={dialog.name} onChange={(e) => setDialog({ name: e.target.value })} maxLength={64}
            onKeyDown={(e) => { if (e.key === 'Enter') commit(dialog.name); if (e.key === 'Escape') setDialog(null) }}
            className="bg-synth-surface border border-synth-border rounded px-2 py-1 text-xs font-mono text-slate-100" />
          <div className="flex gap-2 justify-end"><button className={btn} onClick={() => setDialog(null)}>CANCEL</button>
            <button className={btn + ' bg-synth-amber text-black border-synth-amber'} onClick={() => commit(dialog.name)}>SAVE</button></div>
        </div>)}
    </div>
  )
}
