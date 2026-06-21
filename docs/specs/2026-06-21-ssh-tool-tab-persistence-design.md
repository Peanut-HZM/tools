---
author: peanut
created_at: 2026-06-21
purpose: SSH 工具页面 Tab 化与会话持久化优化设计
---

# SSH 工具 Tab 化与会话持久化优化设计

## 1. 背景与目标

当前 `/tools/ssh-tool` 页面结构为"左列表 + 右单例终端":
- 右侧只渲染一个 `TerminalPanel`,绑定当前 `selectedConfigId`。
- 切换左侧连接时,旧 WebSocket 被 `disconnect()`、xterm 被 `clear()`,上一个会话直接断开。
- 同一连接无法同时开多个独立会话。

### 1.1 优化目标

- **多 Tab**:每次点击左侧任意 SSH 连接,都在右侧新打开一个 tab 页签(同一连接可开多个独立会话)。
- **会话保活**:连接建立后,无论是否闲置、无论是否切换 tab,只要浏览器窗口未关闭,SSH 会话必须保持存活。
- **后台输出**:后台 tab 的终端持续接收输出,切回来时已是最新状态。
- **上限控制**:全局最多 20 个 tab;达到上限阻止新开并 toast 提示,不自动关闭旧 tab。
- **生命周期对齐 tab**:关闭 tab = 断开该 SSH 会话;关闭浏览器 = 所有会话断开。
- **页面刷新语义**:F5 刷新页面视为"小关闭",不恢复 tab;用户需重新点开。

## 2. 架构总览

整体栈不变(FastAPI WebSocket + paramiko + xterm)。核心改动:

- `SSHTool`:从"单选模式"升级为"tab 列表管理",维护 `tabs: SSHSessionTab[]` 与 `activeTabId`。
- `TerminalPanel`:从单例变为每个 tab 一个实例,所有 panel 都保留在 DOM 中,激活的显示、其余 `display: none`,不随 tab 切换卸载。
- 新增 `TabBar` 组件:横向滚动的 tab 行,负责切换、关闭、计数。
- 后端 `handle_ssh_session`:新增心跳保活,修复 `send_to_client` 的 10ms 忙等待。

### 2.1 组件关系

```text
SSHTool
├── ConnectionList (左侧列表,点击 → 新增 tab)
├── TabBar (新增:tab 行,支持切换/关闭/计数)
├── TerminalContainer
│   └── TerminalPanel[] (每个 tab 一个 xterm + WebSocket,常驻 DOM)
└── ConnectionModal
```

## 3. 前端数据模型与状态机

### 3.1 Tab 模型

```typescript
interface SSHSessionTab {
  tabId: string;       // 前端唯一 id(uuid / nanoid)
  configId: string;    // 对应 SSHConfig.id
  configSnapshot: {    // 打开时的快照(防编辑后标题变)
    alias: string;
    host: string;
    port: number;
    username: string;
  };
  createdAt: number;
}
```

### 3.2 全局状态

- `tabs: SSHSessionTab[]`:tab 列表,TabBar 与 TerminalPanel 列表的唯一源。
- `activeTabId: string | null`:当前激活的 tab。
- `MAX_TABS = 20`:全局上限,超过时 toast 提示并阻断新开。

### 3.3 Tab 生命周期状态(由 TerminalPanel 自管理)

- `connecting` → `connected`:连接成功。
- `connected` → `error`:WebSocket 异常断开或心跳超时。
- `connected` / `error` / `disconnected` → 卸载:用户点击 `×` 关闭。

## 4. TabBar 交互

### 4.1 布局

- 水平滚动的 tab 行,位于 TerminalContainer 上方。
- 每个 tab 显示:`[●] alias (user@host:port)` + `[×]`。
- 右端显示计数:`3 / 20`。
- `tabs.length === 0` 时,TerminalContainer 居中显示图标 + "点击左侧连接开始终端会话"空态。
- tab 较多时横向滚动,激活的 tab 始终滚动到可视区。

### 4.2 状态点颜色

- `connected` → 绿点
- `connecting` → 黄点(脉动动画)
- `error` / `disconnected` → 红点 / 灰点

### 4.3 交互行为

- **单击 tab**:切换为 active(置为可见),不重连、不清内容。
- **单击红点 / 错误态 tab 本体**:重试该 tab 的 SSH 连接(重开新 WebSocket,不恢复旧会话)。
- **单击 ×**:关闭该 tab。`connected` 状态弹确认;"确定要断开此 SSH 会话并关闭标签页吗?"+ `[取消] [断开并关闭]`;取消则保持 tab 原样;`disconnected` / `error` 状态直接关闭,不弹确认。
- **中键点击 / Ctrl+点击**:同单击 ×。
- **关闭 active tab**:自动激活紧邻右侧的 tab;若已是最后一个则激活左侧;若只剩一个回到空态。

