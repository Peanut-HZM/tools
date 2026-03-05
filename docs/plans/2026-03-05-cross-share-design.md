# 跨设备消息文件共享工具设计文档

**创建日期:** 2026-03-05
**产品名称:** CrossShare / 设备传传
**版本:** 1.0

---

## 项目概述

### 目标
实现一个基于账号系统的跨设备消息和文件共享工具，让用户在同一账号下的不同设备之间方便地传递消息和文件。

### 产品定位
- **名称:** CrossShare / 设备传传
- **Slogan:** 跨设备传输，从未如此简单
- **核心价值:** 无需配对，登录即用，全平台同步

---

## 功能需求

### 一、消息功能

#### 1.1 文本消息
- 支持发送文本消息（最大 10000 字符）
- 支持 Markdown 格式渲染
- 支持链接自动解析（显示预览卡片）
- 支持消息回复/引用

#### 1.2 文件附件
- 单文件最大可配置（默认 100MB）
- 支持拖拽上传
- 显示上传进度
- 上传完成后自动附加到消息

#### 1.3 剪贴板同步
- 一端复制，自动同步到云端
- 另一端可粘贴获取
- 支持加密存储
- 保留最近 100 条剪贴板历史

#### 1.4 消息分类
| 类型 | 图标 | 说明 |
|------|------|------|
| text | 📝 | 纯文本消息 |
| file | 📎 | 文件消息 |
| link | 🔗 | 链接分享 |
| clipboard | 📋 | 剪贴板 |
| image | 🖼️ | 图片消息 |

### 二、文件管理

#### 2.1 文件列表
- 按时间倒序排列
- 支持分页加载
- 支持搜索（文件名）
- 支持筛选（文件类型、日期范围）
- 支持排序（时间/大小/名称）

#### 2.2 自动分类
| 分类 | 扩展名示例 |
|------|-----------|
| 🖼️ 图片 | jpg, png, gif, webp, svg |
| 📄 文档 | pdf, doc, docx, xls, xlsx, ppt, pptx |
| 🎬 视频 | mp4, mov, avi, mkv, webm |
| 🎵 音频 | mp3, wav, flac, aac, ogg |
| 📦 压缩包 | zip, rar, 7z, tar, gz |
| 📝 文本 | txt, md, json, csv |
| 📦 其他 | 其他所有类型 |

#### 2.3 文件预览
- 图片：在线预览，支持缩放
- 文本：快速查看内容
- PDF：内嵌预览（如可能）
- 视频/音频：在线播放

#### 2.4 文件回收站
- 删除的文件进入回收站
- 回收站保留 30 天
- 支持恢复
- 支持清空回收站

#### 2.5 存储空间统计
- 显示已用空间
- 显示总配额
- 显示各类文件占比（饼图）
- 空间不足时提醒

### 三、设备管理

#### 3.1 设备列表
- 显示设备名称
- 显示设备类型（桌面/移动/平板）
- 显示最后活跃时间
- 显示设备状态（在线/离线）

#### 3.2 设备操作
- ✏️ 重命名设备
- 🚫 设备下线/解绑
- ✅ 设备验证（新设备登录需要验证）
- 📱 查看设备详情（IP、地理位置等）

#### 3.3 设备识别
- 自动识别设备类型（User-Agent）
- 自动生成设备名称（如 "Chrome on Mac"）
- 支持自定义设备名称

### 四、安全功能

#### 4.1 端到端加密（可选）
- 使用 AES-256-GCM 加密
- 密钥由用户密码派生
- 服务器无法解密内容

#### 4.2 消息过期
- 可配置消息过期时间
- 过期后自动删除
- 支持永久保存

#### 4.3 文件访问控制
- 文件访问令牌
- 临时下载链接（限时）
- 防止盗链

#### 4.4 文件类型过滤
- 黑名单：禁止可执行文件（exe, bat, sh 等）
- 白名单模式（可选）
- 病毒扫描（可选，后续迭代）

---

## 数据模型设计

### Device (设备表)
```python
class Device(Base):
    id = Column(UUID, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    device_name = Column(String, nullable=False)
    device_type = Column(String)  # desktop/mobile/tablet
    device_token = Column(String, unique=True)
    user_agent = Column(String)
    ip_address = Column(String)
    is_active = Column(Boolean, default=True)
    last_seen_at = Column(DateTime)
    created_at = Column(DateTime)
```

### CrossMessage (消息表)
```python
class CrossMessage(Base):
    id = Column(UUID, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    from_device_id = Column(UUID, ForeignKey('devices.id'))
    content = Column(Text)
    message_type = Column(String)  # text/file/link/clipboard/image
    file_id = Column(UUID, ForeignKey('cross_files.id'), nullable=True)
    is_encrypted = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime)
```

