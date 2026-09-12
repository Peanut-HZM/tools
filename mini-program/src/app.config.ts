export default {
  pages: [
    'pages/index/index',
    'pages/cross-share/message/index',
    'pages/cross-share/file/index',
    'pages/profile/index',
    'pages/login/index',
    'pages/json-formatter/index',
    'pages/calendar/index',
    'pages/key-generator/index',
    'pages/ocr/index',
    'pages/http-client/index',
    'pages/asr/index',
    'pages/change-password/index',
    'pages/help/index',
    'pages/openclaw/index',
  ],
  subPackages: [
    {
      root: 'package-media',
      pages: [
        'pages/image-downloader/index',
        'pages/video-downloader/index',
      ],
    },
    {
      root: 'package-docs',
      pages: [
        'pages/markitdown-converter/index',
        'pages/markdown-editor/index',
      ],
    },
    {
      root: 'package-learning',
      pages: [
        'pages/course-platform/index',
        'pages/course-platform/detail/index',
        'pages/tech-contents/index',
        'pages/tech-contents/detail/index',
      ],
    },
    {
      root: 'package-stats',
      pages: [
        'pages/token-usage/index',
      ],
    },
  ],
  preloadRule: {},
  window: {
    backgroundTextStyle: 'dark',
    navigationBarBackgroundColor: '#0A1225',
    navigationBarTitleText: '工具箱',
    navigationBarTextStyle: 'white',
    backgroundColor: '#0A1225',
  },
  tabBar: {
    color: '#5C6784',
    selectedColor: '#8B9BFF',
    backgroundColor: '#0A1225',
    borderStyle: 'black',
    list: [
      {
        pagePath: 'pages/index/index',
        text: '工具',
        iconPath: 'assets/icons/tool.png',
        selectedIconPath: 'assets/icons/tool-active.png',
      },
      {
        pagePath: 'pages/cross-share/message/index',
        text: '消息',
        iconPath: 'assets/icons/message.png',
        selectedIconPath: 'assets/icons/message-active.png',
      },
      {
        pagePath: 'pages/cross-share/file/index',
        text: '文件',
        iconPath: 'assets/icons/file.png',
        selectedIconPath: 'assets/icons/file-active.png',
      },
      {
        pagePath: 'pages/profile/index',
        text: '我的',
        iconPath: 'assets/icons/profile.png',
        selectedIconPath: 'assets/icons/profile-active.png',
      },
    ],
  },
}
