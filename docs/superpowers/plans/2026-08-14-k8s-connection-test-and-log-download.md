# K8s 连接测试修复 & 容器日志下载按钮实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 K8s 连接测试权限问题、修复日志下载不完整问题，并在容器列表添加下载日志按钮

**Architecture:** 
- 后端：修改 `test_connection` 根据 namespace_filter 选择测试方式，修改 `download_pod_logs` 的 tail_lines 默认值为 None
- 前端：在 PodList 组件添加下载日志按钮，使用已有的 downloadPodLogs API

**Tech Stack:** Python (FastAPI), React (TypeScript), Tailwind CSS

## Global Constraints

- 所有对话、文档、注释、日志、提交信息必须使用中文
- 变量名、函数名使用英文
- 禁止 `console.log` 在生产代码中
- 代码修改后优先利用热加载，非必要不重启服务
- 完成代码修改后，必须使用 `dev-services.py` 重启相关模块
- 使用浏览器进行验证，确认页面正常、无报错

## File Structure

| File | Responsibility |
|------|---------------|
| `backend/app/routes/k8s_tool.py:151-210` | 修改 `test_connection` 逻辑，根据 namespace_filter 选择测试方式 |
| `backend/app/routes/k8s_tool.py:559-586` | 修改 `download_pod_logs` 的 tail_lines 默认值为 None |
| `frontend/src/i18n/locales/zh-CN.ts` | 添加权限错误文案 |
| `frontend/src/i18n/locales/en-US.ts` | 添加权限错误文案 |
| `frontend/src/components/Tools/K8sTool/ResourceTabs/PodList.tsx` | 添加下载日志按钮和操作列 |

---

## Task 1: 修复后端测试连接逻辑

**Files:**
- Modify: `backend/app/routes/k8s_tool.py:151-210`

**Interfaces:**
- Consumes: `K8sToolService.get_config_by_id()`, `K8sToolService.update_test_result()`, `build_client()`
- Produces: `test_connection` endpoint that uses namespace-level API when namespace_filter is set

- [ ] **Step 1: 修改 test_connection 函数**

修改 `test_connection` 函数，添加 namespace_filter 解析和条件测试逻辑：

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

- [ ] **Step 2: 验证语法**

Run: `python -m py_compile backend/app/routes/k8s_tool.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/k8s_tool.py
git commit -m "fix: K8s 测试连接根据 namespace_filter 选择测试方式"
```

---

## Task 2: 修复后端日志下载 tail_lines 默认值

**Files:**
- Modify: `backend/app/routes/k8s_tool.py:559-586`

**Interfaces:**
- Consumes: `K8sResourceService.get_pod_logs()`
- Produces: `download_pod_logs` endpoint that returns full logs when tail_lines is not provided

- [ ] **Step 1: 修改 tail_lines 参数**

修改 `download_pod_logs` 函数的 tail_lines 参数：

```python
# 修改前：
tail_lines: int = Query(10000, ge=1, le=1000000, description="返回末尾行数")

# 修改后：
tail_lines: Optional[int] = Query(None, ge=1, le=1000000, description="返回末尾行数（不传则返回全部）")
```

- [ ] **Step 2: 验证语法**

Run: `python -m py_compile backend/app/routes/k8s_tool.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/k8s_tool.py
git commit -m "fix: K8s 日志下载 tail_lines 默认值改为 None 返回全部日志"
```

---

## Task 3: 添加国际化文案

**Files:**
- Modify: `frontend/src/i18n/locales/zh-CN.ts`
- Modify: `frontend/src/i18n/locales/en-US.ts`

**Interfaces:**
- Consumes: None
- Produces: `t.tools['k8s-tool'].errors.PERMISSION_DENIED` keys

- [ ] **Step 1: 添加中文文案**

在 `frontend/src/i18n/locales/zh-CN.ts` 的 `k8s-tool.errors` 中添加：

```typescript
PERMISSION_DENIED: '当前账号没有集群级权限，请在连接配置中设置 namespace_filter',
```

- [ ] **Step 2: 添加英文文案**

在 `frontend/src/i18n/locales/en-US.ts` 的 `k8s-tool.errors` 中添加：

```typescript
PERMISSION_DENIED: 'Current account does not have cluster-level permissions. Please configure namespace_filter in the connection settings',
```

