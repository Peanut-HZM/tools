# K8s 连接测试修复 & 容器日志下载按钮

**日期**: 2026-08-14
**状态**: 待批准
**实现**: Phase 14

## 背景

K8s 工具存在以下问题：
1. **连接状态显示错误**：左侧连接列表显示红色警告，即使容器列表已正常加载
2. **测试连接不准确**：编辑页面测试连接显示 403，但实际连接可用
3. **日志下载不完整**：下载的日志只有几十 KB，远小于其他平台下载的几 MB 完整日志

**问题 1 & 2 根因**：测试连接使用集群级操作 `list_namespace()`，对于只有 namespace 级权限的服务账号会返回 403。而获取容器列表使用 namespace 级操作 `list_namespaced_pod(namespace)`，所以能成功。

**问题 3 根因**：后端 `download_pod_logs` 端点的 `tail_lines` 参数默认值为 `10000`。前端已改为不传该参数，但后端默认值导致仍只返回最后 10000 行日志，丢失了更早的历史日志。

## 功能需求

### 1. 修复测试连接逻辑

**当前行为**：
- 测试连接始终使用 `list_namespace()`（集群级操作）
- 对于 namespace 级权限用户返回 403
- 即使实际连接可用，`last_test_error` 被设置，导致前端显示红色

**目标行为**：
- 如果连接配置了 `namespace_filter`，使用 `list_namespaced_pod(namespace)` 测试（namespace 级操作）
- 如果没有配置 `namespace_filter`，仍然使用 `list_namespace()` 测试
- 测试失败时，如果错误是 403 权限问题，提示用户配置有权限的 namespace
- 测试成功后清除 `last_test_error`

### 2. 修复日志下载不完整

**文件**: `backend/app/routes/k8s_tool.py`

**修改 `download_pod_logs` 的 `tail_lines` 参数**：

```python
# 修改前（只返回最后 10000 行）：
tail_lines: int = Query(10000, ge=1, le=1000000, description="返回末尾行数")

# 修改后（不传时返回全部日志）：
tail_lines: Optional[int] = Query(None, ge=1, le=1000000, description="返回末尾行数（不传则返回全部）")
```

这样当 `tail_lines=None` 时，`get_pod_logs` 不会向 K8s API 传递 `tail_lines` 参数，K8s API 会返回容器的完整日志。

### 3. 添加下载日志按钮

**需求**：
- 在容器组/容器列表的每一行添加"下载日志"按钮
- 点击后下载该容器的完整日志到本地
- 使用已有的下载日志 API：`GET /{config_id}/pods/{name}/logs/download`

## 技术方案

### 后端修改

**文件**: `backend/app/routes/k8s_tool.py`

**修改 `test_connection` 函数**：

```python
@router.post("/configs/{config_id}/test", response_model=K8sConnectionHealth)
async def test_connection(
    config_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """测试指定连接的 API Server 连通性"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    try:
        async with build_client(config) as bundle:
            # 解析 namespace_filter
            ns_filter = config.get("namespace_filter", "[]")
            try:
                ns_list = json.loads(ns_filter) if isinstance(ns_filter, str) else []
            except (json.JSONDecodeError, TypeError):
                ns_list = []

            # 根据是否有 namespace_filter 选择不同的测试方式
            if ns_list:
                # 有 namespace_filter：使用 namespace 级操作
                test_namespace = ns_list[0]
                await bundle.core_v1.list_namespaced_pod(test_namespace)
            else:
                # 无 namespace_filter：使用集群级操作
                await bundle.core_v1.list_namespace()

            # 获取 server 版本（非关键操作）
            server_version = None
            try:
                version_info = await bundle.core_v1.api_client.call_api(
                    '/version', 'GET',
                    auth_settings=['BearerToken'],
                    response_type='object',
                    _return_http_data_only=True
                )
                server_version = version_info.get('gitVersion') if version_info else None
            except Exception as e:
                logger.warning(f"获取 server 版本失败: {e}")

            # 更新测试结果（成功）
            K8sToolService.update_test_result(
                config_id,
                success=True,
                error=None,
                metrics_available=True
            )

            return K8sConnectionHealth(
                reachable=True,
                server_version=server_version,
                tested_at=datetime.now(),
            )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"连接测试失败 (config_id={config_id}): {error_msg}", exc_info=True)

        # 检查是否是权限问题
        is_permission_error = "403" in error_msg or "forbidden" in error_msg.lower()

        # 更新测试结果（失败）
        K8sToolService.update_test_result(
            config_id,
            success=False,
            error=error_msg,
            metrics_available=False
        )

        # 如果是权限问题且没有配置 namespace_filter，给出友好提示
        if is_permission_error and not ns_list:
            raise HTTPException(
                status_code=403,
                detail={
                    "error_code": "PERMISSION_DENIED",
                    "message": "当前账号没有集群级权限，请在连接配置中设置 namespace_filter",
                    "raw": error_msg
                }
            )

        raise _k8s_api_error_to_http(e)
```

