# 审查台账：ccusage 统一数据流重构  (2026-06-05)

> 启动时间：2026-06-05 16:42
> 范围：spec-review-loop 循环审新设计文档 + 实施计划
> 技术栈识别：Python (backend) + TypeScript/React (frontend) — **无栈插件可用**（`checklist-python.md` / `checklist-frontend.md` 未提供）
> 维度 1（项目规范）、维度 2（现有功能安全）整体 ⊘ N/A
> 维度 3（SQL 幂等性）、维度 4（设计完整性）按通用核心清单执行

## 待审清单（启动时确认）
- [x] docs/superpowers/specs/2026-06-05-ccusage-unified-data-flow-design.md（481 行）
- [x] docs/superpowers/plans/2026-06-05-ccusage-unified-data-flow.md（1412 行）

## 维度裁决汇总

| 维度 | 名称 | 状态 | 备注 |
|------|------|------|------|
| 1 | 项目规范符合性 | ⊘ N/A | 无 Python/前端栈插件可用 |
| 2 | 现有功能安全性 | ⊘ N/A | 无 Python/前端栈插件可用 |
| 3 | SQL 幂等性 | ✅ 通过 | 复用现有 `_upsert_records` 的 `ON CONFLICT (user_id, device_id, record_date, source, model) DO UPDATE` 天然幂等；3.1 DDL N/A（无 schema 变更）；3.3 数据安全：user_id 无 FK 约束，system_scheduler 安全 |
| 4 | 设计完整性 | ⚠️ 7 项 | 见下表 |

## 发现表（维度 4：设计完整性与一致性）

| ID   | 严重 | 文件:行 | 问题 | 状态 | 发现轮次 |
|------|------|---------|------|------|----------|
| F01  | 低 | spec:365-369 | `backfill_ccusage.py` docstring 写 `python -m backend.scripts.backfill_ccusage`，但脚本 `from app.models.base import SessionLocal` 绝对导入，要求 `backend/` 在 sys.path — 根目录直跑会 `ModuleNotFoundError`。Plan Task 11 Step 2 改为 `cd backend && python -m scripts.backfill_ccusage` 是对的 | 已修复 | 1 |
| F02  | **高** | plan Task 8 Step 2:928-982 | 新端点 5 处错误，会在 import 阶段或运行时直接报错：① `from app.utils.auth import verify_token` — 实际在 `app.utils.jwt`（grep 已确认 `backend/app/utils/auth.py` 不存在）；② `user["user_id"]` — JWT 标准 claim 是 `sub`（`jwt.py:67` 写明 `payload.get("sub")`）；③ 整个鉴权块是**重复造轮子** — 文件已 `from app.routes.auth import get_current_user_id`（line 31），且兄弟端点 `/sync` (line 1057-1072) 用 `get_current_user_id(authorization=authorization)` 一行解决；④ `from app.config.config import settings` 导入但未使用；⑤ `import os` 不在文件现有 import 区 | 已修复 | 1 |
| F03  | 中 | plan Task 5 Step 2:602-614 | 计划在现有 `sync_token_usage(user_id, days=90)` 末尾插入 v2 调用，但代码引用了 `db` / `device_id` / `device_name` / `since_date` / `until_date` — 现有函数签名只接受 `(user_id, days)`，**这些变量在作用域内不存在**。Spec 没要求 v2 集成到 `/sync` 端点（仅 scheduler + 新端点），该 Task 5 的整合**意图不明** | 已修复 | 1 |
| F04  | 低 | plan Task 8 Step 2:956 | 端点代码用 `os.environ.get("DESKTOP_MODE")`，但 `routes/token_usage.py` 现有 imports 没有 `import os`（line 1-33 实测）。需补 `import os` | 已修复 | 1 |
| F05  | 低 | plan Task 8 Step 2:945 | 端点代码用 `get_device_display_name()`，但文件现有 import 只 `from app.utils.device_id import get_device_id`（line 32 实测）。需扩展该 import | 已修复 | 1 |
| F06  | 低 | plan Task 7 Step 1:847-864 | `_sync_today` 用硬编码 `user_id="system_scheduler"`。无 FK 约束不报错，但 scheduler 数据会混入该 user 的 token_usage_records 查询（前端查询 `user_id` 过滤时不会显示，因为 spec 没要求加查询过滤；但审计时不易区分系统数据与真实用户数据）| 已修复 | 1 |
| F07  | 低 | plan Task 4 Step 1:430-496 | `usage_fetcher_v2.py` 重新声明 `_DESKTOP_MODE` / `USER_HOME` / `_cache` / `_CACHE_TTL` / `_get_from_cache` / `_set_cache` / `_run_cmd` — 7 个 helper 从 `usage_fetcher.py` 整体复制。Spec 4.1 写"复用现有"但对 V2 的 helper 复用未提及；DRY 原则下应 `from app.utils.usage_fetcher import _run_cmd, _get_from_cache, _set_cache, _DESKTOP_MODE, USER_HOME` | 已修复 | 1 |