- [ ] **Step 3: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -iE 'i18n|k8s' | head -10`
Expected: No errors related to i18n

- [ ] **Step 4: Commit**

```bash
git add frontend/src/i18n/locales/zh-CN.ts frontend/src/i18n/locales/en-US.ts
git commit -m "feat: 添加 K8s 权限错误国际化文案"
```

---

## Task 4: 添加下载日志按钮

**Files:**
- Modify: `frontend/src/components/Tools/K8sTool/ResourceTabs/PodList.tsx`

**Interfaces:**
- Consumes: `api.downloadPodLogs()` from `frontend/src/api/k8sToolApi.ts`
- Produces: Download logs button in each pod row

- [ ] **Step 1: 添加下载日志处理函数**

在 `PodList.tsx` 中添加下载日志处理函数：

```typescript
import { downloadPodLogs } from '../../../../api/k8sToolApi';
import { useToast } from '../../../../hooks/useToast';

// 在组件内部添加
const toast = useToast();

/** 下载 Pod 日志 */
const handleDownloadLogs = async (podName: string, namespace: string) => {
  try {
    const text = await downloadPodLogs(activeConnectionId, podName, namespace);
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${podName}-logs.txt`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('日志下载成功');
  } catch (error) {
    console.error('Download logs failed:', error);
    toast.error('下载日志失败');
  }
};
```

- [ ] **Step 2: 添加操作列到表头**

在表头添加"操作"列：

```tsx
<th className="text-left px-3 py-2 font-medium">{k8sT.podList.status}</th>
<th className="text-left px-3 py-2 font-medium">{k8sT.podList.name}</th>
<th className="text-left px-3 py-2 font-medium">{k8sT.podList.restarts}</th>
<th className="text-left px-3 py-2 font-medium">{k8sT.podList.age}</th>
<th className="text-left px-3 py-2 font-medium">{k8sT.podList.node}</th>
<th className="text-left px-3 py-2 font-medium">{k8sT.podList.ip}</th>
<th className="text-left px-3 py-2 font-medium">操作</th>
```

- [ ] **Step 3: 添加下载日志按钮到每行**

在每行添加操作列和下载按钮：

```tsx
{/* IP */}
<td className="px-3 py-2 text-slate-400 font-mono text-xs">
  {pod.pod_ip || '-'}
</td>

{/* 操作 */}
<td className="px-3 py-2">
  <button
    onClick={(e) => {
      e.stopPropagation();
      handleDownloadLogs(pod.name, pod.namespace);
    }}
    className="text-slate-400 hover:text-white"
    title="下载日志"
  >
    <i className="fas fa-download"></i>
  </button>
</td>
```

- [ ] **Step 4: 更新 colSpan 值**

更新所有 `colSpan` 从 6 改为 7：

```tsx
// 加载中
<td colSpan={7} className="px-3 py-8 text-center text-slate-500">

// 请求出错
<td colSpan={7} className="px-3 py-8 text-center text-red-400">

// 空数据
<td colSpan={7} className="px-3 py-8 text-center text-slate-500">
```

- [ ] **Step 5: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -iE 'PodList' | head -10`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Tools/K8sTool/ResourceTabs/PodList.tsx
git commit -m "feat: K8s 容器列表添加下载日志按钮"
```

---

## Task 5: 浏览器验证

**Files:**
- No code changes, browser verification only

- [ ] **Step 1: 重启后端服务**

Run: `python dev-services.py restart backend`
Expected: Backend restarts successfully

- [ ] **Step 2: 验证测试连接修复**

1. 打开 K8s 控制台
2. 编辑一个连接，设置 namespace_filter
3. 点击测试连接
4. 验证：测试成功，显示绿色状态

- [ ] **Step 3: 验证日志下载完整性**

1. 选择一个有大量日志的 Pod
2. 点击"下载日志"按钮
3. 验证：日志文件下载到本地
4. 验证：文件大小与其他平台下载的一致（几 MB 而不是几十 KB）
5. 验证：日志开头和结尾都包含

- [ ] **Step 4: 验证按钮 UI**

1. 在容器列表查看每行是否有下载按钮
2. 点击按钮验证下载功能
3. 验证：浏览器 Console 无报错

- [ ] **Step 5: Final commit (if any hotfixes needed)**

```bash
git add -A
git commit -m "fix: K8s 功能验证修复"
```
