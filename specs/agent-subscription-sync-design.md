# 设计：本机 Agent 订阅信息同步到远程数据库（agent-subscription-sync）

> 2026-11-20 | 状态：已审查通过（spec-review-loop 4 轮，台账见 docs/reviews/2026-11-20-agent-subscription-sync-review.md）

## 1. 需求

把所有 AI 编程 Agent 的订阅信息保存到**远程数据库**（应用主库 PostgreSQL）。每次从本机同步 Agent 的订阅服务商信息时按以下规则去重：

1. 同一供应商 + 同一 API Key → 不覆盖不更新，保留原配置（幂等跳过）
2. 同一供应商 + 同一渠道商 + 不同 API Key → 新增一条供应商渠道，**渠道命名必须不同**以区分

## 2. 现状与差距

| 已有 | 差距 |
|---|---|
| `subscription_quota_accounts` 表（含 api_key_enc 加密列、label、category、extra_json） | 无 `api_key_hash` 列，去重靠全量解密明文比对 |
| `QUOTA_STORAGE` 本机/远程双层存储 | 默认 local，导入数据不进远程库 |
| `/import/cc-switch`（规则 1 语义已实现：同 (provider,key) 跳过） | 只覆盖 cc-switch 一个来源；写入位置随 QUOTA_STORAGE（默认本机）；同 provider 不同 Key 的 label 固定为 `{source_name}（cc-switch 导入）`，**重名无区分**（规则 2 缺失） |
| `local_credentials.py` 本机发现（kimi/zcode） | 虚拟账号不落库 |
| 加密体系：本机 `LocalEncryption` / 远程 `app.core.security.encrypt_api_key` | — |

## 3. 方案总览

```
[扫描器] 本机各 Agent 配置（REAL_HOME 展开）
   ├── cc-switch 数据库（复用 scripts.import_ccswitch_providers.load_candidates）
   ├── claude: ~/.claude/settings.json env.{ANTHROPIC_AUTH_TOKEN|ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL}
   ├── codex: ~/.codex/config.toml [model_providers.*] + auth.json OPENAI_API_KEY
   ├── opencode: ~/.local/share/opencode/auth.json + ~/.config/opencode/opencode.json providers
   ├── zcode: 复用 read_provider_keys()（provider_config.json）
   └── kimi/minimax/gemini/pi/copilot: OAuth/无 Key → 报告型（found_login_no_apikey / not_configured）
        ↓ 产出 [{provider_id, provider_name, channel(渠道商), base_url, api_key, source_agent}]
[同步服务] subscription_sync.py
   ├── 目标恒为远程主库 engine（app.models.base.engine），加密用服务器主密钥
   ├── 规则 1：(provider_id, sha256(key)) 已存在 → skip，任何字段不动
   ├── 规则 2：新增行时 label 冲突 → f"{基础名}·{key后4位}"，仍冲突 → "-2"/"-3" 递增
   └── extra 不写 api_key 明文（不复刻 cc-switch 导入的 extra.api_key 旧模式）
[API] POST /subscription-quota/subscriptions/sync   （dry_run 支持）
      GET  /subscription-quota/subscriptions/cloud  （远程库渠道列表，掩码展示）
[前端] SubscriptionQuota 页新增「同步本机订阅到云端」按钮 + 结果反馈 + 云端渠道列表
```

## 4. 数据模型变更（幂等）

`subscription_quota_accounts` 追加列（加入 accounts.py `_EXTRA_COLUMNS`，SQLite 先查列再补 / PG `ADD COLUMN IF NOT EXISTS`，两侧自动生效）：

```sql
api_key_hash VARCHAR(64) NOT NULL DEFAULT ''   -- sha256 hex，同步去重索引键
```

