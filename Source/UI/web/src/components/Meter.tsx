import React, { useEffect, useRef } from 'react'
import { onTelemetryFrame } from '../telemetry'

const W = 112, H = 14
const toBar = (v: number) => Math.max(0, Math.min(1, (20 * Math.log10(Math.max(v, 1e-4)) + 60) / 66))      // -60 dB .. +6 dB
const col = (v: number) => (v > 1 ? '#ff3b5c' : v > 0.7 ? '#ff7728' : '#2fe278')

/** Stereo peak meter drawn on a canvas by a requestAnimationFrame loop; telemetry frames only feed two numbers, React never re-renders. */
export function Meter() {
  const cv = useRef<HTMLCanvasElement>(null), txt = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    const c = cv.current!, g = c.getContext('2d')!
    const dpr = Math.min(2, window.devicePixelRatio || 1)
    c.width = W * dpr; c.height = H * dpr; g.scale(dpr, dpr)
    let inL = 0, inR = 0, l = 0, r = 0, raf = 0, last = performance.now(), idle = false, lastText = ''
    const off = onTelemetryFrame(t => { inL = Math.max(inL, t.peakL); inR = Math.max(inR, t.peakR) })
    const draw = (now: number) => {
      const dt = Math.min(100, now - last); last = now
      const fall = Math.exp(-dt / 280)                                      // fall-back, time constant 280 ms
      l = Math.max(inL, l * fall); r = Math.max(inR, r * fall); inL = inR = 0
      const silent = l < 1e-4 && r < 1e-4
      if (!(silent && idle)) {
        g.clearRect(0, 0, W, H)
        g.fillStyle = 'rgba(0,0,0,0.6)'; g.fillRect(0, 0, W, 6); g.fillRect(0, 8, W, 6)
        g.fillStyle = col(l); g.fillRect(0, 0, W * toBar(l), 6)
        g.fillStyle = col(r); g.fillRect(0, 8, W * toBar(r), 6)
        const m = Math.max(l, r), s = m < 1e-4 ? '-inf dB' : (20 * Math.log10(m)).toFixed(1) + ' dB'
        if (s !== lastText && txt.current) { txt.current.textContent = s; lastText = s }
      }
      idle = silent
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)
    return () => { cancelAnimationFrame(raf); off() }
  }, [])
  return (
    <div className="flex flex-col gap-0.5" title="Output peak">
      <canvas ref={cv} style={{ width: W, height: H }} />
      <span ref={txt} className="text-[9px] font-mono text-slate-400 text-right leading-none">-inf dB</span>
    </div>
  )
}
