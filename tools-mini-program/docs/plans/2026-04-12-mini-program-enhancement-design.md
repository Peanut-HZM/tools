# 小程序功能完善设计文档

## 概述

当前小程序 MVP 已完成 7 个页面（工具首页、登录、个人中心、JSON格式化、日历、密钥生成器、跨设备消息），但距离 PC 端功能完整性和移动端体验要求还有较大差距。本设计文档规划三个阶段的完善方案。

---

## 阶段一：高优先级新功能

### 1. OCR 拍照识别

**页面路径**：`/pages/ocr/index`

**功能**：
- 调用 `Taro.chooseImage` 选择照片或拍照
- 上传图片至后端 `/api/ocr/upload`
- 轮询或等待后端返回识别结果
- 展示识别文本（支持复制）
- 支持历史识别记录

**API 适配**：
- 复用 PC 端 `ocrApi`（`uploadImage` + `getResults`）
- 小程序端使用 `Taro.uploadFile` 替代 `fetch`

**UI 要点**：
- 大按钮"拍照/选图"，占屏幕主要区域
- 识别结果用等宽字体展示，支持长按复制
- 加载状态用骨架屏

### 2. 跨设备文件传输

**页面路径**：`/pages/cross-share/file/index`

**功能**：
- 文件列表展示（名称、大小、上传时间）
- 上传文件（选择本地文件 → 上传）
- 下载文件（调用系统分享或保存到相册）
- 删除文件
- 存储空间统计

**API 适配**：
- `crossShare.ts` 已有 File API：`getFiles`, `uploadFile`, `deleteFile`, `getDownloadUrl`, `getStorageStats`

**UI 要点**：
- 文件列表用列表项展示，每条带大小和时间
- 上传按钮固定在底部
- 文件类型用图标区分（图片/PDF/文档等）

### 3. HTTP API 客户端

**页面路径**：`/pages/http-client/index`

**功能**：
- URL 输入（支持完整 URL）
- 方法选择：GET / POST / PUT / DELETE / PATCH
- Headers 编辑（键值对列表，可添加/删除）
- Request Body 编辑（JSON 格式，支持格式化校验）
- 发送请求并查看响应（状态码、Headers、Body）
- 请求历史记录

**UI 要点**：
- 顶部：URL + 方法下拉，横向排列
- 中部：折叠面板 — Headers / Body
- 底部：发送按钮 + 响应区域
- 响应区域：状态码颜色提示（2xx 绿色、4xx 橙色、5xx 红色）

---

## 阶段二：中优先级 + 体验优化

### 4. ASR 语音识别

**页面路径**：`/pages/asr/index`

**功能**：
- 录音按钮（调用 `Taro.getRecorderManager`）
- 录音时长实时显示
- 上传音频至后端 `/api/asr/upload`
- 展示识别结果文本
- 支持历史记录

**API 适配**：
- 复用 PC 端 `asrApi`（`uploadAudio` + `getResults`）

**UI 要点**：
- 大圆形录音按钮，录音中变红色脉冲动画
- 实时显示录音时长（mm:ss 格式）
- 结果区域用卡片展示

### 5. 密码重置

**页面路径**：`/pages/change-password/index`

**功能**：
- 输入旧密码
- 输入新密码（带强度提示）
- 确认新密码（两次一致校验）
- 提交后自动跳转登录页

**API 适配**：
- `auth.ts` 已有 `changePassword` 方法

### 6. 工具详情页路由映射

**当前问题**：`handleToolClick` 依赖后端返回的 `tool.path`，如果后端未配置则无法跳转。

**解决方案**：
- 在 `tool.ts` 中维护 `TOOL_PATH_MAP`（已有部分映射）
- 补充所有工具的映射：OCR → `/pages/ocr/index`、ASR → `/pages/asr/index`、HTTP → `/pages/http-client/index`
- 如果映射不存在，toast 提示"该工具暂未适配移动端"

### 7. 个人中心功能接入

- "账号设置" → 接入实际的账号信息编辑页
- "修改密码" → 跳转 `/pages/change-password/index`
- "使用帮助" → 简易帮助页（使用说明 + 常见问题）
- "关于工具箱" → 版本信息 + 技术栈说明

