// Telemetry from the audio thread (playhead, playing pattern, output peaks) at ~30 Hz.
// It deliberately lives OUTSIDE React: hot, per-frame consumers (step highlight, meter) update the DOM / a canvas directly,
// and the few React views that show telemetry subscribe to a *selected value* and re-render only when that value changes.
import { useSyncExternalStore } from 'react'
import { bridge } from './bridge'
import { NUM_TRACKS, Playhead } from './model'

export interface Telemetry extends Required<Omit<Playhead, 'steps'>> { steps: number[] }
let state: Telemetry = { running: false, steps: Array(NUM_TRACKS).fill(0), bpm: 120, peakL: 0, peakR: 0, activePattern: 0, pendingPattern: 0, songPosition: 0 }
const frameListeners = new Set<(t: Telemetry) => void>()
const changeListeners = new Set<() => void>()

bridge.onPlayhead(p => {
  state = { running: p.running, steps: p.steps, bpm: p.bpm, peakL: p.peakL ?? 0, peakR: p.peakR ?? 0,
            activePattern: p.activePattern ?? 0, pendingPattern: p.pendingPattern ?? (p.activePattern ?? 0), songPosition: p.songPosition ?? 0 }
  frameListeners.forEach(f => f(state))
  changeListeners.forEach(f => f())
})
/** seed from the initial state fetch (before the first event arrives) */
export const seedTelemetry = (running: boolean, bpm: number) => { state = { ...state, running, bpm }; changeListeners.forEach(f => f()) }

export const getTelemetry = () => state
/** imperative per-frame subscription (no React involved) */
export const onTelemetryFrame = (f: (t: Telemetry) => void) => { frameListeners.add(f); return () => { frameListeners.delete(f) } }

/** React hook: re-renders only when the selected primitive changes */
export function useTelemetry<T extends string | number | boolean>(select: (t: Telemetry) => T): T {
  return useSyncExternalStore(
    (cb) => { changeListeners.add(cb); return () => { changeListeners.delete(cb) } },
    () => select(state))
}
