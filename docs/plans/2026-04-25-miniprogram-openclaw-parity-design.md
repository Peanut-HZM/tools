# 小程序 OpenClaw 功能与 Web 前端保持一致 设计

**目标：** 小程序 OpenClaw 聊天功能与 Web 前端完全一致

**方案：** 直接复用 Web 前端已验证的实现逻辑，移植到 Taro 小程序框架

**涉及文件：**
- `tools-mini-program/src/pages/openclaw/index.tsx`
- `tools-mini-program/src/pages/openclaw/index.scss`
- `tools-mini-program/src/services/openclaw.ts`

---

## 当前问题

1. **消息重复**：`chatStream` onChunk 使用 `last.content + chunk` 追加，但后端发送完整内容
2. **缺少历史消息**：页面未调用 `loadHistory`
3. **未过滤非内容文本**：thinking、bootstrap 提示、时间戳混在消息中
4. **缺少连接状态引导**：未连接时没有提示用户去配置
5. **缺少时间戳显示**：消息没有独立的时间标签

## 移植清单

### 1. 内容过滤（extractText）

复用 Web 前端的 `extractText` 逻辑：
- 过滤 `thinking` 类型内容
- 过滤/去掉 `[Bootstrap pending]` 提示（找到时间戳位置，去掉前面所有内容）
- 过滤/去掉 `[Sat 2026-04-25 ... GMT+8]` 时间戳前缀
- 处理 `content` 为字符串、对象、数组的多种情况

### 2. 历史消息加载

在 `useDidShow` 中调用 `loadHistory`，格式化后 `setMessages`：
- 跳过 `toolResult` 角色
- 使用 `extractText` 提取内容
- 过滤空内容消息
- role 映射：`user` → `user`，其他 → `assistant`

### 3. 消息去重

修改 `chatStream` onChunk：
- Web 端：`content: chunk`（替换）
- 小程序当前：`last.content + chunk`（追加）→ 改为替换

### 4. 连接状态

添加 `isLoading` 状态：
- 页面初始化时显示 loading
- 检查连接状态
- 未连接时显示引导提示（同 Web 端的"服务未连接，请前往管理面板配置"）

### 5. 时间戳显示

在消息气泡下方添加 `HH:mm` 格式时间标签：
- 用户消息右对齐
- AI 消息左对齐

### 6. 错误处理

加载历史失败时静默处理（不弹 toast），避免打扰用户。
