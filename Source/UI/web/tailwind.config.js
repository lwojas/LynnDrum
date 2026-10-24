/** Tokens from concept/stitch_lxr_02_vst_ui_design/code.html */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        synth: {
          bg: '#090b10', panel: '#10131b', surface: '#161a25', border: '#242a3a', activeBorder: '#3b435b', faderTrack: '#0b0d12',
          amber: '#ff7728', cyan: '#00e5ff', emerald: '#2fe278', violet: '#a855f7', red: '#ff3b5c',
        },
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        'glow-amber': '0 0 14px 2px rgba(255, 119, 40, 0.35)',
        'glow-cyan': '0 0 14px 2px rgba(0, 229, 255, 0.35)',
        'inset-deep': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.6)',
      },
    },
  },
  plugins: [],
}
