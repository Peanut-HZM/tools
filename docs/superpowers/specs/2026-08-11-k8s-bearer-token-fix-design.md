# K8s Bearer Token 认证修复设计文档

**日期**: 2026-08-11  
**状态**: 待实现  
**优先级**: 高  

---

## 问题描述

**现象**：导入新的 K8s 配置（bearer_token 类型）后，访问容器平台数据时返回 401 Unauthorized。

**根因**：`backend/app/services/k8s_client_factory.py:114` 错误地将 token 放到了名为 `"authorization"` 的 api_key 字典 key 中：

```python
k8s_config.api_key = {"authorization": f"Bearer {token}"}
```

但 `kubernetes_asyncio` 库（v29.0.0）的 `Configuration.auth_settings()` 方法只识别 key 为 `"BearerToken"` 的项。当 api_key 中没有 `"BearerToken"` 这个 key 时，`auth_settings()` 返回空字典 `{}`，导致客户端**没有附加任何 Authorization header** 给 API 请求。

K8s API Server 收到无认证的请求，返回 `401 Unauthorized: must authenticate`。

---

## 解决方案

### 修复代码

将 `k8s_client_factory.py:114` 改为：

```python
# 修复前
k8s_config.api_key = {"authorization": f"Bearer {token}"}

# 修复后（kubernetes_asyncio 会自动加 'Bearer ' 前缀）
k8s_config.api_key = {"BearerToken": token}
```

**说明**：
- `kubernetes_asyncio` 识别 `"BearerToken"` key 后，自动构造 `Authorization: Bearer <token>` header
- 不需要手动拼接 `f"Bearer {token}"`，库会自动加前缀

### 为什么之前 client_cert 能正常工作？

- `client_cert` 通过 `cert_file`/`key_file` 给 `ssl_context.load_cert_chain()` 用，走 SSL mTLS 双向认证
- 与 `api_key` 字典无关
- 所以 `78ea6728`（client_cert）能成功，`61121d65`（client_cert）也成功

---

## 测试计划

### 单元测试

为 `k8s_client_factory.build_client()` 补充单元测试，覆盖三种认证路径：
1. `bearer_token`：验证 `config.api_key["BearerToken"]` 被正确设置
2. `client_cert`：验证 `config.cert_file` 和 `config.key_file` 被正确设置
3. `basic_auth`：验证 `config.username` 和 `config.password` 被正确设置

### 集成测试

1. 重启后端服务
2. 用 `curl` 调用 bearer_token 配置的 `/api/k8s-tool/{config_id}/namespaces`
   - 预期：返回 200 OK + namespace 列表
3. 用 `curl` 调用 client_cert 配置的 `/api/k8s-tool/{config_id}/namespaces`
   - 预期：返回 200 OK（无回归）
4. 浏览器访问 http://localhost:5178/tools/k8s-tool
   - 验证新导入的 bearer_token 配置能正常加载数据

---

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 修改认证逻辑 | 低 | 仅改动一行代码，且有单元测试覆盖 |
| client_cert 回归 | 无 | client_cert 走 SSL mTLS，与 api_key 无关 |
| basic_auth 回归 | 无 | basic_auth 直接设置 username/password，与 api_key 无关 |

---

## 验收标准

- [ ] bearer_token 配置能正常访问 K8s API（返回 200）
- [ ] client_cert 配置无回归（返回 200）
- [ ] 单元测试覆盖三种认证路径
- [ ] 浏览器 Console 无错误
- [ ] 代码审查通过，提交到 git

---

**下一步**: 用户 review 本文档后，调用 writing-plans skill 生成详细实现计划。
