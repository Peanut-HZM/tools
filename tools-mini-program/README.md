# 工具箱小程序 (tools-mini-program)

基于 Taro 4.x 的微信小程序，与 PC 端工具箱共享后端 API，提供暗色主题的工具浏览和使用体验。

## 项目简介

- **框架**: Taro 4.1 + React 18 + TypeScript
- **UI**: 暗色主题设计系统（与 PC 端一致）
- **状态管理**: Zustand 5
- **后端**: 复用 PC 工具箱 FastAPI 后端（同一套 API）

### 当前功能

| 页面 | 说明 |
|------|------|
| 工具首页 | 搜索、分类筛选、2列卡片网格导航 |
| 登录/注册 | JWT 认证，自动跳转 |
| 个人中心 | 用户信息、角色显示、退出登录 |
| JSON 格式化 | 格式化、压缩、复制 |
| 日历 | 月份切换、日期选择、回到今天 |
| 密钥生成器 | 自定义长度/字符类型、批量生成、UUID、复制 |
| 跨设备消息 | 发送/接收/删除/复制消息，设备自动注册 |
| 跨设备文件 | 文件上传/下载/删除、存储统计 |
| OCR 识别 | 拍照/选图识别、中英文切换、结果复制 |
| ASR 语音识别 | 录音识别、中英文切换、结果复制 |
| HTTP 客户端 | 多方法请求、Headers 编辑、JSON Body、响应查看 |
| 修改密码 | 旧密码校验、新密码强度检测、自动跳转登录 |
| 帮助页 | 常见问题 FAQ、版本信息 |

---

## 快速开始（适合所有人）

### 前提条件

1. 安装 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)（稳定版）

### 步骤

**1. 克隆项目**

```bash
git clone <仓库地址>
cd tools/tools-mini-program
```

**2. 安装依赖**

```bash
npm install
```

**3. 编译**

```bash
npm run build:weapp
```

**4. 导入微信开发者工具**

1. 打开「微信开发者工具」
2. 选择「导入项目」
3. 项目目录选择：`tools/tools-mini-program`
4. AppID 使用测试号或你已申请的 AppID
5. 点击「导入」

**5. 预览**

- 模拟器中直接查看效果
- 点击「预览」→ 手机微信扫码 → 真机体验

> **注意**：首次编译可能需要 1-2 分钟。如果模拟器显示空白，请等待编译完成。

---

## 开发者指南

### 环境要求

| 工具 | 版本 |
|------|------|
| Node.js | >= 18.x |
| npm | >= 9.x |
| 微信开发者工具 | 稳定版（最新） |

### 安装依赖

```bash
npm install
```

### 多环境配置

项目通过 `.env.*` 文件管理不同环境的 API 地址。Taro 编译时读取 `TARO_APP_API_URL` 变量。

| 文件 | 环境 | API 地址 | 说明 |
|------|------|----------|------|
| `.env.development` | 开发 | `http://localhost:19092/api` | 本地后端 |
| `.env.test` | 测试 | `https://tools.peanuthzm.com.cn/api` | 测试服务器 |
| `.env.production` | 生产 | `https://tools.peanuthzm.com.cn/api` | 线上服务器 |

> 文件默认不存在，需要手动创建（见下方环境变量说明）。

### 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `TARO_APP_API_URL` | 后端 API 基础地址 | `http://localhost:19092/api` |

**创建环境文件示例：**

```bash
# .env.development（本地开发）
TARO_APP_API_URL=http://localhost:19092/api

# .env.production（线上）
TARO_APP_API_URL=https://tools.peanuthzm.com.cn/api
```

### 开发命令

```bash
# 开发模式（本地后端，支持热重载）
npm run dev:weapp

# 开发模式（测试环境后端，支持热重载）
npm run dev:weapp:test

# 开发模式（生产环境后端，支持热重载）
npm run dev:weapp:prod

# 构建测试环境（生产构建，无热重载）
npm run build:weapp:test

# 构建生产环境（生产构建，无热重载）
npm run build:weapp:prod

# 仅编译（不指定环境，默认 development）
npm run build:weapp
```

#### 本地开发流程（推荐）

```bash
# 1. 确保后端服务已启动（端口 19092）
cd ../backend
uvicorn app.main:app --reload --port 19092

# 2. 启动小程序开发模式（热重载）
cd tools-mini-program
npm run dev:weapp
```