### CrossFile (文件表)
```python
class CrossFile(Base):
    id = Column(UUID, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    upload_device_id = Column(UUID, ForeignKey('devices.id'))
    oss_bucket = Column(String)
    oss_key = Column(String)
    oss_url = Column(String)
    file_name = Column(String)
    file_size = Column(Integer)
    file_type = Column(String)  # image/document/video/audio/archive/other
    file_hash = Column(String, index=True)  # 用于去重
    download_count = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime)
```

### CrossShareConfig (配置表)
```python
class CrossShareConfig(Base):
    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True, nullable=False)
    max_file_size = Column(Integer, default=104857600)  # 100MB
    storage_quota = Column(Integer, default=5368709120)  # 5GB
    file_expire_days = Column(Integer, default=30)
    enable_encryption = Column(Boolean, default=False)
    enable_clipboard = Column(Boolean, default=True)
    allowed_file_types = Column(Text)  # JSON 格式存储
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

---

## API 接口设计

### 设备管理
```
GET    /api/cross-share/devices              # 获取设备列表
POST   /api/cross-share/devices              # 注册/更新设备
PUT    /api/cross-share/devices/{id}         # 更新设备名称
DELETE /api/cross-share/devices/{id}         # 删除设备
POST   /api/cross-share/devices/{id}/ping    # 更新设备活跃时间
```

### 消息功能
```
GET    /api/cross-share/messages             # 获取消息列表
POST   /api/cross-share/messages             # 发送消息
DELETE /api/cross-share/messages/{id}        # 删除消息
GET    /api/cross-share/messages/clipboard   # 获取剪贴板历史
POST   /api/cross-share/messages/clipboard   # 同步剪贴板
```

### 文件功能
```
GET    /api/cross-share/files                # 获取文件列表
POST   /api/cross-share/files/upload         # 上传文件（获取 OSS token）
GET    /api/cross-share/files/{id}           # 获取文件详情
DELETE /api/cross-share/files/{id}          # 删除文件
POST   /api/cross-share/files/{id}/download # 生成下载链接
GET    /api/cross-share/files/stats          # 获取存储统计
POST   /api/cross-share/files/{id}/preview   # 获取文件预览
```

### 配置
```
GET    /api/cross-share/config               # 获取用户配置
PUT    /api/cross-share/config               # 更新配置
```

### 管理后台
```
GET    /api/admin/cross-share/stats          # 全局统计
GET    /api/admin/cross-share/config         # 获取全局配置
PUT    /api/admin/cross-share/config         # 更新全局配置
```

---

## 前端组件设计

### 页面结构
```
frontend/src/components/Tools/CrossShare/
├── CrossShareMain.tsx       # 主容器组件
├── Header.tsx               # 顶部标题和存储统计
├── Sidebar.tsx              # 侧边栏导航
├── MessagePanel.tsx         # 消息时间线面板
├── FilePanel.tsx            # 文件管理面板
├── DevicePanel.tsx          # 设备管理面板
├── SettingsPanel.tsx        # 设置面板
├── MessageInput.tsx         # 消息输入框（支持拖拽）
├── MessageList.tsx          # 消息列表
├── MessageItem.tsx          # 单条消息展示
├── FileUploader.tsx         # 文件上传组件
├── FileList.tsx             # 文件列表
├── FileItem.tsx             # 单文件展示
├── FilePreview.tsx          # 文件预览
├── DeviceManager.tsx        # 设备管理
├── StorageStats.tsx         # 存储空间统计
└── ClipboardSync.tsx        # 剪贴板同步
```

### UI 布局
```
┌────────────────────────────────────────────────────────┐
│  [Logo] CrossShare 设备传传      [存储空间：2.1GB/5GB]  │
├────────────┬───────────────────────────────────────────┤
│            │                                           │
│  📋 消息    │           主内容区                         │
│  📁 文件    │                                           │
│  📱 设备    │   - 消息时间线 / 文件列表 / 设备管理        │
│  ⚙️ 设置    │                                           │
│            │                                           │
│            │                                           │
└────────────┴───────────────────────────────────────────┘
```

### 颜色主题
- Primary: #6366f1 (靛蓝色)
- Secondary: #10b981 (绿色)
- Background: #0f172a (深蓝灰，与现有主题一致)
- Card: #1e293b (浅蓝灰)

---

## 技术实现方案

### 后端技术栈
- **框架:** FastAPI (复用现有)
- **ORM:** SQLAlchemy (复用现有)
- **数据库:** SQLite/PostgreSQL (复用现有)
- **文件存储:** 阿里云 OSS (复用现有 OSS 服务)
- **认证:** JWT (复用现有 auth 系统)

### 前端技术栈
- **框架:** React 18 + TypeScript (复用现有)
- **样式:** Tailwind CSS (复用现有)
- **HTTP:** Axios (复用现有)
- **状态管理:** Zustand (复用现有)
- **文件上传:** 自定义分片上传

### 关键技术点

#### 1. 文件上传流程
```
1. 前端请求上传凭证 (OSS token)
2. 后端返回 OSS token 和 bucket 信息
3. 前端直传 OSS (分片上传)
4. 上传完成后通知后端，创建文件记录
5. 后端可选：触发病毒扫描、生成缩略图等
```

#### 2. 消息推送
- **方案 A:** WebSocket 实时推送（推荐）
- **方案 B:** 轮询（简单，每 5 秒）
- **方案 C:** SSE (Server-Sent Events)

初期使用轮询方案，后续可升级为 WebSocket。

#### 3. 文件去重
```
1. 上传前计算文件 hash (MD5/SHA256)
2. 查询数据库中是否已存在相同 hash
3. 如存在，直接引用已有文件记录（秒传）
4. 如不存在，正常上传
```

#### 4. 端到端加密
```
1. 用户登录时，由密码派生加密密钥
2. 发送端使用密钥加密消息/文件
3. 接收端使用密钥解密
4. 服务器只存储密文
```

---

## 项目结构

```
backend/
├── app/
│   ├── models/
│   │   └── cross_share.py         # 数据模型
│   ├── schemas/
│   │   └── cross_share.py         # Pydantic 模型
│   ├── services/
│   │   └── cross_share_service.py # 业务逻辑
│   ├── routes/
│   │   └── cross_share.py         # API 路由
│   └── utils/
│       └── oss_utils.py           # OSS 工具（已有则复用）

