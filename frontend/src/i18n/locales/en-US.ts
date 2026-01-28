/**
 * English (US) translations
 */
export const enUS = {
  // Common
  common: {
    save: 'Save',
    cancel: 'Cancel',
    confirm: 'Confirm',
    delete: 'Delete',
    rename: 'Rename',
    create: 'Create',
    close: 'Close',
    search: 'Search',
    settings: 'Settings',
    loading: 'Loading...',
    error: 'Error',
    success: 'Success',
    back: 'Back',
    openFolder: 'Open Folder',
    new: 'New',
    fileName: 'File Name',
    folderName: 'Folder',
    logo: 'Toolbox',
    allTools: 'All Tools',
    view: 'View',
    leaveBlankToKeep: 'Leave blank to keep unchanged',
    copy: 'Copy',
    filter: 'Filter',
  },

  // Navigation
  nav: {
    home: 'Home',
    tools: 'Tools',
    about: 'About',
    help: 'Help',
    feedback: 'Feedback',
  },

  // Auth
  auth: {
    login: 'Login',
    logout: 'Logout',
    register: 'Register',
    username: 'Username',
    password: 'Password',
    email: 'Email',
    confirmPassword: 'Confirm Password',
    loginTitle: 'Login',
    registerTitle: 'Register',
    noAccount: "Don't have an account?",
    hasAccount: 'Already have an account?',
    loginToRegister: 'Register now',
    registerToLogin: 'Login now',
    loginFailed: 'Login failed',
    registerFailed: 'Registration failed',
    invalidCredentials: 'Invalid username or password',
    userExists: 'Username already exists',
    verifying: 'Verifying login status...',
    inputUsername: 'Please enter username',
    inputPassword: 'Please enter password',
    inputEmail: 'Please enter email',
    usernameMinLength: 'Username must be at least 3 characters',
    passwordMinLength: 'Password must be at least 6 characters',
    passwordMaxLength: 'Password cannot exceed 50 characters',
    passwordMismatch: 'Passwords do not match',
    invalidEmail: 'Please enter a valid email address',
    loginProcessing: 'Logging in...',
    registerProcessing: 'Registering...',
  },

  // Hero
  hero: {
    title: 'Toolbox',
    subtitle: 'One-stop collection of practical tools to improve work efficiency and simplify daily tasks. From text processing to format conversion, from calculation aids to design tools, everything you need is here.',
  },

  // Categories
  categories: {
    '全部工具': 'All Tools',
    '文本工具': 'Text Tools',
    '转换工具': 'Conversion',
    '计算工具': 'Calculation',
    '设计工具': 'Design',
    '实用工具': 'Utilities',
    '开发工具': 'Dev Tools',
    'AI工具': 'AI Tools',
  },

  // Features
  features: {
    whyChoose: 'Why Choose Us',
    whyChooseDesc: 'We are committed to providing the most practical and efficient collection of tools to make complex work simple',
    efficient: 'Efficient',
    efficientDesc: 'One-click operation, no complex settings, complete tasks quickly',
    secure: 'Secure',
    secureDesc: 'Local processing, data is not uploaded, protecting your privacy',
    update: 'Continuous Updates',
    updateDesc: 'Regularly adding new tools to meet changing needs',
  },

  // Statistics
  stats: {
    toolsCount: 'Tools',
    dailyUsage: 'Daily Usage',
    uptime: 'Uptime',
    rating: 'Rating',
  },

  // Footer
  footer: {
    desc: 'One-stop collection of practical tools to improve work efficiency and simplify daily tasks.',
    toolCategories: 'Categories',
    support: 'Support',
    about: 'About Us',
    copyright: '© 2024 . All rights reserved. | ICP 12345678',
    links: {
      textTools: 'Text Tools',
      convertTools: 'Conversion Tools',
      calcTools: 'Calculation Tools',
      designTools: 'Design Tools',
      help: 'Help',
      feedback: 'Feedback',
      api: 'API',
      docs: 'Documentation',
      intro: 'Company',
      team: 'Team',
      contact: 'Contact',
      jobs: 'Careers',
    }
  },

  // Tools Data (Titles and Descriptions)
  tools: {
    'image-downloader': {
      title: 'Image Downloader',
      description: 'Paste URL to download all images from the webpage, supporting all formats',
    },
    'video-downloader': {
      title: 'Video Downloader',
      description: 'Paste URL to automatically extract and download videos, supporting MP4, WebM, HLS etc.',
    },
    'json-formatter': {
      title: 'JSON Formatter',
      description: 'Paste JSON string to format and beautify, with syntax checking and error hints',
    },
    'calendar': {
      title: 'Calendar',
      description: 'View calendar with holidays and schedule, supporting year switching',
    },
    'ai-assistant': {
      title: 'AI Assistant',
      description: 'Intelligent AI chat assistant for Q&A and content generation',
    },
    'key-generator': {
      title: 'Key Generator',
      description: 'Generate keys for various encryption algorithms like RSA, ECDSA, AES, HMAC',
    },
    'markdown-editor': {
      title: 'Markdown Editor',
      description: 'Powerful Markdown editor with live preview, syntax highlighting, and file management',
    },
    'markitdown-converter': {
      title: 'Doc to Markdown',
      description: 'Convert Word, Excel, PDF to Markdown with one click, supporting online preview and edit',
    },
    'ocr-tool': {
      title: 'OCR Text Recognition',
      description: 'Offline OCR based on Umi-OCR, supporting screenshots, batch processing, and layout analysis',
    },
    'asr-tool': {
      title: 'Speech Recognition',
      description: 'High-accuracy speech recognition based on FunASR, supporting multiple audio formats',
    },
    'database-tool': {
      title: 'Database Manager',
      description: 'Manage multiple database connections, SQL execution, schema browsing, and history',
    },
  },

  // Editor (Existing)
  editor: {
    title: 'Markdown Editor',
    edit: 'Edit',
    preview: 'Preview',
    split: 'Split',
    selectFile: 'Select a file to start editing',
    unsavedChanges: 'You have unsaved changes. Save before closing?',
    saveSuccess: 'Saved successfully',
    saveFailed: 'Save failed',
    autoSave: 'Auto Save',
  },

  // File Tree (Existing)
  fileTree: {
    title: 'Files',
    newFile: 'New File',
    newFolder: 'New Folder',
    deleteConfirm: 'Are you sure you want to delete "{name}"?',
    deleteFolder: 'Delete Folder',
    deleteFile: 'Delete File',
    renameFile: 'Rename File',
    renameFolder: 'Rename Folder',
    emptyFolder: 'Empty folder',
    noFiles: 'No files',
  },

  // Search (Existing)
  search: {
    title: 'Search',
    placeholder: 'Enter search keyword...',
    fileSearch: 'File Search',
    contentSearch: 'Content Search',
    regex: 'Regex',
    caseSensitive: 'Case Sensitive',
    noResults: 'No results found',
    searching: 'Searching...',
    results: 'Search Results',
    line: 'Line',
  },

  // Settings (Existing)
  settings: {
    title: 'Settings',
    editor: 'Editor',
    preview: 'Preview',
    general: 'General',
    theme: 'Theme',
    themeLight: 'Light',
    themeDark: 'Dark',
    fontSize: 'Font Size',
    tabSize: 'Tab Size',
    useSpaces: 'Use Spaces Instead of Tabs',
    showLineNumbers: 'Show Line Numbers',
    wordWrap: 'Word Wrap',
    showMinimap: 'Show Minimap',
    autoSaveInterval: 'Auto Save Interval (seconds)',
    previewTheme: 'Preview Theme',
    language: 'Language',
    resetDefaults: 'Reset to Defaults',
  },

  // Status Bar (Existing)
  statusBar: {
    line: 'Line',
    column: 'Col',
    saved: 'Saved',
    unsaved: 'Unsaved',
    saving: 'Saving...',
    error: 'Save Error',
    lastSaved: 'Last saved',
  },

  // Recommendations
  recommendations: {
    title: 'Popular Recommendations',
    subtitle: 'Most popular tools used by everyone',
    items: {
      pdfToWord: { title: 'PDF to Word', desc: 'High precision conversion, keeping original format' },
      imageCompress: { title: 'Image Compress', desc: 'Lossless compression, reducing file size' },
      passwordGen: { title: 'Password Generator', desc: 'Secure passwords, custom strength' },
    },
    action: 'Use Now',
  },

  // Database Tool
  database: {
    title: 'Database Manager',
    connections: 'Connections',
    addConnection: 'Add Connection',
    editConnection: 'Edit Connection',
    deleteConnection: 'Delete Connection',
    testConnection: 'Test Connection',
    connect: 'Connect',
    disconnect: 'Disconnect',
    config: {
      alias: 'Alias',
      type: 'Type',
      host: 'Host',
      port: 'Port',
      username: 'Username',
      password: 'Password',
      database: 'Database',
      env: 'Environment',
      group: 'Group',
      ssl: 'SSL Mode',
      charset: 'Charset',
      extra: 'Extra Config',
    },
    status: {
      connected: 'Connected',
      disconnected: 'Disconnected',
      testing: 'Testing...',
      success: 'Connection Successful',
      failed: 'Connection Failed',
      hiddenByFilter: 'All databases hidden by filter',
    },
    executor: {
      title: 'SQL Executor',
      run: 'Run',
      executing: 'Executing...',
      stop: 'Stop',
      clear: 'Clear',
      history: 'History',
      results: 'Results',
      noResults: 'No Results',
      affectedRows: 'Affected Rows: {count}',
      duration: 'Duration: {time}ms',
      placeholder: 'Enter SQL statement...',
    },
    schema: {
      title: 'Schema',
      tables: 'Tables',
      columns: 'Columns',
      indexes: 'Indexes',
      noTables: 'No Tables',
    },
    contextMenu: {
      editConnection: 'Edit Connection',
      testConnection: 'Test Connection',
      newDatabase: 'New Database',
      deleteConnection: 'Delete Connection',
      newTable: 'New Table',
      refresh: 'Refresh',
      deleteDatabase: 'Delete Database',
      viewData: 'View Data',
      viewStructure: 'View Structure',
      modifyStructure: 'Modify Structure',
      emptyData: 'Empty Data (Truncate)',
      deleteTable: 'Delete Table',
      confirmDeleteConnection: 'Are you sure you want to delete this connection?',
      confirmDeleteDatabase: "Are you sure you want to drop database '{name}'? This cannot be undone.",
      confirmDeleteTable: "Are you sure you want to drop table '{name}'? This cannot be undone.",
      confirmTruncateTable: "Are you sure you want to truncate table '{name}'? All data will be lost.",
      generateDDL: 'Generate DDL',
      generateAllDDL: 'Generate All DDL',
      truncateAllTables: 'Truncate All Tables',
      deleteAllTables: 'Delete All Tables',
      confirmTruncateAllTables: "Are you sure you want to truncate ALL tables in '{name}'? All data will be lost.",
      confirmDeleteAllTables: "Are you sure you want to DELETE ALL tables in '{name}'? This cannot be undone.",
    },
    dialog: {
      databaseDDL: 'Database DDL: {name}',
      createDatabase: {
        title: 'Create New Database',
        name: 'Database Name',
        charset: 'Charset',
        cancel: 'Cancel',
        create: 'Create',
        error: 'Failed to create database',
      }
    },
  },

  // Converter
  converter: {
    title: 'Document to Markdown',
    back: 'Back to Tools',
    dragDrop: 'Drag & drop your file here',
    supports: 'Supports PDF, Word, Excel, PowerPoint, HTML',
    browse: 'Browse Files',
    remove: 'Remove file',
    convert: 'Convert to Markdown',
    converting: 'Converting...',
    result: 'Markdown Result',
    copy: 'Copy',
    openInEditor: 'Open in Editor',
    copySuccess: 'Copied to clipboard!',
    openEditorConfirm: 'Markdown content copied to clipboard. Open Markdown Editor now? (You can paste it there)',
    conversionFailed: 'Conversion failed',
  },

  // Errors (Existing)
  errors: {
    networkError: 'Network error, please check your connection',
    authError: 'Authentication failed, please login again',
    fileNotFound: 'File not found',
    permissionDenied: 'Permission denied',
    saveFailed: 'Save failed',
    loadFailed: 'Load failed',
    deleteFailed: 'Delete failed',
    renameFailed: 'Rename failed',
    createFailed: 'Create failed',
    unknownError: 'Unknown error',
    toolLoadFailed: 'Failed to load tools, please try again later',
    toolSearchFailed: 'Search failed, please try again later',
    categoryLoadFailed: 'Failed to load category tools, please try again later',
    toolNotImplemented: 'Tool {toolId} is not implemented yet',
    executionFailed: 'Execution failed',
  },
};

export default enUS;
