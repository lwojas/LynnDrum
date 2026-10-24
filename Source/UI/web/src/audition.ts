// Audition: play the selected voice from the UI. "Auto" re-triggers it whenever a sound control is released,
// which is how you hear a parameter change without a MIDI keyboard or the sequencer.
import { bridge } from './bridge'

let auto = false
let voice = 0
const listeners = new Set<() => void>()

export const audition = (v: number = voice, vel = 110) => bridge.audition(v, vel)
export const setCurrentVoice = (v: number) => { voice = v }
export const isAuto = () => auto
export const setAuto = (on: boolean) => { auto = on; listeners.forEach(f => f()) }
export const onAutoChange = (f: () => void) => { listeners.add(f); return () => { listeners.delete(f) } }
/** call after a sound control was changed by the user (knob released, selection made) */
export const commitSoundEdit = () => { if (auto) audition() }
