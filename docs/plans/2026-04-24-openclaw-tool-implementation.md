# OpenClaw 工具完整实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 OpenClaw AI 对话功能作为标准工具集成到平台，实现前端用户端聊天页面 + 后台管理配置控制面板。

**Architecture:** 基于现有工具注册模式，新增数据库配置表存储 OpenClaw 连接参数，后端扩展热加载配置能力，前端新建聊天组件和管理面板。后端 openclaw_service.py 和 openclaw.py 路由已存在，需在此基础上扩展。

**Tech Stack:** Python (FastAPI, psycopg2), React (TypeScript), SSE (Server-Sent Events), PostgreSQL

---

## Phase 1: 数据库配置表和模型

### Task 1: 创建 openclaw_configs 数据库表初始化逻辑

**Files:**
- Create: `backend/app/services/openclaw_config_service.py`

**Step 1: 编写配置服务**

创建 `backend/app/services/openclaw_config_service.py`：

```python
"""
OpenClaw 配置管理服务
管理 Gateway 连接配置的持久化和热加载
"""
import json
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from app.config.database import get_db_connection

logger = logging.getLogger(__name__)

DEFAULT_CONFIGS = {
    "gateway_url": "ws://127.0.0.1:18081",
    "token": "",
    "enabled": "true",
}


class OpenClawConfigService:
    """OpenClaw 配置管理服务（单例）"""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS openclaw_configs (
                        id VARCHAR(36) PRIMARY KEY,
                        config_key VARCHAR(50) UNIQUE NOT NULL,
                        config_value TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 插入默认配置
                for key, value in DEFAULT_CONFIGS.items():
                    cur.execute(
                        """
                        INSERT INTO openclaw_configs (id, config_key, config_value)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (config_key) DO NOTHING
                        """,
                        (str(uuid.uuid4()), key, value),
                    )
            conn.commit()
            logger.info("OpenClaw configs table initialized")
        except Exception as e:
            logger.error(f"OpenClaw config table initialization failed: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def get_config(self) -> Dict[str, str]:
        """获取所有配置"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT config_key, config_value FROM openclaw_configs")
                rows = cur.fetchall()
                return {row["config_key"]: row["config_value"] for row in rows}
        except Exception as e:
            logger.error(f"Failed to load OpenClaw config: {e}")
            return DEFAULT_CONFIGS.copy()
        finally:
            if conn:
                conn.close()

    def update_config(self, data: Dict[str, str]) -> Dict[str, str]:
        """批量更新配置"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                for key, value in data.items():
                    if key in DEFAULT_CONFIGS:
                        cur.execute(
                            """
                            UPDATE openclaw_configs
                            SET config_value = %s, updated_at = CURRENT_TIMESTAMP
                            WHERE config_key = %s
                            """,
                            (value, key),
                        )
                conn.commit()
            logger.info(f"OpenClaw config updated: {list(data.keys())}")
            return self.get_config()
        except Exception as e:
            logger.error(f"Failed to update OpenClaw config: {e}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def is_enabled(self) -> bool:
        """检查功能是否启用"""
        config = self.get_config()
        return config.get("enabled", "true").lower() == "true"


# 全局单例
openclaw_config_service = OpenClawConfigService()
```

**Step 2: 验证文件语法**

```bash
cd backend && python -m py_compile app/services/openclaw_config_service.py
```
Expected: 无输出（编译成功）

**Step 3: 提交**

```bash
git add backend/app/services/openclaw_config_service.py
git commit -m "feat: 添加 OpenClaw 配置管理服务，支持数据库持久化"
```

---

## Phase 2: 扩展 openclaw_service.py 支持热加载

### Task 2: 修改 openclaw_service.py 集成数据库配置

**Files:**
- Modify: `backend/app/services/openclaw_service.py`

**Step 1: 修改 start() 方法，从数据库读取配置并支持 reload**

在 `backend/app/services/openclaw_service.py` 中进行以下修改：

1. 在文件顶部导入：
```python
from app.services.openclaw_config_service import openclaw_config_service
```

