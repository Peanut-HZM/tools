import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5178,
    strictPort: true, // 端口被占用时直接报错，不尝试其他端口
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:19092',
        changeOrigin: true,
        secure: false
      }
    }
  }
})