frontend/
├── src/
│   ├── components/
│   │   └── Tools/
│   │       └── CrossShare/
│   │           ├── CrossShareMain.tsx
│   │           ├── Header.tsx
│   │           ├── Sidebar.tsx
│   │           ├── MessagePanel.tsx
│   │           ├── FilePanel.tsx
│   │           ├── DevicePanel.tsx
│   │           ├── SettingsPanel.tsx
│   │           ├── MessageInput.tsx
│   │           ├── MessageList.tsx
│   │           ├── MessageItem.tsx
│   │           ├── FileUploader.tsx
│   │           ├── FileList.tsx
│   │           ├── FileItem.tsx
│   │           ├── FilePreview.tsx
│   │           ├── DeviceManager.tsx
│   │           ├── StorageStats.tsx
│   │           └── ClipboardSync.tsx
│   └── services/
│       └── crossShare.ts          # API 服务
```

---

## 配置项设计

### 用户配置（每用户）
| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| max_file_size | 100MB | 单文件最大大小 |
| storage_quota | 5GB | 总存储配额 |
| file_expire_days | 30 | 文件过期天数 |
| enable_encryption | false | 启用端到端加密 |
| enable_clipboard | true | 启用剪贴板同步 |
| allowed_file_types | * | 允许的文件类型 |

### 全局配置（管理后台）
| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| global_max_file_size | 500MB | 全局最大文件大小 |
| global_storage_quota | 10GB | 全局最大存储配额 |
| file_blacklist | exe,bat,sh | 禁止的文件类型 |
| enable_virus_scan | false | 启用病毒扫描 |

---

## 时间估算

| 阶段 | 任务 | 估算时间 |
|------|------|----------|
| 1 | 后端数据模型和 API | 4-5 小时 |
| 2 | OSS 文件上传服务集成 | 2-3 小时 |
| 3 | 前端主页面框架 | 2-3 小时 |
| 4 | 消息功能（发送/接收/列表） | 2-3 小时 |
| 5 | 文件管理（上传/下载/预览） | 3-4 小时 |
| 6 | 设备管理功能 | 2-3 小时 |
| 7 | 设置和配置管理 | 1-2 小时 |
| 8 | 测试和优化 | 2-3 小时 |
| **总计** | | **18-26 小时** |

---

## 成功标准

1. ✅ 用户可以成功登录并看到设备列表
2. ✅ 用户可以发送文本消息和文件
3. ✅ 消息和文件在设备间同步
4. ✅ 文件可以正常上传和下载
5. ✅ 存储空间统计准确
6. ✅ 设备可以正常解绑
7. ✅ 文件预览功能正常
8. ✅ 剪贴板同步功能正常

---

## 后续迭代

- [ ] WebSocket 实时消息推送
- [ ] 文件病毒扫描
- [ ] 文件版本管理
- [ ] 分享链接给非登录用户
- [ ] 批量操作（批量删除、批量下载）
- [ ] 文件标签系统
- [ ] 搜索功能增强（全文搜索）
- [ ] 移动端适配优化