2. 修改 `_connect()` 方法，从数据库配置服务读取 URL 和 Token：

将第 70-72 行：
```python
async def _connect(self):
    """建立 WebSocket 连接并完成握手"""
    url = settings.OPENCLAW_GATEWAY_URL
    token = settings.OPENCLAW_TOKEN
```
改为：
```python
async def _connect(self):
    """建立 WebSocket 连接并完成握手"""
    config = openclaw_config_service.get_config()
    url = config.get("gateway_url", settings.OPENCLAW_GATEWAY_URL)
    token = config.get("token", settings.OPENCLAW_TOKEN)
```

3. 在 `start()` 方法开头添加 enabled 检查：

在 `async def start(self):` 方法体开头（第 34 行后）添加：
```python
async def start(self):
    """启动连接（后台任务）"""
    if self._running:
        return
    if not openclaw_config_service.is_enabled():
        logger.info("OpenClaw 功能未启用，跳过连接")
        return
    self._running = True
    self._connect_task = asyncio.create_task(self._connect_loop())
    logger.info("OpenClaw Gateway 连接任务已启动")
```

4. 新增 `reload_config()` 方法（在 `stop()` 方法之后添加）：

```python
async def reload_config(self, new_config: Dict[str, str]):
    """热加载配置并重新连接"""
    logger.info("OpenClaw 配置热加载中...")
    await self.stop()
    self._running = True
    self._connect_task = asyncio.create_task(self._connect_loop())
    logger.info("OpenClaw 配置热加载完成")
```

5. 添加 `get_connection_info()` 方法（返回当前使用的配置，Token 脱敏）：

```python
def get_connection_info(self) -> dict:
    """获取当前连接信息（Token 脱敏）"""
    config = openclaw_config_service.get_config()
    token = config.get("token", "")
    masked_token = token[:6] + "****" + token[-4:] if len(token) > 10 else "****" if token else ""
    return {
        "gateway_url": config.get("gateway_url", ""),
        "token": masked_token,
        "enabled": config.get("enabled", "true"),
        "connected": self.is_connected(),
    }
```

6. 在文件顶部添加 `from typing import Dict` 到已有的 import 中。

**Step 2: 验证文件语法**

```bash
cd backend && python -m py_compile app/services/openclaw_service.py
```
Expected: 无输出

**Step 3: 提交**

```bash
git add backend/app/services/openclaw_service.py
git commit -m "feat: OpenClaw 服务支持数据库配置热加载"
```

---

## Phase 3: 后端管理 API

### Task 3: 创建 OpenClaw 管理路由

**Files:**
- Create: `backend/app/routes/openclaw_admin.py`
- Modify: `backend/app/main.py`（注册新路由）

**Step 1: 创建管理路由文件**

创建 `backend/app/routes/openclaw_admin.py`：

