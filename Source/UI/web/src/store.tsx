import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { bridge, ParamHandle } from './bridge'
import { Cmd, Pattern, Playhead, applyCmd, emptyPattern } from './model'
import { setCurrentVoice } from './audition'

interface Store {
  pattern: Pattern
  send: (c: Cmd) => void
  playhead: Playhead
  voice: number; setVoice: (v: number) => void
  bar: number; setBar: (b: number) => void
  selStep: number; setSelStep: (s: number) => void
  clipboard: React.MutableRefObject<number | null>
}
const Ctx = createContext<Store | null>(null)
export const useStore = () => useContext(Ctx)!

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [pattern, setPattern] = useState<Pattern>(emptyPattern())
  const [playhead, setPlayhead] = useState<Playhead>({ running: false, steps: [0, 0, 0, 0, 0, 0, 0], bpm: 120 })
  const [voice, setVoice] = useState(0)
  const [bar, setBar] = useState(0)
  const [selStep, setSelStep] = useState(0)
  const clipboard = useRef<number | null>(null)

  useEffect(() => { bridge.getState().then(s => { setPattern(s.pattern); setPlayhead(p => ({ ...p, running: s.running, bpm: s.bpm })) }) }, [])
  useEffect(() => bridge.onPlayhead(p => setPlayhead(p)), [])
  useEffect(() => bridge.onPresetLoaded(() => { bridge.getState().then(s => setPattern(s.pattern)) }), [])

  useEffect(() => { setCurrentVoice(voice) }, [voice])

  const send = useCallback((c: Cmd) => { bridge.cmd(c); setPattern(p => applyCmd(p, c)) }, [])
  const v = useMemo(() => ({ pattern, send, playhead, voice, setVoice, bar, setBar, selStep, setSelStep, clipboard }),
    [pattern, send, playhead, voice, bar, selStep])
  return <Ctx.Provider value={v}>{children}</Ctx.Provider>
}

// Host-automatable parameter as a React hook (normalised 0..1)
export function useParam(id: string, kind: 'slider' | 'toggle' | 'combo' = 'slider'): [number, (v: number) => void, ParamHandle] {
  const h = useMemo(() => bridge.param(id, kind), [id, kind])
  const [val, setVal] = useState(() => h.get())
  useEffect(() => { setVal(h.get()); return h.subscribe(() => setVal(h.get())) }, [h])
  return [val, (x: number) => { h.set(x); setVal(x) }, h]
}
