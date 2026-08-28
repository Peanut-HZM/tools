# LLM 通用配额管理 设计

> **状态：** 设计稿，待用户审阅
> **日期：** 2026-08-24
> **目标读者：** 本项目开发者、维护者
> **改动范围：** 后端 2 张新表 + 1 个新服务 + 6~8 个调用点接入 + 前端 1 个 tab 组件

## 1. 背景与目标

### 1.1 背景

当前项目有零散的"用量控制"机制，但**没有统一的用户级配额系统**：

- `image_gen_quota` 表只覆盖图像生成，且只有"按次数"模式
- 文本生成（PRD Agent / 图像生成的 selfdev brain）、ASR、OCR、Embedding 等无统一管控
- 用户在前端看不到任何"余额"信息；管理员无法批量分配额度
- 不同 LLM 调用点的用量审计缺失，无法做 token 级计费

### 1.2 目标

新增 **LLM 通用配额管理**：

1. **统一配额模型**：所有 LLM 调用（chat、PRD、image_gen、asr、ocr、embedding）走同一套 quota 服务
2. **三选一模式**：每个用户的配额记录互斥地属于 `count` / `token` / `time` 三种模式之一
3. **余额展示**：用户在工具页面看得到自己当前剩余次数 / 已用 token / 配额有效期
4. **管理入口**：在 `/admin/llm-configs` 增加"额度管理" tab，管理员可搜索/分配/重置/撤销
5. **数据迁移**：把 `image_gen_quota` 表已有记录迁移到新表，删旧表

### 1.3 非目标（v1 不做）

- 不做跨用户共享配额（家庭/团队配额）
- 不做自动充值 / 支付集成
- 不做配额预警邮件/消息通知（仅前端余额展示）
- 不改 Dify 路径的内部逻辑（Dify 工作流内部仍按现有方式工作，仅 quota 检查在本项目代码内进行）
- 不做每日/每月自动使用报告（仅靠 `llm_usage_log` 提供原始数据，统计 UI 后续单独设计）

## 2. 架构概览

### 2.1 核心抽象

把"配额检查"抽象为一个 hook service。所有 LLM 调用点都通过 `LLMQuotaService` 完成：
- **调用前**：`check_and_reserve(user_id, category, planned_tokens)` → 通过则预占，失败抛 `QuotaExceeded` → 路由映射为 HTTP 429
- **调用后**：`record_usage(user_id, category, actual_tokens)` → 把实际 token 数写入 usage_log，按 quota_mode 扣减对应字段

```
┌──────── Frontend ────────┐
│  /admin/llm-configs       │
│  [模型供应商][模型配置][额度管理] │  ← 新增 tab
│                            │
│  /tools/image-generation   │
│  顶部余额徽章              │  ← 显示当前用户余额
└─────────────┬────────────┘
              │ JWT
┌─────────────▼────────────┐
│  FastAPI Routes           │
│  LLM 调用点（chat/asr/…） │
│  ├─ check_and_reserve ──┐ │
│  └─ call LLM            │ │
│  └─ record_usage       ◄┘ │
└─────┬────────────────┬───┘
      │                │
      ▼                ▼
┌──────────────┐  ┌────────────────┐
│ LLMQuota     │  │ llm_usage_log  │
│ Service      │  │ (每次调用 1 行) │
└──────┬───────┘  └────────────────┘
       │
       ▼
┌──────────────────┐
│ llm_user_quota   │  ← 每用户 1 行
│ (三选一模式)      │
└──────────────────┘
```

### 2.2 数据库 ER

```
┌─────────────────────────────┐
│ llm_user_quota               │
│─────────────────────────────│
│ user_id          PK (str64)  │
│ quota_mode       str16       │ ← 'count' / 'token' / 'time'
│ -- count 模式字段 --         │
│ daily_limit      int         │
│ daily_used       int (def 0) │
│ daily_reset_date timestamptz │
│ monthly_limit    int         │
│ monthly_used     int (def 0) │
│ monthly_reset_dt timestamptz │
│ -- token 模式字段 --         │
│ token_period     str16       │ ← 'daily' / 'monthly' / 'total'
│ token_limit      int         │
│ token_used       int (def 0) │
│ token_reset_date timestamptz │
│ -- 公共字段 --                │
│ valid_from       timestamptz │
│ valid_until      timestamptz │
│ granted_by       str64       │
│ notes            str512      │
│ created_at       timestamptz │
│ updated_at       timestamptz │
└─────────────────────────────┘

┌─────────────────────────────┐
│ llm_usage_log                │
│─────────────────────────────│
│ id            PK uuid        │
│ user_id       str64 idx      │
│ category      str16 idx      │ ← 'text' / 'image' / 'asr' / 'ocr' / 'embedding'
│ tokens_used   int            │
│ request_count int (def 1)    │
│ model_used    str128         │
│ request_id    str64 (nullable) │  ← 用于关联 LLM 调用请求
│ called_at     timestamptz idx │
└─────────────────────────────┘
```