```python
"""
OpenClaw 管理路由
提供配置管理、连接状态监控、手动重连/断开功能
"""
import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.openclaw_service import openclaw_service
from app.services.openclaw_config_service import openclaw_config_service
from app.middleware.auth_middleware import get_current_user
from app.models.auth_models import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/openclaw", tags=["openclaw-admin"])


def get_admin_user(current_user: UserResponse = Depends(get_current_user)):
    """检查是否为管理员"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="权限不足：需要管理员权限")
    return current_user


class ConfigUpdateRequest(BaseModel):
    gateway_url: Optional[str] = None
    token: Optional[str] = None
    enabled: Optional[str] = None


@router.get("/config")
async def get_config(admin_user: UserResponse = Depends(get_admin_user)):
    """获取当前配置（Token 脱敏）"""
    config = openclaw_config_service.get_config()
    connection_info = openclaw_service.get_connection_info()
    return {**config, **connection_info}


@router.put("/config")
async def update_config(
    request: ConfigUpdateRequest,
    admin_user: UserResponse = Depends(get_admin_user),
):
    """更新配置并热加载"""
    data = request.model_dump(exclude_unset=True)

    # 验证 gateway_url 格式
    if "gateway_url" in data:
        url = data["gateway_url"]
        if url and not re.match(r"^wss?://", url):
            raise HTTPException(status_code=400, detail="Gateway URL 格式错误，应以 ws:// 或 wss:// 开头")

    # 验证 enabled 值
    if "enabled" in data:
        if data["enabled"] not in ("true", "false"):
            raise HTTPException(status_code=400, detail="enabled 值必须为 true 或 false")

    # 更新数据库
    updated_config = openclaw_config_service.update_config(data)

    # 热加载
    try:
        await openclaw_service.reload_config(updated_config)
    except Exception as e:
        logger.error(f"OpenClaw 热加载失败: {e}")
        return {"ok": False, "message": f"配置已保存，但重连失败: {str(e)}", "config": openclaw_service.get_connection_info()}

    return {"ok": True, "config": openclaw_service.get_connection_info()}


@router.get("/status")
async def get_status(admin_user: UserResponse = Depends(get_admin_user)):
    """获取连接状态"""
    connection_info = openclaw_service.get_connection_info()

    if connection_info["connected"]:
        try:
            gateway_status = await openclaw_service.get_status()
            return {"ok": True, **connection_info, "gateway_status": gateway_status}
        except Exception as e:
            return {"ok": True, **connection_info, "gateway_status": {"error": str(e)}}

    return {"ok": True, **connection_info}


@router.post("/reconnect")
async def reconnect(admin_user: UserResponse = Depends(get_admin_user)):
    """手动重连"""
    try:
        config = openclaw_config_service.get_config()
        await openclaw_service.reload_config(config)
        return {"ok": True, "message": "重连成功", "config": openclaw_service.get_connection_info()}
    except Exception as e:
        logger.error(f"OpenClaw 重连失败: {e}")
        raise HTTPException(status_code=500, detail=f"重连失败: {str(e)}")


@router.post("/disconnect")
async def disconnect(admin_user: UserResponse = Depends(get_admin_user)):
    """断开连接"""
    try:
        await openclaw_service.stop()
        return {"ok": True, "message": "已断开连接", "config": openclaw_service.get_connection_info()}
    except Exception as e:
        logger.error(f"OpenClaw 断开连接失败: {e}")
        raise HTTPException(status_code=500, detail=f"断开连接失败: {str(e)}")
```

**Step 2: 注册路由**

在 `backend/app/main.py` 第 251 行附近（`app.include_router(openclaw_router.router, prefix="/api")` 之后）添加：

```python
# OpenClaw Admin router
from app.routes import openclaw_admin as openclaw_admin_router

app.include_router(openclaw_admin_router.router)
```

**Step 3: 验证文件语法**

```bash
cd backend && python -m py_compile app/routes/openclaw_admin.py && python -m py_compile app/main.py
```
Expected: 无输出

**Step 4: 提交**

```bash
git add backend/app/routes/openclaw_admin.py backend/app/main.py
git commit -m "feat: 添加 OpenClaw 管理 API，支持配置管理和连接控制"
```

---

## Phase 4: 注册工具到工具列表

### Task 4: 在 tools_data.py 中注册 OpenClaw 工具

**Files:**
- Modify: `backend/app/data/tools_data.py`（添加新 Tool 条目）

**Step 1: 添加工具条目**

在 `backend/app/data/tools_data.py` 的 `TOOLS_DATA` 列表末尾（第 204 行 `]` 之前）添加：

```python
    Tool(
        id="openclaw",
        icon="fa-comments",
        iconColor="bg-violet-500",
        title="OpenClaw AI 对话",
        description="连接 OpenClaw Gateway 的 AI 智能对话助手",
        rating=4.9,
        usageCount="New",
        category="AI 工具",
        require_login=True,
    ),
```

**Step 2: 验证文件语法**

```bash
cd backend && python -m py_compile app/data/tools_data.py
```
Expected: 无输出

**Step 3: 提交**

```bash
git add backend/app/data/tools_data.py
git commit -m "feat: 在工具列表中注册 OpenClaw 工具"
```

