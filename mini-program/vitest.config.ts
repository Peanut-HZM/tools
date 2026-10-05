import { defineConfig } from 'vitest/config'

// @tarojs/components / runtime 依赖构建期注入的全局常量（与 taro h5 webpack 默认值一致）
const taroDefines = {
  ENABLE_INNER_HTML: JSON.stringify(true),
  ENABLE_ADJACENT_HTML: JSON.stringify(false),
  ENABLE_CLONE_NODE: JSON.stringify(false),
  ENABLE_CONTAINS: JSON.stringify(false),
  ENABLE_SIZE_APIS: JSON.stringify(false),
  ENABLE_MUTATION_OBSERVER: JSON.stringify(false),
  ENABLE_TEMPLATE_CONTENT: JSON.stringify(false),
}

export default defineConfig({
  define: taroDefines,
  test: {
    environment: 'jsdom',
    include: ['src/**/__tests__/**/*.test.ts', 'src/**/__tests__/**/*.test.tsx'],
  },
})
