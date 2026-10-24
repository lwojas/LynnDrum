import React from 'react'
import { Header } from './components/Header'
import { Mixer } from './components/Mixer'
import { SoundDeck } from './components/SoundDeck'
import { SequencerDeck } from './components/SequencerDeck'
import { StoreProvider } from './store'
import { audition } from './audition'

export default function App() {
  React.useEffect(() => {
    const on = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement
      if (t && (t.tagName === 'INPUT' || t.tagName === 'SELECT' || t.tagName === 'TEXTAREA') || e.repeat || e.metaKey || e.ctrlKey || e.altKey) return
      if (e.key >= '1' && e.key <= '7') audition(parseInt(e.key, 10) - 1)
    }
    window.addEventListener('keydown', on); return () => window.removeEventListener('keydown', on)
  }, [])
  return (
    <StoreProvider>
      <div className="h-full w-full flex flex-col bg-synth-bg text-slate-100 overflow-hidden" style={{ minWidth: 900, minHeight: 600 }}>
        <Header />
        <div className="flex-1 min-h-0 flex">
          <Mixer />
          <SoundDeck />
        </div>
        <SequencerDeck />
        <div className="px-3 py-0.5 text-[9px] font-mono text-slate-600 bg-synth-bg border-t border-synth-border">
          LynnDrum · derived from the open-source LXR firmware by Erica Synths (GPL-3.0) · not affiliated with or endorsed by Erica Synths
        </div>
      </div>
    </StoreProvider>
  )
}
