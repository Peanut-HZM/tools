# K8s 日志查看器修复实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 K8s 日志查看器：过滤 LOG_STREAM_ERROR、自动重连、新增完整日志下载 REST API

**Architecture:** 后端新增下载端点 + 前端过滤错误帧 + WebSocket 自动重连 + 前端下载按钮调用新 API

**Tech Stack:** FastAPI + kubernetes_asyncio (后端) / React 18 + TypeScript + WebSocket (前端)

## Global Constraints

- 所有对话、文档、注释、提交信息使用中文
- 修改前后端代码后必须使用浏览器验证
- 优先利用热加载，非必要不重启服务
- TypeScript / Python 编译无新增错误
- 浏览器 Console 无错误
- DDL/DML 必须幂等执行
- 自动重连需有延迟避免连接风暴
- 下载行数上限 100 万行

---

### Task 1: 后端 - 新增日志下载 REST API

**Files:**
- Modify: `backend/app/routes/k8s_tool.py:556`
- Modify: `backend/app/services/k8s_resource_service.py`

**Interfaces:**
- Consumes: `K8sResourceService.get_pod_logs(bundle, name, namespace, container, tail_lines)` 新方法
- Produces: `GET /api/k8s-tool/{config_id}/pods/{name}/logs/download` 端点，返回 `text/plain` 响应

**Context:** 当前只有 WebSocket 端点用于日志流，需要新增 HTTP 端点一次性获取完整日志。

- [ ] **Step 1: 编写失败测试**

在 `backend/tests/test_k8s_resource_service.py` 添加测试：

```python
@pytest.mark.asyncio
async def test_get_pod_logs():
    """获取 pod 完整日志"""
    mock_bundle = MagicMock()
    mock_response = MagicMock()
    mock_response.read = AsyncMock(return_value=b"line1\nline2\nline3\n")
    mock_bundle.core_v1.read_namespaced_pod_log = AsyncMock(return_value=mock_response)

    result = await K8sResourceService.get_pod_logs(
        mock_bundle, "nginx-pod", "default", tail_lines=1000
    )
    assert result == "line1\nline2\nline3\n"
    mock_bundle.core_v1.read_namespaced_pod_log.assert_called_once()
    call_kwargs = mock_bundle.core_v1.read_namespaced_pod_log.call_args.kwargs
    assert call_kwargs["name"] == "nginx-pod"
    assert call_kwargs["namespace"] == "default"
    assert call_kwargs["follow"] is False
    assert call_kwargs["tail_lines"] == 1000
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_k8s_resource_service.py::test_get_pod_logs -v`
Expected: FAIL — `K8sResourceService.get_pod_logs` 不存在

- [ ] **Step 3: 实现 K8sResourceService.get_pod_logs**

在 `backend/app/services/k8s_resource_service.py` 的 `K8sResourceService` 类末尾添加：

```python
    @staticmethod
    async def get_pod_logs(
        bundle,
        name: str,
        namespace: str,
        container: Optional[str] = None,
        tail_lines: int = 10000,
        previous: bool = False,
    ) -> str:
        """获取 pod 完整日志（非 follow，一次性读取）

        Args:
            bundle: K8s 客户端 bundle
            name: Pod 名称
            namespace: 命名空间
            container: 容器名（多容器 pod 时使用）
            tail_lines: 返回末尾行数
            previous: 是否读取上一个已终止容器的日志

        Returns:
            日志文本（utf-8 解码）

        Raises:
            K8sApiException: K8s API 错误
        """
        try:
            kwargs = {
                "name": name,
                "namespace": namespace,
                "tail_lines": tail_lines,
                "follow": False,
                "previous": previous,
            }
            if container:
                kwargs["container"] = container

            response = await bundle.core_v1.read_namespaced_pod_log(**kwargs)
            content = await response.read()
            if isinstance(content, bytes):
                return content.decode("utf-8", errors="replace")
            return content
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_k8s_resource_service.py::test_get_pod_logs -v`
Expected: PASS

- [ ] **Step 5: 实现 HTTP 下载端点**

在 `backend/app/routes/k8s_tool.py` 第 556 行（WebSocket 端点之前）插入：

