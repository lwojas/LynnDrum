import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSingleFile } from 'vite-plugin-singlefile'

// One self-contained index.html: it is embedded into the plugin and served by the JUCE resource provider.
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  build: { target: 'safari14', outDir: 'dist', assetsInlineLimit: 100000000, cssCodeSplit: false },
})