---

## Phase 5: 前端 API 服务层

### Task 5: 创建 OpenClaw 前端 API 服务

**Files:**
- Create: `frontend/src/api/openclawApi.ts`

**Step 1: 创建 API 服务文件**

创建 `frontend/src/api/openclawApi.ts`：

```typescript
import { getAuthHeaders } from './authApi';
import { AUTH_API_BASE_URL } from '../config/api';

const API_BASE_URL = AUTH_API_BASE_URL.replace('/auth', '');

// ============ 用户端 API ============

export interface ChatMessage {
  message: string;
  session_key?: string;
}

/**
 * 流式对话（SSE）
 */
export async function chatStream(
  message: string,
  sessionKey: string = 'main',
  onChunk: (chunk: string) => void,
  onDone?: () => void,
  onError?: (error: string) => void
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/openclaw/chat`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message, session_key: sessionKey }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '请求失败' }));
      onError?.(error.detail || `HTTP ${response.status}`);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      onError?.('浏览器不支持流式响应');
      return;
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith(':')) continue;
        if (trimmed.startsWith('data: ')) {
          const jsonStr = trimmed.slice(6);
          try {
            const data = JSON.parse(jsonStr);
            if (data.type === 'chunk' && data.content) {
              onChunk(data.content);
            } else if (data.type === 'error') {
              onError?.(data.message || '服务端错误');
            } else if (data.type === 'done') {
              onDone?.();
              return;
            }
          } catch {
            // 不完整的 JSON，等待更多数据
          }
        }
      }
    }

    onDone?.();
  } catch (err: any) {
    onError?.(err.message || '网络异常');
  }
}

/** 获取会话历史 */
export async function loadHistory(sessionKey: string = 'main', limit: number = 50) {
  const response = await fetch(`${API_BASE_URL}/openclaw/history`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ session_key: sessionKey, limit }),
  });
  if (!response.ok) throw new Error('获取历史失败');
  const data = await response.json();
  return data.messages || [];
}

/** 中止生成 */
export async function abortChat(sessionKey: string = 'main') {
  const response = await fetch(`${API_BASE_URL}/openclaw/abort`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ session_key: sessionKey }),
  });
  if (!response.ok) throw new Error('中止失败');
  return response.json();
}

/** 重置会话 */
export async function resetSession(sessionKey: string = 'main') {
  const response = await fetch(`${API_BASE_URL}/openclaw/reset?session_key=${sessionKey}`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('重置失败');
  return response.json();
}

/** 获取状态 */
export async function getStatus() {
  const response = await fetch(`${API_BASE_URL}/openclaw/status`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('获取状态失败');
  return response.json();
}

// ============ 管理端 API ============

const ADMIN_API_BASE_URL = AUTH_API_BASE_URL.replace('/auth', '/admin');

export interface OpenClawConfig {
  gateway_url: string;
  token: string;
  enabled: string;
  connected: boolean;
}

/** 获取配置 */
export async function getOpenClawConfig(): Promise<OpenClawConfig> {
  const response = await fetch(`${ADMIN_API_BASE_URL}/openclaw/config`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('获取配置失败');
  return response.json();
}

/** 更新配置 */
export async function updateOpenClawConfig(data: Partial<OpenClawConfig>): Promise<any> {
  const response = await fetch(`${ADMIN_API_BASE_URL}/openclaw/config`, {
    method: 'PUT',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '更新失败' }));
    throw new Error(error.detail || '更新失败');
  }
  return response.json();
}

/** 获取状态 */
export async function getOpenClawStatus() {
  const response = await fetch(`${ADMIN_API_BASE_URL}/openclaw/status`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('获取状态失败');
  return response.json();
}

/** 手动重连 */
export async function reconnectOpenClaw() {
  const response = await fetch(`${ADMIN_API_BASE_URL}/openclaw/reconnect`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '重连失败' }));
    throw new Error(error.detail || '重连失败');
  }
  return response.json();
}