- **DDL 复用方式（防漂移）**：`subscription_sync.py` 不另写 DDL，直接 `from app.services.subscription_quota.accounts import _CREATE_SQL, _EXTRA_COLUMNS, _sqlite_columns`，对 `app.models.base.engine` 执行同一套幂等建表/补列（PG 分支走 `ADD COLUMN IF NOT EXISTS`，SQLite 分支先查列）；模块级 `_schema_ready` 标记只对 base engine 生效一次，不与 `QUOTA_STORAGE` 的位置缓存混用
- 不新建表：同步渠道与手工账号同表同语义（label=渠道名），前端额度查询/管理直接可用
- 存量行 hash 为 ''：去重时对该用户该 provider 的行回退「解密明文比对」（与 cc-switch 导入现状一致）
- 旧数据零影响；不回填（首次同步遇相同 Key 会命中回退比对 → skip，并顺手把 hash 补写进该存量行（仅补 hash，不动其他字段，幂等；dry_run 时不回填）
- **回滚/降级说明**：该列带默认值、纯新增、无读取方依赖（仅同步去重使用）；回滚 = `ALTER TABLE subscription_quota_accounts DROP COLUMN api_key_hash`（PG ≥14 / SQLite ≥3.35 支持），丢掉的只是可由下次同步重建的 hash 缓存，业务无损


## 5. 去重算法（最终语义）

### 5.1 扫描条目归一化（进入去重前）

1. **空 Key 剔除**：`api_key` 为空/解析失败的条目不参与入库，计入该 agent 的 `reportOnly`（原因 `no_api_key`）
2. **provider_id 归一化**：优先映射到 registry `PROVIDER_SPECS` 的 id；映射规则：
   - claude settings（ANTHROPIC_*）→ `anthropic`；codex auth.json（OPENAI_API_KEY）→ `openai`；opencode/zcode 已有 provider 名直接用
   - 无法识别的自定义 provider：`base_url` host 命中已知官方域名（见 5.2）→ 对应 registry id；否则 provider_id 取 `custom`、`provider_name` 取 host，仍可入库（供应商维度用 host 展示）
3. **批内预去重（F01）**：同一轮扫描产出先按 `(provider_id, sha256(api_key))` 去重——多源重叠（如 cc-switch 与 claude settings 同一把 Anthropic Key）只保留一条，来源 agent 记为多来源列表 `source_agents`；保留优先级：cc-switch > zcode > opencode > codex > claude（cc-switch 记录的 source_name/channel 元数据最完整）

### 5.2 官方域名映射（F03，初始清单，代码中一处定义）

| provider_id | 官方域名 |
|---|---|
| anthropic | api.anthropic.com、api.claude.ai |
| openai | api.openai.com |
| zhipu | open.bigmodel.cn |
| deepseek | api.deepseek.com |
| kimi / moonshot | api.moonshot.cn、api.moonshot.ai |
| minimax | api.minimax.chat、api.minimaxi.com |
| gemini | generativelanguage.googleapis.com |
| qwen | dashscope.aliyuncs.com |
| opendesign | amr-api.open-design.ai |

### 5.3 逐条裁决

```
existing = 远程库中该 user 的全部行
key_index:  provider_id -> {hash}（hash 为空的存量行 → 解密明文后补算入索引）
label_index: (provider_id, label) -> key_hash   # 查询与更新共用同一份

for item in 归一化后的扫描条目:          # 已批内去重
    h = sha256(item.api_key)
    if h in key_index[item.provider_id]:
        action = skip                                  # 规则 1：任何字段不动
        （若命中的存量行 hash 为空且非 dry_run → UPDATE 仅补 api_key_hash）
    else:
        label = item.基础渠道名    # f"{provider显示名}-{渠道名}"；官方直连时渠道名="官方"
        if label_index[(provider, label)] 存在且其 key_hash != h:
            label = f"{label}·{item.api_key[-4:]}"     # 规则 2 一次消歧
            若仍冲突（同尾4位不同key，极小概率）→ label 后缀 -2/-3 递增直到唯一
        INSERT（api_key_enc=服务器主密钥加密, api_key_hash=h, label, category,
               extra={base_url, region, source_agents, channel}, app=首个来源agent）
        # 批内即时更新两个索引（F02）：key_index[provider].add(h)；
        # label_index[(provider, label)] = h —— 同批后续条目立刻可见
```

- 基础渠道名：base_url host（如 `api.gptsapi.net`）；无 base_url 或 host 命中 5.2 清单 → 「官方」
- category：官方/无 base_url → `official`；其余 → `third_party`
- **并发兜底（F08）**：不加 (user, provider, hash) 唯一约束（存量数据无法满足）；并发双同步的最坏结果是同 Key 双行，由**下一次同步不再新增**自然封顶 + 人工可删，接受该弱一致并在此明示
- **失败隔离**：单个扫描源异常（文件损坏/权限）只跳过该源并计入 `agents[].error`，不影响其余源与已扫条目的入库（沿用 local_credentials 既有模式）
- API 响应仅含：providerId/providerName/channel/最终 label/maskedKey/action/sourceAgents，**绝无明文 Key**