### 2.3 文件结构

新增：
- `backend/app/models/llm_quota_models.py` — 两张表的 ORM 定义
- `backend/app/services/llm_quota_service.py` — 通用配额服务（替代 `image_gen_quota_service.py`）
- `backend/app/routes/admin_llm_quota.py` — 管理员 API（grant / list / reset / revoke / detail）
- `backend/app/schemas/llm_quota.py` — Pydantic schema
- `backend/scripts/migrate_image_gen_quota_to_llm_quota.py` — 一次性数据迁移脚本（可重复执行，幂等）
- `frontend/src/components/Admin/LLMQuotaManager.tsx` — 第三个 tab 内容组件
- `frontend/src/components/Admin/LLMQuota/` — 子组件目录（UserQuotaTable / GrantModal / QuotaBadge / UsageStats）

修改：
- `backend/app/main.py` — 注册新路由 + 新模型 import
- `backend/app/routes/image_generation.py` — 把 `ImageGenQuotaService` 替换为 `LLMQuotaService`（`check_and_reserve` 调用时 category=`image`）
- `backend/app/routes/admin_image_generation.py` — 重命名/迁移配额 admin 端点到新路由
- `backend/app/services/image_gen_quota_service.py` — 标记 deprecated → 后续删除
- `backend/app/services/image_generation_service.py` — 把 `quota_svc.commit/release` 调用替换为新服务
- `backend/app/services/asr_service.py` / `ocr_service.py` / `embedding_service.py` / PRD chat 路由等 — 接入 quota hook（详见 §6）
- `frontend/src/api/imageGenerationApi.ts` — 调整 `getMyQuota` 路径（如必要）
- `frontend/src/components/Tools/ImageGeneration/index.tsx` — 顶部增加 `<QuotaBadge>` 显示余额
- `frontend/src/components/Admin/LLMConfigsPage.tsx` — 增加第三个 tab

删除：
- `backend/app/models/image_generation_models.py` 中 `ImageGenQuota` 类
- `backend/app/services/image_gen_quota_service.py`（迁移脚本验证后）

## 3. 数据模型详解

### 3.1 `llm_user_quota` 模式字段约束

由 `quota_mode` 决定哪些字段有效：

| mode | 必填字段 | 可选字段 | 含义 |
|------|----------|----------|------|
| `count` | `daily_limit` + `monthly_limit`（至少其一 > 0） | `valid_from`/`valid_until` | 按调用次数 |
| `token` | `token_limit`（> 0）、`token_period` | `valid_from`/`valid_until` | 按 token 总数 |
| `time` | `valid_from`/`valid_until`（必有一个） | 无 | 仅设有效期，无次数/token 上限 |

数据库层不做 CHECK 约束（避免跨方言迁移困难），由 service 层 `grant()` 方法在写入前校验：
```python
if mode == 'count' and not (daily_limit > 0 or monthly_limit > 0):
    raise ValueError("count 模式必须设置 daily_limit 或 monthly_limit")
if mode == 'token' and token_limit <= 0:
    raise ValueError("token 模式必须设置 token_limit > 0")
if mode == 'time' and not (valid_from or valid_until):
    raise ValueError("time 模式必须设置 valid_from 或 valid_until")
```

### 3.2 计数器自动重置

沿用 `image_gen_quota_service` 现有逻辑：
- `_is_same_day(daily_reset_date, now)` 比较日期部分，跨日自动归零 `daily_used`
- `_is_same_month(monthly_reset_date, now)` 跨月归零 `monthly_used`
- `token_period='daily'` 同理按日归零
- `token_period='monthly'` 按月归零
- `token_period='total'` 不归零（总量）

时区处理：DB 存 UTC；比较时统一用 `_now_utc()` 并去 tzinfo 后比较 date 部分（沿用现有 `_to_naive_or_aware` 工具）。

### 3.3 数据迁移

**表结构创建**：由 `Base.metadata.create_all(bind=engine)` 在应用启动时自动建表（沿用现有模式，见 `app/main.py` 第 108/117 行的 Token Usage / Image Gen 现有表）。新表不存在则建，已存在则跳过。

**数据迁移**：手动执行一次性脚本 `backend/scripts/migrate_image_gen_quota_to_llm_quota.py`：

