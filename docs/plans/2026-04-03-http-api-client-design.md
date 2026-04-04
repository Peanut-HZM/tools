# HTTP 接口调用工具设计文档

**创建日期**: 2026-04-03  
**作者**: AI Assistant  
**状态**: 已批准

---

## 1. 概述

### 1.1 产品定位

完整的 API 工作区（类似 Apifox 全功能），用于项目的 HTTP 接口调用、调试和管理。

### 1.2 目标用户

- 后端开发人员：调试 API 接口
- 前端开发人员：查看接口响应、Mock 数据
- 测试人员：接口测试、断言验证
- 技术文档编写者：生成接口文档

### 1.3 核心特性

- 完整的 HTTP 请求编辑和响应查看
- 请求集合管理（文件夹层级）
- 环境变量（多环境切换 + 变量引用）
- 认证管理（Bearer Token、Basic Auth 等）
- 历史记录自动保存
- 混合存储（本地 + 云端同步）

---

## 2. 架构设计

### 2.1 前端架构（三栏式布局）

```
┌────────────────────────────────────────────────────────────────┐
│  顶部工具栏：环境选择 | 新建集合 | 导入/导出 | 搜索请求         │
├───────────┬───────────────────────┬────────────────────────────┤
│           │  标签页栏 (Tabs)       │                            │
│  集合导航  ├───────────────────────┤      请求编辑器             │
│  (左栏)   │                       │                            │
│           │  ┌─────────────────┐  │  [Method▼] [URL 输入框]     │
│  ▼ 集合 A  │  │ 请求 1    ✕    │  │  ─────────────────────────  │
│    请求 A1 │  ├─────────────────┤  │  Tabs: Params | Headers |  │
│    请求 A2 │  │ 请求 2    ✕    │  │  Body | Auth | Settings    │
│           │  └─────────────────┘  │                            │
│  ▼ 集合 B  │                       │  [动态表单区域]            │
│    请求 B1 │                       │                            │
│           │                       │                            │
│           │                       │  [发送按钮]                 │
├───────────┴───────────────────────┴────────────────────────────┤
│  响应面板（可折叠/调整高度）                                      │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Status: 200 OK │ Time: 125ms │ Size: 1.2KB                │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ Body │ Headers │ Cookies │ Tests │                         │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ {                                                        │ │
│  │   "id": 1,                                               │ │
│  │   "name": "张三"                                          │ │
│  │ }                                                        │ │
│  │ [JSON 格式化/高亮]                                        │ │
│  └───────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

### 2.2 前端目录结构

```
frontend/src/components/Tools/HttpApiClient/
├── HttpApiClient.tsx              # 主组件（三栏布局）
├── components/
│   ├── CollectionTree.tsx         # 集合树导航
│   ├── RequestTabs.tsx            # 标签页管理
│   ├── RequestEditor/
│   │   ├── UrlBar.tsx             # URL 输入栏
│   │   ├── MethodSelector.tsx     # 方法选择器
│   │   ├── ParamsPanel.tsx        # 参数编辑
│   │   ├── HeadersPanel.tsx       # Headers 编辑
│   │   ├── BodyEditor.tsx         # Body 编辑器（JSON/Form/Raw）
│   │   └── AuthPanel.tsx          # 认证配置
│   ├── ResponseViewer/
│   │   ├── ResponseHeader.tsx     # 响应头信息
│   │   ├── ResponseBody.tsx       # 响应体查看（JSON 高亮）
│   │   └── ResponseStats.tsx      # 响应统计（时间/大小）
│   ├── EnvironmentSelector.tsx    # 环境选择器
│   └── ImportExportModal.tsx      # 导入/导出弹窗
├── hooks/
│   ├── useCollections.ts          # 集合管理 Hook
│   ├── useRequests.ts             # 请求管理 Hook
│   ├── useEnvironments.ts         # 环境变量 Hook
│   ├── useSendRequest.ts          # 发送请求 Hook
│   └── useSync.ts                 # 云端同步 Hook
└── stores/
    └── httpClientStore.ts         # Zustand 状态管理
```

### 2.3 后端架构

```
backend/app/
├── routes/
│   └── http_client.py             # HTTP 客户端路由
├── services/
│   └── http_client_service.py     # HTTP 客户端服务
├── models/
│   └── http_client_models.py      # 数据模型
└── schemas/
    └── http_client_schemas.py     # Pydantic 模式