### 8. TabBar 图标优化

- 当前图标：Python 生成的 24x24 极简占位图
- 替换为正式 SVG 图标，导出为 81x81 PNG（微信推荐尺寸）
- 三组图标：工具（齿轮/网格）、消息（对话气泡）、我的（用户头像）
- 每组包含正常态（灰色）和选中态（蓝色）

### 9. 登录页体验优化

- 登录成功后跳转回上一页（`Taro.navigateBack`），而非写死首页
- 如果无上一页，跳转工具首页
- 注册成功后自动登录

---

## 阶段三：H5 构建与浏览器预览

### 10. H5 构建配置

**Taro H5 支持**：
- `npm run dev:h5` 启动 H5 开发服务器
- `npm run build:h5` 构建 H5 生产版本

**需要解决的问题**：
1. **小程序 API 降级处理**：
   - `Taro.request` → H5 端使用 `fetch` 或 `axios`（Taro 已内置适配）
   - `Taro.chooseImage` → H5 端使用 `<input type="file">`
   - `Taro.setClipboardData` → H5 端使用 `navigator.clipboard.writeText`
   - `Taro.getStorageSync` → H5 端使用 `localStorage`
   - `Taro.uploadFile` / `Taro.downloadFile` → H5 端使用 `FormData` + `fetch`

2. **样式适配**：
   - Taro 的 `pxtransform` 插件会将 `px` 转为 `rpx`，H5 端需要确保正确转换
   - CSS 变量（`--bg-primary` 等）在 H5 端同样生效

3. **路由配置**：
   - Taro H5 默认使用 hash 路由（`/#/pages/index/index`）
   - 需要在 `config/index.ts` 的 `h5` 部分配置 `router.mode = 'hash'`

### 11. 浏览器预览验证

**验证清单**：
- 所有页面能正常渲染
- 登录/注册流程正常
- 工具首页列表正常显示
- 工具卡片点击跳转正常
- TabBar 切换正常
- JSON 格式化功能正常
- 日历功能正常
- 密钥生成器功能正常
- 消息收发功能正常
- 暗色主题样式正常
- 响应式布局正常（Chrome 开发者工具切换不同设备尺寸）

---

## 技术决策

| 决策项 | 选择 | 原因 |
|--------|------|------|
| 页面路由模式 | 主包（不分包） | 当前页面数量 < 15，无需分包 |
| OCR/ASR 上传图片方式 | `Taro.uploadFile` | 原生 API，无需额外依赖 |
| HTTP 客户端请求体格式 | 固定 JSON | 不支持 form-data，简化实现 |
| H5 路由模式 | Hash | 兼容性好，无需服务端配置 |
| TabBar 图标格式 | PNG 81x81 | 微信小程序官方推荐尺寸 |
| 密码强度校验 | 前端 + 后端双重 | 前端即时反馈，后端安全保障 |

---

## 新增页面清单

| 页面 | 路径 | 阶段 | 状态 |
|------|------|------|------|
| OCR 识别 | `/pages/ocr/index` | 阶段一 | 待开发 |
| 文件传输 | `/pages/cross-share/file/index` | 阶段一 | 待开发 |
| HTTP 客户端 | `/pages/http-client/index` | 阶段一 | 待开发 |
| ASR 语音识别 | `/pages/asr/index` | 阶段二 | 待开发 |
| 修改密码 | `/pages/change-password/index` | 阶段二 | 待开发 |
| 帮助页 | `/pages/help/index` | 阶段二 | 待开发 |

## 优化项清单

| 优化项 | 阶段 | 状态 |
|--------|------|------|
| 工具路由映射补全 | 阶段二 | 待开发 |
| 个人中心功能接入 | 阶段二 | 待开发 |
| TabBar 图标替换 | 阶段二 | 待开发 |
| 登录页跳转优化 | 阶段二 | 待开发 |
| H5 构建配置 | 阶段三 | 待开发 |
| H5 浏览器验证 | 阶段三 | 待开发 |
