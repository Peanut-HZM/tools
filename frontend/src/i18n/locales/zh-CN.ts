/**
 * Chinese (Simplified) translations for Markdown Editor
 */
export const zhCN = {
  // Common
  common: {
    save: '保存',
    cancel: '取消',
    confirm: '确认',
    delete: '删除',
    rename: '重命名',
    create: '创建',
    close: '关闭',
    search: '搜索',
    settings: '设置',
    loading: '加载中...',
    error: '错误',
    success: '成功',
    back: '返回',
    openFolder: '打开文件夹',
    new: '新建',
    fileName: '文件名',
    folderName: '所在目录',
  },

  // Auth
  auth: {
    login: '登录',
    logout: '登出',
    register: '注册',
    username: '用户名',
    password: '密码',
    email: '邮箱',
    confirmPassword: '确认密码',
    loginTitle: '登录到 Markdown 编辑器',
    registerTitle: '注册新账户',
    noAccount: '没有账户？',
    hasAccount: '已有账户？',
    loginFailed: '登录失败',
    registerFailed: '注册失败',
    invalidCredentials: '用户名或密码错误',
    userExists: '用户名已存在',
    verifying: '验证登录状态...',
  },

  // Editor
  editor: {
    title: 'Markdown 编辑器',
    edit: '编辑',
    preview: '预览',
    split: '分屏',
    selectFile: '选择一个文件开始编辑',
    unsavedChanges: '当前文件未保存，是否保存？',
    saveSuccess: '保存成功',
    saveFailed: '保存失败',
    autoSave: '自动保存',
  },

  // File Tree
  fileTree: {
    title: '文件',
    newFile: '新建文件',
    newFolder: '新建文件夹',
    deleteConfirm: '确定要删除 "{name}" 吗？',
    deleteFolder: '删除文件夹',
    deleteFile: '删除文件',
    renameFile: '重命名文件',
    renameFolder: '重命名文件夹',
    emptyFolder: '空文件夹',
    noFiles: '暂无文件',
  },

  // Search
  search: {
    title: '搜索',
    placeholder: '输入搜索关键词...',
    fileSearch: '文件搜索',
    contentSearch: '内容搜索',
    regex: '正则表达式',
    caseSensitive: '区分大小写',
    noResults: '未找到结果',
    searching: '搜索中...',
    results: '搜索结果',
    line: '行',
  },

  // Settings
  settings: {
    title: '设置',
    editor: '编辑器',
    preview: '预览',
    general: '通用',
    theme: '主题',
    themeLight: '浅色',
    themeDark: '深色',
    fontSize: '字体大小',
    tabSize: 'Tab 大小',
    useSpaces: '使用空格代替 Tab',
    showLineNumbers: '显示行号',
    wordWrap: '自动换行',
    showMinimap: '显示小地图',
    autoSaveInterval: '自动保存间隔（秒）',
    previewTheme: '预览主题',
    language: '语言',
    resetDefaults: '恢复默认设置',
  },

  // Status Bar
  statusBar: {
    line: '行',
    column: '列',
    saved: '已保存',
    unsaved: '未保存',
    saving: '保存中...',
    error: '保存错误',
    lastSaved: '上次保存',
  },

  // Errors
  errors: {
    networkError: '网络错误，请检查网络连接',
    authError: '认证失败，请重新登录',
    fileNotFound: '文件不存在',
    permissionDenied: '权限不足',
    saveFailed: '保存失败',
    loadFailed: '加载失败',
    deleteFailed: '删除失败',
    renameFailed: '重命名失败',
    createFailed: '创建失败',
    unknownError: '未知错误',
  },
};

export default zhCN;
