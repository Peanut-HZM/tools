# Image Generation Tool — 部署清单

> 适用版本：Task 13.1 之后的 image-gen 工具端到端上线检查表。
> 假设已合并 Phase 1 ~ Phase 12 的所有代码变更。

---

## 1. 环境变量 (.env)

确保 `backend/.env` 中包含以下变量（参考 `backend/app/config/config.py`）：

```bash
# 数据库（必须：PostgreSQL）
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Dify 工作空间
DIFY_API_URL=https://your-dify-instance.com/v1
DIFY_APP_API_KEY=app-xxxxxxxxxxxxxxxx
DIFY_WORKFLOW_TEXT2IMG=wf-text2img-xxxx
DIFY_WORKFLOW_IMG2IMG=wf-img2img-xxxx
DIFY_WORKFLOW_INPAINT=wf-inpaint-xxxx
DIFY_WORKFLOW_UPLOAD_EDIT=wf-upload-edit-xxxx
DIFY_DEFAULT_TIMEOUT=60

# 图像生成功能开关（默认 True；关闭后前端入口隐藏、路由 503）
IMAGE_GENERATION_ENABLED=true

# 阿里云 OSS
STORAGE_PROVIDER=aliyun_oss
ALIYUN_OSS_ACCESS_KEY_ID=...
ALIYUN_OSS_ACCESS_KEY_SECRET=...
ALIYUN_OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com
ALIYUN_OSS_BUCKET=oss-bucket-name
ALIYUN_OSS_CALLBACK_URL=https://your-domain.com/oss/callback
```

如使用 MinIO 自托管：

```bash
STORAGE_PROVIDER=minio
MINIO_ENDPOINT=minio.example.com:9000
MINIO_API_ENDPOINT=https://minio.example.com:9000
MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...
MINIO_BUCKET_NAME=tools-files
MINIO_SECURE=true
```

---

## 2. Dify 工作空间初始化（一次性）

在 Dify 后台创建 4 个工作流，依次拿到 `workflow_id` 填入 `.env`：

| 操作 | 工作流入口 | 输入 | 输出 |
|---|---|---|---|
| 文生图 (text2img) | 文本提示词 + size + n + style + model_preference | prompt / size / n / style / model_preference | image_urls（列表） |
| 图生图 (img2img) | 文本提示词 + 参考图 URL + strength + size + model | prompt / reference_url / strength / size / model_preference | image_urls |
| 局部重绘 (image) | 提示词 + 图像 URL + 蒙版 URL + size + model | prompt / image_url / mask_url / size / model_preference | image_urls |
| 上传编辑 (upload_edit) | 图像 URL + edit_type + 可选 prompt | image_url / edit_type / prompt | image_urls |

**工作流输出格式约定**（Dify 节点结束响应）：

```json
{
  "images": ["https://...url1.png", "https://...url2.png"],
  "model_used": "qwen-image-v1"
}
```

参考设计文档：`docs/plans/2026-08-23-image-generation-workflow-design.md`

---

## 3. 数据库迁移

### 3.1 新部署（首次）

`backend/app/main.py` 启动时会调用 `Base.metadata.create_all`，自动建表。无需手动迁移。

确认表已创建：

```sql
\dt
-- 应包含：
--   image_gen_history
--   image_gen_quota
--   image_gen_dify_config
--   image_gen_degradation_config
--   image_gen_retention_config
```

### 3.2 已有部署升级

如果是从 Phase 9 之前升级（已有部署已有部分表），可能需要补齐字段或表。建议顺序：

```bash
# 1) 备份数据库
pg_dump -h host -U user dbname > backup_pre_image_gen_$(date +%Y%m%d).sql

# 2) 启动新版本后端（uvicorn），由代码自动 create_all 增量建表
#    （注意：create_all 不会修改已有表结构，仅创建缺失表）

# 3) 如果 Phase 10 加了 `enabled` 列到 image_gen_retention_config 而当前 PG 不存在该列：
python backend/scripts/inspect_image_gen_schema.py  # 自检脚本
ALTER TABLE image_gen_retention_config ADD COLUMN IF NOT EXISTS enabled BOOLEAN DEFAULT TRUE;
```