1. 从 `image_gen_quota` 拷贝数据到 `llm_user_quota`：
   ```sql
   INSERT INTO llm_user_quota (
     user_id, quota_mode, daily_limit, daily_used, daily_reset_date,
     monthly_limit, monthly_used, monthly_reset_date,
     valid_from, valid_until, granted_by, notes, created_at, updated_at
   )
   SELECT
     user_id, 'count', daily_limit, daily_used, daily_reset_date,
     monthly_limit, monthly_used, monthly_reset_date,
     valid_from, valid_until, granted_by, notes, created_at, updated_at
   FROM image_gen_quota
   ON CONFLICT (user_id) DO NOTHING;  -- 幂等
   ```
2. 重启后端，路由全部切到新表
3. 灰度 1 周后人工执行 `DROP TABLE image_gen_quota;`

迁移脚本特性：
- **幂等**：重复执行不会重复插入（`ON CONFLICT DO NOTHING`）
- **可回滚**：保留 `image_gen_quota` 表至少 1 周不删
- **打印统计**：迁移 N 条 / 跳过 M 条（已存在）
- **入口**：`python -m backend.scripts.migrate_image_gen_quota_to_llm_quota`

## 4. 服务层设计

### 4.1 `LLMQuotaService` 公共接口

```python
class LLMQuotaService:
    def __init__(self, db: Session): ...

    # --- 用户侧（每次 LLM 调用前后调用） ---
    def check_and_reserve(
        self, user_id: str, category: str, planned_tokens: int = 0
    ) -> str:
        """调用前：校验 + 预占，返回 reservation_id（用于后续 record_usage/rollback）。

        - count 模式：daily_used +1、monthly_used +1
        - token 模式：token_used += planned_tokens（按模式周期可能预占到当期）
        - time 模式：仅校验 valid_from/valid_until，不递增任何计数器

        失败抛 QuotaExceeded → HTTP 429。
        """

    def record_usage(
        self,
        user_id: str,
        category: str,
        actual_tokens: int,
        reservation_id: str,
        model_used: Optional[str] = None,
    ) -> None:
        """调用后：写 llm_usage_log + 按模式校正扣减。

        - count 模式：daily/monthly_used 已在 check_and_reserve 时 +1；这里只写 log + 修正预留
        - token 模式：把 token_used -= planned_tokens，再 += actual_tokens 校正
        - time 模式：只写 log
        """

    def rollback(self, reservation_id: str) -> None:
        """调用失败/取消：按 reservation_id 回滚预占。

        - count 模式：daily/monthly_used -1
        - token 模式：token_used -= planned_tokens
        """

    # --- 用户查询 ---
    def get_user_quota(self, user_id: str) -> Optional[QuotaInfo]:
        """返回完整余额视图（含 daily_remaining/monthly_remaining/token_remaining/is_valid）"""

    # --- 管理员侧 ---
    def grant(self, *, user_id: str, quota_mode: str, ...) -> QuotaInfo:
        """创建/覆盖配额。校验模式字段合法性。"""

    def revoke(self, user_id: str) -> None:
        """删除配额行"""

    def reset_counters(self, user_id: str) -> None:
        """把 count 模式 daily/monthly_used 归零；token 模式 token_used 归零"""

    def list_users(self, skip=0, limit=50, search=None) -> List[QuotaInfo]:
        """分页 + 模糊搜索 user_id"""

    def count_users(self, search=None) -> int:
        """统计有配额的用户数"""
```

### 4.2 预占/回滚设计（关键）

**问题**：`check_and_reserve` 时只能预估 `planned_tokens`，但实际 token 在调用后才返回（`actual_tokens` 可能 ≠ `planned_tokens`）。

**方案**：
- `check_and_reserve` 返回 `reservation_id = str(uuid.uuid4())`
- 把 (user_id, reservation_id, planned_tokens) 存入内存 dict（service 实例生命周期内）或 Redis（多实例部署）
- `record_usage(user_id, category, actual_tokens, reservation_id=...)` 时按 reservation_id 找到 planned_tokens，按 `actual_tokens` 实际扣减
- `rollback(reservation_id)` 时按 reservation_id 释放预占

**v1 简化**：单实例部署 + 低并发场景下，预占用内存 dict 即可（与 `_test_lock` threading.Lock 类似思路）。后续多实例再迁 Redis。

### 4.3 计数流程（伪代码）

```python
# 在每个 LLM 调用点（如 chat 路由）：
async def chat(user_id, prompt):
    quota_svc = LLMQuotaService(db)
    res_id = quota_svc.check_and_reserve(
        user_id=user_id, category="text", planned_tokens=estimate(prompt)
    )
    try:
        result = await llm_gateway.generate(...)
        quota_svc.record_usage(
            user_id=user_id, category="text",
            actual_tokens=result.usage["total_tokens"],
            reservation_id=res_id, model_used=result.model,
        )
        return result
    except Exception:
        quota_svc.rollback(reservation_id=res_id)
        raise
```

