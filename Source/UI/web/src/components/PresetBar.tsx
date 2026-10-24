import React, { useEffect, useState } from 'react'
import { bridge, PresetInfo, PresetState } from '../bridge'

export function PresetBar() {
  const [items, setItems] = useState<PresetInfo[]>([])
  const [cur, setCur] = useState<PresetState>({ current: '', factory: true, dirty: false })
  const [dialog, setDialog] = useState<null | { name: string }>(null)
  const refresh = () => bridge.presets().then(p => { setItems(p.items ?? []); setCur({ current: p.current, factory: p.factory, dirty: p.dirty }) })
  useEffect(() => { refresh(); return bridge.onPreset(p => setCur(c => ({ ...c, ...p }))) }, [])

  const index = items.findIndex(i => i.name === cur.current && i.factory === cur.factory)
  const step = (d: number) => { if (!items.length) return; const n = items[(Math.max(index, 0) + d + items.length) % items.length]; bridge.loadPreset(n.name, n.factory) }
  const commit = async (name: string) => { if (name.trim() && await bridge.savePreset(name.trim())) { await refresh(); setDialog(null) } }
  const isUser = !cur.factory
  const btn = 'px-2 py-1 rounded border border-synth-border bg-synth-surface text-slate-300 hover:bg-synth-border text-[10px] font-mono'

  return (
    <div className="flex items-center gap-1.5 relative">
      <button className={btn} title="Previous preset" onClick={() => step(-1)}>‹</button>
      <select value={index >= 0 ? `${cur.factory ? 'f' : 'u'}:${cur.current}` : ''} className="bg-synth-surface border border-synth-border rounded px-2 py-1 text-xs font-mono text-synth-cyan max-w-[210px]"
        onChange={(e) => { const [k, ...n] = e.target.value.split(':'); bridge.loadPreset(n.join(':'), k === 'f') }}>
        <optgroup label="Factory">{items.filter(i => i.factory).map(i => <option key={'f' + i.name} value={`f:${i.name}`}>{i.name}</option>)}</optgroup>
        {items.some(i => !i.factory) && <optgroup label="User">{items.filter(i => !i.factory).map(i => <option key={'u' + i.name} value={`u:${i.name}`}>{i.name}</option>)}</optgroup>}
      </select>
      <button className={btn} title="Next preset" onClick={() => step(1)}>›</button>
      {cur.dirty && <span className="text-[10px] font-mono text-synth-amber border border-synth-amber/60 rounded px-1">*MOD</span>}
      <button className={btn} title={isUser ? 'Overwrite this user preset' : 'Save as a new user preset'} onClick={() => (isUser ? commit(cur.current) : setDialog({ name: '' }))}>SAVE</button>
      <button className={btn} title="Save a copy under a new name" onClick={() => setDialog({ name: isUser ? cur.current + ' 2' : '' })}>SAVE AS</button>
      {isUser && <button className={btn + ' text-synth-red'} title="Delete this user preset" onClick={async () => { await bridge.deletePreset(cur.current); await refresh(); step(0) }}>DEL</button>}
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
