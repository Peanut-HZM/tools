import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '', '')

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5178,
      strictPort: true,
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:19092',
          changeOrigin: true,
          secure: false,
          // SSE/长生成保护：后端生成一张图可能耗时 1-2 分钟，
          // 默认无超时配置下会被 Node/代理层掐断导致前端 Failed to fetch
          timeout: 600000,
          proxyTimeout: 600000
        }
      }
    },
    build: {
      define: {
        'import.meta.env.PROD': JSON.stringify(mode === 'production')
      }
    }
  }
})
