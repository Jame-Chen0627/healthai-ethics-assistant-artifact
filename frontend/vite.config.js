import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/analyze-code': 'http://localhost:8000',
      '/generate-test-cases': 'http://localhost:8000',
      '/metamorphic': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