### 4.4 错误处理

`QuotaExceeded` 异常细分（沿用现有）：
- `"no_quota"` — 用户无配额记录
- `"daily_limit_exceeded"` / `"monthly_limit_exceeded"` — count 模式超限
- `"token_limit_exceeded"` — token 模式超限
- `"validity_not_started"` / `"validity_expired"` — 有效期外

路由层把所有 `QuotaExceeded` 映射为 HTTP 429 + body `{"detail": "..."}`。

## 5. API 设计

### 5.1 管理员 API（`/api/admin/llm-quota`）

| Method | Path | 描述 |
|--------|------|------|
| GET | `/admin/llm-quota/users?search=&skip=&limit=` | 分页列出有配额用户 |
| GET | `/admin/llm-quota/users/{user_id}` | 单个用户配额详情（含使用历史汇总） |
| POST | `/admin/llm-quota/users/{user_id}/grant` | 创建/覆盖配额 |
| POST | `/admin/llm-quota/users/{user_id}/reset` | 计数器归零 |
| DELETE | `/admin/llm-quota/users/{user_id}` | 撤销配额 |
| GET | `/admin/llm-quota/stats` | 统计：今日 / 本月 / 总用量，按 category 分组 |

`grant` 请求体：
```json
{
  "quota_mode": "count" | "token" | "time",
  "daily_limit": 100,        // count 模式可选
  "monthly_limit": 3000,     // count 模式可选
  "token_limit": 100000,     // token 模式必填
  "token_period": "monthly",  // token 模式必填：daily/monthly/total
  "valid_from": "2026-01-01T00:00:00Z",  // 可选
  "valid_until": "2026-12-31T23:59:59Z",  // 可选
  "notes": "高级会员月度配额"
}
```

### 5.2 用户 API（`/api/quota`）

| Method | Path | 描述 |
|--------|------|------|
| GET | `/quota/me` | 当前用户配额余额（含 daily_remaining / monthly_remaining / token_remaining / valid_until） |

无 quota 记录时返回 HTTP 404（前端按"未配置"展示，不报错）。

## 6. 调用点接入

需要在以下位置接入 quota hook（每个位置先 `check_and_reserve`，调用后 `record_usage` 或失败 `rollback`）：

| 调用点 | category | planned_tokens 估算 | 备注 |
|--------|----------|---------------------|------|
| 图像生成 `routes/image_generation.py:chat` | `image` | `len(prompt) // 4` | 文本生成/编辑统一 |
| 图像生成 `routes/image_generation.py:generate` | `image` | `len(prompt) // 4` | 单图生成 |
| 图像生成 `routes/image_generation.py:polish-prompt` | `text` | `len(prompt) // 4` | prompt 润色是文本调用 |
| PRD Agent chat | `text` | `len(messages) * 100 // 4` | 估算 |
| ASR 服务 | `asr` | `duration_seconds * 10` | 估算每秒 10 token |
| OCR 服务 | `ocr` | `image_kb // 4` | 估算 |
| Embedding 服务 | `embedding` | `len(text) // 4` | 1 token ≈ 4 字符 |

实际 token 在调用后用 LLM 返回的 `usage.total_tokens` 覆盖估算值。

### 6.1 不在范围内

- Dify 工作流**内部**的 LLM 调用（Dify 自己计费）
- 项目内部工具型调用（非 LLM）：database-tool、http-client、k8s-tool 等
- OCR/ASR 的非 LLM 后备路径（如正则抽取）

## 7. 前端设计

**严格遵循《设计系统全量重构设计》（`2026-08-24-design-system-overhaul-design.md`）的视觉语言**：所有颜色 / 字体 / 间距 / 圆角 / 阴影 / 动效全部通过 token 引用或 Tailwind utility，**不写死 hex / px**；不绕过组件原语直接拼 HTML；图标走 lucide-react；背景在 admin 区域使用 `.bg-mesh.bg-mesh--subtle`。

### 7.1 第三个 tab「额度管理」布局

复用现有 LLMConfigsPage 的 tab 容器（沿用 `bg-canvas` + `bg-surface-1` tab 切换样式，新设计 token 接管）。

