// Bridge to the plugin (JUCE WebBrowserComponent) with a browser-side mock for development.
import * as Juce from './juce/index.js'
import { SOUND_PARAMS } from './params.generated'
import { Cmd, GlobalCmd, Pattern, PluginState, Playhead, NUM_TRACKS, emptyPattern, applyCmd, PATTERN_LEVEL, SONG_END } from './model'

export interface ParamHandle {
  get(): number                          // normalised 0..1
  set(v: number): void
  begin(): void
  end(): void
  subscribe(cb: () => void): () => void
}
export interface PresetInfo { name: string; factory: boolean }
export interface PresetState { items?: PresetInfo[]; current: string; factory: boolean; dirty: boolean }
export interface Bridge {
  readonly isMock: boolean
  getState(): Promise<PluginState>
  getPattern(pat: number): Promise<Pattern>
  euclid(length: number, steps: number, rotation: number): Promise<number[]>
  cmd(c: (string | number)[]): void
  onPlayhead(cb: (p: Playhead) => void): () => void
  param(id: string, kind: 'slider' | 'toggle' | 'combo'): ParamHandle
  audition(voice: number, velocity: number): void
  presets(): Promise<PresetState>
  loadPreset(name: string, factory: boolean): Promise<boolean>
  savePreset(name: string): Promise<boolean>
  deletePreset(name: string): Promise<boolean>
  onPreset(cb: (p: PresetState) => void): () => void
  onPresetLoaded(cb: () => void): () => void
}

// juce/index.js installs a placeholder window.__JUCE__ in a plain browser; the real backend lists its native functions
const hasJuce = () => !!(window as any).__JUCE__?.initialisationData?.__juce__functions?.includes('lynn_getState')

// ---------------------------------------------------------------------------------------------------- real bridge
function realBridge(): Bridge {
  const nGet = (Juce as any).getNativeFunction('lynn_getState')
  const nCmd = (Juce as any).getNativeFunction('lynn_cmd')
  const nGetPat = (Juce as any).getNativeFunction('lynn_getPattern')
  const nEuclid = (Juce as any).getNativeFunction('lynn_euclid')
  const handles = new Map<string, ParamHandle>()
  const nPresets = (Juce as any).getNativeFunction('lynn_presets'), nLoad = (Juce as any).getNativeFunction('lynn_loadPreset')
  const nAud = (Juce as any).getNativeFunction('lynn_audition')
  const nSave = (Juce as any).getNativeFunction('lynn_savePreset'), nDel = (Juce as any).getNativeFunction('lynn_deletePreset')
  const listen = (ev: string, cb: (e: any) => void) => { const id = (window as any).__JUCE__.backend.addEventListener(ev, cb); return () => (window as any).__JUCE__.backend.removeEventListener(id) }
  return {
    isMock: false,
    audition(v, vel) { nAud(v, vel) },
    async presets() { return JSON.parse(await nPresets()) as PresetState },
    loadPreset: (n, f) => nLoad(n, f), savePreset: (n) => nSave(n), deletePreset: (n) => nDel(n),
    onPreset: (cb) => listen('preset', cb), onPresetLoaded: (cb) => listen('presetLoaded', () => cb()),
    async getState() { return JSON.parse(await nGet()) as PluginState },
    async getPattern(p) { return JSON.parse(await nGetPat(p)) as Pattern },
    async euclid(l, s, r) { return JSON.parse(await nEuclid(l, s, r)) as number[] },
    cmd(c) { nCmd(JSON.stringify(c)) },
    onPlayhead(cb) {
      const id = (window as any).__JUCE__.backend.addEventListener('playhead', (e: any) => cb(e as Playhead))
      return () => (window as any).__JUCE__.backend.removeEventListener(id)
    },
    param(id, kind) {
      const key = kind + id
      let h = handles.get(key); if (h) return h
      const J: any = Juce
      const st = kind === 'slider' ? J.getSliderState(id) : kind === 'toggle' ? J.getToggleState(id) : J.getComboBoxState(id)
      h = {
        get: () => (kind === 'slider' ? st.getNormalisedValue() : kind === 'toggle' ? (st.getValue() ? 1 : 0) : st.getChoiceIndex()),
        set: (v) => (kind === 'slider' ? st.setNormalisedValue(v) : kind === 'toggle' ? st.setValue(!!v) : st.setChoiceIndex(v)),
        begin: () => { if (kind === 'slider') st.sliderDragStarted() },
        end: () => { if (kind === 'slider') st.sliderDragEnded() },
        subscribe: (cb) => {
          const ev = st.valueChangedEvent
          const l = ev.addListener(cb)
          return () => ev.removeListener(l)
        },
      }
      handles.set(key, h); return h
    },
  }
}

