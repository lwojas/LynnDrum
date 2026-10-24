// Data model shared with the plugin (see Source/Plugin/SeqBridge.*). Mirrors LXR's pattern layout:
// 7 tracks x 64 steps; per step volume/probability/note, flam (0..5) and shift index (0..14, 7 = none).
export const NUM_TRACKS = 7
export const NUM_STEPS = 64
export const SHIFT_NONE = 7

export interface TrackInfo { id: number; short: string; tag: string; name: string; role: string; algo: string; note: number }
export const TRACKS: TrackInfo[] = [
  { id: 0, short: 'BD 1', tag: 'BD1',   name: 'DRUM 1',     role: 'FM DRUM',   algo: '2-OP FM DRUM + TRANSIENT CLICK', note: 36 },
  { id: 1, short: 'DRUM 2', tag: 'DR2', name: 'DRUM 2',     role: 'FM DRUM',   algo: '2-OP FM DRUM + TRANSIENT CLICK', note: 41 },
  { id: 2, short: 'DRUM 3', tag: 'DR3', name: 'DRUM 3',     role: 'FM DRUM',   algo: '2-OP FM DRUM + TRANSIENT CLICK', note: 43 },
  { id: 3, short: 'SNARE', tag: 'SNR', name: 'SNARE',      role: 'NOISE+OSC', algo: 'OSCILLATOR + NOISE, SNAP EG',    note: 38 },
  { id: 4, short: 'CYMBAL', tag: 'CYM', name: 'CYMBAL',     role: 'CLANG',     algo: '3-OSC FM, REPEAT ENVELOPE',      note: 49 },
  { id: 5, short: 'CH', tag: 'CH',  name: 'CLOSED HAT', role: 'HAT',       algo: '3-OSC METALLIC, SHORT DECAY',    note: 42 },
  { id: 6, short: 'OH', tag: 'OH',  name: 'OPEN HAT',   role: 'HAT',       algo: '3-OSC METALLIC, LONG DECAY',     note: 46 },
]

export interface TrackPattern {
  on: boolean[]; vol: number[]; prob: number[]; note: number[]; flam: number[]; shift: number[]
  lockPar1: number[]; lockVal1: number[]; lockPar2: number[]; lockVal2: number[]      // p-locks: PAR_* index or -1
  length: number            // 1..64 steps
}
export interface Pattern { tracks: TrackPattern[]; shuffle: number }

export const FLAM_LABELS = ['OFF', 'x2', 'x3', 'x4', 'x6', 'x8']
export const shiftOf = (index: number) => index - SHIFT_NONE

export function emptyTrack(): TrackPattern {
  return {
    on: Array(NUM_STEPS).fill(false), vol: Array(NUM_STEPS).fill(100), prob: Array(NUM_STEPS).fill(100),
    note: Array(NUM_STEPS).fill(60), flam: Array(NUM_STEPS).fill(0), shift: Array(NUM_STEPS).fill(SHIFT_NONE),
    lockPar1: Array(NUM_STEPS).fill(-1), lockVal1: Array(NUM_STEPS).fill(0), lockPar2: Array(NUM_STEPS).fill(-1), lockVal2: Array(NUM_STEPS).fill(0),
    length: 16,
  }
}
export const emptyPattern = (): Pattern => ({ tracks: Array.from({ length: NUM_TRACKS }, emptyTrack), shuffle: 0 })

// ---- commands: applied identically by the UI (optimistic) and by the plugin -----------------------------------------
export type Cmd =
  | ['step', track: number, idx: number, on: number]
  | ['stepVol', track: number, idx: number, v: number]
  | ['stepProb', track: number, idx: number, v: number]
  | ['stepNote', track: number, idx: number, v: number]
  | ['stepFlam', track: number, idx: number, v: number]
  | ['stepShift', track: number, idx: number, v: number]
  | ['euclid', track: number, length: number, steps: number, rotation: number]       // computed by the plugin (firmware generator): the view is reloaded
  | ['stepLock', track: number, idx: number, slot: number, par: number, v: number]
  | ['trackLength', track: number, len: number]
  | ['clearTrack', track: number]
  | ['copyTrack', src: number, dst: number]
  | ['shuffle', v: number]

export function applyCmd(p: Pattern, c: Cmd): Pattern {
  const q: Pattern = { shuffle: p.shuffle, tracks: p.tracks.slice() }
  const edit = (t: number, f: (x: TrackPattern) => void) => {
    const x = { ...q.tracks[t], on: q.tracks[t].on.slice(), vol: q.tracks[t].vol.slice(), prob: q.tracks[t].prob.slice(),
      note: q.tracks[t].note.slice(), flam: q.tracks[t].flam.slice(), shift: q.tracks[t].shift.slice(),
      lockPar1: q.tracks[t].lockPar1.slice(), lockVal1: q.tracks[t].lockVal1.slice(), lockPar2: q.tracks[t].lockPar2.slice(), lockVal2: q.tracks[t].lockVal2.slice() }
    f(x); q.tracks[t] = x
  }
  switch (c[0]) {
    case 'step': edit(c[1], x => {
      x.on[c[2]] = !!c[3]
      if (c[3]) { x.vol[c[2]] = x.vol[c[2]] || 100; if (!x.prob[c[2]]) x.prob[c[2]] = 100 }
    }); break
    case 'stepVol': edit(c[1], x => { x.vol[c[2]] = c[3] }); break
    case 'stepProb': edit(c[1], x => { x.prob[c[2]] = c[3] }); break
    case 'stepNote': edit(c[1], x => { x.note[c[2]] = c[3] }); break
    case 'stepFlam': edit(c[1], x => { x.flam[c[2]] = c[3] }); break
    case 'stepShift': edit(c[1], x => { x.shift[c[2]] = c[3] }); break
    case 'euclid': break
    case 'stepLock': edit(c[1], x => { const [par, val] = c[3] === 1 ? [x.lockPar1, x.lockVal1] : [x.lockPar2, x.lockVal2]; par[c[2]] = c[4]; val[c[2]] = c[5] }); break
    case 'trackLength': edit(c[1], x => { x.length = c[2] }); break
    case 'clearTrack': q.tracks[c[1]] = { ...emptyTrack(), length: q.tracks[c[1]].length }; break
    case 'copyTrack': q.tracks[c[2]] = { ...q.tracks[c[1]] }; break
    case 'shuffle': q.shuffle = c[1]; break
  }
  return q
}

/** commands that address one pattern: the store inserts the viewed pattern's number after the name on the wire */
export const PATTERN_LEVEL = new Set(['euclid', 'stepLock', 'step', 'stepVol', 'stepProb', 'stepNote', 'stepFlam', 'stepShift', 'trackLength', 'clearTrack', 'copyTrack', 'shuffle'])
/** commands with explicit arguments, sent as they are */
export type GlobalCmd =
  | ['mute', track: number, on: number]
  | ['clearPattern', pat: number]
  | ['copyPattern', src: number, dst: number]
  | ['selectPattern', pat: number]
  | ['songMode', on: number]
  | ['songSet', pos: number, pat: number]
  | ['roll', track: number, on: number]
  | ['rollRate', rate: number]
export const SONG_END = 64, SONG_LOOP = 65

export interface Playhead { running: boolean; steps: number[]; bpm: number; peakL?: number; peakR?: number; activePattern?: number; pendingPattern?: number; songPosition?: number }
export interface BankInfo { used: boolean[]; song: number[]; songMode: boolean; mutes: boolean[] }
export interface PluginState extends BankInfo { pattern: Pattern; bpm: number; running: boolean }
