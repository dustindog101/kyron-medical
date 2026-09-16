import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    port: 5173,
    open: false,
    // Local dev: forward /api/* to the Flask backend (Docker/EC2: port
    // 5000; `python wsgi.py` locally defaults to 5050 — adjust as needed).
    // Production builds use relative paths (see src/api/client.js), so the
    // server hosting dist/ answers /api on the same origin. No telephony
    // keys are needed anywhere in this frontend.
    proxy: {
      '/api': {
        target: process.env.VITE_DEV_API_TARGET || 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
});