```

---

## 3. 数据模型设计

### 3.1 数据库表结构

#### 3.1.1 请求集合表（http_request_collections）

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | VARCHAR(64) | 主键，UUID |
| name | VARCHAR(100) | 集合名称 |
| description | TEXT | 描述 |
| workspace_id | VARCHAR(64) | 工作区 ID（预留多工作区） |
| parent_id | VARCHAR(64) | 父集合 ID（支持嵌套） |
| sort_order | INT | 排序 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

#### 3.1.2 HTTP 请求表（http_requests）

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | VARCHAR(64) | 主键，UUID |
| collection_id | VARCHAR(64) | 所属集合 ID |
| name | VARCHAR(100) | 请求名称 |
| method | VARCHAR(10) | HTTP 方法 |
| url | TEXT | 请求 URL（可包含变量） |
| headers | JSONB | 请求头 |
| params | JSONB | 查询参数 |
| body_type | VARCHAR(20) | json/form/raw/none |
| body | TEXT | 请求体 |
| auth_type | VARCHAR(20) | bearer/basic/apikey/none |
| auth_config | JSONB | 认证配置 |
| sort_order | INT | 排序 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

#### 3.1.3 环境变量表（http_environments）

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | VARCHAR(64) | 主键，UUID |
| name | VARCHAR(50) | 环境名称 |
| workspace_id | VARCHAR(64) | 工作区 ID |
| variables | JSONB | 变量名 -> 值 |
| is_active | BOOLEAN | 是否激活 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

#### 3.1.4 请求历史表（http_request_history）

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | VARCHAR(64) | 主键，UUID |
| user_id | VARCHAR(64) | 用户 ID |
| request_id | VARCHAR(64) | 关联的请求 ID（可选） |
| method | VARCHAR(10) | HTTP 方法 |
| url | TEXT | 请求 URL |
| status_code | INT | 响应状态码 |
| response_time | INT | 响应时间（毫秒） |
| request_data | JSONB | 请求数据快照 |
| response_data | JSONB | 响应数据快照 |
| timestamp | TIMESTAMP | 时间戳 |

#### 3.1.5 云端同步记录表（http_sync_records）

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | VARCHAR(64) | 主键，UUID |
| user_id | VARCHAR(64) | 用户 ID |
| entity_type | VARCHAR(20) | collection/request/environment |
| entity_id | VARCHAR(64) | 实体 ID |
| action | VARCHAR(10) | create/update/delete |
| local_data | JSONB | 本地数据快照 |
| synced_at | TIMESTAMP | 同步时间 |

### 3.2 Pydantic 模型

```python
# backend/app/models/http_client_models.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime

class CollectionBase(BaseModel):
    name: str
    description: Optional[str] = None
    workspace_id: str
    parent_id: Optional[str] = None
    sort_order: int = 0

class CollectionCreate(CollectionBase):
    pass

class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None

class Collection(CollectionBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class HttpRequestBase(BaseModel):
    collection_id: str
    name: str
    method: str = "GET"
    url: str
    headers: Dict[str, str] = Field(default_factory=dict)
    params: Dict[str, str] = Field(default_factory=dict)
    body_type: str = "none"  # json, form, raw, none
    body: Optional[str] = None
    auth_type: str = "none"  # bearer, basic, apikey, none
    auth_config: Dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0

class HttpRequestCreate(HttpRequestBase):
    pass

class HttpRequestUpdate(BaseModel):
    name: Optional[str] = None
    method: Optional[str] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, str]] = None
    body_type: Optional[str] = None
    body: Optional[str] = None
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    sort_order: Optional[int] = None

