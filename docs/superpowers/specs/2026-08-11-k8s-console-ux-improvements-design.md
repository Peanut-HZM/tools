# K8s 控制台体验优化设计文档

**日期**: 2026-08-11  
**状态**: 待实现  
**优先级**: 中  

---

## 需求分析

### 需求 1：错误提示优化

**问题**：当 K8s ServiceAccount 没有 RBAC 权限列出所有 namespace 时，前端显示 "Failed to fetch"，用户不知道如何解决。

**现状**：
- `useK8sNamespaces` hook 调用 `/api/k8s-tool/{id}/namespaces`
- 后端返回 403 Forbidden
- 前端显示红色错误提示 "Failed to fetch"

**目标**：显示友好提示，引导用户在编辑配置时指定 namespace_filter。

---

### 需求 2：编辑集群连接配置

**问题**：编辑模式下只展示名称和命名空间过滤字段，用户无法查看完整的连接配置（server、auth_type 等）。

**现状**：
- 后端 API 返回脱敏数据（`has_auth_data`、`has_ca_cert` 布尔标志）
- 前端编辑模式只展示 name 和 namespace_filter

**目标**：
- 编辑模式下展示完整配置（server、auth_type、cluster_name 等）
- 敏感字段（token/cert/key）不展示原文，但支持重新输入
- 确保修改后能正确生效

---

### 需求 3：集群连接排序

**问题**：集群连接列表默认按创建时间排序，用户希望按名称排序，并支持自定义拖动排序。

**现状**：
- 后端 `get_configs` 按 `created_at DESC` 排序
- 前端无排序功能

**目标**：
- 默认按名称排序
- 支持拖动自定义排序
- 排序结果持久化到数据库

---

## 解决方案

### 方案 1：错误提示优化

#### 1.1 后端修改

**文件**：`backend/app/services/k8s_resource_service.py`

**修改**：在 `_api_exception_to_k8s_error` 函数中，当错误是 403 Forbidden 且原因是 namespace 权限不足时，返回特殊错误码：

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
        message=f"K8s API 错误: {e.reason}",
        k8s_reason=str(e.body) if e.body else "",
        status_code=e.status,
    ))
```

#### 1.2 前端修改

**文件**：`frontend/src/hooks/useK8sClient.ts`

**修改**：在 `useK8sNamespaces` hook 中捕获错误，返回特殊标志：

```typescript
export const useK8sNamespaces = (configId: string | null) => {
  const { setNamespaces } = useK8sStore();
  const [error, setError] = useState<'forbidden' | null>(null);
  
  return useQuery({
    queryKey: ['k8s', configId, 'namespaces'],
    queryFn: async () => {
      if (!configId) return [];
      try {
        const data = await api.listNamespaces(configId);
        const names = data.map((n) => n.name);
        setNamespaces(names);
        setError(null);
        return data;
      } catch (err: any) {
        if (err?.response?.data?.error?.code === 'NAMESPACE_FORBIDDEN') {
          setError('forbidden');
        } else {
          setError(null);
        }
        throw err;
      }
    },
    enabled: !!configId,
  });
};
```

**文件**：`frontend/src/components/Tools/K8sTool/TopBar/NamespaceFilter.tsx`

**修改**：显示友好提示：

```tsx
const { isError, error } = useK8sNamespaces(activeConnectionId);