```tsx
// frontend/src/components/Admin/LLMQuotaManager.tsx
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Icon } from '@/components/ui/icon';  // lucide-react 分发器

export function LLMQuotaManager() {
  return (
    <div className="bg-canvas text-ink space-y-6">
      {/* 顶部统计卡：四宫格，每格用 Card 玻璃变体 */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard icon="zap" label="今日用量" value="1,234" unit="次" tone="accent" />
        <StatCard icon="calendar" label="本月用量" value="28,901" unit="次" tone="warm" />
        <StatCard icon="users" label="在线配额用户" value="12" tone="info" />
        <StatCard icon="shield" label="总用户" value="35" tone="muted" />
      </div>

      {/* 搜索 + 操作 */}
      <div className="flex gap-2">
        <Input placeholder="搜索 user_id..." className="flex-1" />
        <Button variant="primary" size="md">
          <Icon name="plus" className="h-4 w-4" />
          分配额度
        </Button>
      </div>

      {/* 用户列表：Card 包裹 + tabular 数字 + 模式 Badge */}
      <Card variant="bordered" padding="none">
        <table className="w-full">
          <thead className="bg-surface-2 text-ink-muted text-body-sm">
            <tr>
              <th className="px-4 py-3 text-left">user_id</th>
              <th className="px-4 py-3 text-left">模式</th>
              <th className="px-4 py-3 text-right">余额</th>
              <th className="px-4 py-3 text-left">有效期</th>
              <th className="px-4 py-3 text-right">操作</th>
            </tr>
          </thead>
          <tbody className="font-tabular">
            <tr className="border-t border-border hover:bg-surface-1">
              <td className="px-4 py-3 font-mono text-body-sm">admin</td>
              <td className="px-4 py-3"><Badge variant="soft" tone="info">按次</Badge></td>
              <td className="px-4 py-3 text-right">99 / 100 日</td>
              <td className="px-4 py-3 text-ink-muted">长期</td>
              <td className="px-4 py-3 text-right"><RowMenu /></td>
            </tr>
            {/* ... */}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
```

视觉要点：
- **数字统一加 `font-tabular`**：避免对齐跳动
- **模式徽章**：`<Badge variant="soft" tone="info|warning|success">` 三种语义色对应 count/token/time
- **行 hover**：`hover:bg-surface-1`（对比度保持 WCAG AA）
- **背景**：admin layout 已挂 `.bg-mesh.bg-mesh--subtle`，本组件无需重复

### 7.2 Grant 模态框（用 Modal 原语）

```tsx
// frontend/src/components/Admin/LLMQuota/GrantModal.tsx
import { Modal } from '@/components/ui/modal';
import { RadioGroup } from '@/components/ui/radio-group';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export function GrantModal({ open, onOpenChange, onSubmit }) {
  const [mode, setMode] = useState<'count' | 'token' | 'time'>('count');

  return (
    <Modal open={open} onOpenChange={onOpenChange} title="分配配额" size="md">
      <form onSubmit={onSubmit} className="space-y-6">
        {/* 模式选择：三个 radio，每个带说明 */}
        <RadioGroup value={mode} onValueChange={setMode}>
          <RadioGroup.Item value="count" label="按次数" description="日/月调用次数上限" />
          <RadioGroup.Item value="token" label="按 Token" description="总 token 配额" />
          <RadioGroup.Item value="time" label="按时间" description="仅设有效期" />
        </RadioGroup>

        {/* 模式字段（动态渲染） */}
        {mode === 'count' && (
          <div className="grid grid-cols-2 gap-4">
            <Field label="日调用上限" type="number" min={0} name="daily_limit" />
            <Field label="月调用上限" type="number" min={0} name="monthly_limit" />
          </div>
        )}
        {mode === 'token' && (
          <div className="grid grid-cols-2 gap-4">
            <Field label="Token 总数" type="number" min={1} name="token_limit" />
            <SelectField label="周期" name="token_period" options={[
              { value: 'daily', label: '每日' },
              { value: 'monthly', label: '每月' },
              { value: 'total', label: '一次性' },
            ]} />
          </div>
        )}
        {mode === 'time' && (
          <div className="grid grid-cols-2 gap-4">
            <Field label="生效时间" type="datetime-local" name="valid_from" />
            <Field label="失效时间" type="datetime-local" name="valid_until" />
          </div>
        )}

        {/* 高级选项：折叠 */}
        <details className="text-body-sm">
          <summary className="text-ink-muted cursor-pointer hover:text-ink">高级选项</summary>
          <div className="mt-4 space-y-4">
            {/* 公共 valid_from/valid_until/notes（time 模式已用上面，此处折叠其他模式） */}
          </div>
        </details>

        <div className="flex justify-end gap-2 pt-4 border-t border-border">
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button type="submit" variant="primary">保存</Button>
        </div>
      </form>
    </Modal>
  );
}
```

视觉要点：
- **入场动画**：Modal 原语自带 Framer Motion ease-stripe 240ms
- **校验错误**：`<Input error="..." />` 原语变体（红色 border + 错误提示）
- **Submit 按钮**：primary 渐变 + loading spinner

### 7.3 行操作菜单（用 Dropdown 原语）