### 前端修改

#### 1. 修改错误提示

**文件**: `frontend/src/i18n/locales/zh-CN.ts` 和 `en-US.ts`

在 `k8s-tool` 命名空间添加：
```typescript
errors: {
  // ... 现有错误
  PERMISSION_DENIED: '当前账号没有集群级权限，请在连接配置中设置 namespace_filter',
}
```

#### 2. 添加下载日志按钮

**文件**: `frontend/src/components/Tools/K8sTool/PodList.tsx` 或相关容器列表组件

在每行操作列添加"下载日志"按钮：

```typescript
// 下载日志处理函数
const handleDownloadLogs = async (podName: string, containerName?: string) => {
  try {
    const params = new URLSearchParams({ namespace: selectedNamespace });
    if (containerName) params.append('container', containerName);

    const response = await fetch(
      `${K8S_API_URL}/${encodeURIComponent(configId)}/pods/${encodeURIComponent(podName)}/logs/download?${params}`,
      { headers: getAuthHeaders() }
    );

    if (!response.ok) {
      throw new Error(`下载日志失败: ${response.status}`);
    }

    const text = await response.text();
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${podName}-${containerName || 'all'}-logs.txt`;
    a.click();
    URL.revokeObjectURL(url);

    toast.success('日志下载成功');
  } catch (error) {
    console.error('Download logs failed:', error);
    toast.error('下载日志失败');
  }
};
```

在表格操作列添加按钮：
```tsx
<button
  onClick={() => handleDownloadLogs(pod.name, pod.containerName)}
  className="text-slate-400 hover:text-white"
  title="下载日志"
>
  <i className="fas fa-download"></i>
</button>
```

## 影响范围

### 修改的文件

- `backend/app/routes/k8s_tool.py` — 修改 `test_connection` 逻辑 + 修复 `download_pod_logs` 的 `tail_lines` 默认值
- `backend/app/services/k8s_tool_service.py` — 修改 `get_config_by_id` 返回完整 config（含 namespace_filter）
- `frontend/src/i18n/locales/zh-CN.ts` — 添加权限错误文案
- `frontend/src/i18n/locales/en-US.ts` — 添加权限错误文案
- `frontend/src/components/Tools/K8sTool/PodList.tsx` — 添加下载日志按钮（或相关容器列表组件）

### 不需要修改

- 下载日志 API 已存在，`get_pod_logs` 已正确处理 `tail_lines=None`
- 连接列表组件无需修改（状态判断逻辑不变，但 `last_test_error` 会被正确清除）

## 测试场景

### 功能测试

1. **有 namespace_filter 的连接**
   - 编辑连接，设置 namespace_filter
   - 点击测试连接
   - 验证：测试成功，显示绿色状态

2. **无 namespace_filter 的连接**
   - 编辑连接，清空 namespace_filter
   - 点击测试连接
   - 如果有集群级权限：测试成功
   - 如果没有集群级权限：显示 403 错误和友好提示

3. **下载日志**
   - 在容器列表点击"下载日志"按钮
   - 验证：日志文件下载到本地
   - 验证：文件名格式正确 `{podName}-{containerName}-logs.txt`
   - 验证：日志内容完整（与其他平台下载的日志行数一致）

4. **日志下载完整性**
   - 选择一个有大量日志的 Pod（日志量 > 10000 行）
   - 下载日志，验证文件大小与其他平台下载的一致
   - 验证日志开头和结尾都包含

### 边界测试

1. 多容器 Pod 下载日志（指定容器名）
2. 日志量特别大的情况（验证下载超时处理）
3. namespace_filter 为空数组的情况
