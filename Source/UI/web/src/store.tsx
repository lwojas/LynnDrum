import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { bridge, ParamHandle } from './bridge'
import { BankInfo, Cmd, GlobalCmd, NUM_TRACKS, PATTERN_LEVEL, Pattern, SONG_END, applyCmd, emptyPattern } from './model'
import { setCurrentVoice } from './audition'
import { onTelemetryFrame, seedTelemetry } from './telemetry'

// Editing state (pattern data, selections) lives in React. Telemetry (playhead, meter) does not: see telemetry.ts.
interface Store {
  pattern: Pattern                                  // the pattern being edited (viewPat)
  viewPat: number; setViewPat: (p: number) => void
  follow: boolean; setFollow: (f: boolean) => void  // the view follows the playing pattern
  bank: BankInfo
  send: (c: Cmd) => void                            // edit the viewed pattern
  sendG: (c: GlobalCmd) => void                     // commands with explicit arguments (mute, patterns, song, roll)
  voice: number; setVoice: (v: number) => void
  bar: number; setBar: (b: number) => void
  selStep: number; setSelStep: (s: number) => void
  clipboard: React.MutableRefObject<number | null>          // copied track
  patClipboard: React.MutableRefObject<number | null>       // copied pattern
}
const Ctx = createContext<Store | null>(null)
export const useStore = () => useContext(Ctx)!

const emptyBank = (): BankInfo => ({ used: Array(64).fill(false), song: Array(64).fill(SONG_END), songMode: false, mutes: Array(NUM_TRACKS).fill(false), solos: Array(NUM_TRACKS).fill(false) })

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [pattern, setPattern] = useState<Pattern>(emptyPattern())
  const [bank, setBank] = useState<BankInfo>(emptyBank())
  const [viewPat, setViewPatState] = useState(0)
  const [follow, setFollow] = useState(true)
  const [voice, setVoice] = useState(0)
  const [bar, setBar] = useState(0)
  const [selStep, setSelStep] = useState(0)
  const clipboard = useRef<number | null>(null)
  const patClipboard = useRef<number | null>(null)
  const view = useRef(0); view.current = viewPat

  const loadView = useCallback((p: number) => { bridge.getPattern(p).then(x => { if (view.current === p) setPattern(x) }) }, [])
  const refreshBank = useCallback(() => bridge.getState().then(s => { setBank({ used: s.used, song: s.song, songMode: s.songMode, mutes: s.mutes, solos: s.solos ?? Array(NUM_TRACKS).fill(false) }); seedTelemetry(s.running, s.bpm) }), [])
  const setViewPat = useCallback((p: number) => { view.current = p; setViewPatState(p); setBar(0); loadView(p) }, [loadView])

  useEffect(() => { refreshBank(); loadView(0) }, [])
  useEffect(() => bridge.onPresetLoaded(() => { refreshBank(); loadView(view.current) }), [loadView, refreshBank])
  useEffect(() => { setCurrentVoice(voice) }, [voice])

  // the view follows the playing pattern (the sequencer switches at the end of the bar) - decided per telemetry frame, outside React
  const followRef = useRef(follow); followRef.current = follow
  useEffect(() => {
    let last = -1
    return onTelemetryFrame(t => {
      if (t.activePattern !== last) { last = t.activePattern; if (followRef.current && t.running && t.activePattern !== view.current) setViewPat(t.activePattern) }
    })
  }, [setViewPat])

  const send = useCallback((c: Cmd) => {
    const p = view.current
    bridge.cmd(PATTERN_LEVEL.has(c[0]) ? [c[0], p, ...c.slice(1)] : (c as any))
    if (c[0] === 'euclid') setTimeout(() => loadView(p), 0)             // computed by the plugin: fetch the result
    else setPattern(x => applyCmd(x, c))
    if (c[0] === 'step' || c[0] === 'clearTrack' || c[0] === 'copyTrack' || c[0] === 'euclid') setBank(b => b.used[p] ? b : { ...b, used: b.used.map((u, i) => (i === p ? true : u)) })
  }, [loadView])
  const sendG = useCallback((c: GlobalCmd) => {
    bridge.cmd(c as any)
    if (c[0] === 'solo') setBank(b => ({ ...b, solos: b.solos.map((m, i) => (i === c[1] ? !!c[2] : m)) }))
    if (c[0] === 'mute') setBank(b => ({ ...b, mutes: b.mutes.map((m, i) => (i === c[1] ? !!c[2] : m)) }))
    else if (c[0] === 'songMode') setBank(b => ({ ...b, songMode: !!c[1] }))
    else if (c[0] === 'songSet') setBank(b => ({ ...b, song: b.song.map((e, i) => (i === c[1] ? c[2] : e)) }))
    else if (c[0] === 'clearPattern') { setBank(b => ({ ...b, used: b.used.map((u, i) => (i === c[1] ? false : u)) })); if (c[1] === view.current) loadView(c[1]) }
    else if (c[0] === 'copyPattern') { setBank(b => ({ ...b, used: b.used.map((u, i) => (i === c[2] ? b.used[c[1]] : u)) })); if (c[2] === view.current) setTimeout(() => loadView(c[2]), 0) }
  }, [loadView])

  const v = useMemo(() => ({ pattern, viewPat, setViewPat, follow, setFollow, bank, send, sendG, voice, setVoice, bar, setBar, selStep, setSelStep, clipboard, patClipboard }),
    [pattern, viewPat, setViewPat, follow, bank, send, sendG, voice, bar, selStep])
  return <Ctx.Provider value={v}>{children}</Ctx.Provider>
}

// Host-automatable parameter as a React hook (normalised 0..1)
export function useParam(id: string, kind: 'slider' | 'toggle' | 'combo' = 'slider'): [number, (v: number) => void, ParamHandle] {
  const h = useMemo(() => bridge.param(id, kind), [id, kind])
  const [val, setVal] = useState(() => h.get())
  useEffect(() => { setVal(h.get()); return h.subscribe(() => setVal(h.get())) }, [h])
  return [val, (x: number) => { h.set(x); setVal(x) }, h]
}