```python
from fastapi import Response


@router.get("/{config_id}/pods/{name}/logs/download")
async def download_pod_logs(
    config_id: str,
    name: str,
    namespace: str = Query(..., description="命名空间"),
    container: Optional[str] = Query(None, description="容器名"),
    tail_lines: int = Query(10000, ge=1, le=1000000, description="返回末尾行数"),
    previous: bool = Query(False, description="是否读取上一个已终止容器的日志"),
    user_id: str = Depends(get_current_user_id),
):
    """下载容器完整日志（不 follow）"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            text = await K8sResourceService.get_pod_logs(
                bundle, name, namespace, container, tail_lines, previous
            )
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)

    filename = f"{name}-{container or 'all'}-logs.txt"
    return Response(
        content=text,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 6: 运行所有 K8s 测试**

Run: `cd backend && python -m pytest tests/test_k8s_resource_service.py -v 2>&1 | tail -20`
Expected: 全部通过

- [ ] **Step 7: Commit**

```bash
git add backend/app/routes/k8s_tool.py backend/app/services/k8s_resource_service.py backend/tests/test_k8s_resource_service.py
git commit -m "feat(k8s): 新增容器完整日志下载 REST API"
```

---

### Task 2: 前端 - 添加 downloadPodLogs API 方法

**Files:**
- Modify: `frontend/src/api/k8sToolApi.ts:210`

**Interfaces:**
- Consumes: `getAuthHeaders()`
- Produces: `downloadPodLogs(configId, podName, namespace, container?, tailLines)` API 方法

**Context:** 前端需要新的 API 方法调用后端下载端点。

- [ ] **Step 1: 添加 API 方法**

在 `frontend/src/api/k8sToolApi.ts` 第 228 行（`buildLogsWebSocketUrl` 之后）插入：

```typescript
/** 下载容器完整日志 */
export const downloadPodLogs = async (
  configId: string,
  podName: string,
  namespace: string,
  container?: string,
  tailLines: number = 10000,
): Promise<string> => {
  const params = new URLSearchParams({
    namespace,
    tail_lines: String(tailLines),
  });
  if (container) params.append('container', container);

  const response = await fetch(
    `${K8S_API_URL}/${encodeURIComponent(configId)}/pods/${encodeURIComponent(podName)}/logs/download?${params}`,
    { headers: getAuthHeaders() }
  );
  if (!response.ok) {
    throw new Error(`下载日志失败: ${response.status}`);
  }
  return response.text();
};
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep "k8sToolApi" | head -5`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/k8sToolApi.ts
git commit -m "feat(k8s): 前端新增 downloadPodLogs API 方法"
```

---

### Task 3: 前端 - 修复错误帧过滤 + 自动重连 + 新下载逻辑

**Files:**
- Modify: `frontend/src/components/Tools/K8sTool/LogsViewer/LogsViewer.tsx`

**Interfaces:**
- Consumes: `downloadPodLogs` (Task 2), `useToast`
- Produces: 错误帧过滤、follow 模式自动重连、新下载逻辑

**Context:** 
- 错误帧 `LOG_STREAM_ERROR` 被作为普通日志显示
- WebSocket 关闭后不重连
- 下载只保存内存中的日志（受 MAX_LINES 限制）

- [ ] **Step 1: 添加 isLogStreamError 工具函数**

修改 `frontend/src/components/Tools/K8sTool/LogsViewer/LogsViewer.tsx`，在文件顶部常量区添加（`MAX_LINES` 之后）：

```tsx
// 重连延迟（毫秒）
const RECONNECT_DELAY = 2000;

/** 检测是否为日志流错误帧 */
function isLogStreamError(text: string): boolean {
  if (!text.startsWith('{"type":"error"')) return false;
  try {
    const parsed = JSON.parse(text);
    return parsed.code === 'LOG_STREAM_ERROR';
  } catch {
    return false;
  }
}
```

- [ ] **Step 2: 修改 socket.onmessage 过滤错误帧**

修改第 78-86 行（`socket.onmessage` 回调）：

```tsx
// 修改前：
socket.onmessage = (event) => {
  const text = typeof event.data === 'string' ? event.data : '';
  const newLines = text.split('\n');
  bufferRef.current.push(...newLines);
  if (rafIdRef.current === null) {
    rafIdRef.current = requestAnimationFrame(flushBuffer);
  }
};

// 修改后：
socket.onmessage = (event) => {
  const text = typeof event.data === 'string' ? event.data : '';
  // 过滤 LOG_STREAM_ERROR 错误帧，不显示为日志
  if (isLogStreamError(text)) {
    console.warn('Log stream error:', text);
    return;
  }
  const newLines = text.split('\n');
  bufferRef.current.push(...newLines);
  if (rafIdRef.current === null) {
    rafIdRef.current = requestAnimationFrame(flushBuffer);
  }
};
```

- [ ] **Step 3: 修改 socket.onclose 实现自动重连**

修改第 92-96 行（`socket.onclose` 回调）：

```tsx
// 修改前：
socket.onclose = () => {
  if (socketRef.current === socket) {
    socketRef.current = null;
  }
};

// 修改后：
socket.onclose = () => {
  if (socketRef.current === socket) {
    socketRef.current = null;
    // follow 模式下自动重连
    if (followRef.current) {
      setTimeout(() => {
        if (followRef.current && socketRef.current === null) {
          reconnect();
        }
      }, RECONNECT_DELAY);
    }
  }
};
```

**注意**：需要在 useEffect 之前添加 `followRef` ref：

```tsx
const followRef = useRef(follow);
useEffect(() => { followRef.current = follow; }, [follow]);
```