```tsx
// frontend/src/components/Admin/LLMQuota/RowMenu.tsx
import { DropdownMenu } from '@/components/ui/dropdown-menu';
import { Icon } from '@/components/ui/icon';

export function RowMenu({ user, onAction }) {
  return (
    <DropdownMenu>
      <DropdownMenu.Trigger asChild>
        <Button variant="ghost" size="sm" aria-label="操作">
          <Icon name="more-horizontal" className="h-4 w-4" />
        </Button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Content align="end">
        <DropdownMenu.Item onSelect={() => onAction('detail')}>
          <Icon name="eye" className="h-4 w-4" />
          查看详情
        </DropdownMenu.Item>
        <DropdownMenu.Item onSelect={() => onAction('reset')}>
          <Icon name="refresh-cw" className="h-4 w-4" />
          重置计数器
        </DropdownMenu.Item>
        <DropdownMenu.Item onSelect={() => onAction('edit')}>
          <Icon name="edit" className="h-4 w-4" />
          编辑
        </DropdownMenu.Item>
        <DropdownMenu.Separator />
        <DropdownMenu.Item onSelect={() => onAction('revoke')} tone="danger">
          <Icon name="trash-2" className="h-4 w-4" />
          撤销配额
        </DropdownMenu.Item>
      </DropdownMenu.Content>
    </DropdownMenu>
  );
}
```

### 7.4 用户余额徽章（工具页顶部）

```tsx
// frontend/src/components/QuotaBadge.tsx
import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip';

interface QuotaInfo { /* ... */ }

export function QuotaBadge() {
  const [quota, setQuota] = useState<QuotaInfo | null>(null);

  useEffect(() => {
    const fetchQuota = () => fetchMyQuota().then(setQuota).catch(() => setQuota(null));
    fetchQuota();
    const id = setInterval(fetchQuota, 60_000);  // 60s 自动 refetch
    return () => clearInterval(id);
  }, []);

  if (!quota) return null;

  const text = quota.mode === 'count'
    ? `今日 ${quota.daily_remaining}/${quota.daily_limit} · 本月 ${quota.monthly_remaining}/${quota.monthly_limit}`
    : quota.mode === 'token'
    ? `本月 ${formatToken(quota.token_remaining)}/${formatToken(quota.token_limit)}`
    : `有效期至 ${formatDate(quota.valid_until)}`;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge variant="soft" tone="accent" className="font-tabular">
          <Icon name="coins" className="h-3 w-3 mr-1" />
          {text}
        </Badge>
      </TooltipTrigger>
      <TooltipContent>
        <p>点击查看详情</p>
      </TooltipContent>
    </Tooltip>
  );
}
```

使用：在各工具页顶部条（`<header className="bg-surface-1 ...">`）右侧紧贴操作按钮放置。

### 7.5 样式约束清单（与设计系统一致）

| 项 | 标准 | 反例（禁止） |
|---|---|---|
| 背景 | `bg-canvas` / `bg-surface-1/2/3` | `bg-slate-900` / `bg-gray-100` |
| 文字 | `text-ink` / `text-ink-muted` / `text-ink-faint` / `text-accent` / `text-accent-warm` | `text-white` / `text-gray-700` |
| 边框 | `border-border` / `border-border-strong` / `border-border-accent` | `border-slate-700` |
| 按钮 | `<Button variant="primary|secondary|ghost|outline|destructive">` | `<button className="bg-blue-600 ...">` |
| 卡片 | `<Card variant="default|bordered|elevated|glass">` | `<div className="bg-slate-800 rounded-lg">` |
| 模态框 | `<Modal>` (Radix Dialog) | 自定义遮罩 + 定位 div |
| 下拉菜单 | `<DropdownMenu>` (Radix) | 自定义 ul + 状态 |
| 标签页 | `<Tabs>` (Radix) | 现有 inline div（LLMConfigsPage 沿用旧实现，本期需同步升级到 Tabs 原语） |
| Badge | `<Badge variant="solid|soft|outline|dot" tone="...">` | `<span className="bg-cyan-600 ...">` |
| Input | `<Input>` / `<Input error>` / `<Input with-icon>` | `<input className="bg-slate-700 ...">` |
| 图标 | `<Icon name="...">`（lucide 优先，FA 兜底） | `<i className="fas fa-...">` |
| 数字对齐 | `font-tabular`（启用 tabular-nums） | 默认字距 |
| 暗/亮模式 | 全部颜色通过 token 引用，`data-theme` 自动适配 | 写死 hex / rgba |
| 焦点环 | `focus-visible:shadow-focus`（token） | 自定义 outline |
| 圆角 | `rounded-sm|md|lg|xl|2xl|pill`（token） | `rounded-md`（默认 6px，仍是 token 值，但确保不混用 `rounded-[7px]`） |
| 阴影 | `shadow-sm|md|lg|xl|glow|focus`（token） | `shadow-2xl`（默认） |

