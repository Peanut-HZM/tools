---
author: Claude
created_at: 2026-06-25
purpose: GLM-Coding Pro 抢购工具增强版设计方案，消除所有虚假判断，确保结果真实可追溯
---

# GLM-Coding Pro 抢购工具增强版设计方案

## 一、项目背景

当前 GLM-Coding Pro 抢购工具存在多个"虚假判断"问题：
1. 登录态检测使用"负面检测"（没发现未登录特征就认为已登录），容易误判
2. 抢购成功判断有兜底逻辑（未检测到支付页跳转就用当前 URL 作为 payment_url）
3. 存在"测试模式"，可能在非抢购时间误判
4. 配置存在内存中，重启后丢失
5. 日志通过轮询获取，实时性差

**核心目标**：消除所有虚假判断，确保每个关键步骤都有真实验证和可追溯证据。

---

## 二、整体架构

```
前端 (React)
  ↓ WebSocket (实时日志推送)
后端 (FastAPI)
  ↓
抢购服务 (增强版)
  ├─ 登录态检测模块 (正面检测)
  ├─ 时间窗口控制器 (10 分钟限制)
  ├─ 按钮检测与点击
  ├─ 支付页验证模块 (双重检测)
  ├─ 截图管理器 (关键步骤截图)
  ├─ 错误重试管理器 (3 次重试)
  ├─ 配置持久化服务 (数据库)
  └─ WebSocket 推送器
```

**数据流**：
1. 用户配置 → 保存到数据库 → 启动抢购任务
2. 任务执行 → 实时日志通过 WebSocket 推送到前端
3. 关键步骤 → 自动截图保存到 `backend/data/glm_coding_rusher/screenshots/`
4. 抢购结果 → 双重验证 → 真实反馈给用户

**新增依赖**：
- FastAPI WebSocket（内置，无需额外安装）
- SQLite 配置表（已定义，直接使用）

---

## 三、核心模块设计

### 3.1 登录态检测模块

**改进**：从"负面检测"改为**正面检测**——必须检测到明确的已登录特征才算已登录。

**已登录特征**：
```python
LOGIN_INDICATORS = [
    "img.avatar",
    "img[alt*='头像']",
    ".user-name",
    ".user-email",
    "[class*='user-info']",
    "button:has-text('我的账户')",
    "button:has-text('个人中心')",
    "a:has-text('退出登录')",
]
```

**检测逻辑**：
- 检测到至少一个特征才算已登录
- 异常情况一律视为未登录（不再兜底）
- 登录成功时自动截图保存证据

---

### 3.2 抢购成功判断模块

**改进**：采用**双重检测**——URL 变化 + 支付页特征，缺一不可。

**支付页特征**：
```python
# URL 关键词
PAYMENT_URL_KEYWORDS = [
    "payment", "order", "checkout", "confirm", "pay", "billing",
]

# 页面内容关键词
PAYMENT_PAGE_INDICATORS = [
    "订单确认", "支付", "付款", "金额", "订单详情", "请选择支付方式",
]
```

**验证逻辑**：
```python
def _verify_payment_page(page, original_url: str) -> dict:
    current_url = page.url
    url_changed = current_url != original_url
    
    # 检测 1: URL 关键词匹配
    url_matched = any(keyword in current_url.lower() for keyword in PAYMENT_URL_KEYWORDS)
    
    # 检测 2: 页面内容匹配
    content_matched = [indicator for indicator in PAYMENT_PAGE_INDICATORS if indicator in body_text]
    
    # 双重检测：URL 必须变化 + (URL 关键词 OR 页面内容)
    is_payment_page = url_changed and (url_matched or len(content_matched) > 0)
    
    return {
        "is_payment_page": is_payment_page,
        "current_url": current_url,
        "url_changed": url_changed,
        "payment_indicators": content_matched,
        "evidence": f"URL变化={url_changed}, URL关键词={url_matched}, 页面特征={content_matched}",
    }
```

**关键改进**：
- 删除兜底逻辑（原第 761-767 行）
- 未进入支付页一律标记为失败
- 保存截图作为证据
- 日志中记录详细的验证证据

---

### 3.3 时间窗口控制

