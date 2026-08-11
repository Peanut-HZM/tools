# K8s Bearer Token 认证修复实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 bearer_token 类型 K8s 配置返回 401 Unauthorized 的问题，并补充单元测试防止回归。

**Architecture:** 将 `k8s_client_factory.py:114` 的 api_key 字典 key 从 `"authorization"` 改为 `"BearerToken"`，使 kubernetes_asyncio 能正确识别并附加 Authorization header。补充单元测试覆盖 bearer_token/client_cert/basic_auth 三种认证路径。

**Tech Stack:** Python 3.10+, pytest, kubernetes_asyncio 29.0.0

## Global Constraints

- 所有对话、文档、注释、日志、提交信息必须使用中文
- 修改前后端代码后，必须使用浏览器进行验证
- 前端端口 5178，后端端口 19092
- 服务重启统一用 `python dev-services.py restart`
- TypeScript 文件修改后需验证编译无错误
- 每个任务需编写测试并验证通过

---

### Task 1: 修复 bearer_token 认证注入 bug

**Files:**
- Modify: `backend/app/services/k8s_client_factory.py:114`

**Interfaces:**
- Consumes: `config.api_key` dict
- Produces: 正确的 Authorization header 注入

- [ ] **Step 1: 修改 api_key 字典的 key**

将 `k8s_client_factory.py:114` 从：

```python
k8s_config.api_key = {"authorization": f"Bearer {token}"}
```

改为：

```python
k8s_config.api_key = {"BearerToken": token}
```

**说明**：
- `kubernetes_asyncio` 的 `Configuration.auth_settings()` 方法只识别 key 为 `"BearerToken"` 的项
- 当识别到 `"BearerToken"` 后，库会自动构造 `Authorization: Bearer <token>` header
- 不需要手动拼接 `f"Bearer {token}"`，库会自动加前缀

- [ ] **Step 2: 验证修改**

运行：
```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m py_compile app/services/k8s_client_factory.py
```

预期：无语法错误

- [ ] **Step 3: Commit**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/app/services/k8s_client_factory.py
git commit -m "fix: 修复 bearer_token 认证注入，使用 BearerToken key 使 kubernetes_asyncio 能正确附加 Authorization header"
```

---

### Task 2: 补充单元测试防止回归

**Files:**
- Modify: `backend/tests/test_k8s_client_factory.py`

**Interfaces:**
- Consumes: `build_client` 函数
- Produces: 覆盖三种认证路径的单元测试

- [ ] **Step 1: 扩展测试文件，覆盖三种认证路径**

在 `test_k8s_client_factory.py` 末尾添加以下测试：

```python
@pytest.mark.asyncio
async def test_build_client_bearer_token_sets_api_key_correctly(mock_config):
    """验证 bearer_token 模式下 api_key 字典使用 BearerToken key"""
    with patch("app.services.k8s_client_factory.EncryptionUtils") as mock_enc, \
         patch("app.services.k8s_client_factory.k8s_client") as mock_k8s:

        mock_enc.decrypt.return_value = json.dumps({"token": "my-token"})
        
        mock_api_client = MagicMock()
        fut = asyncio.Future()
        fut.set_result(None)
        mock_api_client.close.return_value = fut
        mock_k8s.ApiClient.return_value = mock_api_client
        
        async with build_client(mock_config) as bundle:
            # 验证 Configuration 被正确构造
            config_call = mock_k8s.Configuration.return_value
            assert config_call.api_key == {"BearerToken": "my-token"}
            assert config_call.host == mock_config["server"]


@pytest.mark.asyncio
async def test_build_client_client_cert(mock_config):
    """验证 client_cert 模式下 cert_file 和 key_file 被正确设置"""
    mock_config["auth_type"] = "client_cert"
    
    with patch("app.services.k8s_client_factory.EncryptionUtils") as mock_enc, \
         patch("app.services.k8s_client_factory.k8s_client") as mock_k8s, \
         patch("app.services.k8s_client_factory._write_temp_file") as mock_write:

        mock_enc.decrypt.return_value = json.dumps({
            "client_cert": "CERT_CONTENT",
            "client_key": "KEY_CONTENT"
        })
        mock_write.side_effect = ["/tmp/cert.crt", "/tmp/key.key"]
        
        mock_api_client = MagicMock()
        fut = asyncio.Future()
        fut.set_result(None)
        mock_api_client.close.return_value = fut
        mock_k8s.ApiClient.return_value = mock_api_client
        
        async with build_client(mock_config) as bundle:
            config_call = mock_k8s.Configuration.return_value
            assert config_call.cert_file == "/tmp/cert.crt"
            assert config_call.key_file == "/tmp/key.key"
            
            # 验证临时文件被写入
            assert mock_write.call_count == 2