并在 useEffect 顶部添加 reconnect 函数（需要重构 useEffect 以提取可重用的连接逻辑，或将连接代码提取为 `connect()` 函数并从 useEffect 和 onclose 中调用）。

- [ ] **Step 4: 重构 useEffect 提取 connect 函数**

将 useEffect 内的 WebSocket 连接逻辑提取为 `connect` 函数：

```tsx
const connect = useCallback(() => {
  socketRef.current?.close();

  const wsUrl = buildLogsWebSocketUrl(
    configId,
    podName,
    namespace,
    selectedContainer || undefined,
    tailLines,
    true,
  );

  const socket = new WebSocket(wsUrl);
  socketRef.current = socket;

  socket.onmessage = (event) => {
    const text = typeof event.data === 'string' ? event.data : '';
    if (isLogStreamError(text)) {
      console.warn('Log stream error:', text);
      return;
    }
    const newLines = text.split('\n');
    bufferRef.current.push(...newLines);
    if (rafIdRef.current === null) {
      rafIdRef.current = requestAnimationFrame(flushBuffer);
    }
  };

  socket.onerror = () => {};

  socket.onclose = () => {
    if (socketRef.current === socket) {
      socketRef.current = null;
      if (followRef.current) {
        setTimeout(() => {
          if (followRef.current && socketRef.current === null) {
            connect();
          }
        }, RECONNECT_DELAY);
      }
    }
  };
}, [configId, podName, namespace, selectedContainer, tailLines, flushBuffer]);

const reconnect = useCallback(() => connect(), [connect]);

useEffect(() => {
  setLines([]);
  connect();
  return () => {
    socketRef.current?.close();
    socketRef.current = null;
    if (rafIdRef.current !== null) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    }
  };
}, [connect]);
```

- [ ] **Step 5: 替换 handleDownload 实现**

修改第 173-182 行（`handleDownload` 函数）：

```tsx
// 修改前：
const handleDownload = () => {
  const text = lines.join('\n');
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${podName}-${selectedContainer || 'all'}-logs.txt`;
  a.click();
  URL.revokeObjectURL(url);
};

// 修改后：
const [downloading, setDownloading] = useState(false);

const handleDownload = async () => {
  setDownloading(true);
  try {
    const text = await downloadPodLogs(
      configId, podName, namespace, selectedContainer || undefined, tailLines
    );
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${podName}-${selectedContainer || 'all'}-logs.txt`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error('Download failed:', err);
    addToast({ message: lt.downloadError || '下载失败', type: 'error' });
  } finally {
    setDownloading(false);
  }
};
```

并在文件顶部添加 import：

```tsx
import { downloadPodLogs } from '../../../../api/k8sToolApi';
```

- [ ] **Step 6: 修改下载按钮显示下载状态**

修改第 246-253 行（下载按钮）：

```tsx
// 修改前：
<button
  onClick={handleDownload}
  disabled={lines.length === 0}
  className="..."
>
  <i className="fas fa-download text-xs"></i>
</button>

// 修改后：
<button
  onClick={handleDownload}
  disabled={downloading}
  className="..."
>
  <i className={`fas ${downloading ? 'fa-spinner fa-spin' : 'fa-download'} text-xs`}></i>
</button>
```

- [ ] **Step 7: 添加 i18n 下载错误翻译**

在 `frontend/src/i18n/locales/zh-CN.ts` 和 `en-US.ts` 的 `k8s-tool.logs` 中添加 `downloadError`：

```typescript
// zh-CN.ts
logs: {
  // ... 现有 key
  downloadError: '下载日志失败',
}

// en-US.ts
logs: {
  // ... 现有 key
  downloadError: 'Failed to download logs',
}
```

- [ ] **Step 8: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -E "(LogsViewer|k8sToolApi)" | head -10`
Expected: 无错误

- [ ] **Step 9: 运行 K8s 相关测试**

Run: `cd frontend && npx vitest run src/components/Tools/K8sTool/LogsViewer 2>&1 | tail -10`
Expected: 全部通过（如果有测试）

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/Tools/K8sTool/LogsViewer/LogsViewer.tsx frontend/src/i18n/locales/zh-CN.ts frontend/src/i18n/locales/en-US.ts
git commit -m "fix(k8s): 过滤 LOG_STREAM_ERROR 错误帧、自动重连、下载完整日志"
```

---

## 验收标准

- [ ] LOG_STREAM_ERROR 错误帧不显示为日志行
- [ ] WebSocket 断开后自动重连（follow 模式，2 秒延迟）
- [ ] 日志下载获取容器完整日志（不限于 MAX_LINES=10000）
- [ ] 下载按钮显示加载状态（spinner）
- [ ] 下载失败时显示 toast 错误提示
- [ ] 后端测试通过
- [ ] TypeScript 编译无错误
- [ ] 浏览器 Console 无错误（手动验证）
- [ ] i18n 中英文翻译一致