## 6. 安全设计（密钥暴露面规则对齐）

1. 扫描 → 加密 → 入库全程服务端内存；**不写日志**（日志只记 provider/agent/数量/行 id）
2. 响应只出掩码；掩码格式与 `QuotaAccount.masked_key()` 一致（前 4 + `*` + 后 4，长度 ≤8 全掩码）；`to_public_dict` 沿用既有脱敏
3. extra **不含** api_key 明文（与旧导入行为不同，新代码不复制旧缺陷）
4. 提交前对 diff 做 `sk-|LTAI|*_SECRET=` 等特征 grep（提交门禁）
5. 本机路径全部经 `expand_user_path`/REAL_HOME 展开（遵守真实家目录规则）

## 7. API 设计

```
POST /api/subscription-quota/subscriptions/sync     Header: Authorization
  body: { "dryRun": false }
  resp: { agents: [{agent, discovered, reportOnly, error?}],
          items: [{providerId, providerName, channel, label, maskedKey, action, sourceAgents}],
          created, skipped, backfilled, dryRun }
GET  /api/subscription-quota/subscriptions/cloud
  resp: { accounts: [public dict（掩码）], total }
```

- 鉴权：`_require_user(authorization)` 同模块既有模式
- 路由文件不加业务逻辑：路由薄封装，逻辑在 `services/subscription_quota/subscription_sync.py`

## 8. 前端

- `SubscriptionQuota/index.tsx` 操作区（cc-switch 导入按钮旁）新增「同步本机订阅到云端」按钮：调用 sync → 展示 created/skipped/明细（含渠道命名）
- 新增「云端渠道」小节：拉取 `/subscriptions/cloud` 展示远程库渠道列表（label/供应商/渠道商/掩码 Key/来源 Agent）
- service 层走既有 subscription API helper（客户端路径 DRY：新路径常量加到同一处定义）

## 9. 测试（隔离三要素 + ZZTEST）

- 单测（新 `test_subscription_sync.py`）：
  - 去重：规则 1（同 provider+key 跳过 + 存量空 hash 回填）、规则 2（同 provider 同渠道不同 key → 两行、命名 `·尾4位` 消歧、`-2` 兜底）
  - **批内**：同 key 多来源只插一行（source_agents 合并）；同批同渠道两条不同 key 的 label 消歧互不重名
  - 归一化：空 api_key 剔除入 reportOnly；自定义 provider 落 `custom`+host；官方域名清单命中 → 渠道名「官方」+category=official
  - 扫描器：tmp_path 伪造 claude settings.json / codex config.toml+auth.json / opencode auth.json，断言解析结果（期望值手工可核算）
  - 安全：sync 响应与 public dict 序列化后不含任何明文 Key
  - dry_run：不 INSERT、不回填 hash
- 集成：patch sync 模块 engine → 临时 SQLite；`dryRun` 不落库
- 运行范围：仅新增测试文件 + `test_subscription_quota_api.py`（同路由文件回归）

## 10. 验收计划

1. 单测/集成测试通过（最小化范围）
2. 本地浏览器验收（dev-services.py，5178/19092）：同步按钮 → 真实扫描本机 → 查远程库行（掩码）→ **二次同步全 skip（规则 1 实证）** → 渠道命名检查（规则 2，若本机存在同渠道多 Key 真实样本则实证，否则以测试为准）→ Console/Network 无错
3. 部署服务器（deploy.py）→ 服务器验收：接口可达、鉴权有效、无本机配置时优雅返回空扫描
4. 提交推送：fetch + pull --rebase --autostash → 显式 add 本任务文件 → push origin master（用户已明确要求上传）

## 11. 边界与不做

- 不改 `QUOTA_STORAGE` 默认值（本机/远程双层现状保留，同步是显式的「写远程」动作）
- 不迁移本机 SQLite 存量账号
- OAuth 型凭据（kimi/zcode 登录 token、copilot/gemini 登录态）不入库（无 API Key 无从按规则去重，token 自动轮换存了即过期），扫描结果中以 reportOnly 呈现
- 不修复旧导入的 extra.api_key 明文存量（记录为审查发现，另行决策）
