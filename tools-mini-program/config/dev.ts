import type { UserConfigExport } from '@tarojs/cli'
export default {
  h5: {
    devServer: {
      port: 5173,
      hot: true,
      devMiddleware: {
        writeToDisk: false,
      },
    },
  },
} satisfies UserConfigExport