## 维度 4 子项裁决

### 4.1 文档一致性
- ✅ Spec 11 个验收标准 → Plan 13 个 Task 全部覆盖（plan Self-Review Checklist 1401-1411 已自验）
- ✅ F01 已修复：spec vs plan 的 backfill 启动命令表述一致（统一为 `cd backend && python -m scripts.backfill_ccusage`）
- ✅ Spec 字段映射表 vs Plan Task 2 Step 1 输出字段一致
- ✅ Spec 工具 ID 列表（15 个 + other）vs Plan `AGENT_DISPLAY_NAMES` 一致
- ✅ 验收标准引用 `frontend/src/components/Tools/TokenUsage.tsx:514`（line 514 实测命中 `item.source === 'claude' ? 'Claude' : ...`）和 `backend/app/routes/token_usage.py:1029`（line 1029 实测命中 `TokenUsageRecord.source == req.source`） — 兼容性声称有据
- ✅ 无 TBD / TODO / FIXME / "类似 Task N" 占位符（grep 未命中）
- ✅ 无"等 / 相关 / 适当"模糊词

### 4.2 实现完整性
- ✅ 13 个 Task 每个都有具体文件和操作步骤
- ✅ 错误场景表覆盖 11 类边界（spec:402-415）
- ✅ 回滚方案："git revert 即可"（spec:473），所有改动 1-2 个 commit 范围内
- ✅ F02 已修复：端点改用 `get_current_user_id(authorization=authorization)` 一行（仿 /sync 端点）
- ✅ F03 已修复：`sync_token_usage` 签名改为接受可选 `since_date` / `until_date` kwargs，v2 调用用这些
- ✅ F04 / F05 已修复：plan Task 8 import 区已显式声明 `import os` + 扩展 `get_device_display_name`
- ✅ F06 已修复：`_sync_today` 用 `_resolve_scheduler_user_id(db)` 函数（env > admin > system 三级兜底）
- ✅ F07 已修复：`usage_fetcher_v2.py` 头部 `from app.utils.usage_fetcher import _run_cmd, _get_from_cache, _set_cache, _DESKTOP_MODE`，删除 7 个重复 helper

## 轮次日志
- 第 1 轮：新增 7 项（F01-F07），全部已修复
  - F02 高风险，1 项中风险，5 项低风险
  - 白名单内直接修复：F01（spec 文档）、F04 / F05（plan 缺失 import） → 3 项
  - 白名单外用户决策：F02 / F03 / F06 / F07 → 4 项
  - 连续无发现计数 = 0
- 第 2 轮：复审所有 7 项修复 + 维度 3/4 完整子项
  - 新增 0 项
  - 连续无发现计数 = 1
- 第 3 轮：复审复审 + 最终质量检查
  - 新增 0 项
  - 连续无发现计数 = 2 → **达到终止条件，审查结束**

## 最终结论
- **总体**：7 项问题全部已修复
- **SQL 幂等性**：✅ 通过（无 schema 变更，复用现有 upsert）
- **设计完整性**：✅ 通过（13 Task 全部覆盖 spec 11 验收标准，所有 helper 引用已对齐现有代码）
- **白名单内修改**：3 项（spec 文档 1，plan import 2）
- **白名单外修改**：4 项（端点鉴权重构 / 签名扩展 / user_id 解析 / DRY 复用）