### 3.3 索引确认

性能敏感的索引应在迁移后手动确认存在：

```sql
CREATE INDEX IF NOT EXISTS idx_img_gen_history_user_created
  ON image_gen_history (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_img_gen_history_user_deleted
  ON image_gen_history (user_id, is_deleted);

CREATE INDEX IF NOT EXISTS idx_img_gen_history_last_accessed
  ON image_gen_history (last_accessed_at);
```

---

## 4. 默认管理员配额

首次部署后，**至少为管理员账号分配配额**，否则无法通过 UI 自测：

```sql
INSERT INTO image_gen_quota (
    user_id, daily_limit, monthly_limit, daily_used, monthly_used,
    daily_reset_date, monthly_reset_date, valid_from, valid_until,
    granted_by, notes, created_at, updated_at
) VALUES (
    'admin-user-id', 100, 3000, 0, 0,
    NOW(), NOW(), NULL, NULL,
    'system-bootstrap', 'default admin quota', NOW(), NOW()
);
```

或通过 admin 页面：

1. 登录 → 访问 `http://your-domain/admin/image-generation`
2. 切到「用户配额」Tab → 顶部「分配配额」
3. 填入 admin user_id（从 `auth_users` 表查）
4. 保存

---

## 5. OSS 配置

参考项目根 `backend/app/config/config.py` 中的 `OssService`。验证：

```bash
# 测试 OSS 连通性（在 backend 目录）
python -c "from app.services.oss_service import OssService; print(OssService().test_connection())"
```

应输出 `True`。

**Bucket 权限**：

- 上传走 STS / Sign URL（推荐）：bucket 私有读写，前端通过签名 URL 临时访问
- 若使用公共读：注意防盗链

**目录约定**：

```
image-gen/ref/<uuid>.png     # 参考图
image-gen/mask/<uuid>.png    # 蒙版图
image-gen/result/<uuid>.png  # 结果图
```

---

## 6. 前端构建

```bash
cd frontend
npm ci --no-audit --prefer-offline
npm run build
```

构建产物在 `frontend/dist/`，由后端 StaticFiles 挂载（或反向代理到 nginx）。

确认 `frontend/dist/assets/` 中包含 image-gen chunk：

```bash
ls frontend/dist/assets/ | grep -i image
# 应输出多个 image-gen 相关 JS / CSS
```

---

## 7. 后端启动

```bash
# 1) 安装依赖
cd backend
pip install -r requirements.txt

# 2) 启动服务（推荐通过项目脚本）
python dev-services.py restart backend
# 或手动：
uvicorn app.main:app --host 0.0.0.0 --port 19092 --workers 2

# 3) 验证健康
curl http://localhost:19092/health
```

**Worker 数**：并发配额校验依赖 DB 行锁（SELECT FOR UPDATE），多 worker 安全；
但 Dify 调用是阻塞 HTTP，worker 数 ≈ CPU 核数即可，过多反而因排队拉长响应时间。

---

## 8. 验证步骤

### 8.1 前端冒烟测试

| 步骤 | 期望 |
|---|---|
| 访问 `/tools/image-generation` | 显示 4 个 Tab（文生图/图生图/局部重绘/上传编辑） |
| 切换 Tab | 表单字段正确切换 |
| 输入提示词 + 点「开始生成」 | 进度条显示，返回生成结果大图 |
| 历史 Tab | 显示本次生成记录 |
| 多语言切换（中/英） | 所有 UI 文案随之切换 |

### 8.2 后端 API 验证

```bash
# 1) 获取 JWT
TOKEN=$(curl -s -X POST http://localhost:19092/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"***"}' | jq -r .access_token)

# 2) 测试配额
curl -s http://localhost:19092/api/image-generation/quota/me \
  -H "Authorization: Bearer $TOKEN" | jq

# 3) 测试生成
curl -X POST http://localhost:19092/api/image-generation/generate \
  -H "Authorization: Bearer $TOKEN" \
  -F "operation=text2img" \
  -F "prompt=test cat"
```

