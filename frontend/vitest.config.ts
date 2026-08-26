import { defineConfig } from 'vitest/config';
import path from 'node:path';

export default defineConfig({
  test: {
    environment: 'jsdom',
    // 让测试可以解析 `@/components/ui/*` 等别名导入（与 vite.config.ts / tsconfig 保持一致）
    server: {
      deps: {
        inline: ['@/components/ui'],
      },
    },
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});