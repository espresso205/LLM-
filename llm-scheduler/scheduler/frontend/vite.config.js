import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({
  plugins: [vue()],
  build: { outDir: '../app/static', emptyOutDir: true },
  server: { proxy: { '/api': 'http://localhost:8001', '/health': 'http://localhost:8001' } },
})