### 4.4 上限控制

点击侧边栏连接时若 `tabs.length >= MAX_TABS`:
- 不打开新 tab。
- toast 提示 `t.ssh.tabLimitReached`。

### 4.5 本期不做

- 拖拽重排
- 右键菜单
- 双击重命名

## 5. TerminalPanel 生命周期与保活

### 5.1 挂载策略

- 组件在 tab 创建时挂载,tab 关闭时卸载。
- 所有 panel 常驻 DOM,激活的 `display: block`,其余 `display: none`。
- tab 切换不触发 mount / unmount。

### 5.2 Fit 时序

- `window.resize`:所有 panel 的 `FitAddon.fit()` 被调用(对 hidden 的 panel 无副作用)。
- tab 切换为 active:下一帧补一次 `fit()` 并发送 `{type: "resize", cols, rows}`。
- 连接刚建立时发送初始 `resize`。

### 5.3 WebSocket 与输出接收

- tab 创建后,`useEffect` 立即建立 WebSocket,`socket.onopen` 发初始 `resize`。
- `socket.onmessage` 始终把数据 `terminal.write()` 进 xterm,即使 tab 非 active。
- WebSocket 与 xterm 实例持续存活,无论 tab 是否 active。

### 5.4 心跳保活

- **后端 → 前端**:后端每 30s 发 `{"type": "pong"}`。
- **前端判活**:前端收到任何 WS 数据(SSH 输出或 pong)算活跃;连续 **90s** 无数据判定死亡,主动 `socket.close()` 并进入 `error` 状态,TabBar 红点,用户点击可重试。
- **SSH Transport**:`ssh.connect()` 成功后立即 `ssh.get_transport().set_keepalive(30)`,paramiko 每 30s 向 SSH server 发 keepalive,防止被 server TCP idle timeout 切断。

### 5.5 断开与清理

- 用户点击 `×` → `TerminalPanel.disconnect()`(`socket.close()`)→ tab 从 `tabs` 移除 → React 卸载 → `useEffect` cleanup 清理 timer、dispose xterm、remove listener。
- 浏览器窗口关闭:浏览器自动 close 所有 WebSocket,后端每个 session 捕获 `WebSocketDisconnect` → finally `ssh.close()`。

### 5.6 重连语义

- `error` 状态点击重试:用同样的 `configId` 重开 WebSocket,后端建立**新的** SSH 会话,旧会话已断开。
- 重连**不是恢复**旧会话,而是新开(SSH 本身不支持跨 WebSocket 恢复)。

### 5.7 xterm 缓冲

- `scrollback: 1000`(xterm 默认值)。多 tab 长期 `tail -f` 若出现内存压力,后续可调到 `5000` 上限或提示用户关闭部分 tab。本期保持默认。

## 6. 后端心跳保活与并发

### 6.1 心跳协议

- **后端主动发 pong**:每个 WebSocket session 启动一个 `asyncio.create_task`,每 30s `websocket.send_text(json.dumps({"type": "pong"}))`。
- **前端不发 ping**:简化实现。后端只发 pong,前端以"最近 90s 收到任何数据"为活跃判定。

### 6.2 修复 send_to_client 忙等待

当前 `if not recv_ready: await asyncio.sleep(0.01)` 单协程 10ms 轮询。多 tab 并发时 CPU 占用显著。改为:
- 使用 `asyncio.get_event_loop().run_in_executor(None, channel.recv, 4096)`,让 paramiko 的阻塞 `recv` 在 executor 里运行,超时或返回数据后再进入下一轮。
- 或设置 `channel.settimeout(5.0)` + 捕获 `socket.timeout` 后继续循环。

推荐:使用 `run_in_executor` + `channel.settimeout`,避免 10ms 忙等待。

### 6.3 并发连接

- 前端 20 tab 上限已经兜底,后端本期**不做**额外并发限制。
- 记录日志:每个新连接记 `INFO SSH session started: user_id / config_id`,关闭记 `INFO SSH session closed`。

### 6.4 错误消息推送

- SSH 连接失败(密码错、host 不通等):后端先 `websocket.send_text(json.dumps({"type": "error", "message": "..."}))`,再 `websocket.close(code=4000)`。
- 这样前端能拿到具体原因,不依赖浏览器对 close reason 的支持。
- 服务端主动关闭 SSH(exit / channel close):后端发 `{"type": "exit"}` 后主动 close;前端 `TerminalPanel` 收到该消息后把 tab 状态改为 `disconnected`(而非 `error`),TabBar 显示灰点,用户点击可重连。

### 6.5 WebSocket 断开

