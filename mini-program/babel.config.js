// babel-preset-taro 会处理 TypeScript 和其他转换
module.exports = {
  presets: [
    ['taro', {
      framework: 'react',
      ts: true
    }]
  ]
}
