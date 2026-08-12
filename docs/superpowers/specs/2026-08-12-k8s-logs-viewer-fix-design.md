# K8s 日志查看器修复设计文档

**日期**: 2026-08-12  
**状态**: 已批准  
**优先级**: 高

---

## 1. 需求背景

K8s 容器日志查看器存在两个问题：

1. **LOG_STREAM_ERROR 误显示**：当日志流异常时，后端发送错误帧，前端将其作为普通日志行显示，导致最后一行出现 JSON 错误信息且停止接收新日志
2. **日志下载不完整**：当前下载功能只保存浏览器内存中的日志（受 MAX_LINES=10000 限制），而非容器的完整日志

---

## 2. 设计目标

1. 错误帧不显示为日志行，WebSocket 自动重连保持实时跟踪
2. 日志下载通过后端 REST API 获取完整容器日志

---

## 3. 改动范围

### 3.1 前端：过滤错误帧 + 自动重连

**文件**: `frontend/src/components/Tools/K8sTool/LogsViewer/LogsViewer.tsx`

**改动 1**: `onmessage` 检测错误帧

```tsx
socket.onmessage = (event) => {
  const text = typeof event.data === 'string' ? event.data : '';
  
  // 过滤错误帧，不显示为日志
  if (text.startsWith('{"type":"error"')) {
    try {
      const parsed = JSON.parse(text);
      if (parsed.code === 'LOG_STREAM_ERROR') {
        console.warn('Log stream error:', parsed.message);
        return;
      }
    } catch {
      // 非 JSON 错误格式，按普通日志处理
    }
  }
  
  const newLines = text.split('\n');
  bufferRef.current.push(...newLines);
  if (rafIdRef.current === null) {
    rafIdRef.current = requestAnimationFrame(flushBuffer);
  }
};
```

**改动 2**: 关闭后自动重连

```tsx
socket.onclose = () => {
  if (socketRef.current === socket) {
    socketRef.current = null;
    // follow 模式下自动重连
    if (follow) {
      setTimeout(() => reconnect(), 2000);
    }
  }
};
```

### 3.2 后端：新增日志下载端点

**文件**: `backend/app/routes/k8s_tool.py`

**新增端点**:

```python
@router.get("/{config_id}/pods/{name}/logs/download")
async def download_pod_logs(
    config_id: str,
    name: str,
    namespace: str = Query(...),
    container: Optional[str] = Query(None),
    tail_lines: int = Query(10000, ge=1, le=1000000),
    previous: bool = Query(False),
    current_user: dict = Depends(get_current_user_from_token),
):
    """下载容器完整日志（不 follow）"""
    config = K8sToolService.get_config_by_id(current_user["id"], config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    async with build_client(config) as bundle:
        kwargs = {
            "name": name,
            "namespace": namespace,
            "tail_lines": tail_lines,
            "follow": False,
            "previous": previous,
        }
        if container:
            kwargs["container"] = container
        
        log_response = await bundle.core_v1.read_namespaced_pod_log(**kwargs)
        content = await log_response.read()
        text = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content
    
    filename = f"{name}-{container or 'all'}-logs.txt"
    return Response(
        content=text,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

### 3.3 前端：下载按钮改造

**文件**: `frontend/src/components/Tools/K8sTool/LogsViewer/LogsViewer.tsx`

**改动**: `handleDownload` 改为调用 REST API

```tsx
const [downloading, setDownloading] = useState(false);

const handleDownload = async () => {
  setDownloading(true);
  try {
    const response = await api.downloadPodLogs(
      configId, podName, namespace, selectedContainer || undefined, tailLines
    );
    const blob = new Blob([response.data], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${podName}-${selectedContainer || 'all'}-logs.txt`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    addToast({ message: lt.downloadError || '下载失败', type: 'error' });
  } finally {
    setDownloading(false);
  }
};
```

---

## 4. 验收标准

- [ ] LOG_STREAM_ERROR 错误帧不显示在日志列表中
- [ ] WebSocket 断开后自动重连（follow 模式）
- [ ] 日志下载获取容器完整日志（不限于 MAX_LINES）
- [ ] 下载按钮显示加载状态
- [ ] 下载失败时显示错误提示
- [ ] TypeScript 编译无错误
- [ ] 后端测试通过
- [ ] 浏览器 Console 无错误

---

## 5. 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 自动重连导致连接风暴 | 中 | 2 秒延迟 + 指数退避 |
| 大日志下载超时 | 中 | tail_lines 上限 100 万行 |
| 后端鉴权失败 | 低 | 复用现有鉴权中间件 |

---

## 6. 实施计划

1. 后端新增下载端点 + 单元测试
2. 前端修复错误帧过滤 + 自动重连
3. 前端下载按钮调用新 API
4. 浏览器端到端验证

---

**下一步**: 用户 review 本文档后，调用 writing-plans 技能生成详细实现计划。