/** 断开连接 */
export async function disconnectOpenClaw() {
  const response = await fetch(`${ADMIN_API_BASE_URL}/openclaw/disconnect`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '断开失败' }));
    throw new Error(error.detail || '断开失败');
  }
  return response.json();
}
```

**Step 2: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc --noEmit src/api/openclawApi.ts 2>&1 | head -20
```
Expected: 无错误输出或仅有模块引用警告（正常）

**Step 3: 提交**

```bash
git add frontend/src/api/openclawApi.ts
git commit -m "feat: 添加 OpenClaw 前端 API 服务层"
```

---

## Phase 6: 前端用户端聊天组件

### Task 6: 创建 OpenClawChat 用户端组件

**Files:**
- Create: `frontend/src/components/Tools/OpenClawChat/OpenClawChat.tsx`

**Step 1: 创建聊天组件目录和主文件**

```bash
mkdir -p frontend/src/components/Tools/OpenClawChat
```

创建 `frontend/src/components/Tools/OpenClawChat/OpenClawChat.tsx`：

```typescript
import { useState, useRef, useEffect, useCallback } from 'react';
import { useAuth } from '../../../stores/authStore';
import { useNavigate } from 'react-router-dom';
import {
  chatStream,
  loadHistory,
  abortChat,
  resetSession,
  getStatus,
} from '../../../api/openclawApi';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  isStreaming?: boolean;
}

export default function OpenClawChat() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionKey] = useState('main');
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 检查连接状态
  const checkConnection = useCallback(async () => {
    try {
      const status = await getStatus();
      setIsConnected(status.connected === true);
      if (status.disabled) {
        setError('OpenClaw 功能已禁用，请联系管理员');
      }
    } catch {
      setIsConnected(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 加载历史消息
  const loadMessages = useCallback(async () => {
    try {
      const history = await loadHistory(sessionKey);
      const formatted: Message[] = history.map((msg: any, idx: number) => ({
        id: `hist-${idx}`,
        role: msg.role === 'user' ? 'user' : 'assistant',
        content: msg.content || '',
        timestamp: Date.now(),
      }));
      setMessages(formatted);
    } catch {
      // 忽略历史加载错误
    }
  }, [sessionKey]);

  useEffect(() => {
    checkConnection();
    loadMessages();
  }, [checkConnection, loadMessages]);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!inputValue.trim() || isSending || !isConnected) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setIsSending(true);
    setError(null);

    // 添加用户消息
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: userMessage,
      timestamp: Date.now(),
    };

    // 添加助理消息占位
    const assistantMsgId = `assistant-${Date.now()}`;
    const assistantMsg: Message = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    await chatStream(
      userMessage,
      sessionKey,
      // onChunk
      (chunk) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? { ...msg, content: msg.content + chunk }
              : msg
          )
        );
      },
      // onDone
      () => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? { ...msg, isStreaming: false }
              : msg
          )
        );
        setIsSending(false);
      },
      // onError
      (err) => {
        setError(err);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? { ...msg, content: msg.content || `请求失败：${err}`, isStreaming: false }
              : msg
          )
        );
        setIsSending(false);
      }
    );
  };

  const handleAbort = async () => {
    try {
      await abortChat(sessionKey);
      setIsSending(false);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.isStreaming ? { ...msg, isStreaming: false, content: msg.content + '\n\n[已中止]' } : msg
        )
      );
    } catch {
      // 忽略中止错误
    }
  };

  const handleReset = async () => {
    try {
      await resetSession(sessionKey);
      setMessages([]);
    } catch (err: any) {
      setError(err.message || '重置失败');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 未登录跳转
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-120px)]">
        <div className="text-center text-slate-400">
          <div className="text-6xl mb-4">
            <i className="fas fa-comments text-violet-500"></i>
          </div>
          <p className="text-xl mb-4 text-white">OpenClaw AI 对话</p>
          <p className="mb-4">需要登录后才能使用此功能</p>
          <button
            onClick={() => navigate('/login')}
            className="px-6 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition-colors"
          >
            前往登录
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-120px)]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-violet-500"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] bg-slate-900 rounded-xl border border-slate-700/50 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/50 bg-slate-800/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-purple-600 rounded-lg flex items-center justify-center">
            <i className="fas fa-comments text-white"></i>
          </div>
          <div>
            <h2 className="text-white font-semibold">OpenClaw AI 对话</h2>
            <div className="flex items-center gap-2 text-sm">
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></span>
              <span className="text-slate-400">{isConnected ? '已连接' : '未连接'}</span>
            </div>
          </div>
        </div>
        <button
          onClick={handleReset}
          className="px-3 py-1.5 text-sm text-slate-400 hover:text-white border border-slate-600 rounded-lg hover:border-slate-500 transition-colors"
        >
          <i className="fas fa-rotate mr-1"></i>
          新对话
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="px-6 py-2 bg-red-500/10 border-b border-red-500/30 text-red-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">
            <i className="fas fa-times"></i>
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-500">
            <div className="text-center">
              <div className="text-5xl mb-3">
                <i className="fas fa-comments text-violet-500/50"></i>
              </div>
              <p className="text-lg">发送一条消息开始对话</p>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  msg.role === 'user'
                    ? 'bg-violet-600 text-white rounded-br-md'
                    : 'bg-slate-800 text-slate-200 rounded-bl-md'
                }`}
              >
                <p className="whitespace-pre-wrap break-words">{msg.content || (msg.isStreaming ? 'Thinking...' : '')}</p>
                {msg.isStreaming && (
                  <span className="inline-block w-1.5 h-4 bg-violet-400 animate-pulse ml-1"></span>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="px-6 py-4 border-t border-slate-700/50 bg-slate-800/30">
        <div className="flex gap-3">
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息... (Shift+Enter 换行，Enter 发送)"
            disabled={!isConnected || isSending}
            className="flex-1 bg-slate-800 text-white placeholder-slate-500 border border-slate-600 rounded-xl px-4 py-3 resize-none focus:outline-none focus:border-violet-500 disabled:opacity-50"
            rows={1}
          />
          {isSending ? (
            <button
              onClick={handleAbort}
              className="px-4 py-3 bg-red-600 text-white rounded-xl hover:bg-red-700 transition-colors self-end"
            >
              <i className="fas fa-stop"></i>
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!inputValue.trim() || !isConnected}
              className="px-4 py-3 bg-violet-600 text-white rounded-xl hover:bg-violet-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed self-end"
            >
              <i className="fas fa-paper-plane"></i>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
```

**Step 2: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -i "OpenClawChat" | head -10
```
Expected: 无错误

**Step 3: 提交**

```bash
git add frontend/src/components/Tools/OpenClawChat/
git commit -m "feat: 添加 OpenClaw 用户端聊天页面"
```

---

## Phase 7: 前端后台管理面板

### Task 7: 创建 OpenClawManagement 管理面板

**Files:**
- Create: `frontend/src/components/Admin/OpenClawManagement.tsx`

**Step 1: 创建管理面板组件**

创建 `frontend/src/components/Admin/OpenClawManagement.tsx`：

```typescript
import { useState, useEffect } from 'react';
import {
  getOpenClawConfig,
  updateOpenClawConfig,
  getOpenClawStatus,
  reconnectOpenClaw,
  disconnectOpenClaw,
  type OpenClawConfig,
} from '../../api/openclawApi';

export default function OpenClawManagement() {
  const [config, setConfig] = useState<OpenClawConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 表单状态
  const [gatewayUrl, setGatewayUrl] = useState('');
  const [token, setToken] = useState('');
  const [enabled, setEnabled] = useState('true');

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getOpenClawConfig();
      setConfig(data);
      setGatewayUrl(data.gateway_url || '');
      setToken(''); // Token 不回显
      setEnabled(data.enabled || 'true');
    } catch (err: any) {
      setError(err.message || '加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const data: any = { enabled };
      if (gatewayUrl) data.gateway_url = gatewayUrl;
      if (token) data.token = token;

      const result = await updateOpenClawConfig(data);
      if (result.ok === false) {
        setError(result.message || '配置已保存，但重连失败');
      }
      await loadData();
    } catch (err: any) {
      setError(err.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleReconnect = async () => {
    setActionLoading('reconnect');
    setError(null);
    try {
      await reconnectOpenClaw();
      await loadData();
    } catch (err: any) {
      setError(err.message || '重连失败');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDisconnect = async () => {
    setActionLoading('disconnect');
    setError(null);
    try {
      await disconnectOpenClaw();
      await loadData();
    } catch (err: any) {
      setError(err.message || '断开失败');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-cyan-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">OpenClaw 管理</h1>
        <p className="text-slate-400 mt-1">管理 OpenClaw Gateway 连接配置和状态</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* 状态卡片 */}
      <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
        <h2 className="text-lg font-semibold text-white mb-4">连接状态</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-slate-400 text-sm">状态</p>
            <div className="flex items-center gap-2 mt-1">
              <span className={`w-2.5 h-2.5 rounded-full ${config?.connected ? 'bg-green-500' : 'bg-red-500'}`}></span>
              <span className="text-white font-medium">{config?.connected ? '已连接' : '未连接'}</span>
            </div>
          </div>
          <div>
            <p className="text-slate-400 text-sm">启用状态</p>
            <p className="text-white font-medium mt-1">{enabled === 'true' ? '已启用' : '已禁用'}</p>
          </div>
          <div>
            <p className="text-slate-400 text-sm">Gateway 地址</p>
            <p className="text-white font-mono text-sm mt-1">{config?.gateway_url || '-'}</p>
          </div>
          <div>
            <p className="text-slate-400 text-sm">Token</p>
            <p className="text-white font-mono text-sm mt-1">{config?.token || '(未设置)'}</p>
          </div>
        </div>
        <div className="flex gap-3 mt-6">
          <button
            onClick={handleReconnect}
            disabled={actionLoading !== null}
            className="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors disabled:opacity-50"
          >
            <i className="fas fa-rotate mr-1"></i>
            重新连接
          </button>
          <button
            onClick={handleDisconnect}
            disabled={actionLoading !== null || !config?.connected}
            className="px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 transition-colors disabled:opacity-50"
          >
            <i className="fas fa-plug-circle-xmark mr-1"></i>
            断开连接
          </button>
        </div>
      </div>

      {/* 配置表单 */}
      <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
        <h2 className="text-lg font-semibold text-white mb-4">连接配置</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-slate-300 text-sm mb-1">Gateway URL</label>
            <input
              type="text"
              value={gatewayUrl}
              onChange={(e) => setGatewayUrl(e.target.value)}
              placeholder="ws://127.0.0.1:18081"
              className="w-full bg-slate-900 text-white border border-slate-600 rounded-lg px-4 py-2.5 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>
          <div>
            <label className="block text-slate-300 text-sm mb-1">Token</label>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="留空表示不修改"
              className="w-full bg-slate-900 text-white border border-slate-600 rounded-lg px-4 py-2.5 focus:outline-none focus:border-cyan-500 font-mono"
            />
            <p className="text-slate-500 text-xs mt-1">输入新 Token 将覆盖当前配置，留空不修改</p>
          </div>
          <div>
            <label className="block text-slate-300 text-sm mb-1">功能开关</label>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setEnabled(enabled === 'true' ? 'false' : 'true')}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  enabled === 'true' ? 'bg-green-500' : 'bg-slate-600'
                }`}
              >
                <span
                  className={`absolute top-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
                    enabled === 'true' ? 'left-6' : 'left-0.5'
                  }`}
                />
              </button>
              <span className="text-white">{enabled === 'true' ? '已启用' : '已禁用'}</span>
            </div>
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="mt-6 px-6 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-lg hover:from-cyan-600 hover:to-blue-700 transition-all disabled:opacity-50"
        >
          <i className="fas fa-save mr-1"></i>
          {saving ? '保存中...' : '保存配置'}
        </button>
      </div>
    </div>
  );
}
```

**Step 2: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -i "OpenClawManagement" | head -10
```
Expected: 无错误

