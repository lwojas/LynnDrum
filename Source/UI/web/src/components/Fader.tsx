import React, { useRef } from 'react'
import { ParamHandle } from '../bridge'

// Vertical fader bound to a normalised parameter; pointer-capture drag with gesture begin/end for host automation.
export function Fader({ value, handle, onChange, color = '#ff7728' }: { value: number; handle: ParamHandle; onChange: (v: number) => void; color?: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)
  const setFrom = (clientY: number, fine: boolean, startY?: number, startV?: number) => {
    const r = ref.current!.getBoundingClientRect()
    if (fine && startY !== undefined && startV !== undefined) onChange(Math.min(1, Math.max(0, startV + (startY - clientY) / r.height / 8)))
    else onChange(Math.min(1, Math.max(0, 1 - (clientY - r.top) / r.height)))
  }
  const start = useRef<{ y: number; v: number }>({ y: 0, v: 0 })
  return (
    <div ref={ref} className="fader-track relative flex-1 w-7 rounded-md touch-none" style={{ minHeight: 80 }}
      onPointerDown={(e) => { (e.target as Element).setPointerCapture?.(e.pointerId); dragging.current = true; handle.begin(); start.current = { y: e.clientY, v: value }; setFrom(e.clientY, e.shiftKey) }}
      onPointerMove={(e) => { if (dragging.current) { if (e.shiftKey) setFrom(e.clientY, true, start.current.y, start.current.v); else setFrom(e.clientY, false) } }}
      onPointerUp={() => { dragging.current = false; handle.end() }}
      onDoubleClick={() => onChange(1)}>
      <div className="absolute left-1/2 -translate-x-1/2 w-0.5 top-1 bottom-1 bg-black/60" />
      <div className="absolute left-1/2 -translate-x-1/2 bottom-1 w-1 rounded" style={{ height: `calc(${value * 100}% - 4px)`, background: color, opacity: 0.55 }} />
      <div className="fader-thumb absolute left-0 right-0 h-3.5 rounded-sm border border-black/60 flex items-center justify-center" style={{ bottom: `calc(${value * 100}% - 7px)` }}>
        <div className="h-0.5 w-4/5 bg-slate-300/80 rounded" />
      </div>
    </div>
  )
}
