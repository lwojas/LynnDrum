import React, { useState } from 'react'
import { useStore } from '../store'
import { SONG_END, SONG_LOOP } from '../model'

const BANKS = ['A', 'B', 'C', 'D']

function SongEditor({ onClose }: { onClose: () => void }) {
  const { bank, sendG, playhead } = useStore()
  const firstEnd = bank.song.findIndex(e => e >= SONG_END)
  const shown = Math.min(64, (firstEnd < 0 ? 64 : firstEnd) + 1)
  return (
    <div className="absolute right-0 bottom-9 z-50 w-[560px] max-w-[92vw] bg-synth-panel border border-synth-activeBorder rounded-lg p-3 shadow-xl">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-mono font-bold text-slate-200">SONG - patterns play in this order, one per bar of the longest track</span>
        <button className="text-slate-400 hover:text-white text-xs" onClick={onClose}>✕</button>
      </div>
      <div className="grid gap-1" style={{ gridTemplateColumns: 'repeat(8, minmax(0, 1fr))' }}>
        {Array.from({ length: shown }, (_, i) => {
          const v = bank.song[i]
          const playing = bank.songMode && playhead.running && playhead.songPosition === i
          return (
            <label key={i} className={`flex flex-col text-[8px] font-mono text-slate-500 rounded border p-0.5 ${playing ? 'border-synth-cyan' : 'border-synth-border'}`}>
              {String(i + 1).padStart(2, '0')}
              <select value={v} onChange={(e) => sendG(['songSet', i, parseInt(e.target.value, 10)])}
                className={`bg-synth-surface text-[10px] font-mono rounded ${v >= SONG_END ? 'text-slate-400' : 'text-synth-amber'}`}>
                {Array.from({ length: 64 }, (_, p) => <option key={p} value={p}>{p + 1}</option>)}
                <option value={SONG_END}>END</option><option value={SONG_LOOP}>LOOP</option>
              </select>
            </label>)
        })}
      </div>
      <div className="text-[9px] font-mono text-slate-500 mt-2">END stops the sequencer after the last pattern, LOOP restarts the song. Song mode is switched with the SONG button.</div>
    </div>
  )
}

export function PatternBar() {
  const { viewPat, setViewPat, bank, sendG, playhead, follow, setFollow, patClipboard } = useStore()
  const [songOpen, setSongOpen] = useState(false)
  const page = Math.floor(viewPat / 16)
  const active = playhead.activePattern ?? 0, pending = playhead.pendingPattern ?? active
  const btn = 'px-2 py-0.5 rounded bg-synth-surface hover:bg-synth-border border border-synth-border text-slate-300 disabled:opacity-40'
  return (
    <div className="flex items-center gap-2 text-[10px] font-mono relative">
      <span className="font-extrabold text-xs tracking-wider text-slate-200">PATTERN</span>
      <div className="flex bg-synth-surface p-0.5 rounded border border-synth-border">
        {BANKS.map((b, i) => <button key={b} onClick={() => setViewPat(i * 16 + (viewPat % 16))} className={`px-2 py-0.5 rounded font-bold ${page === i ? 'bg-synth-activeBorder text-white' : 'text-slate-400'}`}>{b}</button>)}
      </div>
      <div className="grid gap-1 flex-1" style={{ gridTemplateColumns: 'repeat(16, minmax(0, 1fr))' }}>
        {Array.from({ length: 16 }, (_, k) => {
          const p = page * 16 + k
          const viewed = p === viewPat, playing = p === active, queued = p === pending && pending !== active
          return (
            <button key={p} title={`Pattern ${p + 1}${bank.used[p] ? '' : ' (empty)'} - click: edit and play next, shift-click: edit only`}
              onClick={(e) => { setViewPat(p); if (!e.shiftKey) sendG(['selectPattern', p]) }}
              className={`relative rounded border py-0.5 font-bold ${viewed ? 'bg-synth-amber text-black border-synth-amber' : 'bg-synth-surface text-slate-300 border-synth-border hover:bg-synth-border'}
                          ${playing ? 'ring-2 ring-synth-cyan' : ''} ${queued ? 'animate-pulse ring-2 ring-synth-amber' : ''}`}>
              {p + 1}{bank.used[p] && !viewed && <span className="absolute top-0.5 right-0.5 w-1 h-1 rounded-full bg-synth-emerald" />}
            </button>)
        })}
      </div>
      <button className={btn + (follow ? ' text-synth-cyan border-synth-cyan' : '')} title="The edit view follows the playing pattern" onClick={() => setFollow(!follow)}>FOLLOW</button>
      <div className="flex gap-1">
        <button className={btn} title="Copy this pattern" onClick={() => { patClipboard.current = viewPat }}>COPY</button>
        <button className={btn} disabled={patClipboard.current === null || patClipboard.current === viewPat} title="Paste over this pattern" onClick={() => patClipboard.current !== null && sendG(['copyPattern', patClipboard.current, viewPat])}>PASTE</button>
        <button className={btn} title="Empty this pattern" onClick={() => sendG(['clearPattern', viewPat])}>CLEAR</button>
      </div>
      <button className={btn + (bank.songMode ? ' bg-synth-cyan/20 border-synth-cyan text-synth-cyan font-bold' : '')} onClick={() => sendG(['songMode', bank.songMode ? 0 : 1])}>SONG</button>
      <button className={btn} title="Edit the song" onClick={() => setSongOpen(!songOpen)}>⋯</button>
      {songOpen && <SongEditor onClose={() => setSongOpen(false)} />}
    </div>
  )
}