**Step 3: 提交**

```bash
git add frontend/src/components/Admin/OpenClawManagement.tsx
git commit -m "feat: 添加 OpenClaw 后台管理面板"
```

---

## Phase 8: 路由注册和侧边栏

### Task 8: 注册前端路由和后台侧边栏入口

**Files:**
- Modify: `frontend/src/App.tsx`（注册路由）
- Modify: `frontend/src/components/Admin/AdminLayout.tsx`（添加侧边栏入口）

**Step 1: 注册路由**

在 `frontend/src/App.tsx` 中：

1. 在文件顶部 import 区（第 38 行附近）添加：
```typescript
import OpenClawChat from './components/Tools/OpenClawChat/OpenClawChat';
import OpenClawManagement from './components/Admin/OpenClawManagement';
```

2. 在工具路由区域（第 316-317 行附近）添加用户端路由：
```typescript
<Route path="/tools/openclaw" element={<OpenClawChat />} />
```

3. 在 admin 路由区域（第 332 行附近）添加管理路由：
```typescript
<Route path="openclaw" element={<OpenClawManagement />} />
```

**Step 2: 添加侧边栏入口**

在 `frontend/src/components/Admin/AdminLayout.tsx` 的 `menuItems` 数组（第 32-43 行）中添加：

```typescript
{ path: '/admin/openclaw', label: 'OpenClaw 管理', icon: 'fa-comments' },
```