启动后，在「微信开发者工具」中打开项目，每次修改 `src/` 下的代码后：
1. Taro 会自动重新编译（终端输出 `Compiled successfully`）
2. 微信开发者工具会自动刷新模拟器，无需手动操作
3. 修改保存后约 2-5 秒即可看到最新效果

> **热重载说明**：`dev:weapp` 命令启用了 `--watch` 模式，文件保存后自动触发重新编译。如果修改后未生效，可尝试在微信开发者工具中点击「编译」按钮手动刷新。

### 目录结构

```
tools-mini-program/
├── config/                    # Taro 构建配置
│   ├── index.ts
│   ├── dev.ts
│   └── prod.ts
├── src/
│   ├── app.tsx                # 应用入口
│   ├── app.scss               # 全局样式（暗色主题变量）
│   ├── app.config.ts          # 页面路由 + TabBar 配置
│   ├── components/            # 公共组件
│   │   ├── CategoryTabs/      # 分类标签
│   │   ├── EmptyState/        # 空状态
│   │   ├── Loading/           # 加载中
│   │   ├── SearchBar/         # 搜索栏
│   │   └── ToolCard/          # 工具卡片
│   ├── pages/                 # 页面
│   │   ├── index/             # 工具首页
│   │   ├── login/             # 登录/注册
│   │   ├── profile/           # 个人中心
│   │   ├── json-formatter/    # JSON 格式化
│   │   ├── calendar/          # 日历
│   │   ├── key-generator/     # 密钥生成器
│   │   ├── cross-share/       # 跨设备共享
│   │   │   ├── message/       # 消息列表
│   │   │   └── file/          # 文件传输
│   │   ├── ocr/               # OCR 图片识别
│   │   ├── asr/               # ASR 语音识别
│   │   ├── http-client/       # HTTP API 客户端
│   │   ├── change-password/   # 修改密码
│   │   └── help/              # 帮助与关于
│   ├── services/              # API 服务层
│   │   ├── request.ts         # Taro.request 封装（含上传下载）
│   │   ├── auth.ts            # 认证相关 API
│   │   ├── tool.ts            # 工具列表 API
│   │   └── crossShare.ts      # 跨设备共享 API（消息/文件/设备）
│   ├── stores/                # Zustand 状态管理
│   │   ├── auth.ts            # 登录状态
│   │   └── device.ts          # 设备状态
│   ├── types/                 # TypeScript 类型
│   └── utils/                 # 工具函数
├── project.config.json        # 微信小程序项目配置
├── babel.config.js            # Babel 配置
├── tsconfig.json              # TypeScript 配置
└── package.json
```

---

## H5 构建与浏览器预览

小程序基于 Taro 框架，支持构建 H5 版本在浏览器中预览。

### H5 开发模式

```bash
# 启动 H5 开发服务器（支持热重载）
npm run dev:h5

# 启动后访问 http://localhost:10086 在浏览器查看
```

### H5 生产构建

```bash
# 构建 H5 生产版本
npm run build:h5

# 构建产物在 dist/ 目录，可直接部署到静态服务器
```

> **注意**：H5 版本使用 Hash 路由模式（`/#/pages/index/index`），兼容性好，无需服务端配置。部分小程序专属 API（如拍照、录音）在 H5 端会自动降级或不可用。

---

## 部署指南

### 1. 构建生产版本

```bash
npm run build:weapp -- --env-mode production
```

### 2. 上传代码

1. 在微信开发者工具中确认编译产物在 `dist/` 目录
2. 点击右上角「上传」按钮
3. 填写版本号和项目备注
4. 点击「上传」

### 3. 提交审核

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)
2. 进入「版本管理」→ 找到刚上传的版本
3. 填写版本信息、选择功能页面
4. 点击「提交审核」

### 4. 发布上线

审核通过后，在「版本管理」中点击「发布」即可。

---

## 常见问题

### 编译失败

```
# 清理缓存重新编译
rm -rf dist
npx taro build --type weapp
```

### 接口请求失败

1. 确认 `.env.*` 文件中的 `TARO_APP_API_URL` 正确
2. 小程序真机调试需在微信公众平台配置「服务器域名」
3. 开发阶段可在微信开发者工具中勾选「不校验合法域名」

### 端口被占用

Taro 编译使用 webpack，不会占用 API 端口。如果后端服务未启动，请先启动后端：

```bash
cd ../backend
uvicorn app.main:app --reload --port 19092
```

### 体验版过期

微信小程序体验版默认有效期为 14 天。过期后需重新上传新版本并设置为体验版。
