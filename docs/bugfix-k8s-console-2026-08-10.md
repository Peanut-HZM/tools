# K8s 控制台 Bug 修复报告

**日期**: 2026-08-10
**修复人**: Claude
**问题页面**: http://localhost:5178/tools/k8s-tool

---

## 修复的三个 Bug

### Bug 1: 文件上传无法选择无后缀文件和 .kubeconfig 文件 ✅

**问题描述**: 文件选择器限制了 `accept` 属性，只允许 `.yaml`、`.yml`、`.json`、`.conf`、`.config` 后缀的文件，导致无后缀和 `.kubeconfig` 后缀的文件无法选择。

**根本原因**: `react-dropzone` 的 `accept` 配置过于严格，且包含无效的空字符串扩展名。

**修复方案**: 移除 `accept` 限制，允许选择任何文件。后端会验证文件内容是否为有效的 kubeconfig YAML。

**修改文件**:
- `frontend/src/components/Tools/K8sTool/ConnectionModal.tsx` (line 115-124)

**修改内容**:
```typescript
// 修改前
const { getRootProps, getInputProps, isDragActive } = useDropzone({
  onDrop,
  accept: {
    'application/x-yaml': ['.yaml', '.yml'],
    'application/json': ['.json'],
    'text/plain': ['.conf', '.config', ''],  // 空字符串无效
  },
  maxSize: MAX_FILE_SIZE,
  multiple: false,
});

// 修改后
const { getRootProps, getInputProps, isDragActive } = useDropzone({
  onDrop,
  // 不限制 accept，允许选择任何文件（包括无后缀和 .kubeconfig）
  // 后端会验证文件内容是否为有效的 kubeconfig YAML
  maxSize: MAX_FILE_SIZE,
  multiple: false,
});
```

---

### Bug 2: 添加配置成功后列表没有立即刷新 ✅

**问题描述**: 上传/粘贴/手动创建配置成功后，连接列表没有立即显示新配置，需要等待 30 秒的轮询刷新。

**根本原因**: 没有在成功回调中调用 React Query 的 `invalidateQueries` 来刷新 `['k8s', 'connections']` 缓存。

**修复方案**: 在 `handleUpload`、`handlePaste`、`handleManualCreate` 成功后立即调用 `queryClient.invalidateQueries`。

**修改文件**:
- `frontend/src/components/Tools/K8sTool/ConnectionModal.tsx` (handleUpload, handlePaste, handleManualCreate)

**修改内容**:
```typescript
// 在三个函数的成功回调中添加
queryClient.invalidateQueries({ queryKey: ['k8s', 'connections'] });
```

---

### Bug 3: 配置有效但一直显示"无法连接到集群" ✅

这个 Bug 有 4 个子问题，已全部修复：

#### Bug 3a: test/health 端点返回 501 Not Implemented ✅

**问题描述**: `POST /configs/{config_id}/test` 和 `GET /configs/{config_id}/health` 端点还是 TODO 占位符，直接返回 501 错误。

**修复方案**: 实现真实的连通性测试逻辑：
1. 调用 `build_client` 创建 K8s 客户端
2. 尝试 `list_namespace()` 验证连通性
3. 尝试获取 `/version` 获取服务器版本
4. 更新数据库的 `last_test_at`、`last_test_error`、`is_metrics_available`

**修改文件**:
- `backend/app/routes/k8s_tool.py` (line 121-186)
- `backend/app/services/k8s_tool_service.py` (新增 `update_test_result` 方法)

#### Bug 3b: kubeconfig 使用 exec/auth-provider 插件导致 token 为空 ✅

**问题描述**: 某些 kubeconfig（如 AWS EKS、GCP GKE）使用 `exec` 或 `auth-provider` 插件获取 token，但解析器不支持这些插件，导致 token 为 None，最终匿名访问被 403 拒绝。

**修复方案**: 在 `_resolve_auth` 中检测这些插件，抛出明确的错误提示用户改用 token 方式：

```python
# 检测 exec 插件（如 aws eks get-token, gcloud config config-helper 等）
if "exec" in user_data:
    exec_config = user_data["exec"]
    command = exec_config.get("command", "")
    raise KubeconfigParseError(
        f"该 kubeconfig 使用 exec 认证插件（command: {command}），暂不支持。"
        f"请使用 token、客户端证书或用户名密码方式创建连接。"
    )

# 检测 auth-provider 插件（如 gcp, azure, oidc 等）
if "auth-provider" in user_data:
    provider_name = user_data["auth-provider"].get("name", "")
    raise KubeconfigParseError(
        f"该 kubeconfig 使用 auth-provider 认证插件（provider: {provider_name}），暂不支持。"
        f"请使用 token、客户端证书或用户名密码方式创建连接。"
    )
```