**改进**：
1. **完全移除测试模式**
2. **启动时间窗口限制**：只允许在开抢前 10 分钟内启动任务
3. **太早启动直接拒绝**，返回明确的错误信息
4. **补抢时间窗口**：已过开抢时间 20 分钟内仍可尝试抢购

**实现逻辑**：
```python
def start_rush(config: dict) -> dict:
    # 校验启动时间窗口
    sale_time = config.get("sale_time", "")
    target = next_sale_time(sale_time)
    now = datetime.now()
    wait_seconds = (target - now).total_seconds()
    max_advance_minutes = 10
    
    if wait_seconds > max_advance_minutes * 60:
        return {
            "success": False,
            "message": f"距离开抢还有 {int(wait_seconds // 60)} 分钟，超过最大提前量 {max_advance_minutes} 分钟",
            "task_id": None,
        }
    
    # 已过开抢时间超过 20 分钟，放弃补抢
    if wait_seconds < -1200:
        return {
            "success": False,
            "message": "已过开抢时间 20 分钟，放弃补抢",
            "task_id": None,
        }
    
    # ... 启动任务 ...
```

---

### 3.4 错误处理与重试机制

**改进**：
1. **区分错误类型**：临时性错误自动重试，永久性错误立即失败
2. **自动重试机制**：临时性错误最多重试 3 次
3. **详细错误日志**：每次异常都记录完整的错误信息和上下文
4. **所有错误如实反馈**：不隐藏任何错误

**错误类型分类**：
```python
class ErrorType(str, Enum):
    TEMPORARY = "temporary"    # 临时性错误（可重试）：timeout, network, connection
    PERMANENT = "permanent"    # 永久性错误（不可重试）：not found, login expired
    UNKNOWN = "unknown"        # 未知错误（默认重试）
```

**重试逻辑**：
```python
def execute_with_retry(func, max_retries: int = 3, context: str = "", task_id: str = ""):
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            error_type = classify_error(e, context)
            
            if error_type == ErrorType.PERMANENT:
                # 永久性错误，立即失败
                raise
            
            if attempt < max_retries:
                # 临时性错误，重试
                time_module.sleep(1)
            else:
                # 已达到最大重试次数
                raise
```

---

### 3.5 截图保存机制

**截图时机**：
1. 登录成功时
2. 点击按钮前（可选）
3. 进入支付页时
4. 发生错误时

**存储策略**：
- 保存位置：`backend/data/glm_coding_rusher/screenshots/`
- 文件命名：`{step}_{task_id}_{timestamp}.png`
- 自动清理：保留 7 天，超过自动删除
- 数据库记录：截图信息保存到 `glm_coding_rusher_logs` 表（phase="screenshot"）

**实现**：
```python
class ScreenshotManager:
    def take_screenshot(self, page, step: str, description: str = "") -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{step}_{self.task_id}_{timestamp}.png"
        filepath = SCREENSHOT_DIR / filename
        
        page.screenshot(path=str(filepath))
        _append_log("screenshot", f"截图已保存: {filepath}", self.task_id)
        
        return filepath
```

---

### 3.6 配置持久化

**改进**：使用已定义的数据库表 `glm_coding_rusher_configs` 保存配置，移除内存中的 `_config_store`。

**实现**：
```python
def get_config(user_id: str = "system") -> dict:
    """从数据库读取配置"""
    db = _get_db()
    config = db.query(GlmCodingRusherConfig).filter(
        GlmCodingRusherConfig.user_id == user_id
    ).first()
    
    if config:
        return { ... }
    else:
        # 没有配置，返回默认值并创建记录
        default_config = { ... }
        save_config(default_config, user_id)
        return default_config

def save_config(config: dict, user_id: str = "system") -> dict:
    """保存配置到数据库"""
    validate_config(config)
    # ... 更新或创建配置记录 ...
```

---

### 3.7 WebSocket 实时日志

**改进**：使用 WebSocket 替代轮询，实现实时日志推送。

**后端实现**：
```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def broadcast_log(self, log_entry: dict):
        """广播日志到所有连接的客户端"""
        for connection in self.active_connections:
            await connection.send_json({"type": "log", "data": log_entry})

@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    # 先发送历史记录
    recent_logs = get_task_logs(limit=50)
    await websocket.send_json({"type": "history", "data": recent_logs})
    # 保持连接，等待新日志
```

