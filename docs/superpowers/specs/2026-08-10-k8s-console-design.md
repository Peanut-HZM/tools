---
purpose: 为 tools 平台新增 K8s 控制台工具，支持通过导入 kubeconfig 连接 Kubernetes 集群，查看 Pod / 工作负载 / Node 状态、实时日志、交互式终端、监控指标、事件流、YAML 只读查看及关联资源跳转
date: 2026-08-10
---

# K8s 控制台工具设计

## 背景

tools 平台已具备 SSH、Redis、数据库、HTTP 客户端等常用运维/开发工具，但缺少 Kubernetes 集群的统一可视化控制台。目前开发 / 运维人员查看 Pod 状态、拉日志、进入容器排障需要：

1. 在多个终端窗口之间切换（`kubectl get pods` / `kubectl logs` / `kubectl exec`）
2. 在本机 `~/.kube/config`、云厂商控制台、Lens 桌面客户端之间反复跳转
3. 多个集群切换依赖手动 `kubectl config use-context`，缺乏可视化提示

本项目希望参考 [Lens](https://lenshq.io/) 的核心能力，在 tools 平台内嵌入一个 Web 版 K8s 控制台，让用户在同一入口完成：配置导入、状态查看、日志拉取、容器进入、指标观察、事件分析。

## 目标

- 一个 Web 页面承载 K8s 全部日常查看 / 排障能力
- 支持多集群、多 namespace、多用户隔离
- 纯只读，不修改集群状态
- 优雅降级：Metrics Server 缺失、容器无 bash、集群不可达 等场景均不阻塞核心功能

## 非目标（v1 明确不做）

- 写操作：删除 Pod、扩缩容、编辑 YAML 并 apply、rollout restart
- 完整资源类型：RBAC / CRD / HPA / PV / ServiceAccount / Ingress / Service 等 v1 不做
- 多集群聚合视图（一次看多个集群的 Pod）
- 云厂商 API 拉取集群列表（ACK/TKE/EKS）
- CRD 自定义资源浏览

## 总体架构

```
┌────────────────────────────────────────────────────────────────┐
│ Frontend (React + xterm.js + recharts)                         │
│  - 顶部：ClusterSwitcher + NamespaceFilter                     │
│  - 左侧：ConnectionList (kubeconfig 列表)                      │
│  - 主区：ResourceTabs (Pods/Workloads/Nodes/Events) + Detail   │
└──────────────────────────────┬─────────────────────────────────┘
                               │ HTTP REST (资源列表/详情/指标)
                               │ WebSocket (日志流/exec 终端)
┌──────────────────────────────┴─────────────────────────────────┐
│ Backend (FastAPI + kubernetes_asyncio)                         │
│  - /api/k8s-tool/configs  (连接配置 CRUD)                       │
│  - /api/k8s-tool/{id}/...  (资源查询，按需创建 KubernetesClient) │
│  - WebSocket endpoints   (logs streaming, exec shell)          │
│  - 每个连接配置对应一个加密的 kubeconfig 存 DB                    │
└──────────────────────────────┬─────────────────────────────────┘
                               │ TLS + Bearer Token / Client Cert
                               ▼
                    Kubernetes API Server (目标集群)
```

关键设计决策：

- **客户端生命周期**：每次 API 请求按需从 DB 解密 kubeconfig、构造临时 `kubernetes_asyncio.ApiClient`，用完释放。不在内存长期持有，避免 kubeconfig 修改后失效。
- **用户隔离**：所有连接配置带 `user_id`，查询自动过滤。
- **只读保证**：后端代码只调用 `CoreV1Api.list_*` / `AppsV1Api.read_*` 等读接口，不导入 write/patch/delete 方法，从代码层杜绝写操作。
- **加密存储**：kubeconfig 中的证书/token 用 Fernet 对称加密后存 DB，key 从环境变量读取。
- **实现方案**：Python `kubernetes_asyncio` 官方客户端 + WebSocket（与现有 SSH 工具架构模式一致）。

## 模块 1：后端连接配置管理

### 数据模型

```python
# backend/app/models/k8s_tool_models.py
class K8sConnection(Base):
    id: str                        # UUID, PK
    user_id: str                   # FK → users.id, indexed
    name: str                      # 用户给的显示名, 如 "生产集群-context-1"
    source_type: str               # 'kubeconfig_file' | 'kubeconfig_text' | 'manual'
    cluster_name: str              # 从 kubeconfig 解析出的 cluster name
    context_name: str              # 原始 context 名 (manual 模式下可选)
    server: str                    # API server URL
    auth_type: str                 # 'bearer_token' | 'client_cert' | 'basic_auth' | 'oidc'
    auth_data_encrypted: bytes     # Fernet 加密的 {token/cert/key/username+password}
    ca_cert_encrypted: bytes | None  # 集群 CA 证书 (自签名场景)
    namespace_filter: list[str]    # 可选: 只暴露指定 namespace (空=全部), 后端查询时自动 WHERE namespace IN (filter)
    is_metrics_available: bool     # 上次探测 Metrics Server 是否可用
    last_test_at: datetime | None  # 上次连通性测试时间
    last_test_error: str | None
    created_at: datetime
    updated_at: datetime
```

### 导入流程

三种入口（上传文件 / 粘贴文本 / 手动表单），统一归一化：

```
[上传文件] ──┐
[粘贴文本] ──┼─→ parse_kubeconfig(content)
[手动表单] ──┘          │
                        ▼
              ┌─────────────────────────┐
              │ 解析出 contexts 数组      │
              │ 每个 context → 一条配置   │
              └─────────────────────────┘
                        │
                        ▼
        对每个 context：
        - 生成 K8sConnection 记录
        - 加密敏感字段
        - 自动命名："cluster-name / context-name"
        - 立即发起一次连通性测试（list namespaces）
        - 探测 Metrics Server 可用性
```

### API 路由

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/k8s-tool/configs` | 列出当前用户的所有连接配置（脱敏） |
| POST | `/api/k8s-tool/configs/upload` | 上传 kubeconfig 文件，解析后批量创建 |
| POST | `/api/k8s-tool/configs/paste` | 粘贴 kubeconfig 文本，解析后批量创建 |
| POST | `/api/k8s-tool/configs/manual` | 手动表单创建单条配置 |
| PUT | `/api/k8s-tool/configs/{id}` | 更新（重命名、调整 namespace 过滤等） |
| DELETE | `/api/k8s-tool/configs/{id}` | 删除 |
| POST | `/api/k8s-tool/configs/{id}/test` | 重新测试连通性 |
| GET | `/api/k8s-tool/configs/{id}/health` | 返回健康状态 + metrics server 可用性 |

### 安全要点

1. **Fernet 加密**：使用 `cryptography.fernet`，密钥从 `K8S_FERNET_KEY` 环境变量读取（启动时缺失则报错）。
2. **响应脱敏**：`GET /configs` 永不返回 `auth_data_encrypted` / `ca_cert_encrypted` 原文，只返回 `auth_type` 和是否已配置。
3. **用户隔离**：所有查询自动 `WHERE user_id = current_user_id`，路由层用 `Depends(get_current_user_id)`。
4. **文件大小限制**：kubeconfig 上传限制 1MB（正常 kubeconfig 几 KB）。

## 模块 2：后端资源查询层

### 客户端构造

```python
# backend/app/services/k8s_client_factory.py
async def build_client(config: K8sConnection) -> AsyncContextManager[ClientBundle]:
    """
    解密 auth_data → 构造 kubernetes_asyncio.Configuration → 创建 ApiClient
    返回 ClientBundle，包含 core_v1 / apps_v1 / custom_objects 等 API 实例
    退出 context 时自动 close ApiClient 释放连接池
    """
```

### 资源 API 路由

所有路由前缀 `/api/k8s-tool/{config_id}`，依赖 `build_client` 注入。

**Namespace & Node（集群级）**

| Method | Path | 说明 |
|--------|------|------|
| GET | `/{id}/namespaces` | 列出所有 namespace（用于顶部筛选器） |
| GET | `/{id}/nodes` | 列出所有 node（名称、状态、角色、版本、内核、OS、运行时间） |
| GET | `/{id}/nodes/{name}` | node 详情（标签、注解、条件、容量、可调度性） |
| GET | `/{id}/nodes/{name}/metrics` | node CPU/内存实时指标 |

**Pod（核心资源）**

| Method | Path | 说明 |
|--------|------|------|
| GET | `/{id}/pods?namespace=` | 列出 pod（分页、按 label/状态筛选） |
| GET | `/{id}/pods/{name}?namespace=` | pod 详情（状态、容器列表、重启次数、IP、node、QoS） |
| GET | `/{id}/pods/{name}/yaml?namespace=` | pod 完整 YAML（只读） |
| GET | `/{id}/pods/{name}/events?namespace=` | 该 pod 相关 events（关联 UID） |
| GET | `/{id}/pods/{name}/metrics?namespace=` | pod CPU/内存实时指标 |
| WS | `/{id}/ws/pods/{name}/logs?namespace=&container=&tail_lines=&since_seconds=&follow=` | 日志流 |
| WS | `/{id}/ws/pods/{name}/exec?namespace=&container=&command=` | 交互式 exec shell |

**工作负载控制器**

| Method | Path | 说明 |
|--------|------|------|
| GET | `/{id}/deployments?namespace=` | 列表（期望/就绪/可用副本数、策略、镜像） |
| GET | `/{id}/deployments/{name}?namespace=` | 详情 + 关联 pod 列表 |
| GET | `/{id}/deployments/{name}/yaml?namespace=` | YAML |
| 同上模式 | `replicasets` / `statefulsets` / `daemonsets` / `jobs` / `cronjobs` | |

**Events & 关联资源**

| Method | Path | 说明 |
|--------|------|------|
| GET | `/{id}/events?namespace=&field_selector=` | events 列表（支持按 involvedObject 过滤） |
| GET | `/{id}/configmaps/{name}?namespace=` | configmap 详情 + data 内容（只读） |
| GET | `/{id}/secrets/{name}?namespace=` | secret 详情 + data（base64 解码返回明文，便于查看；通过 Python `logging` 记录审计信息：user_id、config_id、secret_name、timestamp，便于事后追溯） |
| GET | `/{id}/pvcs/{name}?namespace=` | PVC 详情（状态、容量、绑定 PV、StorageClass） |

### 日志 WebSocket 设计

```python
@router.websocket("/ws/pods/{name}/logs")
async def pod_logs_ws(websocket: WebSocket, config_id: str, name: str,
                      namespace: str, container: str | None,
                      tail_lines: int = 100, since_seconds: int | None = None,
                      follow: bool = True):
    # 1. 鉴权 (query param 带 JWT token，与 SSH 工具一致)
    # 2. build_client → 调 core_v1.read_namespaced_pod_log(..., _preload_content=False)
    # 3. 异步迭代 chunk → websocket.send_text()
    # 4. 客户端发 {"type": "resize"} / {"type": "stop"} → 控制流
    # 5. 异常/断开 → 清理 ApiClient
```

支持参数：

- `container`：多容器 pod 必选，单容器可省（默认第一个）
- `tail_lines`：最近 N 行（历史区间）
- `since_seconds`：最近 N 秒（历史区间）
- `follow=true`：实时 tail；`follow=false`：一次性拉取
- `previous=true`：上一个崩溃容器的日志（排查 CrashLoopBackOff 必备）

### Exec WebSocket 设计

```python
@router.websocket("/ws/pods/{name}/exec")
async def pod_exec_ws(websocket: WebSocket, config_id: str, name: str,
                      namespace: str, container: str | None,
                      command: str = "/bin/sh"):
    # 1. 鉴权
    # 2. build_client → core_v1.connect_get_namespaced_pod_exec(
    #        name, namespace, command=[command],
    #        stdin=True, stdout=True, stderr=True, tty=True,
    #        _preload_content=False)
    # 3. 双向转发: websocket.recv ↔ k8s stream
    # 4. 客户端 {"type": "input", "data": "..."} → stdin
    # 5. 服务端 stdout/stderr → {"type": "output", "data": "..."}
    # 6. 客户端 {"type": "resize", "cols": N, "rows": N} → channel 0 resize
```

兼容性处理：

- 有些镜像没有 `/bin/bash`，回退到 `/bin/sh`
- 前端提供命令切换下拉（bash / sh / 自定义）
- 容器未 running → 立即返回错误提示

### 错误处理统一约定

```python
class K8sError(BaseModel):
    code: str          # 'CONNECTION_FAILED' | 'FORBIDDEN' | 'NOT_FOUND' | 'METRICS_UNAVAILABLE' | 'TIMEOUT'
    message: str       # 中文可读消息
    k8s_reason: str    # 原始 K8s API 返回的 reason（用于调试）
    status_code: int | None
```

前端根据 `code` 显示不同提示，例如：

- `METRICS_UNAVAILABLE` → "该集群未安装 Metrics Server，监控指标不可用"（优雅降级）
- `FORBIDDEN` → "当前 kubeconfig 无权限访问该资源"

## 模块 3：前端布局与组件结构

### 整体布局

```
┌─────────────────────────────────────────────────────────────────────┐
│ TopBar: [ClusterSwitcher ▼] [NamespaceFilter ▼/All] [连接健康指示] │
├──────────┬──────────────────────────────────────────────────────────┤
│          │  ResourceTabs: [Pods] [Workloads] [Nodes] [Events]     │
│ Connect  │  ┌──────────────────────────────────────────────────┐  │
│  ionList │  │ 搜索框 + Label 筛选 + 状态筛选 (Running/Failed)  │  │
│          │  ├──────────────────────────────────────────────────┤  │
│ [新建]   │  │ 资源列表表格 (sortable, paginated)               │  │
│ [编辑]   │  │  - 状态图标 (绿/红/黄)                           │  │
│ [删除]   │  │  - 重启次数、运行时间、节点、IP                   │  │
│          │  │  - 点击行 → 右侧展开详情                          │  │
│  (类似   │  └──────────────────────────────────────────────────┘  │
│  SSH     │  ┌──────────────────────────────────────────────────┐  │
│  Tool)   │  │ ResourceDetail (右侧抽屉 / 下方面板)             │  │
│          │  │  - SubTabs:                                       │  │
│          │  │    [Overview][Containers][Logs][Terminal]         │  │
│          │  │    [YAML][Events][Metrics][Related]               │  │
│          │  └──────────────────────────────────────────────────┘  │
└──────────┴──────────────────────────────────────────────────────────┘
```

### 组件拆分

`frontend/src/components/Tools/K8sTool/`：

```
K8sTool/
├── K8sTool.tsx              # 主容器，管理连接列表、选中集群、namespace
├── types.ts                 # 类型定义
├── ConnectionList.tsx       # 左侧连接配置列表（复用 SSH 模式）
├── ConnectionModal.tsx      # 新建/编辑配置（3 种导入方式 Tab 切换）
│   ├── KubeconfigUploader.tsx     # 文件上传
│   ├── KubeconfigEditor.tsx       # 文本粘贴（带 YAML 语法高亮）
│   └── ManualForm.tsx             # 手动表单
├── TopBar/
│   ├── ClusterSwitcher.tsx        # 顶部集群切换下拉
│   └── NamespaceFilter.tsx        # namespace 筛选
├── ResourceTabs/
│   ├── PodList.tsx                # Pod 列表（带状态图标、重启次数）
│   ├── WorkloadList.tsx           # 统一工作负载列表（支持切换 Deployment/RS/STS/DS/Job/CronJob）
│   ├── NodeList.tsx               # Node 列表
│   └── EventsList.tsx             # 集群/namespace 级别事件流
├── ResourceDetail/
│   ├── PodDetail.tsx              # Pod 详情（含子 Tab）
│   ├── WorkloadDetail.tsx         # 工作负载详情（含关联 Pod 列表）
│   ├── NodeDetail.tsx
│   ├── OverviewPanel.tsx          # 标签、注解、状态、Owner Reference
│   ├── ContainersPanel.tsx        # 容器列表、状态、重启、镜像、资源限制
│   ├── LogsPanel.tsx              # 日志查看器
│   ├── YamlPanel.tsx              # YAML 只读（语法高亮 + 折叠）
│   ├── EventsPanel.tsx            # 资源相关 Events
│   ├── MetricsPanel.tsx           # CPU/内存折线图
│   └── RelatedPanel.tsx           # 关联 ConfigMap/Secret/PVC 跳转
├── LogsViewer/
│   ├── LogsViewer.tsx             # 日志主组件（WebSocket 驱动）
│   ├── LogsToolbar.tsx            # 容器选择、历史区间、follow 开关、搜索、下载
│   └── LogsContent.tsx            # 虚拟滚动日志行（高亮关键字）
├── TerminalPanel/                 # 复用 SSH 工具的 TerminalPanel 模式
└── EmptyState.tsx
```

### 关键交互设计

**集群切换**

- 顶部下拉显示当前激活的集群名
- 下拉列表按 `last_test_at` 排序，健康状态用圆点指示（绿/红/灰）
- 切换后清空 namespace 筛选、清空资源列表、重置详情

**Namespace 筛选**

- 下拉支持多选 + "All Namespaces"
- URL query 同步（`?namespace=prod&namespace=staging`），方便分享链接
- 切换到"All"时，Pod 列表增加 namespace 列

**资源列表 → 详情**

- 点击行 → 右侧展开抽屉（占屏宽 50-70%），不跳页
- 抽屉内子 Tab 切换：Overview / Containers / Logs / Terminal / YAML / Events / Metrics / Related
- 详情 URL：`/tools/k8s-tool/{config_id}/pod/{namespace}/{name}` 等（包含 config_id，支持多集群场景下刷新保持状态）

**日志查看器**

- 默认实时 tail + 最近 100 行历史
- 工具栏：容器下拉（多容器 Pod）、时间范围切换（最近 N 行 / N 分钟 / 自定义）、follow 开关、previous 开关
- 搜索框支持正则，匹配行高亮
- 虚拟滚动（日志量大时不卡）
- 下载按钮 → 当前缓冲区导出 `.txt`

**终端**

- 完全复用 SSH 工具的 `TerminalPanel` 模式（xterm.js + WebSocket）
- 命令下拉：`/bin/bash` / `/bin/sh` / 自定义
- 容器下拉（多容器 Pod）
- 多 Tab（同时打开多个 Pod 的终端，与 SSH 工具一致）

### 状态管理

```typescript
// zustand store
interface K8sStore {
  // 连接 & 上下文
  connections: K8sConnection[]
  activeConnectionId: string | null
  namespaces: string[]
  selectedNamespaces: string[]  // 多选

  // 资源
  resourceType: 'pods' | 'workloads' | 'nodes' | 'events'
  selectedResource: { type, namespace, name } | null

  // Actions
  loadConnections: () => Promise<void>
  setActiveConnection: (id: string) => void
  loadNamespaces: () => Promise<void>
  setSelectedResource: (r) => void
}
```

数据获取用 React Query：

- `useQuery(['k8s', configId, 'pods', namespaces], () => fetchPods(...))`
- `useQuery(['k8s', configId, 'pod', ns, name], () => fetchPodDetail(...))`
- 自动刷新：`refetchInterval: 10_000`（Pod 列表 10 秒刷新一次）

### 复用与抽离

SSH 工具的 `TerminalPanel`、`TabBar` 抽到 `frontend/src/components/shared/terminal/`，被两个工具共享。未来如果要加 Docker 控制台等工具也能复用。

## 模块 4：i18n / 错误处理 / 测试 / 集成

### 国际化

沿用项目现有模式，在 `frontend/src/i18n/locales/zh-CN.ts` 和 `en-US.ts` 增加 `k8s-tool` 命名空间：

```typescript
// zh-CN.ts
'k8s-tool': {
  title: 'K8s 控制台',
  connection: {
    addConfig: '新建连接',
    editConfig: '编辑连接',
    deleteConfirm: '确定删除连接 "{name}"？',
    sourceTypes: {
      kubeconfig_file: '上传 kubeconfig',
      kubeconfig_text: '粘贴配置文本',
      manual: '手动填写',
    },
    testSuccess: '连接测试成功',
    testFailed: '连接失败：{reason}',
    metricsAvailable: 'Metrics Server 可用',
    metricsUnavailable: 'Metrics Server 未安装',
  },
  resources: {
    pods: '容器组',
    deployments: '部署',
    replicasets: '副本集',
    statefulsets: '有状态集',
    daemonsets: '守护进程集',
    jobs: '任务',
    cronjobs: '定时任务',
    nodes: '节点',
    events: '事件',
  },
  status: {
    running: '运行中',
    pending: '等待中',
    failed: '失败',
    succeeded: '成功',
    crashed: '崩溃',
    unknown: '未知',
  },
  logs: {
    title: '日志',
    container: '容器',
    follow: '实时跟随',
    previous: '上一容器日志',
    search: '搜索日志（支持正则）',
    download: '下载日志',
    clear: '清空显示',
    noLogs: '暂无日志',
  },
  terminal: {
    title: '终端',
    command: '执行命令',
    connectFailed: '终端连接失败',
    disconnected: '已断开',
  },
  errors: {
    CONNECTION_FAILED: '无法连接到集群，请检查配置',
    FORBIDDEN: '当前配置无权限访问该资源',
    NOT_FOUND: '资源不存在',
    METRICS_UNAVAILABLE: '该集群未安装 Metrics Server，监控指标不可用',
    TIMEOUT: '请求超时',
  },
}
```

### 错误处理分层

| 层级 | 处理方式 |
|------|---------|
| K8s API 错误 | 后端捕获 `kubernetes.client.ApiException`，映射成统一的 `K8sError(code, message, k8s_reason, status_code)` |
| 后端业务错误 | HTTPException + 中文消息 |
| WebSocket 错误 | 发送 `{"type": "error", "code": "...", "message": "..."}` 帧，前端显示 toast |
| 前端展示 | 根据 `error.code` 查 i18n 字典，显示友好提示；开发模式下额外显示 `k8s_reason` |

### 优雅降级矩阵

| 场景 | 行为 |
|------|------|
| Metrics Server 未安装 | 监控 Tab 显示"不可用"提示 + 重新检测按钮，其他功能正常 |
| Pod 没有 bash | 终端默认回退到 `/bin/sh`，失败时提示用户手动指定命令 |
| 容器非 Running 状态 | 终端按钮禁用 + tooltip 提示；日志自动开启 `previous=true` |
| kubeconfig 证书过期 | 连接列表红点 + 错误消息，点击重新测试 |
| 集群不可达 | 顶部集群切换器旁显示红色图标，自动重试 3 次后提示 |

### 测试策略

**后端单元测试**（`backend/tests/test_k8s_tool_*.py`）

| 文件 | 覆盖点 |
|------|--------|
| `test_k8s_config_parsing.py` | kubeconfig 解析（多 context、各种 auth_type、非法格式） |
| `test_k8s_config_encryption.py` | Fernet 加解密、密钥缺失报错、响应脱敏 |
| `test_k8s_client_factory.py` | 客户端构造、context manager 释放、异常路径 |
| `test_k8s_resource_apis.py` | 资源列表/详情/mock K8s API 调用（用 `unittest.mock` 模拟 kubernetes 客户端） |
| `test_k8s_websocket.py` | 日志/exec WebSocket 握手、鉴权、错误帧（用 FastAPI TestClient WebSocket） |

**前端单元测试**（`frontend/src/components/Tools/K8sTool/*.test.tsx`）

| 文件 | 覆盖点 |
|------|--------|
| `ConnectionModal.test.tsx` | 三种导入方式的表单切换、校验、提交 |
| `PodList.test.tsx` | 状态图标渲染、排序、分页、筛选 |
| `LogsViewer.test.tsx` | WebSocket mock、follow 切换、搜索高亮 |
| `NamespaceFilter.test.tsx` | 多选、URL 同步 |

**E2E 测试（可选）**：用 Playwright 覆盖"上传 kubeconfig → 切换集群 → 查看 Pod 列表 → 打开日志"主流程（需要一个本地 K3s/KinD 集群）。

### 集成点

**App.tsx 注册**

```typescript
// toolRoutes 新增
'k8s-tool': '/tools/k8s-tool',
// Route 新增
<Route path="/tools/k8s-tool" element={<K8sTool />} />
```

**工具注册（后端 tools 列表）**

在 `backend/app/routes/tools.py` 增加一条工具元数据，让首页能显示 K8s 控制台入口。

**数据库迁移**

`K8sConnection` 表通过 SQLAlchemy `Base.metadata.create_all()` 在启动时创建（沿用项目现有模式，`CREATE TABLE IF NOT EXISTS`，支持幂等）。

**环境变量**

```bash
# .env 新增
K8S_FERNET_KEY=<32 字节 base64 编码密钥>
```

启动时检测，缺失则报错退出。提供生成脚本：

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**依赖新增**

```txt
# backend/requirements.txt
kubernetes_asyncio==29.0.0
cryptography>=41.0.0  # Fernet
pyyaml>=6.0           # kubeconfig 解析 (已有则复用)
```

```json
// frontend/package.json
"@xterm/xterm": "^5.x"
"@xterm/addon-fit": "^0.x"
"@xterm/addon-web-links": "^0.x"
"recharts": "^2.x"
"react-dropzone": "^14.x"
"monaco-editor" 或 "prism-react-renderer"  // YAML / kubeconfig 文本编辑高亮
```

> **决策**：选用 `prism-react-renderer`。YAML 查看是只读场景，不需要 Monaco 的编辑能力；prism 体积小（~30KB gzipped）、启动快，符合 YAGNI。kubeconfig 文本粘贴编辑器也用 prism，通过 textarea + 同步高亮层实现。

### 文件组织

```
backend/app/
├── models/k8s_tool_models.py          # K8sConnection 模型
├── schemas/k8s_tool_schemas.py        # Pydantic 请求/响应模型
├── routes/k8s_tool.py                 # REST + WebSocket 路由
├── services/
│   ├── k8s_tool_service.py            # 连接配置 CRUD
│   ├── k8s_client_factory.py          # ApiClient 构造
│   ├── k8s_resource_service.py        # 资源查询 (pod/workload/node/event)
│   ├── k8s_log_service.py             # 日志流处理
│   ├── k8s_exec_service.py            # exec 流处理
│   └── k8s_metrics_service.py         # 指标查询 + 降级
└── utils/
    ├── k8s_config_parser.py           # kubeconfig 解析、context 拆分
    └── encryption.py                  # Fernet 加解密工具（可能已有）
```

```
frontend/src/
├── api/k8sToolApi.ts                   # HTTP/WS 客户端封装
├── stores/k8sStore.ts                  # zustand store
├── hooks/
│   ├── useK8sClient.ts                 # React Query 封装
│   ├── useK8sLogs.ts                   # 日志 WebSocket hook
│   └── useK8sExec.ts                   # exec WebSocket hook
└── components/
    ├── Tools/K8sTool/                   # 主工具目录（见上文组件拆分）
    └── shared/terminal/                 # 抽离的共享 TerminalPanel (SSH + K8s 共用)
```

## 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| kubeconfig 加密密钥泄露 | 所有集群凭证暴露 | 密钥只存环境变量，不入代码库；生产环境通过 secrets manager 注入；DB 字段加密存储 |
| kubernetes_asyncio 长连接堆积 | FastAPI 主进程被拖慢 | 设置 ApiClient 连接池上限；日志/exec WebSocket 增加空闲超时（默认 30 分钟无活动断开） |
| K8s API 限流（高 refetch 频率） | 集群 API Server 压力 | React Query `refetchInterval` 默认 10s，用户可在设置中调整；列表接口用 `resourceVersion` 做 watch 优化（v2） |
| 某些集群禁用了 exec | 终端功能不可用 | 后端捕获 Forbidden，前端优雅提示 |
| Secret 数据明文返回 | 审计风险 | 后端通过 Python `logging` 记录审计信息（user_id、config_id、secret_name、timestamp）；前端提供"隐藏/显示"开关，默认隐藏 |

## 后续演进（v2 方向，本次不做）

- 完整资源类型（Service / Ingress / RBAC / CRD / HPA 等）
- 写操作（扩缩容、删除 Pod、rollout restart）配合二次确认 + 审计日志
- 多集群聚合视图（跨集群搜索 Pod）
- Watch 长连接优化（用 K8s watch API 替代轮询，减少 API Server 压力）
- 云厂商 API 自动拉取 kubeconfig（ACK/TKE/EKS）
- Helm releases 查看
- K8s 事件告警推送（WebSocket 推送新 Warning Event）
