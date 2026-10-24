import React from 'react'
import { useStore } from '../store'
import { SOUND_PARAMS } from '../params.generated'
import { Knob, Select, Switch } from './controls'
import { TRACKS } from '../model'

// one row per sound voice (the two hi-hat tracks share the hat voice's parameters)
const ROWS = [
  { group: 'Drum 1', voice: 0 }, { group: 'Drum 2', voice: 1 }, { group: 'Drum 3', voice: 2 },
  { group: 'Snare', voice: 3 }, { group: 'Cymbal', voice: 4 }, { group: 'Hi-hat', voice: 5 },
]
export interface Col { name: string; label: string; w: number }

function Cell({ group, name, accent }: { group: string; name: string; accent: string }) {
  const d = SOUND_PARAMS.find(p => p.group === group && p.name === name)
  if (!d) return <div className="text-slate-700 text-center font-mono text-[10px]">–</div>
  if (d.kind === 'int') return <Knob id={d.id} label=" " accent={accent} size={30} />
  if (d.kind === 'bool') return <Switch id={d.id} label="ON" />
  return <Select id={d.id} label=" " />
}

/** all voices at a glance for a set of parameters; click a row label to select that voice */
export function Matrix({ cols, accent }: { cols: Col[]; accent: string }) {
  const { voice, setVoice } = useStore()
  const tmpl = `64px ${cols.map(c => `minmax(${c.w}px, 1fr)`).join(' ')}`
  return (
    <div className="rounded-xl border border-synth-border bg-synth-panel/70 p-3 overflow-auto shrink-0">
      <div className="grid gap-x-3 gap-y-1 items-center min-w-fit" style={{ gridTemplateColumns: tmpl }}>
        <div />
        {cols.map(c => <div key={c.name} className="text-[10px] font-mono font-bold tracking-wider text-center" style={{ color: accent }}>{c.label}</div>)}
        {ROWS.map(r => {
          const sel = Math.min(voice, 5) === r.voice
          return (
            <React.Fragment key={r.group}>
              <button onClick={() => setVoice(r.voice)}
                className={`rounded px-1 py-1 text-[10px] font-extrabold font-mono ${sel ? 'bg-synth-amber text-black' : 'bg-synth-border text-slate-200'}`}>{TRACKS[r.voice].tag}</button>
              {cols.map(c => <div key={c.name} className={`flex justify-center ${sel ? '' : 'opacity-90'}`}><Cell group={r.group} name={c.name} accent={accent} /></div>)}
            </React.Fragment>
          )
        })}
      </div>
    </div>
  )
}