放在课程管理之后。

**Step 3: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```
Expected: 无错误

**Step 4: 提交**

```bash
git add frontend/src/App.tsx frontend/src/components/Admin/AdminLayout.tsx
git commit -m "feat: 注册 OpenClaw 前端路由和后台侧边栏入口"
```

---

## Phase 9: 集成测试与验证

### Task 9: 启动服务并验证全流程

**Step 1: 启动后端**

```bash
cd backend && uvicorn app.main:app --reload --port 19092
```
Expected: 启动成功，日志中显示 `OpenClaw 连接任务已启动` 或 `OpenClaw 功能未启用，跳过连接`

**Step 2: 启动前端**

```bash
cd frontend && npm run dev
```
Expected: 前端启动在端口 5178

**Step 3: 验证工具列表**

访问 `http://localhost:5178`，确认工具列表中显示 "OpenClaw AI 对话" 工具（ violet 图标）。

**Step 4: 验证聊天页面**

点击 "OpenClaw AI 对话" 工具，验证：
- 页面正常渲染
- 连接状态指示灯显示
- Empty state 提示
- 输入框和发送按钮

**Step 5: 验证后台管理**

访问 `http://localhost:5178/admin/openclaw`（需要 admin 账号登录），验证：
- 连接状态卡片显示
- 配置表单正常
- Gateway URL 和 Token 字段可编辑
- 启用/禁用开关可用
- 保存配置按钮可用

**Step 6: 验证 API 端点**

```bash
# 测试状态接口
curl http://localhost:19092/api/openclaw/status

# 测试管理配置接口（需要登录获取 token）
curl -H "Authorization: Bearer <token>" http://localhost:19092/api/admin/openclaw/config
```

**Step 7: 提交**

```bash
git status
```
确认所有变更已提交。

---

## 总结

本计划共 9 个 Task，按照依赖顺序排列：

1. **Task 1**: 数据库配置表和服务（基础）
2. **Task 2**: 扩展 openclaw_service 热加载能力（依赖 Task 1）
3. **Task 3**: 后端管理 API（依赖 Task 1, 2）
4. **Task 4**: 工具注册（独立）
5. **Task 5**: 前端 API 服务层（独立）
6. **Task 6**: 用户端聊天组件（依赖 Task 5）
7. **Task 7**: 后台管理面板（依赖 Task 5）
8. **Task 8**: 路由注册（依赖 Task 6, 7）
9. **Task 9**: 集成测试验证（依赖所有前置）

每个 Task 提交一次，确保可回滚。