- 前端正常关或浏览器窗口关闭:后端 `receive_from_client` 捕获 `WebSocketDisconnect` break → `gather` 结束 → finally `ssh.close()` 释放 TCP。
- 服务端主动关闭 SSH(网络断 / sshd 拒绝):`send_to_client` 中 `recv` 返回空 → break → finally。

## 7. 错误场景处理

| 场景 | 处理方式 |
|------|----------|
| 服务端 SSH 连接失败 | 后端发 `{"type": "error", "message": "..."}` 后 close;前端 TabBar 红点,Tooltip 显示原因,点击重试 |
| WebSocket 意外断开(网络断、服务重启) | 前端 `onclose` 非 1000 code,TabBar 置 `error`,**不自动重连**,点击重试或 `×` |
| 服务端主动关闭 SSH(exit / 服务端 close) | 后端发 `{"type": "exit"}` 后 close;前端 Tab 状态改 `disconnected`(灰点),点击可重连 |
| 心跳超时(90s 无数据) | 前端主动 `socket.close()` 并置 `error` |
| 页面刷新(F5) | 所有 tab 消失,不恢复(等价"小关闭") |
| 浏览器窗口关闭 | 浏览器自动 close 所有 WebSocket,后端 finally 释放所有 SSH TCP |

## 8. i18n 补全

同时更新 `frontend/src/i18n/locales/zh-CN.ts` 和 `en-US.ts` 的 `ssh:` 块:

| key | zh-CN | en-US |
|-----|-------|-------|
| `tabLimitReached` | 最多保留 20 个 SSH 会话,请先关闭其他会话 | Maximum 20 SSH sessions, close others first |
| `confirmCloseTab` | 确定要断开此 SSH 会话并关闭标签页吗? | Disconnect this SSH session and close the tab? |
| `retryConnection` | 重试 | Retry |
| `closeTab` | 关闭标签 | Close tab |
| `connectionTimeout` | 连接超时,请重试 | Connection timed out, please retry |
| `sessionDisconnected` | 会话已断开 | Session disconnected |
| `connectionError` | 连接失败: {reason} | Connection failed: {reason} |
| `tabCount` | {count} / {max} | {count} / {max} |

## 9. 测试策略

### 9.1 前端单元测试(Vitest + React Testing Library)

- `TabBar`:
  - 渲染正确的 tab 数量与顺序
  - 点击 tab 切换 active
  - 点击 × 触发 onClose,`connected` 状态弹确认
  - `20 / 20` 计数显示
  - Tab 状态点颜色对应正确
- `SSHTool`:
  - 点击侧边栏新连接 → `tabs` 新增一项
  - 重复点击同一连接 → 每次都新增独立 tab
  - 达到 20 个时再点 → toast 提示,tab 数不变
  - 关闭 active tab 后自动激活相邻 tab
  - 关闭最后一个 tab 时回到空态
- `TerminalPanel`:
  - mock WebSocket → 连接成功 / 失败 / 断开三种状态正确切换
  - 90s 无数据判定死亡(用 fake timers 测试)
  - `window.resize` 触发 fit

### 9.2 后端单元测试

- `handle_ssh_session` 30s 后发出 `pong`
- WebSocket 断开后 `ssh.close()` 被调用(mock paramiko)
- SSH 连接失败时推送 `{"type": "error"}` 消息再 close

### 9.3 端到端手动验证(按 CLAUDE.md 要求使用浏览器)

- 登录 → 点侧边栏连接 → 看到新 tab 出现并绿点
- 输入命令,切换 tab 后回来,终端输出完整保留
- 闲置 10 分钟(可用 fake idle 或实际等待)后回来仍活着
- 开 20 个 tab 后再点侧边栏,toast 提示
- 关闭某 tab → 关闭浏览器窗口 → 服务端日志显示所有 session 已清理

## 10. 范围外 / 后续可考虑

- F5 刷新后恢复 tab(需后端 session 持久化 + 前端 sessionStorage 记录)
- 拖拽重排 / 右键菜单 / 双击重命名
- 后端并发上限加固
- xterm scrollback 动态调整
- 同一连接共享 Transport 连接池(节省 TCP 连接,但违反"独立会话"语义)
- 单 WebSocket 多路复用(过度工程,收益不大)

## 11. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 20 tab 全 `tail -f` 内存压力 | xterm scrollback 默认 1000;必要时调上限或提示用户关 tab |
| 20 个并发 SSH TCP 连接对 sshd 压力 | 典型 sshd `MaxStartups 10:30:100`,20 个远在上限内 |
| `display: none` 导致 resize 失真 | 切回 active 时补一次 fit + resize 消息 |
| 浏览器限制单域名 WebSocket 数 | Chrome 上限 ~200+,20 tab 安全 |
| 中间代理 TCP idle timeout | 双向心跳(后端 30s pong + paramiko 30s keepalive) |
