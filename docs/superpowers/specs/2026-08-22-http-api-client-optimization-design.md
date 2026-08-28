# HTTP API 客户端优化设计文档

## 概述

参考 APIfox 和 Postman，完善和优化当前 HTTP API 客户端工具。采用模块化重构方案，分 5 个变更按优先级实施。

## 变更拆分

| 变更 | 功能 | 优先级 | 状态 |
|---|---|---|---|
| 变更 1 | Form-data Body、变量语法高亮、HTML/图片预览 | P0 | 待实施 |
| 变更 2 | Collection 嵌套文件夹（5层）、OAuth 2.0 全类型 | P0 | 待实施 |
| 变更 3 | Pre-request Scripts、Tests/Assertions、Cookie 管理 | P1 | 待实施 |
| 变更 4 | Collection Runner、请求时间分解、GraphQL | P1 | 待实施 |
| 变更 5 | OpenAPI 导入、Mock Server、PDF/音视频预览 | P2 | 待实施 |

## 技术选型

- **编辑器**: Monaco Editor（变量高亮、代码编辑）
- **脚本引擎**: 前端 JavaScript（Pre-request/Tests）+ 后端 Python（复杂逻辑）
- **状态管理**: Zustand（现有）+ Script Store（新增）
- **后端**: FastAPI + httpx（现有）+ Python 脚本执行器（新增）
- **Collection Runner**: 前端并行执行（最多 6 并发）
- **OAuth 2.0**: 全部支持（Authorization Code、Client Credentials、Password、Implicit）
- **文件夹嵌套**: 最多 5 层
- **响应预览**: 全部支持（HTML、图片、PDF、音频、视频）

## 数据模型变更

### 新增表

```sql
-- 脚本表（Pre-request Scripts / Tests）
CREATE TABLE http_request_scripts (
    id UUID PRIMARY KEY,
    request_id UUID REFERENCES http_requests(id),
    script_type VARCHAR(20),  -- 'pre_request' | 'test'
    language VARCHAR(20),     -- 'javascript' | 'python'
    code TEXT,
    enabled BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Cookie 存储
CREATE TABLE http_cookies (
    id UUID PRIMARY KEY,
    user_id VARCHAR(50),
    domain VARCHAR(255),
    name VARCHAR(255),
    value TEXT,
    path VARCHAR(255),
    expires_at TIMESTAMP,
    created_at TIMESTAMP
);

-- Collection Runner 结果
CREATE TABLE collection_runs (
    id UUID PRIMARY KEY,
    collection_id UUID REFERENCES http_request_collections(id),
    user_id VARCHAR(50),
    total_requests INTEGER,
    success_count INTEGER,
    fail_count INTEGER,
    results JSONB,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);
```

### 修改表

```sql
ALTER TABLE http_requests ADD COLUMN body_type_new VARCHAR(20);
ALTER TABLE http_requests ADD COLUMN form_data JSONB;
ALTER TABLE http_requests ADD COLUMN graphql_query TEXT;
ALTER TABLE http_requests ADD COLUMN graphql_variables TEXT;
```

## 前端组件架构

### 新增组件

```
frontend/src/components/Tools/HttpApiClient/
├── components/
│   ├── ScriptEditor/           # Monaco Editor 封装
│   │   ├── ScriptEditor.tsx
│   │   └── VariableHighlighter.tsx
│   ├── FormDataEditor/         # Form-data 编辑器
│   │   └── FormDataEditor.tsx
│   ├── FileUpload/             # 文件上传组件
│   │   └── FileUpload.tsx
│   ├── ResponsePreview/        # 响应预览组件
│   │   ├── HtmlPreview.tsx
│   │   ├── ImagePreview.tsx
│   │   ├── PdfPreview.tsx
│   │   └── MediaPreview.tsx
│   ├── CookieManager/          # Cookie 管理
│   │   └── CookieManager.tsx
│   ├── CollectionRunner/       # 集合运行器
│   │   ├── RunnerPanel.tsx
│   │   └── RunnerResults.tsx
│   └── OAuth2Config/           # OAuth 2.0 配置
│       └── OAuth2Config.tsx
```

### 修改组件

- `RequestEditor.tsx` — 集成 Monaco Editor，添加 Form-data、GraphQL 标签页
- `ResponseViewer.tsx` — 集成新的预览组件
- `CollectionTree.tsx` — 支持嵌套文件夹（5 层）
- `EnvironmentSelector.tsx` — 增强变量管理（全局变量、密钥变量）

## 后端服务架构

### 新增服务

```
backend/app/services/
├── script_executor.py          # Python 脚本执行器（沙箱）
├── cookie_service.py           # Cookie 管理
├── collection_runner.py        # 集合运行器
└── oauth2_service.py           # OAuth 2.0 认证流程
```

### 新增路由

```python
POST   /http-client/scripts/execute          # 执行脚本
POST   /http-client/cookies                  # 保存 Cookie
GET    /http-client/cookies                  # 获取 Cookie
DELETE /http-client/cookies/{id}             # 删除 Cookie
POST   /http-client/runner/start             # 启动集合运行
GET    /http-client/runner/{run_id}          # 获取运行结果
POST   /http-client/oauth2/token             # 获取 OAuth2 Token
POST   /http-client/import/openapi           # OpenAPI 导入
POST   /http-client/mock/start               # 启动 Mock Server
```

## 脚本执行安全

- **Python 脚本**: 使用 `RestrictedPython` 沙箱执行，禁止 `import os`、文件操作、网络请求
- **JavaScript 脚本**: 前端使用 `new Function()` 执行，限制全局对象访问

## 实施计划

### 变更 1（P0）：基础体验优化
- Form-data Body 支持
- 变量语法高亮（Monaco Editor）
- HTML/图片响应预览

### 变更 2（P0）：组织管理
- Collection 嵌套文件夹（5 层）
- OAuth 2.0 全类型认证

### 变更 3（P1）：脚本能力
- Pre-request Scripts（前端 JS + 后端 Python）
- Tests/Assertions
- Cookie 管理

### 变更 4（P1）：高级功能
- Collection Runner（前端并行）
- 请求时间分解（DNS/Connect/TLS）
- GraphQL 支持

### 变更 5（P2）：生态集成
- OpenAPI 导入
- Mock Server
- PDF/音视频预览

## 验收标准

每个变更完成后：
1. 功能正常工作
2. 现有功能不受影响
3. 代码通过编译/语法检查
4. 部署到服务器验证
