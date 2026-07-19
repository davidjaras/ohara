import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      // The SPA shares its origin with Django for the API, the auth pages and
      // the admin. Inside docker-compose the backend is reached by service
      // name; OHARA_API_ORIGIN overrides the default for that case.
      '/api': process.env.OHARA_API_ORIGIN ?? 'http://127.0.0.1:8000',
      '/accounts': process.env.OHARA_API_ORIGIN ?? 'http://127.0.0.1:8000',
      '/admin': process.env.OHARA_API_ORIGIN ?? 'http://127.0.0.1:8000',
      '/static': process.env.OHARA_API_ORIGIN ?? 'http://127.0.0.1:8000',
    },
  },
})