@pytest.mark.asyncio
async def test_build_client_basic_auth(mock_config):
    """验证 basic_auth 模式下 username 和 password 被正确设置"""
    mock_config["auth_type"] = "basic_auth"
    
    with patch("app.services.k8s_client_factory.EncryptionUtils") as mock_enc, \
         patch("app.services.k8s_client_factory.k8s_client") as mock_k8s:

        mock_enc.decrypt.return_value = json.dumps({
            "username": "admin",
            "password": "secret"
        })
        
        mock_api_client = MagicMock()
        fut = asyncio.Future()
        fut.set_result(None)
        mock_api_client.close.return_value = fut
        mock_k8s.ApiClient.return_value = mock_api_client
        
        async with build_client(mock_config) as bundle:
            config_call = mock_k8s.Configuration.return_value
            assert config_call.username == "admin"
            assert config_call.password == "secret"
```

- [ ] **Step 2: 运行测试**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_k8s_client_factory.py -v
```

预期：所有测试通过（包括新增的 3 个 + 原有的 2 个 = 5 个）

- [ ] **Step 3: Commit**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/tests/test_k8s_client_factory.py
git commit -m "test: 补充 k8s_client_factory 三种认证路径的单元测试"
```

---

### Task 3: 重启后端并验证修复效果

**Files:**
- 无文件修改（纯测试任务）

- [ ] **Step 1: 重启后端服务**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
python dev-services.py restart backend
```

- [ ] **Step 2: 验证 bearer_token 配置**

获取一个 bearer_token 类型的配置 ID：

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
source venv/bin/activate
python -c "
from app.config.database import get_pooled_db_connection, release_db_connection
conn = get_pooled_db_connection()
cur = conn.cursor()
cur.execute(\"SELECT id FROM k8s_connections WHERE auth_type = 'bearer_token' AND deleted = FALSE LIMIT 1\")
row = cur.fetchone()
print(row['id'] if row else 'NO_CONFIG')
cur.close()
release_db_connection(conn)
"
```

假设返回的 ID 是 `13c08020-2873-4b9e-a3f0-2544df90119b`（it-sap-pd-bj4hw），则调用：

```bash
# 先获取 token
TOKEN=$(curl -s -X POST http://localhost:19092/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"peanut","password":"Peanut2817*#"}' | jq -r '.access_token')

# 调用 namespaces 接口
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:19092/api/k8s-tool/13c08020-2873-4b9e-a3f0-2544df90119b/namespaces
```

预期：返回 200 OK + namespace 列表（如 `["default","kube-system",...]`）

- [ ] **Step 3: 验证 client_cert 配置无回归**

获取一个 client_cert 类型的配置 ID：

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
source venv/bin/activate
python -c "
from app.config.database import get_pooled_db_connection, release_db_connection
conn = get_pooled_db_connection()
cur = conn.cursor()
cur.execute(\"SELECT id FROM k8s_connections WHERE auth_type = 'client_cert' AND deleted = FALSE LIMIT 1\")
row = cur.fetchone()
print(row['id'] if row else 'NO_CONFIG')
cur.close()
release_db_connection(conn)
"
```

假设返回的 ID 是 `78ea6728-bd14-4197-b8d3-48a8b8ce9aee`（ehr-dev），则调用：

```bash
# 使用上面获取的 TOKEN
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:19092/api/k8s-tool/78ea6728-bd14-4197-b8d3-48a8b8ce9aee/namespaces
```

预期：返回 200 OK + namespace 列表（无回归）

- [ ] **Step 4: 浏览器验证**

访问：http://localhost:5178/tools/k8s-tool

验证步骤：
1. 点击之前失败的 bearer_token 配置（如 it-sap-pd-bj4hw）
2. 验证能正常加载 namespace 和 pod 列表
3. 点击 client_cert 配置（如 ehr-dev）
4. 验证仍能正常加载数据（无回归）
5. 打开浏览器 DevTools → Console，确认无红色错误

- [ ] **Step 5: 验证完成**

如果所有验证通过，标记任务完成。

---

## 总结

本实现计划共 3 个任务：

1. **Task 1**: 修复 bearer_token 认证注入 bug（一行代码）
2. **Task 2**: 补充单元测试（3 个测试用例，覆盖三种认证路径）
3. **Task 3**: 重启后端并验证修复效果（API + 浏览器端到端验证）

预计总工时：30 分钟