// ----------------------------------------------------------------------------------------------------- mock bridge
function mockBridge(): Bridge {
  const bank: Pattern[] = Array.from({ length: 64 }, () => emptyPattern())
  const demo = (t: number, steps: number[], vol = 100) => steps.forEach(s => { bank[0] = applyCmd(bank[0], ['step', t, s, 1]); bank[0] = applyCmd(bank[0], ['stepVol', t, s, vol]) })
  demo(0, [0, 4, 8, 12], 110); demo(3, [4, 12], 105); demo(5, [0, 2, 4, 6, 8, 10, 12, 14], 80); demo(6, [14], 90)
  bank[1] = applyCmd(applyCmd(emptyPattern(), ['step', 0, 0, 1]), ['step', 3, 4, 1])
  const song = Array(64).fill(SONG_END); song[0] = 0; song[1] = 1; song[2] = 65
  let songMode = false; const mutes = Array(NUM_TRACKS).fill(false), solos = Array(NUM_TRACKS).fill(false)
  let active = 0, pending = 0
  let running = true; const bpm = 120
  const listeners = new Set<(p: Playhead) => void>()
  let tick = 0
  setInterval(() => {
    tick++
    const step = Math.floor(tick / 5) % 16
    if (step === 0 && tick % 80 === 5) active = pending
    const steps = Array.from({ length: NUM_TRACKS }, (_, t) => step % bank[active].tracks[t].length)
    listeners.forEach(l => l({ running, steps, bpm, activePattern: active, pendingPattern: pending, songPosition: 0 }))
  }, 100)
  const params: Record<string, number> = { master: 0.5, seqSync: 0, seqRun: 0, tempo: 0.33 }
  for (let i = 1; i <= 7; i++) params['fader' + i] = 1
  for (const d of SOUND_PARAMS) params[d.id] = d.kind === 'int' ? (d.def - d.min) / (d.max - d.min) : d.def
  const subs = new Map<string, Set<() => void>>()
  let items = [{ name: 'Init', factory: true }, { name: 'Tight 4/4', factory: true }, { name: 'Deep Backbeat', factory: true }, { name: 'Metal Broken', factory: true }]
  let cur = 'Tight 4/4', curF = true, dirty = false
  const pl = new Set<(p: PresetState) => void>(), ll = new Set<() => void>()
  const push = () => pl.forEach(f => f({ current: cur, factory: curF, dirty }))
  return {
    isMock: true,
    audition() {},
    async presets() { return { items, current: cur, factory: curF, dirty } },
    async loadPreset(n, f) { cur = n; curF = f; dirty = false; push(); ll.forEach(x => x()); return true },
    async savePreset(n) { if (!items.some(i => i.name === n)) items = [...items, { name: n, factory: false }]; cur = n; curF = false; dirty = false; push(); return true },
    async deletePreset(n) { items = items.filter(i => i.factory || i.name !== n); push(); return true },
    onPreset(cb) { pl.add(cb); return () => pl.delete(cb) }, onPresetLoaded(cb) { ll.add(cb); return () => ll.delete(cb) },
    async getState() { return { pattern: bank[0], bpm, running, used: bank.map(p => JSON.stringify(p) !== JSON.stringify(emptyPattern())), song, songMode, mutes, solos } },
    async getPattern(p) { return bank[p] },
    async euclid(l, s, r) { const out = Array(64).fill(0); for (let i = 0; i < l; i++) out[(i + r) % l] = Math.floor(((i + 1) * s) / l) > Math.floor((i * s) / l) ? 1 : 0; return out },     // dev stand-in (the plugin uses the firmware's generator)
    cmd(c) {
      const [name, ...a] = c as [string, ...number[]]
      if (name !== 'euclid' && PATTERN_LEVEL.has(name)) { const p = a[0]; bank[p] = applyCmd(bank[p], [name, ...a.slice(1)] as any) }
      else if (name === 'euclid') { const [p, t, l, st, r] = a; const x = emptyPattern().tracks[0]; const o = bank[p]; const bits: number[] = Array(64).fill(0); for (let i = 0; i < l; i++) bits[(i + r) % l] = Math.floor(((i + 1) * st) / l) > Math.floor((i * st) / l) ? 1 : 0; const tr = { ...o.tracks[t], length: l, on: bits.map(b => !!b) }; void x; bank[p] = { ...o, tracks: o.tracks.map((q, i) => (i === t ? tr : q)) } }
      else if (name === 'mute') mutes[a[0]] = !!a[1]
      else if (name === 'solo') solos[a[0]] = !!a[1]
      else if (name === 'clearPattern') bank[a[0]] = emptyPattern()
      else if (name === 'copyPattern') bank[a[1]] = JSON.parse(JSON.stringify(bank[a[0]]))
      else if (name === 'selectPattern') { pending = a[0]; if (!running) active = a[0] }
      else if (name === 'songMode') songMode = !!a[0]
      else if (name === 'songSet') song[a[0]] = a[1]
    },
    onPlayhead(cb) { listeners.add(cb); return () => listeners.delete(cb) },
    param(id) {
      return {
        get: () => params[id] ?? 0,
        set: (v) => { params[id] = v; subs.get(id)?.forEach(f => f()) },
        begin() {}, end() {},
        subscribe: (cb) => { if (!subs.has(id)) subs.set(id, new Set()); subs.get(id)!.add(cb); return () => subs.get(id)!.delete(cb) },
      }
    },
  }
}

export const bridge: Bridge = hasJuce() ? realBridge() : mockBridge()