class HttpRequest(HttpRequestBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class EnvironmentBase(BaseModel):
    name: str
    workspace_id: str
    variables: Dict[str, str] = Field(default_factory=dict)
    is_active: bool = False

class EnvironmentCreate(EnvironmentBase):
    pass

class EnvironmentUpdate(BaseModel):
    name: Optional[str] = None
    variables: Optional[Dict[str, str]] = None
    is_active: Optional[bool] = None

class Environment(EnvironmentBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class RequestHistoryBase(BaseModel):
    user_id: str
    request_id: Optional[str] = None
    method: str
    url: str
    status_code: int
    response_time: int
    request_data: Dict[str, Any] = Field(default_factory=dict)
    response_data: Dict[str, Any] = Field(default_factory=dict)

class RequestHistoryCreate(RequestHistoryBase):
    pass

class RequestHistory(RequestHistoryBase):
    id: str
    timestamp: datetime
    
    class Config:
        from_attributes = True

class SendRequestRequest(BaseModel):
    method: str
    url: str
    headers: Dict[str, str] = Field(default_factory=dict)
    params: Dict[str, str] = Field(default_factory=dict)
    body_type: str = "none"
    body: Optional[str] = None
    timeout: int = 30000  # 毫秒
    follow_redirects: bool = True

class SendRequestResponse(BaseModel):
    status_code: int
    headers: Dict[str, str]
    body: str
    response_time: int  # 毫秒
    content_type: Optional[str] = None

class ImportResult(BaseModel):
    success: bool
    imported_count: int
    failed_count: int
    errors: List[str] = Field(default_factory=list)
```

---

## 4. API 接口设计

### 4.1 集合管理

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/http-client/collections` | 获取所有集合 |
| POST | `/api/http-client/collections` | 创建集合 |
| GET | `/api/http-client/collections/{id}` | 获取集合详情 |
| PUT | `/api/http-client/collections/{id}` | 更新集合 |
| DELETE | `/api/http-client/collections/{id}` | 删除集合（级联删除子项） |

### 4.2 请求管理

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/http-client/requests?collection_id=xxx` | 获取请求列表 |
| POST | `/api/http-client/requests` | 创建请求 |
| GET | `/api/http-client/requests/{id}` | 获取请求详情 |
| PUT | `/api/http-client/requests/{id}` | 更新请求 |
| DELETE | `/api/http-client/requests/{id}` | 删除请求 |
| POST | `/api/http-client/requests/import` | 导入请求 |
| GET | `/api/http-client/requests/export?collection_id=xxx` | 导出请求 |

### 4.3 环境变量

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/http-client/environments` | 获取所有环境 |
| POST | `/api/http-client/environments` | 创建环境 |
| PUT | `/api/http-client/environments/{id}` | 更新环境 |
| DELETE | `/api/http-client/environments/{id}` | 删除环境 |
| POST | `/api/http-client/environments/{id}/activate` | 激活环境 |

### 4.4 发送请求

| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | `/api/http-client/send` | 发送 HTTP 请求（代理转发） |

### 4.5 历史记录

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/http-client/history?limit=50` | 获取历史记录 |
| DELETE | `/api/http-client/history/{id}` | 删除单条历史 |
| POST | `/api/http-client/history/clear` | 清空历史 |

### 4.6 云端同步

| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | `/api/http-client/sync/push` | 推送本地数据到云端 |
| POST | `/api/http-client/sync/pull` | 从云端拉取数据 |
| GET | `/api/http-client/sync/status` | 获取同步状态 |

---

## 5. 技术选型

### 5.1 前端技术栈

| 技术 | 用途 | 版本 |
|-----|------|------|
| React | UI 框架 | 18+ |
| TypeScript | 类型系统 | 5+ |
| Tailwind CSS | 样式 | 3+ |
| Zustand | 状态管理 | 4+ |
| Monaco Editor | 代码编辑器 | 0.40+ |
| PrismJS | 语法高亮 | latest |
| axios | HTTP 客户端 | 1+ |
| react-resizable-panels | 可调整面板 | 2+ |

### 5.2 后端技术栈

| 技术 | 用途 | 版本 |
|-----|------|------|
| FastAPI | Web 框架 | 0.100+ |
| httpx | 异步 HTTP 客户端 | 0.24+ |
| SQLAlchemy | ORM | 2.0+ |
| Pydantic | 数据验证 | 2+ |
| psycopg2 | PostgreSQL 驱动 | latest |

---

## 6. 实现计划

### 6.1 第一期（MVP）- 核心功能

**目标**: 实现可用的 HTTP 请求发送和响应查看

**任务**:
1. 后端代理转发接口（`POST /api/http-client/send`）
2. 前端基础布局（三栏式）
3. 请求编辑器（Method、URL、Headers、Params、Body）
4. 响应查看器（状态码、响应体、JSON 高亮）
5. 本地存储（IndexedDB 临时存储）

**预计工期**: 3-4 天

### 6.2 第二期 - 数据持久化

**目标**: 实现请求集合和历史的持久化存储

**任务**:
1. 数据库表创建迁移
2. 后端 CRUD API
3. 集合管理（创建、编辑、删除、排序）
4. 请求管理（创建、编辑、删除、排序）
5. 历史记录保存和查看

**预计工期**: 4-5 天

### 6.3 第三期 - 高级功能

**目标**: 实现环境变量和认证管理

**任务**:
1. 环境变量 CRUD
2. 环境变量 UI 选择器
3. 变量替换（{{variableName}}）
4. 认证管理（Bearer、Basic、API Key）
5. 云端同步（push/pull）

**预计工期**: 4-5 天

### 6.4 第四期 - 增强体验

**目标**: 提升用户体验和导入导出

**任务**:
1. 多标签页支持
2. 请求搜索和过滤
3. 导入（Postman Collection v2.1）
4. 导出（JSON 格式）
5. 性能优化和 Bug 修复

**预计工期**: 4-5 天

---

## 7. 安全考虑

### 7.1 SSRF 防护

后端代理发送请求时，必须检查目标地址，禁止访问内网：

```python
import ipaddress
import socket
from urllib.parse import urlparse

def is_safe_url(url: str) -> bool:
    """检查 URL 是否安全（非内网地址）"""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
        
        # 解析 IP 地址
        ip = socket.gethostbyname(hostname)
        ip_addr = ipaddress.ip_address(ip)
        
        # 检查是否为私有地址
        if ip_addr.is_private:
            return False
        if ip_addr.is_loopback:
            return False
        if ip_addr.is_link_local:
            return False
        
        return True
    except Exception:
        return False
```

### 7.2 请求频率限制

对发送请求接口进行限流，防止滥用：

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/send")
@limiter.limit("60/minute")
async def send_request(request: Request, ...):
    ...
```

### 7.3 敏感信息处理

- Auth 配置在数据库中加密存储
- 响应日志中脱敏敏感字段
- 前端不持久化敏感认证信息

### 7.4 CORS 配置

仅允许信任的源访问后端 API（已在 main.py 中配置）

---

## 8. 与现有工具的集成

### 8.1 工具导航

在首页工具列表中添加入口：

```typescript
// frontend/src/App.tsx
const toolRoutes: Record<string, string> = {
  // ...existing tools
  'http-api-client': '/tools/http-api-client',
};
```

### 8.2 路由配置

```typescript
// frontend/src/App.tsx
<Route path="/tools/http-api-client" element={<HttpApiClient />} />
```

### 8.3 后端路由注册

```python
# backend/app/main.py
app.include_router(http_client.router, prefix="/api")
```

### 8.4 用户认证

复用现有 JWT 认证系统，请求需携带 Authorization header

### 8.5 数据库

复用现有 PostgreSQL 连接配置

---

## 9. 测试计划

### 9.1 后端测试

- [ ] 发送请求接口（正常场景）
- [ ] 发送请求接口（异常场景：超时、DNS 错误、SSL 错误）
- [ ] SSRF 防护测试
- [ ] CRUD API 测试
- [ ] 数据完整性测试

### 9.2 前端测试

- [ ] 三栏布局响应式
- [ ] 请求编辑器功能
- [ ] 响应查看器功能
- [ ] 环境变量切换
- [ ] 集合管理功能
- [ ] 导入导出功能

### 9.3 集成测试

- [ ] 前后端联调
- [ ] 数据持久化
- [ ] 云端同步

---

## 10. 验收标准

### 10.1 功能验收

- [ ] 可以创建、编辑、删除请求集合
- [ ] 可以创建、编辑、删除 HTTP 请求
- [ ] 可以发送 HTTP 请求并查看响应
- [ ] 响应支持 JSON 高亮和格式化
- [ ] 可以切换环境变量
- [ ] 可以查看历史记录
- [ ] 可以导入 Postman Collection

### 10.2 性能验收

- [ ] 请求发送响应时间 < 3s（目标 API 正常时）
- [ ] 页面加载时间 < 2s
- [ ] 列表滚动流畅（60fps）

### 10.3 安全验收

- [ ] SSRF 防护生效
- [ ] 频率限制生效
- [ ] 敏感信息不泄露

---

## 11. 参考资料

- [Apifox 文档](https://www.apifox.cn/help/)
- [Postman API](https://www.postman.com/postman/workspace/postman-public-workspace/documentation/1300985-c99c163b-8b55-4b2c-a2c9-2d523c0f5e71?ctx=documentation)
- [httpx 文档](https://www.python-httpx.org/)
- [Monaco Editor 文档](https://microsoft.github.io/monaco-editor/)

---

## 附录 A：Postman Collection 导入格式

支持导入 Postman Collection v2.1 格式：

```json
{
  "info": {
    "name": "My API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Users",
      "item": [
        {
          "name": "Get User",
          "request": {
            "method": "GET",
            "header": [],
            "url": {
              "raw": "https://api.example.com/users/1",
              "protocol": "https",
              "host": ["api", "example", "com"],
              "path": ["users", "1"]
            }
          }
        }
      ]
    }
  ]
}
```

---

**文档结束**