// 在 namespace 列表为空时显示提示
{namespaces.length === 0 && (
  <div className="px-3 py-4 text-sm text-center">
    {error === 'forbidden' ? (
      <div className="text-yellow-400">
        <i className="fas fa-exclamation-triangle mr-2"></i>
        无法获取命名空间列表<br/>
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

---

### 方案 2：编辑集群连接配置

#### 2.1 后端修改

**文件**：`backend/app/routes/k8s_tool.py`

**修改**：保持现状，不返回敏感字段原文（安全考虑）。

**文件**：`backend/app/models/k8s_tool_models.py`

**修改**：添加 `has_auth_data`、`has_ca_cert` 字段（已存在）。

#### 2.2 前端修改

**文件**：`frontend/src/components/Tools/K8sTool/ConnectionModal.tsx`

**修改**：编辑模式下展示完整配置：

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

    {/* 其他认证类型类似... */}

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
    ...
  </div>
) : (
  // 新建模式...
)}
```

**文件**：`frontend/src/api/k8sToolApi.ts`

**修改**：添加更新敏感字段的 API：

```typescript
export const updateK8sConfigWithAuth = async (
  payload: UpdateK8sManualRequest
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
    throw new Error(error.detail || '更新配置失败');
  }
  return response.json();
};
```

**文件**：`backend/app/routes/k8s_tool.py`

**修改**：添加更新敏感字段的 API：

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

**文件**：`backend/app/services/k8s_tool_service.py`

**修改**：添加 `update_config_auth` 方法：

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
        if auth_type == 'bearer_token' and request.token:
            auth_data = {"token": request.token}
            auth_data_encrypted = EncryptionUtils.encrypt(json.dumps(auth_data))
            update_fields.append("auth_data_encrypted = %s")
            params.append(auth_data_encrypted)
        
        # client_cert 和 basic_auth 类似...
        
        params.extend([request.id, user_id])
        
        cursor.execute(
            f"UPDATE k8s_connections SET {', '.join(update_fields)} WHERE id = %s AND user_id = %s AND deleted = FALSE",
            params,
        )
        conn.commit()
        
        # 返回更新后的配置
        cursor.execute("SELECT * FROM k8s_connections WHERE id = %s", (request.id,))
        row = cursor.fetchone()
        return K8sToolService._row_to_response(row)
    finally:
        cursor.close()
        release_db_connection(conn)
```

---

### 方案 3：集群连接排序

#### 3.1 数据库修改

**文件**：`backend/app/services/k8s_tool_service.py`

**修改**：添加 `sort_order` 字段：

```python
@staticmethod
def _ensure_table():
    """创建 k8s_connections 表（幂等，可重复执行）"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS k8s_connections (
                id VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                name VARCHAR(128) NOT NULL,
                source_type VARCHAR(32) NOT NULL,
                cluster_name VARCHAR(255) NOT NULL,
                context_name VARCHAR(255) NOT NULL,
                server VARCHAR(512) NOT NULL,
                auth_type VARCHAR(32) NOT NULL,
                auth_data_encrypted TEXT,
                ca_cert_encrypted TEXT,
                namespace_filter TEXT DEFAULT '[]',
                is_metrics_available BOOLEAN DEFAULT FALSE,
                last_test_at TIMESTAMP,
                last_test_error TEXT,
                sort_order INTEGER DEFAULT 0,  -- 新增字段
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_k8s_conn_user "
            "ON k8s_connections(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_k8s_conn_user_deleted "
            "ON k8s_connections(user_id, deleted)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_k8s_conn_user_sort "
            "ON k8s_connections(user_id, sort_order, name)"
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        release_db_connection(conn)
```

#### 3.2 后端 API 修改

**文件**：`backend/app/services/k8s_tool_service.py`

**修改**：`get_configs` 方法按 `sort_order` 排序：

```python
@staticmethod
def get_configs(user_id: str) -> List[K8sConfigResponse]:
    """获取当前用户的所有连接配置（脱敏，不含敏感字段原文）"""
    K8sToolService._ensure_table()
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM k8s_connections "
            "WHERE user_id = %s AND deleted = FALSE "
            "ORDER BY sort_order ASC, name ASC",  -- 修改排序逻辑
            (user_id,),
        )
        rows = cursor.fetchall()
        return [K8sToolService._row_to_response(row) for row in rows]
    finally:
        cursor.close()
        release_db_connection(conn)
```

**修改**：添加更新排序的 API：

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

**文件**：`backend/app/routes/k8s_tool.py`

**修改**：添加更新排序的 API：

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

#### 3.3 前端修改

**文件**：`frontend/src/api/k8sToolApi.ts`

**修改**：添加更新排序的 API：

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

**文件**：`frontend/src/components/Tools/K8sTool/ConnectionList.tsx`

**修改**：使用 `@dnd-kit/sortable` 实现拖动排序：

```tsx
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface Props {
  configs: K8sConnection[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAdd: () => void;
  onEdit: (config: K8sConnection) => void;
  onDelete: (id: string) => void;
  onSortEnd: (configIds: string[]) => void;  // 新增
}

const SortableConnectionItem: React.FC<{
  conn: K8sConnection;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onEdit: (config: K8sConnection) => void;
  onDelete: (id: string) => void;
}> = ({ conn, selectedId, onSelect, onEdit, onDelete }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: conn.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  // ... 渲染逻辑
};

export const ConnectionList: React.FC<Props> = ({
  configs,
  selectedId,
  onSelect,
  onAdd,
  onEdit,
  onDelete,
  onSortEnd,
}) => {
  const [items, setItems] = useState(configs);
  
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    
    if (over && active.id !== over.id) {
      const oldIndex = items.findIndex(item => item.id === active.id);
      const newIndex = items.findIndex(item => item.id === over.id);
      
      const newItems = arrayMove(items, oldIndex, newIndex);
      setItems(newItems);
      onSortEnd(newItems.map(item => item.id));
    }
  };

  useEffect(() => {
    setItems(configs);
  }, [configs]);

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={items.map(item => item.id)} strategy={verticalListSortingStrategy}>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {items.map(conn => (
            <SortableConnectionItem
              key={conn.id}
              conn={conn}
              selectedId={selectedId}
              onSelect={onSelect}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
};
```

---

## 实施计划

### Phase 1：错误提示优化（1 天）

1. 后端：修改 `_api_exception_to_k8s_error` 函数
2. 前端：修改 `useK8sNamespaces` hook
3. 前端：修改 `NamespaceFilter` 组件
4. 测试：验证 403 错误时显示友好提示

### Phase 2：编辑集群连接配置（2 天）

1. 后端：添加 `update_config_auth` 方法
2. 后端：添加 `/configs/update-auth` API
3. 前端：修改 `ConnectionModal` 组件（编辑模式）
4. 前端：添加 `updateK8sConfigWithAuth` API
5. 测试：验证编辑功能正常

### Phase 3：集群连接排序（2 天）

1. 后端：添加 `sort_order` 字段
2. 后端：修改 `get_configs` 排序逻辑
3. 后端：添加 `/configs/sort` API
4. 前端：安装 `@dnd-kit` 库
5. 前端：修改 `ConnectionList` 组件
6. 测试：验证拖动排序功能

---

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 后端 API 变更 | 中 | 保持向后兼容，添加新 API 而非修改现有 API |
| 前端组件重构 | 中 | 逐步迁移，保持现有功能正常 |
| 数据库迁移 | 低 | `sort_order` 字段有默认值，不影响现有数据 |
| 第三方库依赖 | 低 | `@dnd-kit` 是成熟的库，社区活跃 |

---

## 验收标准

- [ ] 403 错误时显示友好提示，引导用户配置 namespace_filter
- [ ] 编辑模式下展示完整连接配置（server、auth_type 等）
- [ ] 支持重新输入敏感字段（token/cert/key）
- [ ] 集群连接默认按名称排序
- [ ] 支持拖动自定义排序
- [ ] 排序结果持久化到数据库
- [ ] 浏览器 Console 无错误

---

**下一步**: 用户 review 本文档后，调用 writing-plans skill 生成详细实现计划。
