# 后端图标迁移计划 (FA class 字符串 → lucide icon 标识符)

> 状态: 计划草案 (Phase 6 文档产出)
> 创建日期: 2026-08-26
> 范围: 仅描述计划，不包含实现; 实施时需要单独的计划文档 + 提交记录

## Background

### 当前状态

- 后端 `backend/app/data/tools_data.py` 以及 `Tool` / `Category` 等数据模型中的 `icon` 字段, 当前存储的是 **Font Awesome class 字符串** (`'fa-server'`、`'fas fa-key'` 等)。
- 前端通过 `frontend/src/utils/iconResolver.ts` 在运行时把这些 FA class 字符串映射到 `lucide-react` 组件, 从而彻底移除对 Font Awesome CDN 的依赖。
- `iconResolver.ts` 维护了一份 `faIconMap: Record<string, ComponentType>`, 包含几十条 FA 名 → lucide 组件的手工映射。

### 根因

- 数据层 (`tools_data.py` 中的种子数据、数据库里的 `tool.icon` 列) 在 Phase 3 icon 迁移之前就已经存在。
- Phase 3 迁移只动了前端渲染层, 把 FA 字符串 → lucide 组件, 没有改后端存储格式。
- 结果: 后端数据仍是 FA 字符串, 前端承担"翻译"职责; 这是临时方案, 长期看应当把翻译职责下沉到数据写入端, 让后端直接存储 lucide icon 名。

## Goal

把后端存储的 `icon` 字段从 FA class 字符串改为 lucide icon 标识符, 这样:

1. `iconResolver.ts` 中的 FA 解析分支可以退役。
2. 系统里不再残留任何 FA 形态的数据 (字符串里不再出现 `fa-` / `fas` / `far` 等 token)。
3. 后端校验和前端组件可以共用同一份"合法的 icon 名"清单。

## Migration plan

### Phase A — inventory (盘点)

1. 在后端代码中 grep 所有 FA class 字符串:
   ```bash
   grep -rn 'fa-' backend/app/data/ backend/app/models/ backend/app/api/
   ```
2. 列出所有使用过的唯一 icon 名。
3. 与 `frontend/src/utils/iconResolver.ts` 中的 `faIconMap` 做交叉校验, 确保每个后端使用过的 icon 在前端都有对应映射。
4. 输出"需要迁移的 icon 清单": `'fa-server' → 'Server'`、`'fas fa-key' → 'Key'` 等, 后续作为 Phase B 迁移脚本的输入。

### Phase B — backend changes (后端改造)

1. 新增后端 enum / 校验器: `LucideIconName`, 值集合镜像 `iconResolver.faIconMap` 的 keys (即 lucide 组件的 PascalCase 名)。建议放在 `backend/app/models/enums.py` 或 `backend/app/utils/icon_catalog.py`。
2. 编写迁移脚本 (一次性 Alembic 数据迁移或独立 Python 脚本), 把现有数据按 Phase A 的清单转换:
   - `'fa-server'` → `'Server'`
   - `'fas fa-key'` → `'Key'`
   - 等等
3. 更新 `Tool.icon` / `Category.icon` 的字段定义: 类型仍是 `str`, 但新增 Pydantic validator, 校验值必须在 `LucideIconName` 集合内。
4. 更新管理后台 UI (`ToolManagement` 等) 的 placeholder 文案: 由 "fa-server" 改成 "Server, Key, ..." 之类的提示。
5. **deprecation window 兜底**: 在过渡期内 (至少一个发布周期), 后端接受任何字符串, 对未识别值打 warning 日志并 fallback 到 `'Wrench'`。这样:
   - 不会因为遗漏某些 icon 名而阻塞写入;
   - 前端不需要立刻同步改造 (但前端的 FA 解析逻辑仍然保留作为兜底)。

### Phase C — frontend changes (前端改造)

1. `Tool.icon` 字段类型保持 `string` (语义从 FA class 改为 lucide 名, 但类型不变, 避免大量接口同步改动)。
2. 更新 `iconResolver.ts`:
   - 新增"PascalCase 直接查找"分支: 如果字符串是 `'Server'` / `'Key'` 这种单纯 PascalCase 名, 直接在 `lucideIconMap` (新 map, key 为 PascalCase 名) 中查找。
   - 保留 FA 解析分支作为过渡期兜底。
   - 实现策略: 简单判断是否包含空格或连字符, 是则走 FA 解析, 否则走 PascalCase 直接查找。
3. 一个发布周期后 (Phase D 验证完毕), 删除 FA 解析分支和 `faIconMap`, `iconResolver.ts` 退化为单一 `PascalCase → Component` map。

### Phase D — verify (验证)

1. 所有 tools / categories 渲染出正确的 lucide icon (人工 + 截图回归)。
2. 管理后台 ToolManagement 的 placeholder 文案展示 lucide 名 (而非 FA class)。
3. 数据库中旧的 FA class 字符串要么被迁移脚本改写、要么 (deprecation window 期间) 被后端 fallback 为 Wrench, 不应再渲染出 "未知图标"。
4. `iconResolver.ts` 可以被删除, 或被裁剪为只包含 PascalCase → Component 的简单 map。

## Risks

- **长尾 icon 漏配**: 数据库里可能有 `faIconMap` 没覆盖的旧值。处理方式: 迁移脚本里对未映射值记录日志, 走 Wrench fallback, 同时提醒补 `faIconMap`。
- **管理后台历史值**: 后台表单可能允许用户手填过任意字符串, 这些值不在 `LucideIconName` 集合内。处理方式: Pydantic validator 在写入时校验, 不合法的拒绝或 fallback。
- **API 消费者依赖 FA 字符串**: 如果有外部消费者 (例如移动端、未来对接的小程序) 仍然依赖 FA 字符串格式, 切换后端存储会破坏它们。
  - 缓解: 保留一个版本字段, 或者在 API 响应里同时返回 `icon` (lucide 名) 和 `icon_legacy` (FA class) 双字段, 过渡一段时间后再撤掉 `icon_legacy`。
- **迁移脚本回滚**: 数据迁移脚本应当可在 transaction 内回滚, 避免把脏数据写进去。

## Out-of-scope

- 本文档只描述计划, 不包含实际实现。
- 实施阶段需要单独的计划文档 + 多个原子提交 (数据迁移、字段校验、UI 文案、兜底 fallback、最终清理 `iconResolver.ts`)。
- 不涉及其他 icon 来源 (例如 emoji、SVG 自定义图标) 的统一。

## 关联文件

- `backend/app/data/tools_data.py` — 种子数据, 包含 FA class 字符串。
- `backend/app/models/` — `Tool` / `Category` 模型定义, `icon` 字段。
- `backend/app/api/` — 暴露 `icon` 字段的 API 路由。
- `frontend/src/utils/iconResolver.ts` — 当前前端 FA → lucide 翻译层, 计划退役。
- `frontend/src/components/Admin/` — 管理后台 UI, placeholder 文案需要更新。