## 8. 测试策略

### 8.1 后端单元测试

- `test_llm_quota_service.py`：
  - `check_and_reserve` count 模式超限抛 `QuotaExceeded("daily_limit_exceeded")`
  - `check_and_reserve` token 模式超限抛 `QuotaExceeded("token_limit_exceeded")`
  - `check_and_reserve` time 模式过期抛 `QuotaExceeded("validity_expired")`
  - `record_usage` token 模式扣减正确
  - 跨日/跨月自动重置
  - `grant` 模式字段校验（count 无 limit 报错 / token 无 limit 报错 / time 无有效期报错）
  - `rollback` 释放预占

### 8.2 后端集成测试

- `test_admin_llm_quota_api.py`：
  - grant → list → reset → revoke 全流程
  - 非管理员调用返回 403

### 8.3 迁移测试

- `test_migrate_image_gen_quota.py`：
  - 在测试库中创建 image_gen_quota 含 N 条数据 → 跑迁移 → 校验 llm_user_quota 内容一致
  - 幂等：跑两次结果不变

### 8.4 前端组件测试（vitest + RTL）

- `<LLMQuotaManager>` 默认渲染列表
- Grant 模态框：选择 count/token/time 显示对应字段
- 提交校验：count 模式留空报错
- `<QuotaBadge>` 三种模式正确显示

## 9. 部署与回滚

### 9.1 上线步骤

1. **后端**部署新代码（兼容旧 image_gen_quota 调用，旧路由仍工作但走 service 适配层）
2. **执行迁移脚本**（幂等，可重复）
3. **验证**：新表数据 = 旧表数据
4. **后端**部署"切换到新表"版本（这一步路由 / service 全部切到 llm_user_quota）
5. **前端**部署新 tab
6. **观察 1 周**无异常
7. **人工 DROP TABLE image_gen_quota**

### 9.2 回滚

- 第 6 步前任何阶段：后端代码回滚 → 服务用旧 image_gen_quota（仍存在）
- 迁移脚本不删旧表，回滚安全

## 10. 全局约束

- **服务语言**：所有对话和注释使用中文
- **最小变更**：只修改必要的代码，不改动已正常的业务逻辑
- **日志**：quota 关键路径必须包含日志（grant / revoke / reset / 超限事件）
- **时区**：DB 存 UTC，比较时统一去 tzinfo
- **并发**：使用 PostgreSQL `SELECT FOR UPDATE` 行锁（与现有 `image_gen_quota_service` 一致）
- **保留审计**：所有 grant / revoke / reset 操作记录到 `notes` 字段（"granted_by=admin at 2026-08-24"）
- **热重载**：通过 `dev-services.py` 重启；不直接用 uvicorn / npm run dev

## 11. 与《设计系统全量重构》的协调

本 spec 的前端实现必须**严格遵循** `2026-08-24-design-system-overhaul-design.md` 的视觉语言与组件原语，**禁止**重复发明或绕过。

### 11.1 实施时机

| 设计系统 Phase | 状态 | LLM 配额可否开始实施？ |
|---|---|---|
| Phase 1：Token + 基建 | ✅ 已落地（commit `7c945de` / `d1a4831` / `f006143`） | 后端可立即开始；前端等 Phase 2 |
| Phase 2：组件原语（Button/Card/Modal/Tabs/Badge...） | 🔜 计划中 | **前端必须等待 Phase 2 完成后开始** |
| Phase 3：Admin + 工具页 | 🔜 计划中 | 与本 spec 的 `§2.3 文件结构`重叠，需合并/协调 |
| Phase 4：主题整合 | 🔜 计划中 | 与本 spec 的 `§7.4 QuotaBadge` 集成主题切换器有关 |

**建议执行顺序**：
1. **立即**：后端实施（§3-6，零前端依赖），独立可测
2. **等 Phase 2 完成**：前端开始 `LLMQuotaManager` / `GrantModal` / `QuotaBadge` 组件实现，全部用新原语
3. **Phase 3 阶段**：把 `<LLMQuotaManager>` 作为 Admin 页面"第三梯队"组件接入；同时把 `<QuotaBadge>` 推广到所有 LLM 工具页（ImageGen、ASR、OCR、Embedding）

### 11.2 不允许出现的样式 / 类名（与设计系统冲突）