**前端实现**：
```typescript
export const connectLogsWebSocket = (onLog: (log: any) => void, onHistory: (logs: any[]) => void) => {
  const ws = new WebSocket(wsUrl);
  
  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === 'log') {
      onLog(message.data);
    } else if (message.type === 'history') {
      onHistory(message.data);
    }
  };
  
  // 自动重连
  ws.onclose = () => {
    setTimeout(() => connectLogsWebSocket(onLog, onHistory), 5000);
  };
};
```

---

### 3.8 前端改动

**改进内容**：
1. WebSocket 实时日志，移除轮询（保留降级方案）
2. 日志按 phase 分类，使用不同图标和颜色
3. 配置加载时显示加载状态
4. 配置保存时显示校验结果
5. 任务状态详细展示（包括错误详情、支付 URL）
6. 错误信息直接展示后端返回的详细提示

**日志展示**：
```typescript
const getPhaseIcon = (phase: string) => {
  const icons: Record<string, { icon: string; color: string }> = {
    preheating: { icon: '🔥', color: 'text-orange-500' },
    refreshing: { icon: '🔄', color: 'text-blue-500' },
    clicking: { icon: '🖱️', color: 'text-purple-500' },
    success: { icon: '✅', color: 'text-green-500' },
    failed: { icon: '❌', color: 'text-red-500' },
    warning: { icon: '⚠️', color: 'text-yellow-500' },
    payment: { icon: '💳', color: 'text-indigo-500' },
    screenshot: { icon: '📸', color: 'text-pink-500' },
  };
  return icons[phase] || { icon: '📝', color: 'text-gray-500' };
};
```

---

## 四、数据模型

使用已定义的数据库表：
- `glm_coding_rusher_configs`：配置表
- `glm_coding_rusher_logs`：日志表
- `glm_coding_rusher_tasks`：任务记录表

无需新增表结构。

---

## 五、实施步骤

1. **后端核心逻辑重构**
   - 登录态检测改为正面检测
   - 抢购成功判断改为双重检测
   - 移除测试模式，增加时间窗口控制
   - 增加错误重试机制
   - 增加截图管理器

2. **后端配置持久化**
   - 实现 `get_config` 和 `save_config` 函数
   - 移除内存中的 `_config_store`

3. **后端 WebSocket 实现**
   - 实现 `ConnectionManager`
   - 添加 WebSocket 端点 `/ws/logs`
   - 在 `_append_log` 中集成 WebSocket 推送

4. **前端改动**
   - 移除轮询逻辑，改用 WebSocket
   - 增强日志展示（图标、颜色）
   - 配置表单改进
   - 任务状态展示增强

5. **测试验证**
   - 测试登录态检测逻辑
   - 测试抢购成功判断逻辑
   - 测试时间窗口控制
   - 测试错误重试机制
   - 测试 WebSocket 实时日志
   - 测试截图保存

---

## 六、风险与注意事项

1. **登录态特征选择器**：需要根据 GLM-Coding 实际页面结构调整 `LOGIN_INDICATORS`
2. **支付页特征**：需要根据实际支付页 URL 和页面内容调整 `PAYMENT_URL_KEYWORDS` 和 `PAYMENT_PAGE_INDICATORS`
3. **WebSocket 兼容性**：需要确保前端环境支持 WebSocket
4. **截图存储**：需要定期清理旧截图，避免占用过多磁盘空间
5. **并发控制**：当前仍为单实例模式，不支持多用户并发抢购

---

## 七、验收标准

1. ✅ 登录态检测必须检测到明确的已登录特征
2. ✅ 抢购成功必须双重检测通过（URL 变化 + 支付页特征）
3. ✅ 距离开抢超过 10 分钟拒绝启动
4. ✅ 已过开抢时间 20 分钟放弃补抢
5. ✅ 临时性错误自动重试 3 次，永久性错误立即失败
6. ✅ 关键步骤自动截图保存
7. ✅ 配置持久化到数据库，重启后不丢失
8. ✅ 日志通过 WebSocket 实时推送
9. ✅ 所有错误如实反馈给用户，无兜底逻辑
