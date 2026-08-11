# K8s 控制台体验优化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化 K8s 控制台用户体验：改进错误提示、完善编辑模式、支持拖动排序。

**Architecture:** 
- Phase 1: 后端检测 namespace 权限不足错误，前端显示友好提示
- Phase 2: 编辑模式展示完整配置，支持重新输入敏感字段
- Phase 3: 数据库添加 sort_order 字段，前端使用 @dnd-kit 实现拖动排序

**Tech Stack:** React 18, TypeScript, Zustand, @tanstack/react-query, @dnd-kit/core, FastAPI, PostgreSQL

## Global Constraints

- 所有对话、文档、注释、日志、提交信息必须使用中文
- 修改前后端代码后，必须使用浏览器进行验证
- 前端端口 5178，后端端口 19092
- 服务重启统一用 `python dev-services.py restart`
- TypeScript 文件修改后需验证编译无错误
- 每个任务需编写测试并验证通过

---

### Task 1: 后端 - 优化错误码识别

**Files:**
- Modify: `backend/app/services/k8s_resource_service.py`

**Interfaces:**
- Consumes: `kubernetes_asyncio.client.ApiException`
- Produces: `K8sApiException` with special error code for namespace forbidden

- [ ] **Step 1: 修改 _api_exception_to_k8s_error 函数**

在 `k8s_resource_service.py` 中找到 `_api_exception_to_k8s_error` 函数（约第 337 行），修改为：

```python
def _api_exception_to_k8s_error(e: ApiException) -> K8sApiException:
    """K8s ApiException → K8sApiException"""
    code_map = {
        401: "CONNECTION_FAILED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        408: "TIMEOUT",
    }
    
    # 检测是否是 namespace 权限不足
    is_namespace_forbidden = (
        e.status == 403 and 
        e.body and 
        "namespaces is forbidden" in str(e.body)
    )
    
    return K8sApiException(K8sError(
        code="NAMESPACE_FORBIDDEN" if is_namespace_forbidden else code_map.get(e.status, "CONNECTION_FAILED"),
        message=f"K8s API 错误：{e.reason}",
        k8s_reason=str(e.body) if e.body else "",
        status_code=e.status,
    ))
```

- [ ] **Step 2: 验证语法**

Run: `cd backend && python -m py_compile app/services/k8s_resource_service.py`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/k8s_resource_service.py
git commit -m "feat(k8s): 添加 namespace 权限不足的特殊错误码"
```

---

### Task 2: 前端 - 优化 NamespaceFilter 错误提示

**Files:**
- Modify: `frontend/src/components/Tools/K8sTool/TopBar/NamespaceFilter.tsx`

**Interfaces:**
- Consumes: `useK8sNamespaces` hook error state
- Produces: 友好提示 UI

- [ ] **Step 1: 修改 NamespaceFilter 组件**

在 `NamespaceFilter.tsx` 中，找到显示 namespace 列表为空的部分（约第 170-174 行），替换为：

```tsx
{namespaces.length === 0 && (
  <div className="px-3 py-4 text-sm text-center">
    {isError ? (
      <div className="text-yellow-400">
        <i className="fas fa-exclamation-triangle mr-2"></i>
        无法获取命名空间列表
        <br />
        <span className="text-xs text-slate-500">
          请在编辑配置时指定命名空间过滤
        </span>
      </div>
    ) : (
      k8sT.emptyConnections
    )}
  </div>
)}
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Tools/K8sTool/TopBar/NamespaceFilter.tsx
git commit -m "feat(k8s): NamespaceFilter 显示友好错误提示"
```

---

### Task 3: 后端 - 添加更新认证信息 API

**Files:**
- Create: `backend/app/models/k8s_tool_models.py` (add `UpdateK8sAuthRequest`)
- Modify: `backend/app/services/k8s_tool_service.py` (add `update_config_auth` method)
- Modify: `backend/app/routes/k8s_tool.py` (add endpoint)

**Interfaces:**
- Consumes: 配置 ID、新的认证信息
- Produces: 更新后的 `K8sConfigResponse`

- [ ] **Step 1: 添加 UpdateK8sAuthRequest 模型**

在 `k8s_tool_models.py` 中添加：

```python
class UpdateK8sAuthRequest(BaseModel):
    """更新连接认证信息请求"""
    id: str
    token: Optional[str] = None  # bearer_token
    client_cert: Optional[str] = None  # client_cert
    client_key: Optional[str] = None  # client_cert
    username: Optional[str] = None  # basic_auth
    password: Optional[str] = None  # basic_auth
    ca_cert: Optional[str] = None  # 所有类型通用