| 类别 | 禁止用法 | 替代（token / 原语） |
|---|---|---|
| 颜色 | `bg-slate-*` / `bg-gray-*` / `text-white` / `text-slate-*` / `bg-cyan-600` / `bg-blue-600` | `bg-canvas` / `bg-surface-1/2/3` / `text-ink` / `text-ink-muted` / `text-accent` |
| 颜色（语义） | `bg-red-500` / `text-yellow-600` / `bg-green-400` | `bg-danger` / `text-warning` / `bg-success` |
| 边框 | `border-slate-*` / `border-gray-*` | `border-border` / `border-border-strong` / `border-border-accent` |
| 圆角 | `rounded-[7px]` / 自定义 px 值 | `rounded-md` / `rounded-lg` 等 token 类 |
| 阴影 | `shadow-2xl`（默认） / 自定义 box-shadow | `shadow-md` / `shadow-lg` / `shadow-glow` |
| 组件 | 自定义 `<button className="bg-... px-... py-...">` | `<Button variant="...">` 原语 |
| 模态框 | 自定义遮罩 + 定位 | `<Modal>` (Radix Dialog) |
| 下拉菜单 | 自定义 `<ul>` + 状态管理 | `<DropdownMenu>` (Radix) |
| 标签页 | 现有 inline `<button>` + state 切换（LLMConfigsPage 当前模式） | `<Tabs>` (Radix Tabs) — LLMConfigsPage 升级时一并使用 |
| 表格 | 原生 `<table>` 无样式 | `<Card variant="bordered">` 包裹 + `font-tabular` |
| 图标 | `<i className="fas fa-...">` | `<Icon name="...">` (lucide) |
| 字体 | 自定义 font-family | `font-sans` (Geist + HarmonyOS Sans SC 自动) |
| 数字 | 默认对齐 | `font-tabular` class |

### 11.3 必须遵守的视觉规则

- **背景**：admin layout 已挂 `.bg-mesh.bg-mesh--subtle`，LLM 配额组件不重复挂背景层
- **暗 / 亮双模式**：所有颜色通过 token 引用，**不写死 hex / rgba**，自动跟随 `data-theme` 切换
- **焦点环**：交互元素用 `focus-visible:shadow-focus`（来自 token），不用自定义 outline
- **入场动画**：弹窗 / 抽屉走 Modal/Dropdown 原语自带的 Framer Motion ease-stripe 240ms
- **WCAG AA 对比度**：所有文本与背景组合的对比度由 token 保证；不为单个组件再调整
- **数字显示**：所有数字（余额、限制、统计）必须加 `font-tabular` 启用 tabular-nums

### 11.4 与 Phase 3 的合并点

`design-system-overhaul` Phase 3 提到"Admin 后台页面切换无样式异常"作为验收标准。本 spec 实施时：
- **不重复做 admin layout 整体重构**——只新增第三个 tab 和对应的组件
- **若 Phase 3 还没动 AdminLayout**：使用现有 `AdminLayout.tsx` 结构，外层样式不动
- **若 Phase 3 已升级 AdminLayout**：直接用新原语（Tabs / Button / Card 等已就绪）
- **冲突优先级**：以设计系统为准——若本 spec 与设计系统冲突，遵循设计系统规范，本 spec 服从

### 11.5 实施后回归验证

完成本 spec 后必须验证：
- [ ] `/admin/llm-configs` 三个 tab 视觉一致（使用同一 Tab 原语）
- [ ] 切换暗 / 亮模式，所有 quota 相关组件颜色 / 对比度正确
- [ ] LCP 不退化（QuotaBadge 自动 refetch 不阻塞渲染）
- [ ] 数字列对齐整齐（font-tabular 生效）
- [ ] 模态框入场动画与设计系统一致（240ms ease-stripe）
- [ ] 不存在 `bg-slate-*` / `text-white` / `fas fa-*` 等遗留用法（grep 校验）

## 12. 风险与权衡

| 风险 | 影响 | 缓解 |
|------|------|------|
| 接入 LLM 调用点遗漏 | 某些接口不消耗配额 | 启动时打 log 列出所有 LLM 调用点 + 接入 checklist |
| `planned_tokens` 估算不准 | 预占过多/过少 | 用实际 token 在 `record_usage` 时校正；超限延迟到 `record_usage` 才报 |
| 旧 image_gen_quota→新表迁移丢数据 | 用户额度丢失 | 迁移前备份 DB；迁移脚本幂等 + 打印统计 |
| 第三个 tab 与设计系统 Phase 3 的 AdminLayout 重构冲突 | 视觉不一致或重复施工 | §11.4 明确先后顺序 + 优先级；后做 LLM quota 时沿用已就绪的原语 |
| 通用 quota 拖慢 LLM 调用 | 用户感知延迟 | service 调用 < 5ms（FOR UPDATE 锁行 + 单条 UPDATE）；监控 p99 |
| 前端在设计系统 Phase 2 原语未就绪前实施 | 不得不写自定义组件，后期需重写 | §11.1 明确"等 Phase 2 完成"；后端先行不阻塞 |

---

> 下一步：用户审核本 spec → 调用 writing-plans skill 创建实施计划。
