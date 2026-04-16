import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: '../app/static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/auth': 'http://localhost:8080',
      '/v1': 'http://localhost:8080',
      '/api': 'http://localhost:8080',
    },
  },
})
