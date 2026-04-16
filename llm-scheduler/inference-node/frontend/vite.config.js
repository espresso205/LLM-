import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({
  plugins: [vue()],
  build: { outDir: '../app/static', emptyOutDir: true },
  server: { proxy: { '/v1': 'http://localhost:8003', '/api': 'http://localhost:8003', '/health': 'http://localhost:8003' } },
})