### 8.3 管理后台

访问 `/admin/image-generation`，验证 5 个 Tab：

1. 使用统计：图表数据渲染（至少有 1 条历史才能看到非零）
2. Dify 配置：4 个 workflow_id 可编辑，「测试连通性」按钮返回成功
3. 降级配置：启用 / 阈值 / 持续时长表单可保存
4. 保留策略：mode / n_days / cron 表单可保存，「手动触发清理」按钮响应
5. 用户配额：搜索 user_id、分配 / 编辑 / 撤销 / 重置操作

---

## 9. 已知限制 / 风险

### 9.1 并发性能

- 单进程 uvicorn 下并发能力受限于 worker 数；
- 配额校验走 DB 行锁，并发 100+ 请求时 PostgreSQL 锁等待会增加尾延迟；
- 若日活 > 1000 用户，建议：
  - 增加 worker 数（2~4 个即可）
  - 高频场景引入 Redis 计数（每次 +1 先 Redis，再异步刷 PG）

### 9.2 Dify 工作流变更

- 修改 Dify 工作流后必须同步更新 `image_gen_dify_config` 表中的对应 `workflow_id`；
- 否则旧 workflow_id 被删除/迁移后会导致 502 错误；
- 推荐通过 admin 后台「Dify 配置」Tab 更新（不需重启后端）。

### 9.3 配额计数器

- 当前按 UTC 自然日 / 自然月重置（`daily_reset_date` / `monthly_reset_date` 与 `now` 比较）；
- 中国大陆用户若按本地日界线判定，需自行修改 `app/services/image_gen_quota_service.py` 中的
  `_is_same_day` / `_is_same_month`（将 `datetime.now(timezone.utc)` 替换为带时区的本地时间）。

### 9.4 OSS 成本

- 默认保留所有历史对应的 OSS 文件；
- 启用「保留策略」（admin 后台）后才会按 `n_days` 自动清理 result OSS key；
- `image-gen/ref/` 和 `image-gen/mask/` 不在自动清理范围，若需清理需自行扩展。

### 9.5 降级触发

- 当前降级服务（`DegradationService`）在 Phase 9 之后启用；
- 升级前请确认 `image_gen_degradation_config` 表已存在并至少一行 `enabled=false` 默认配置。

### 9.6 测试用并发

- 集成测试中的「并发不超限」用例（`test_concurrent_generations_no_overlimit_postgres`）需要真实 PostgreSQL；
- 默认 SQLite 跳过该用例，CI 上若需验证并发安全，请设置 `IMAGE_GEN_TEST_PG_URL` 指向专用测试库。

---

## 10. 回滚方案

若上线后发现严重问题：

```bash
# 1) 通过环境变量快速禁用整个 image-gen 功能
IMAGE_GENERATION_ENABLED=false  # 重启后端

# 2) 前端入口自动隐藏（`/tools/image-generation` 路由前置检查）
# 3) 后端所有 /api/image-generation/* 端点返回 503

# 完全回滚代码：
git revert <commit-sha>
python dev-services.py restart
```

降级启用不影响现有用户数据；恢复时把 env 改回 `true` 即可。

---

## 11. 监控建议

- 接入 Prometheus / Grafana（项目若已部署）：
  - `image_gen_request_total{operation, status}` — 请求计数
  - `image_gen_request_duration_seconds{operation}` — 耗时直方图
  - `image_gen_quota_usage{user_id}` — 当前用量（高基数，慎用）
  - `image_gen_degraded` — 当前降级状态（0 / 1）
- 告警规则建议：
  - 5xx 错误率 > 5% 持续 5 分钟
  - Dify 平均响应 > 30s 持续 5 分钟
  - OSS 上传失败率 > 1%

---

## 附录：相关文档

- 架构设计：`docs/plans/2026-08-23-image-generation-workflow-design.md`
- 数据库迁移：`backend/scripts/` 下相关脚本
- API Swagger：`http://localhost:19092/docs#/image-generation`
- 集成测试：`backend/tests/test_image_generation_integration.py`