**修改文件**:
- `backend/app/utils/k8s_config_parser.py` (line 149-188)

同时在 `parse_kubeconfig` 中聚合所有不支持认证的 context 错误，如果全部失败则给出详细错误信息。

#### Bug 3c: raise K8sError TypeError ✅

**问题描述**: `_api_exception_to_k8s_error` 返回的是 Pydantic `BaseModel`，而 `raise` 需要 `Exception` 子类，导致 `TypeError: exceptions must derive from BaseException`，掩盖了真实的 K8s API 错误。

**修复方案**: 创建真正的异常类 `K8sApiException`，它包装 `K8sError` 模型：

```python
class K8sApiException(Exception):
    """K8s API 异常，携带 K8sError 详情"""

    def __init__(self, error: K8sError):
        self.error = error
        super().__init__(error.message)
```

**修改文件**:
- `backend/app/models/k8s_tool_models.py` (新增 K8sApiException 类)
- `backend/app/services/k8s_resource_service.py` (line 336-349，修改返回类型为 K8sApiException)

#### Bug 3d: 前端显示通用错误而不是真实错误消息 ✅

**问题描述**: 所有资源列表组件（PodList、WorkloadList、NodeList、EventsList）在出错时只显示通用的 `k8sT.errors.CONNECTION_FAILED`，不显示后端返回的真实错误信息。

**修复方案**: 从 React Query 的 `error` 对象中提取真实的错误消息：

```typescript
// 修改前
const { data: pods = [], isLoading, isError } = useK8sPods(...);

// 修改后
const { data: pods = [], isLoading, error } = useK8sPods(...);
const isError = !!error;
const errorMessage = error instanceof Error ? error.message : k8sT.errors.CONNECTION_FAILED;
```

**修改文件**:
- `frontend/src/components/Tools/K8sTool/ResourceTabs/PodList.tsx`
- `frontend/src/components/Tools/K8sTool/ResourceTabs/WorkloadList.tsx`
- `frontend/src/components/Tools/K8sTool/ResourceTabs/NodeList.tsx`
- `frontend/src/components/Tools/K8sTool/ResourceTabs/EventsList.tsx`

---

## 测试验证

### 后端测试 ✅
- 所有 33 个 K8s 相关测试通过
- 语法检查通过（所有修改的 .py 文件）
- 后端服务已成功重启（PID: 88076）

### API 路由验证 ✅
- `/api/k8s-tool/configs/{config_id}/test` 已实现
- `/api/k8s-tool/configs/{config_id}/health` 已实现

### 前端编译 ✅
- TypeScript 编译无错误（K8s 相关文件）

---

## 修改的文件清单

### 后端（6 个文件）
1. `backend/app/models/k8s_tool_models.py` - 新增 K8sApiException 类
2. `backend/app/services/k8s_resource_service.py` - 修改 _api_exception_to_k8s_error 返回异常
3. `backend/app/services/k8s_tool_service.py` - 新增 update_test_result 方法
4. `backend/app/routes/k8s_tool.py` - 实现 test/health 端点
5. `backend/app/utils/k8s_config_parser.py` - 支持检测 exec/auth-provider 插件

### 前端（5 个文件）
1. `frontend/src/components/Tools/K8sTool/ConnectionModal.tsx` - 修复 accept 限制 + 添加列表刷新
2. `frontend/src/components/Tools/K8sTool/ResourceTabs/PodList.tsx` - 显示真实错误消息
3. `frontend/src/components/Tools/K8sTool/ResourceTabs/WorkloadList.tsx` - 显示真实错误消息
4. `frontend/src/components/Tools/K8sTool/ResourceTabs/NodeList.tsx` - 显示真实错误消息
5. `frontend/src/components/Tools/K8sTool/ResourceTabs/EventsList.tsx` - 显示真实错误消息

---

## 使用建议

1. **对于 exec/auth-provider kubeconfig**: 如果你的 kubeconfig 使用了 `exec` 或 `auth-provider` 插件（如 AWS EKS、GCP GKE），现在会看到明确的错误提示。请改用以下方式创建连接：
   - **手动填写**: 使用 token 或客户端证书方式
   - **生成静态 token**: 运行 `kubectl create token <service-account>` 生成长期 token

2. **健康状态指示**: 连接列表的健康圆点现在会正确显示：
   - 🟢 绿色：测试成功
   - 🔴 红色：测试失败（显示具体错误）
   - ⚫ 灰色：从未测试

3. **立即刷新**: 添加/编辑配置后，列表会立即刷新，无需等待 30 秒轮询。

---

**修复完成时间**: 2026-08-10 18:15
**测试状态**: ✅ 所有测试通过
**可以安全使用**: 是
