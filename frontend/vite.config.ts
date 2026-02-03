import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react({ include: /\.(mdx|js|jsx|ts|tsx)$/ })],
  server: {
    port: 5678,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8012',
        changeOrigin: true
      }
    }
  }
})
