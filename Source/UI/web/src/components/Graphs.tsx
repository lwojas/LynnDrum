import React from 'react'
import { useParam } from '../store'
import T from '../readout.golden.json'
import { fmtHz, fmtMs } from '../readout'

const W = 180, H = 56

const useRaw = (id: string) => { const [n] = useParam(id, 'slider'); return Math.round(n * 127) }
const useChoice = (id: string) => useParam(id, 'combo')[0]

const Frame: React.FC<{ children: React.ReactNode; color: string; caption: string }> = ({ children, color, caption }) => (
  <div className="mb-1.5 shrink-0">
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="w-full h-9 rounded bg-synth-bg/60 border border-synth-border/60" style={{ color }}>{children}</svg>
    <div className="text-[9px] font-mono text-slate-500 mt-0.5">{caption}</div>
  </div>
)

/** 2-pole state-variable response; q is the engine's damping term (small = resonant) */
function mag(type: number, x: number, q: number): number {
  const d = Math.hypot(1 - x * x, q * x)
  switch (type) {
    case 0: case 6: return 1 / d
    case 1: return (x * x) / d
    case 2: return x / d
    case 3: return (q * x) / d
    case 4: return Math.abs(1 - x * x) / d
    case 5: return (1 + x * x) / d
    default: return 1
  }
}

export function FilterGraph({ n }: { n: number }) {
  const f = useRaw(`filter_freq_${n}`), r = useRaw(`reso_${n}`), type = useChoice(`filter_type_${n}`)
  const hz = T.cutoffHz[f], q = T.filterQ[r]
  const pts: string[] = []
  const lo = Math.log10(20), hi = Math.log10(20000)
  for (let i = 0; i <= 90; i++) {
    const fr = Math.pow(10, lo + (hi - lo) * i / 90)
    const db = type === 7 ? 0 : 20 * Math.log10(Math.max(1e-4, mag(type, fr / Math.max(hz, 1), q)))
    const y = H / 2 - (Math.max(-30, Math.min(24, db)) / 30) * (H / 2 - 4)
    pts.push(`${(i / 90 * W).toFixed(1)},${(Math.min(H - 1, Math.max(1, y))).toFixed(1)}`)
  }
  const cx = ((Math.log10(Math.max(hz, 20)) - lo) / (hi - lo)) * W
  return (
    <Frame color="#00e5ff" caption={type === 7 ? 'filter off' : `cutoff ${fmtHz(hz)} · 20 Hz–20 kHz, ±30 dB (idealised 2-pole)`}>
      <line x1={0} x2={W} y1={H / 2} y2={H / 2} stroke="#242a3a" />
      <line x1={cx} x2={cx} y1={0} y2={H} stroke="#242a3a" strokeDasharray="2 2" />
      <polyline points={pts.join(' ')} fill="none" stroke="currentColor" strokeWidth={1.6} />
    </Frame>
  )
}

const shape = (v: number, s: number) => (1 + s) * v / (1 + s * Math.abs(v))

export function EnvGraph({ n, decayId }: { n: number; decayId: string }) {
  const a = useRaw(`veloa${n}`), d = useRaw(decayId), sl = useRaw(`vol_slope${n}`)
  const aMs = T.attack[a] > 0 ? T.blockMs / T.attack[a] : 0
  const dMs = T.decay[d] > 0 ? T.blockMs / T.decay[d] : Infinity
  const amount = ((sl / 127) - 0.5) * 1.999
  const slope = 2 * amount / (1 - amount), inv = 2 * -amount / (1 + amount)
  const total = Math.min(3000, Math.max(50, (isFinite(dMs) ? aMs + dMs : 3000)))
  const pts: string[] = []
  for (let i = 0; i <= 120; i++) {
    const t = (i / 120) * total
    let y: number
    if (t < aMs) y = shape(t / aMs, inv)
    else y = isFinite(dMs) ? shape(Math.max(0, 1 - (t - aMs) / dMs), slope) : 1
    pts.push(`${(i / 120 * W).toFixed(1)},${(H - 3 - y * (H - 8)).toFixed(1)}`)
  }
  return (
    <Frame color="#2fe278" caption={`amp: attack ${fmtMs(aMs)} · decay ${fmtMs(dMs)} · window ${fmtMs(total)} (shape approximate)`}>
      <line x1={0} x2={W} y1={H - 3} y2={H - 3} stroke="#242a3a" />
      <polyline points={pts.join(' ')} fill="none" stroke="currentColor" strokeWidth={1.6} />
    </Frame>
  )
}