```

- [ ] **Step 2: 添加 update_config_auth 方法**

在 `k8s_tool_service.py` 中添加：

```python
@staticmethod
def update_config_auth(
    user_id: str, request: UpdateK8sAuthRequest
) -> K8sConfigResponse:
    """更新连接的认证信息（仅更新提供的字段）"""
    K8sToolService._ensure_table()
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        # 检查配置是否存在
        cursor.execute(
            "SELECT id, auth_type FROM k8s_connections WHERE id = %s AND user_id = %s AND deleted = FALSE",
            (request.id, user_id),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("连接配置不存在或无权操作")
        
        auth_type = row['auth_type']
        update_fields = ["updated_at = %s"]
        params: list = [datetime.now()]
        
        # 根据认证类型更新对应字段
        auth_data_updates = {}
        
        if auth_type == 'bearer_token' and request.token:
            auth_data_updates['token'] = request.token
        
        if auth_type == 'client_cert':
            if request.client_cert:
                auth_data_updates['client_cert'] = request.client_cert
            if request.client_key:
                auth_data_updates['client_key'] = request.client_key
        
        if auth_type == 'basic_auth':
            if request.username:
                auth_data_updates['username'] = request.username
            if request.password:
                auth_data_updates['password'] = request.password
        
        # 如果有认证数据更新
        if auth_data_updates:
            # 先获取现有的 auth_data
            cursor.execute(
                "SELECT auth_data_encrypted FROM k8s_connections WHERE id = %s",
                (request.id,),
            )
            existing_row = cursor.fetchone()
            if existing_row and existing_row['auth_data_encrypted']:
                # 解密现有数据
                existing_decrypted = EncryptionUtils.decrypt(existing_row['auth_data_encrypted'])
                existing_data = json.loads(existing_decrypted)
                # 合并更新
                existing_data.update(auth_data_updates)
                auth_data_encrypted = EncryptionUtils.encrypt(json.dumps(existing_data))
            else:
                auth_data_encrypted = EncryptionUtils.encrypt(json.dumps(auth_data_updates))
            
            update_fields.append("auth_data_encrypted = %s")
            params.append(auth_data_encrypted)
        
        # CA 证书更新
        if request.ca_cert:
            ca_cert_encrypted = EncryptionUtils.encrypt(request.ca_cert)
            update_fields.append("ca_cert_encrypted = %s")
            params.append(ca_cert_encrypted)
        
        params.extend([request.id, user_id])
        
        cursor.execute(
            f"UPDATE k8s_connections SET {', '.join(update_fields)} WHERE id = %s AND user_id = %s AND deleted = FALSE",
            params,
        )
        conn.commit()
        
        if cursor.rowcount == 0:
            raise ValueError("连接配置不存在或无权操作")
        
        # 返回更新后的配置
        cursor.execute("SELECT * FROM k8s_connections WHERE id = %s", (request.id,))
        row = cursor.fetchone()
        return K8sToolService._row_to_response(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        release_db_connection(conn)
```

- [ ] **Step 3: 添加 API 端点**

在 `k8s_tool.py` 中添加：

```python
@router.post("/configs/update-auth", response_model=K8sConfigResponse)
async def update_config_auth(
    request: UpdateK8sAuthRequest,
    user_id: str = Depends(get_current_user_id),
):
    """更新连接的认证信息（token/cert/key 等）"""
    try:
        return K8sToolService.update_config_auth(user_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

- [ ] **Step 4: 验证语法**

Run: `cd backend && python -m py_compile app/routes/k8s_tool.py`
Expected: 无错误

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/k8s_tool_models.py backend/app/services/k8s_tool_service.py backend/app/routes/k8s_tool.py
git commit -m "feat(k8s): 添加更新认证信息 API"
```

---

### Task 4: 前端 - 完善编辑模式 UI

**Files:**
- Modify: `frontend/src/components/Tools/K8sTool/ConnectionModal.tsx`

**Interfaces:**
- Consumes: `K8sConnection` with full info
- Produces: Enhanced edit form with auth fields

- [ ] **Step 1: 修改编辑模式 UI**

在 `ConnectionModal.tsx` 中，找到编辑模式的渲染部分（约第 289-331 行），替换为：

```tsx
{isEditing ? (
  <div className="space-y-4">
    {/* 只读展示的连接信息 */}
    <div className="bg-slate-900 rounded-md p-3 border border-slate-700">
      <div className="text-xs text-slate-500 mb-2">连接信息</div>
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <i className="fas fa-server text-xs text-slate-400"></i>
          <span className="text-sm text-slate-300">{initialData.server}</span>
        </div>
        <div className="flex items-center gap-2">
          <i className="fas fa-key text-xs text-slate-400"></i>
          <span className="text-sm text-slate-300">
            {k8sT.modal.authTypes[initialData.auth_type]}
            {initialData.has_auth_data && <i className="fas fa-check-circle ml-1 text-green-400"></i>}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <i className="fas fa-shield-alt text-xs text-slate-400"></i>
          <span className="text-sm text-slate-300">
            {initialData.has_ca_cert ? '已配置 CA 证书' : '使用系统 CA'}
          </span>
        </div>
      </div>
    </div>

    {/* 可编辑的字段 */}
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-1">
        {k8sT.modal.fields.name}
      </label>
      <input
        type="text"
        required
        className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
        value={editName}
        onChange={e => setEditName(e.target.value)}
      />
    </div>

    {/* 敏感字段重新输入 */}
    {initialData.auth_type === 'bearer_token' && (
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          {k8sT.modal.fields.token}
          <span className="text-xs text-slate-500 ml-2">（留空表示不修改）</span>
        </label>
        <input
          type="password"
          className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          placeholder="输入新的 token，留空则保持原值"
          value={editToken}
          onChange={e => setEditToken(e.target.value)}
        />
      </div>
    )}

    {initialData.auth_type === 'client_cert' && (
      <>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            {k8sT.modal.fields.clientCert}
            <span className="text-xs text-slate-500 ml-2">（留空表示不修改）</span>
          </label>
          <textarea
            rows={3}
            className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500 resize-y"
            placeholder="输入新的证书，留空则保持原值"
            value={editClientCert}
            onChange={e => setEditClientCert(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            {k8sT.modal.fields.clientKey}
            <span className="text-xs text-slate-500 ml-2">（留空表示不修改）</span>
          </label>
          <textarea
            rows={3}
            className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500 resize-y"
            placeholder="输入新的私钥，留空则保持原值"
            value={editClientKey}
            onChange={e => setEditClientKey(e.target.value)}
          />
        </div>
      </>
    )}

    {initialData.auth_type === 'basic_auth' && (
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            {k8sT.modal.fields.username}
            <span className="text-xs text-slate-500 ml-2">（留空表示不修改）</span>
          </label>
          <input
            type="text"
            className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            placeholder="输入新的用户名"
            value={editUsername}
            onChange={e => setEditUsername(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            {k8sT.modal.fields.password}
            <span className="text-xs text-slate-500 ml-2">（留空表示不修改）</span>
          </label>
          <input
            type="password"
            className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            placeholder="输入新的密码"
            value={editPassword}
            onChange={e => setEditPassword(e.target.value)}
          />
        </div>
      </div>
    )}

    {/* CA 证书 */}
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-1">
        {k8sT.modal.fields.caCert}
        <span className="text-xs text-slate-500 ml-2">（留空表示不修改）</span>
      </label>
      <textarea
        rows={2}
        className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500 resize-y"
        placeholder="输入新的 CA 证书，留空则保持原值"
        value={editCaCert}
        onChange={e => setEditCaCert(e.target.value)}
      />
    </div>

    {/* 命名空间过滤 */}
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-1">
        {k8sT.modal.fields.namespaceFilter}
      </label>
      <input
        type="text"
        className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
        placeholder={k8sT.modal.fields.namespaceHint}
        value={editNamespaceFilter}
        onChange={e => setEditNamespaceFilter(e.target.value)}
      />
    </div>

    {/* 测试连接 + 保存按钮 */}
    <div className="flex items-center gap-3">
      <button
        type="button"
        disabled={isTesting}
        onClick={() => handleTestConnection(initialData!.id)}
        className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-md text-sm font-medium text-slate-200 hover:bg-slate-600 transition-colors disabled:opacity-60"
      >
        {isTesting ? k8sT.testing : k8sT.testConnection}
      </button>
      {testMessage && (
        <span className={`text-sm ${testStatus === 'success' ? 'text-green-400' : 'text-red-400'}`}>
          {testMessage}
        </span>
      )}
    </div>
  </div>
) : (
  // 新建模式保持不变...
)}
```

- [ ] **Step 2: 添加编辑模式状态**

在组件顶部添加新的状态变量（在 `editNamespaceFilter` 附近）：

```tsx
// 编辑模式敏感字段状态
const [editToken, setEditToken] = useState('');
const [editClientCert, setEditClientCert] = useState('');
const [editClientKey, setEditClientKey] = useState('');
const [editUsername, setEditUsername] = useState('');
const [editPassword, setEditPassword] = useState('');
const [editCaCert, setEditCaCert] = useState('');
```

- [ ] **Step 3: 修改 useEffect 初始化**

在 `useEffect` 中重置所有编辑状态：

```tsx
useEffect(() => {
  if (!isOpen) return;
  if (initialData) {
    setEditName(initialData.name);
    setEditNamespaceFilter(initialData.namespace_filter.join(', '));
    // 重置敏感字段
    setEditToken('');
    setEditClientCert('');
    setEditClientKey('');
    setEditUsername('');
    setEditPassword('');
    setEditCaCert('');
  }
  // ... 其他重置逻辑
}, [isOpen, initialData]);
```

- [ ] **Step 4: 修改保存逻辑**

修改 `handleEditSave` 函数，支持更新认证信息：

```tsx
const handleEditSave = async () => {
  if (!initialData || !editName.trim()) return;
  setIsSaving(true);
  try {
    // 先更新基本信息
    const updatedConfig = await api.updateK8sConfig({
      id: initialData.id,
      name: editName.trim(),
      namespace_filter: parseNamespaceFilter(editNamespaceFilter),
    });

    // 如果有敏感字段更新，调用 update-auth API
    const hasAuthUpdates = 
      (initialData.auth_type === 'bearer_token' && editToken) ||
      (initialData.auth_type === 'client_cert' && (editClientCert || editClientKey)) ||
      (initialData.auth_type === 'basic_auth' && (editUsername || editPassword)) ||
      editCaCert;

    if (hasAuthUpdates) {
      await api.updateK8sConfigAuth({
        id: initialData.id,
        token: editToken || undefined,
        client_cert: editClientCert || undefined,
        client_key: editClientKey || undefined,
        username: editUsername || undefined,
        password: editPassword || undefined,
        ca_cert: editCaCert || undefined,
      });
    }

    addToast(k8sT.saveSuccess, 'success');

    // 立即刷新连接列表
    queryClient.invalidateQueries({ queryKey: ['k8s', 'connections'] });

    // 如果编辑的是当前活跃连接，更新 store 中的 namespace_filter
    if (updatedConfig.namespace_filter) {
      const { setNamespaces } = useK8sStore.getState();
      setNamespaces(updatedConfig.namespace_filter);
    }

    onClose();
  } catch (err) {
    addToast(err instanceof Error ? err.message : t.common.error, 'error');
  } finally {
    setIsSaving(false);
  }
};
```

- [ ] **Step 5: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增错误

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Tools/K8sTool/ConnectionModal.tsx
git commit -m "feat(k8s): 完善编辑模式 UI，支持重新输入敏感字段"
```

---

### Task 5: 前端 - 添加 update-auth API

**Files:**
- Modify: `frontend/src/api/k8sToolApi.ts`

**Interfaces:**
- Consumes: auth update payload
- Produces: `K8sConnection`

- [ ] **Step 1: 添加 updateK8sConfigAuth API**

在 `k8sToolApi.ts` 中添加：

```typescript
export const updateK8sConfigAuth = async (
  payload: {
    id: string;
    token?: string;
    client_cert?: string;
    client_key?: string;
    username?: string;
    password?: string;
    ca_cert?: string;
  }
): Promise<K8sConnection> => {
  const response = await fetch(`${API_BASE}/k8s-tool/configs/update-auth`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('token')}`,
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '更新认证信息失败');
  }
  return response.json();
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/k8sToolApi.ts
git commit -m "feat(k8s): 添加更新认证信息 API"
```

---

### Task 6: 后端 - 添加排序支持

**Files:**
- Modify: `backend/app/services/k8s_tool_service.py`
- Modify: `backend/app/routes/k8s_tool.py`
- Create: `backend/app/models/k8s_tool_models.py` (add `UpdateConfigSortRequest`)

**Interfaces:**
- Consumes: config ID list
- Produces: sorted connections

- [ ] **Step 1: 添加 UpdateConfigSortRequest 模型**

在 `k8s_tool_models.py` 中添加：

```python
class UpdateConfigSortRequest(BaseModel):
    """更新连接配置排序请求"""
    config_ids: List[str]
```

- [ ] **Step 2: 添加 update_sort_order 方法**

在 `k8s_tool_service.py` 中添加：

```python
@staticmethod
def update_sort_order(
    user_id: str, config_ids: List[str]
) -> None:
    """批量更新连接配置的排序顺序"""
    K8sToolService._ensure_table()
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        for idx, config_id in enumerate(config_ids):
            cursor.execute(
                "UPDATE k8s_connections SET sort_order = %s, updated_at = %s WHERE id = %s AND user_id = %s AND deleted = FALSE",
                (idx, datetime.now(), config_id, user_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        release_db_connection(conn)
```

- [ ] **Step 3: 添加 API 端点**

在 `k8s_tool.py` 中添加：

```python
@router.post("/configs/sort")
async def update_config_sort(
    request: UpdateConfigSortRequest,
    user_id: str = Depends(get_current_user_id),
):
    """批量更新连接配置的排序顺序"""
    try:
        K8sToolService.update_sort_order(user_id, request.config_ids)
        return {"message": "排序已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/k8s_tool_models.py backend/app/services/k8s_tool_service.py backend/app/routes/k8s_tool.py
git commit -m "feat(k8s): 添加连接配置排序 API"
```

---

### Task 7: 前端 - 添加排序 API

**Files:**
- Modify: `frontend/src/api/k8sToolApi.ts`

- [ ] **Step 1: 添加 updateK8sConfigSort API**

```typescript
export const updateK8sConfigSort = async (
  configIds: string[]
): Promise<void> => {
  const response = await fetch(`${API_BASE}/k8s-tool/configs/sort`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('token')}`,
    },
    body: JSON.stringify({ config_ids: configIds }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '更新排序失败');
  }
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/k8sToolApi.ts
git commit -m "feat(k8s): 添加更新排序 API"
```

---

### Task 8: 前端 - 安装 @dnd-kit 并实现拖动排序

**Files:**
- Modify: `frontend/package.json` (add @dnd-kit dependencies)
- Modify: `frontend/src/components/Tools/K8sTool/ConnectionList.tsx`

- [ ] **Step 1: 安装依赖**

Run: `cd frontend && npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities`

- [ ] **Step 2: 修改 ConnectionList 组件**

添加拖动排序功能（参考设计文档中的代码）。

- [ ] **Step 3: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增错误

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/src/components/Tools/K8sTool/ConnectionList.tsx
git commit -m "feat(k8s): 实现连接配置拖动排序"
```

---

## 总结

本实现计划共 8 个任务：

1. **Task 1**: 后端添加 namespace 权限不足错误码
2. **Task 2**: 前端显示友好错误提示
3. **Task 3**: 后端添加更新认证信息 API
4. **Task 4**: 前端完善编辑模式 UI
5. **Task 5**: 前端添加 update-auth API
6. **Task 6**: 后端添加排序 API
7. **Task 7**: 前端添加排序 API
8. **Task 8**: 前端实现拖动排序

预计总工时：3-4 天
