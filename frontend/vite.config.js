import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    port: 3000,
    // Erlaubt Zugriff ueber Tailscale Serve / Funnel (Hostname homelab.tailb8858a.ts.net).
    allowedHosts: true,
    proxy: {
      '/api': process.env.API_TARGET || 'http://localhost:8000',
    },
  },
})
