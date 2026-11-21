# 设计：订阅中心 ↔ 本机 CC Switch / Magpie 双向同步（agent-subscription-bridge）

> 2026-11-21 | 状态：已审查通过（spec-review-loop 8 轮 + 实施期 4 项回写，台账见 docs/reviews/2026-11-21-agent-subscription-bridge-review.md）> 
> 实施进度：T1–T7 已完成（后端模型/去重/深链/导出接口/本地桥/前端面板/浏览器验收 + 生产部署）
> 关联：`specs/agent-subscription-sync-design.md`（本机 → 云端单向）、`docs/design/agent-subscription-merge.md`（订阅中心合并）
> 源码依据：`D:\GitHubProjects\cc-switch` @ 902a02da（v4.0.36）、`D:\GitHubProjects\magpie` @ 4716a77ff

## 1. 目标

| 编号 | 目标 |
|---|---|
| G1 | **云端 → 本机**：在网页点按钮，把订阅中心的订阅推送到本机 CC Switch 与 Magpie |
| G2 | **本机 → 云端**：把本机 CC Switch / Magpie 里新增的订阅同步回订阅中心 |
| G3 | **去重**：以「订阅调用的 base_url + API Key」判定同一条；两者都相同即同一条，**完全跳过不处理**；URL 相同但 Key 不同视为不同订阅，正常保存 |
| G4 | **交互**：所有渠道、所有操作都支持**单条**操作，也支持**全选 / 多选批量**操作 |
| G5 | **静默优先**：能静默就静默（Magpie 可完全静默）；CC Switch 官方只支持确认框，接受一次确认 |

## 2. 架构约束（决定方案的根本事实）

工具部署在服务器，**服务器读不到用户机器的 `~/.cc-switch`、`~/.config/magpie`**。因此「任何设备打开网页即可同步」只有两条执行路径：

```
                 ┌──────────────── 云端（本工具服务器） ────────────────┐
                 │  订阅中心 PostgreSQL（唯一真相源）                    │
                 │  subscription_quota_accounts                          │
                 └───────────┬──────────────────────────┬──────────────┘
                             │ HTTPS(JWT/设备Token)      │ HTTPS(设备Token)
              ┌──────────────▼───────────┐   ┌──────────▼─────────────────┐
              │  A. 浏览器（本机）         │   │  B. 本地桥脚本（本机）       │
              │  系统协议深链              │   │  python subscription_bridge │
              │  ccswitch://  magpie://   │   │  读/写 本机 app，做真去重     │
              └──────────────┬───────────┘   └──────────┬─────────────────┘
                             │                          │
                    ┌────────▼──────────┐      ┌────────▼─────────────┐
                    │ CC Switch / Magpie │      │ ~/.cc-switch/*.db    │
                    │ （用户点确认）      │      │ ~/.config/magpie/*   │
                    └───────────────────┘      └──────────────────────┘
```

| 能力 | A 纯网页深链 | B 本地桥 |
|---|---|---|
| 云端 → 本机 | ✅（每条一次确认） | ✅（Magpie 静默 / CC Switch 确认） |
| 本机 → 云端 | ❌ 无法读本机 | ✅ |
| 按 (URL, Key) 去重 | ❌ 看不到本机现状 | ✅ |
| 批量 | ⚠️ 受浏览器「一次手势一个协议」限制 | ✅ |

**结论**：G1+G3+G4 完整满足需要 A+B 并存；A 作为零安装兜底，B 作为推荐路径。

## 3. 目标应用源码事实（只列约束性结论）

### 3.1 CC Switch（`ccswitch://`）

- 链接：`ccswitch://v1/import?resource=provider&app=<app>&name=&endpoint=&apiKey=&model=&homepage=&notes=&icon=&configFormat=&config=`
  - 解析：`src-tauri/src/deeplink/parser.rs`；写入：`src-tauri/src/deeplink/provider.rs`
- 合法 `app`：`agy|copilot|claude|claude-desktop|codex|gemini|grokbuild|opencode|openclaw|hermes|pi|mcode|kimi|dsh|omp`
  - `pi|mcode|kimi|dsh|omp` **必须带 model**，否则解析期报错
- **ID 生成 `{slug}-{时间戳}` / `{slug}-{uuid}` → 同一链接重复导入必然产生重复记录**（本工具必须自己去重）
- 导入必须先经前端**确认框**（`commands/deeplink.rs` → pending → 用户确认）
- **无 CLI**；`export/import` 是整库 SQL 备份（`commands/import_export.rs`），不能增量合并
- 读取本机现状：`~/.cc-switch/cc-switch.db` → `providers(id, app_type, name, settings_config, website_url, category, notes, icon, meta, is_current, …)`

### 3.2 Magpie（`magpie://` 与 CLI / 本地 API）

- 链接：`magpie://import?preset=<id>&key=…&region=…` 或 `magpie://import?name=…&id=…&chat=|responses=|anthropic=|gemini=<base_url>&key=…&models=&catalog=&website=&icon=&balance=`
  - 解析：`internal/provider/importurl.go`
- 深链**必须用户确认**（`internal/gui/importlink.go`，「A link never saves anything by itself」）
- **CLI 可静默**：`magpie import -y <link>`（`internal/cli/providers_cli.go:1819`；非终端必须 `-y`）
  - **同 id 会覆盖既有供应商**（源码提示 "replaces your …"）→ id 必须稳定且先查重
- **本地管理 API**：`/v1/magpie/admin/` → `GET /providers`、`POST /provider/{save|delete|on|off|…}`（`internal/gui/admin.go`）
  - 必须带 **admin 权限的 gateway key**（`magpie gateway-key admin <id> local`）
  - **拒绝带 `Origin` / `Sec-Fetch-*` 的请求**（只允许脚本，不允许网页）
  - → 桥脚本走 HTTP body 传 Key，比命令行参数更安全
- 读取：`~/.config/magpie/providers.json`（`providers[]`: id/name/preset/key/chat/anthropic/gemini/catalog/models/website/keysUrl/icon）、`magpie accounts --json`、`magpie quota --json`

### 3.3 本工具现状

- 表 `subscription_quota_accounts`：`provider_id / label / api_key_enc(AES) / api_key_hash(sha256) / extra_json{base_url,region,channel,source_agents} / app / category / is_channel / enabled / sort_order`
- 去重（`subscription_sync.py`）：① 同 `(provider_id, sha256(key))` → 跳过；② 同 `(provider_id, 渠道)` 不同 Key → 新增行；③ 同 Key 全局唯一
- 已有「从 cc-switch / magpie 同步」「同步本机订阅到云端」= 读**后端所在机器**（本机可用；云端为空）
- 实测 23 行存在：8 行 base_url 为空、同 Key 的 kimi 两条（一条停用）、`zhipu` 与 `zhipu_team` 同 base_url → **provider_id 漂移，必须在同步前归一**

## 4. 数据模型变更

### 4.1 新增列（双栈幂等 DDL）

| 列 | 类型 | 说明 |
|---|---|---|
| `base_url` | TEXT NOT NULL DEFAULT '' | 订阅调用地址（原始值，展示用） |
| `base_url_norm` | TEXT NOT NULL DEFAULT '' | 归一化地址（去重键用） |

`api_key_hash` 已存在（VARCHAR(64)）。

幂等写法（沿用 `accounts.py::_ensure_schema` 的分方言处理，两库都必须可重复执行）：

- PostgreSQL：`ALTER TABLE subscription_quota_accounts ADD COLUMN IF NOT EXISTS base_url TEXT NOT NULL DEFAULT ''`（两列各一条）
- SQLite：先 `PRAGMA table_info(subscription_quota_accounts)` 判列，缺列才 `ALTER TABLE ... ADD COLUMN ...`（SQLite 不支持 `ADD COLUMN IF NOT EXISTS`）
- 两列均带 `DEFAULT ''`，历史行无需回填也不会违反 NOT NULL

### 4.2 唯一索引（去重键落地）

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_sq_accounts_url_key
  ON subscription_quota_accounts (user_id, base_url_norm, api_key_hash)
  WHERE api_key_hash <> '';
```

- 部分索引：历史行 `api_key_hash` 为空时不参与唯一性（避免迁移期冲突）；PostgreSQL 与 SQLite 均支持
- **provider_id 不进入唯一键**：`kimi` / `kimi-coding` / `zhipu` / `zhipu_team` 这类漂移不应产生重复记录；供应商只作为展示与目标映射

**建索引前置校验（必须，否则可能阻塞启动）**

存量数据已观察到同 URL 重复行；若存在 `(user_id, base_url_norm, api_key_hash)` 完全相同的两行，`CREATE UNIQUE INDEX` 会直接失败。因此：

1. 建索引前先跑冲突检测（同一去重键出现 ≥2 行的分组）：

```sql
SELECT user_id, base_url_norm, api_key_hash, count(*) AS n, array_agg(id) AS ids
FROM subscription_quota_accounts
WHERE api_key_hash <> ''
GROUP BY user_id, base_url_norm, api_key_hash
HAVING count(*) > 1;
```

2. 有冲突 → **跳过建索引**，冲突组写入「重复项报告」并记 WARN 日志，服务照常启动（去重仍由应用层 `dedupe_key()` 保证）
3. 无冲突 → 建索引；建索引包在 `try/except` 中，失败同样降级为「无索引 + 报告」，**绝不因索引问题阻断服务启动**

**回滚（每条可单独执行、可重复执行）**

```sql
DROP INDEX IF EXISTS uq_sq_accounts_url_key;
-- 列回滚（确认无代码引用后执行；PG 支持 IF EXISTS，SQLite 需先 PRAGMA 判列）
ALTER TABLE subscription_quota_accounts DROP COLUMN IF EXISTS base_url_norm;
ALTER TABLE subscription_quota_accounts DROP COLUMN IF EXISTS base_url;
```

回滚运行时行为：去重逻辑由开关 `QUOTA_DEDUPE_MODE=url_key|legacy` 控制（默认 `url_key`），异常时可切回 `legacy` 走旧规则，无需改代码与重启数据库。

### 4.3 归一化函数 `normalize_base_url(url)`

1. 去首尾空白；空值 → `official`
2. 解析失败（非 URL）→ 小写原文
3. scheme/host 小写；去默认端口（:80/:443）
4. 去 query、fragment
5. 路径去末尾 `/`
6. 去末尾单个版本段：`/v1`、`/v1beta`、`/v1alpha`、`/v2` —— **只去最后一段且必须匹配 `^v\d+(beta|alpha)?$`**，不做更激进的合并
7. 重新拼回 `scheme://host[:port]/path`

> 不做「跨路径合并」：`/anthropic` 与 `/v1` 是不同端点，视为不同订阅（宁可不合并，不可错合并）。

### 4.4 回填（幂等，默认 dry-run）

回填由 **Python 逐行**处理，不在 SQL 里做 JSON 抽取与归一化——原因：PG `extra_json::jsonb` 遇到任何脏数据会让整条 `UPDATE` 失败，且两库正则/JSON 路径语法不同。

1. 取待补行：`SELECT id, base_url, extra_json FROM subscription_quota_accounts WHERE user_id = :uid AND (base_url = '' OR base_url_norm = '')`
2. 逐行 `json.loads(extra_json)`：解析失败 → `skipped += 1` 并继续（不中断整体回填）
3. `base_url = base_url or extra.get('base_url', '')`；`base_url_norm = normalize_base_url(base_url)`
4. 逐行写回（行级 WHERE 保证幂等与并发安全）：

```sql
UPDATE subscription_quota_accounts
   SET base_url = :url, base_url_norm = :norm, updated_at = :now
 WHERE id = :id
   AND user_id = :uid
   AND (base_url = '' OR base_url_norm = '');
```

5. 默认 `--dry-run` 只输出「将更新 N 行 / 跳过 M 行 / 明细 20 条」，`--apply` 才写库

- 执行顺序：**先回填（T1）→ 再跑冲突检测 → 最后建索引**（§4.2），否则新列全为空时索引无意义
- 重复执行安全：命中 `WHERE` 的行才更新；已补过的行不再命中
- 归一化只在 Python 侧实现一处（`normalize_base_url`），SQL 不重复实现

### 4.5 provider 别名表（仅展示与映射，不参与唯一性）

```
kimi/kimi-for-coding/kimi-coding/kimi-code → kimi
zhipu/zhipu_team/zhipuai-coding-plan → zhipu
opencode-go/opencode_go → opencode_go
alibaba/alibaba-cn/qwen/qwen-cn → qwen | alibaba（按 region）
```

### 4.6 provider → 默认 endpoint（base_url 为空时补全）

实测有 8 行 `base_url` 为空（opencode 官方直连）。CC Switch 深链的 `endpoint` 是**必填**，因此必须有一张默认地址表（来源：`registry.py` 中的官方地址 + magpie preset 定义）：

| provider | 默认 endpoint | 备注 |
|---|---|---|
| `anthropic` / `claude` | `https://api.anthropic.com` | |
| `openai` / `codex` | `https://api.openai.com/v1` | |
| `gemini` | `https://generativelanguage.googleapis.com` | |
| `deepseek` | `https://api.deepseek.com/v1` | |
| `zhipu` | `https://open.bigmodel.cn/api/anthropic`（region=intl 时 `https://api.z.ai/api/anthropic`） | |
| `kimi` | `https://api.kimi.com/coding/v1` | |
| `minimax` | `https://api.minimaxi.com/anthropic` | region 只影响 Magpie preset（`minimax` / `minimax-cn`），不改 endpoint |
| `qwen` / `alibaba` | `https://coding.dashscope.aliyuncs.com/v1` | |
| `opencode_go` | `https://opencode.ai/zen/go` | |
| `opendesign` | `https://amr-api.open-design.ai` | 需控制面 Key |
| 未收录 | 无默认值 | 返回 `warnings: ["缺少 endpoint，请先编辑该账号填写 base_url"]`，不生成 CC Switch 链接（Magpie 仍可用 preset 或跳过） |

- 该表只用于**生成链接**，不写库、不参与去重
- 每行生成链接时 `endpoint = base_url or 默认 endpoint`；两者都没有 → 不生成并给 warning

### 4.7 设备 Token 作用域列（与 §9 配套）

`user_api_tokens` 新增一列（双栈幂等，写法同 §4.1）：

| 列 | 类型 | 说明 |
|---|---|---|
| `scope` | VARCHAR(64) NOT NULL DEFAULT 'mcp' | `mcp`（既有）/ `subscription:read` / `subscription:export`；多值用逗号分隔 |

- 历史 token 默认 `mcp`，**行为不变**；`/export/links` 与 `/push-items` 校验 `subscription:export` / `subscription:read`
- **建列在 T1（数据模型）完成**；T3 路由先按 JWT 放行，T6 再补 token scope 校验（顺序：T1 建列 → T3 上线 → T6 收紧），避免出现「路由已上线但列不存在」

## 5. 去重规则（本设计的核心）

判定键：`(user_id, base_url_norm, sha256(api_key))`

| 场景 | 处理 |
|---|---|
| base_url 相同 + Key 相同 | **完全跳过**：不新增、不更新、不改 label / enabled / sort_order |
| base_url 相同 + Key 不同 | 新增一条（同一渠道多把 Key = 多个订阅，正常保存） |
| base_url 不同 + Key 相同 | 新增一条（两个端点各一份，按用户规则不算同一条） |
| base_url 为空（官方直连） | 归一为 `official`，等价于「同一官方端点」参与判定 |

- 与旧规则关系：旧「同 provider+Key 跳过」「同 Key 全局唯一」**被本节取代**；同步入口统一调用同一个 `dedupe_key()`，禁止各处自实现。实现期由 `QUOTA_DEDUPE_MODE`（默认 `url_key`，回滚可切 `legacy`）选择规则集
- **并发安全**：两个客户端同时提交同一 `(url, key)` 时，唯一索引会抛 `IntegrityError` / PG `UniqueViolation` → 捕获后按 **skip** 处理（返回 `reason=duplicate`），**不得 500**；无索引（降级态）时由应用层先 SELECT 再 INSERT，同样以唯一冲突兜底
- **存量 hash 缺失**：`api_key_hash = ''` 的行在判重前先用 `decrypt_api_key(api_key_enc)` 现算 sha256（复用现有 `subscription_sync` 的补算逻辑）；解密失败的行**不参与判重**并进「异常行报告」，绝不因此误判为「不存在」而重复插入
- **新行字段映射**：`category` 沿用 provider spec 的类别、`app` 取来源 agent（不在 cc-switch app 列表内则留空）、`is_channel=TRUE`、`enabled=TRUE`、`sort_order = max+1`（与现有 insert 逻辑一致）
- 存量数据：**不自动删除**；提供「重复项报告」（`GET /subscriptions/duplicates`）列出命中同一去重键的行，由用户在 UI **单条或批量**确认后处理（处理动作：`保留最新` / `保留指定 id` / `全部保留`；删除走软删除语义的有确认流程，不做物理 DROP）
- 回填：见 §4.4（`backfill_base_url_norm()`，dry-run 默认）

## 6. 云端 → 本机（推送）

### 6.1 链接生成（服务端，纯网页路径）

`GET /api/subscription-quota/export/links?target=ccswitch|magpie&ids=<id,id>`

响应：

```json
{
  "target": "ccswitch",
  "items": [
    {"accountId": "...", "label": "...", "providerId": "kimi", "maskedKey": "sk-k…XBud",
     "url": "ccswitch://v1/import?...", "warnings": []}
  ]
}
```

- `ids` 为空 = 全量
- 生成规则见 §6.2 / §6.3；无法生成（缺 model、缺 endpoint）时 `url=null` + `warnings[]` 说明原因，**不静默失败**
- 响应头必须 `Cache-Control: no-store`、`Pragma: no-cache`（响应体含明文 Key，禁止任何中间层缓存）
- **绝不写日志**；审计记录只含 `user_id / accountId / target / maskedKey / sha256(url)`，不含完整链接
- 单次最多 200 条（`ids` 超限返回 400），避免一次响应携带过多明文凭据

### 6.2 CC Switch 链接映射

| 本工具 provider | app | endpoint | 附加参数 |
|---|---|---|---|
| anthropic / claude | `claude` | 账号 base_url（空则 §4.6 默认值） | — |
| openai / codex / deepseek / qwen | `codex` | base_url / 默认值 | — |
| gemini / google | `gemini` | base_url / 默认值 | — |
| 其它（中继/中转/opendesign） | `opencode` | base_url / 默认值 | `apiFormat=anthropic`（URL 含 `/anthropic`）否则 `openai_chat` |

- `pi|mcode|kimi|dsh|omp` **不生成**（这些 app 的深链必须带 `model`，本工具无模型元数据，会解析期报错）→ 返回 warning 并建议改选 `claude`/`opencode`
- `name` 用账号 label（去掉掩码后缀）；`notes` 注明「来自订阅中心」
- `enabled` 语义按 app 类型区分（依据 cc-switch 源码注释）：
  - **切换式**（claude / codex / gemini / copilot / kimi / dsh …）：`enabled=false` = 只入库到列表，**不改该应用当前供应商**
  - **累加式**（opencode / openclaw / hermes / pi）：`enabled=false` = **不写入该应用的配置文件**，仅存进 CC Switch 列表
  - 本设计统一传 `enabled=false`，即「导入但不改变本机 Agent 现有行为」，需要生效时由用户在 CC Switch 里点切换

### 6.3 Magpie 链接映射

| 本工具 provider | preset | 备注 |
|---|---|---|
| kimi | `kimi-code` / `kimi-code-cn`（按 region） | |
| zhipu | `zhipu` / `zai`（按 region） | |
| minimax | `minimax` / `minimax-cn` | |
| deepseek / siliconflow / openrouter / volcengine / stepfun / qwen | 同名 preset | |
| opencode_go | `opencode-go` | |
| opendesign / 未知中继 | 无 preset → `name=` + `anthropic=`/`chat=` + region | id 由 name 派生（桥侧会先查重） |

- 链接始终带 `key=`；`models=` 有则带（magpie 允许多模型）
- `balance=` 仅当 base_url 与查询端点同 host 时才带（magpie 的安全校验要求同 host）

### 6.4 前端交互（G4）

新增 Tab `local`（「同步到本机」）：

- 列表列：勾选框 / 供应商 / label / 渠道 host / 掩码 Key / 两个按钮（「CC Switch」「Magpie」）
- 顶部：`全选` / `反选` / `同步选中到 CC Switch` / `同步选中到 Magpie` / `刷新`
- **批量实现**：浏览器一次用户手势只能打开一个自定义协议 →
  - 采用**队列模式**：点击批量后，页面显示「待打开 N 条」，逐条高亮并提供「打开下一条」按钮（仍是一次手势一条），或
  - 或走本地桥（一条命令静默/确认），页面展示命令块
- 队列状态：存在组件内存（`useState`），显示 `待打开 / 已完成 / 失败` 三个计数；刷新页面即重置（不持久化，避免误以为已同步）；「打开下一条」失败可重试该条
- 每行按钮 = 单条操作（G4 的「单独操作」）；任意渠道（CC Switch / Magpie）都同时具备单条与批量入口
- 页面固定提示：深链会把 Key 放进浏览器历史，建议使用本地桥（附命令）

## 7. 本机 → 云端（拉取）

### 7.1 新增上行接口

`POST /api/subscription-quota/subscriptions/push-items`（JWT 或设备 Token，见 §9）

请求体沿用本项目既有约定的 **snake_case**（与 `addAccount` 的 `provider_id / api_key / window_type` 一致）：

```json
{"dry_run": false, "items": [
  {"provider_id": "kimi", "provider_name": "Kimi Code",
   "base_url": "https://api.kimi.com/coding/v1", "region": "",
   "channel": "api.kimi.com", "api_key": "sk-…", "source_agents": ["cc-switch"]}
]}
```

响应体沿用本项目既有约定的 **camelCase**（与 `/providers`、`/query` 一致）：

```json
{"created": 1, "skipped": 2, "items": [
  {"action": "create", "label": "Kimi·XBud", "maskedKey": "sk-k…XBud", "reason": null}
]}
```

- 走与 §5 相同的去重器；`reason` 取值 `duplicate` / `missing_key` / `invalid_url`
- 明文 Key 仅服务端内存短暂存在（加密入库、只回 masked）
- 与现有 `/subscriptions/sync` 的区别：`/sync` 是「服务端扫描本机」，`/push-items` 是「客户端上传条目」，云端部署下用后者
- 单次最多 500 条，超出返回 400 并提示分批

### 7.1.1 配套的明文导出接口（桥 push 用）

`GET /api/subscription-quota/export/accounts`（作用域 `subscription:export`）

- 返回 `{items: [{accountId, providerId, label, baseUrl, region, channel, maskedKey, apiKey}], count}`
- 供桥脚本自行决定写 Magpie（CLI）还是 CC Switch（深链），比解析深链更稳
- 同样 `no-store`、同样只写脱敏审计（`action=export_account`）

### 7.2 桥 pull 流程

1. 扫描本机：`scan_local_subscriptions()`（cc-switch / claude / codex / opencode / zcode）× `magpie providers.json`
2. 归一 + 本地内去重（同 §5 键）
3. `POST /subscriptions/push-items`
4. 打印 `created / skipped` 明细（掩码 Key）

## 8. 本地桥 CLI（`backend/scripts/subscription_bridge.py`）

```
# 云端 → 本机
python -m scripts.subscription_bridge push --server https://tools.peanuthzm.com.cn \
    --token $env:TOOLS_DEVICE_TOKEN [--target both|ccswitch|magpie] [--dry-run] [--json]

# 本机 → 云端
python -m scripts.subscription_bridge pull --server ... --token ... [--dry-run] [--json]

# 查看差集（不写任何东西）
python -m scripts.subscription_bridge plan --server ... --token ... [--json]
```

- **push 流程**：拉云端账号（含明文 Key）→ 读本机现状 → 按 §5 键求差集 → 写入
  - Magpie：`magpie import -y <link>`（官方 CLI，静默；非终端环境必须带 `-y`）
    - 后续可选优化：`/v1/magpie/admin/provider/save`（需先在本机 `magpie gateway-key admin <id> local`）——本次未接线，避免在用户机器上自动创建管理 Key
  - CC Switch：`os.startfile("ccswitch://…")` 逐条打开（用户确认）；`--yes` 不解弹窗（CC Switch 无静默通道）
- **pull 流程**：见 §7.2
- `--dry-run` 只打印差集（`action=create|skip` + 原因）；`--json` 输出给页面/脚本消费
- **网络策略**：单请求超时 30s，失败重试 2 次（指数退避 1s/3s）；重试仍失败 → 退出码 1
- **幂等性**：`push` / `pull` 重复执行天然安全（差集 + 服务端去重），中断后可直接重跑
- 退出码：0 成功；1 参数/网络错误；2 部分失败（明细在输出里）
- 未安装某 app：跳过该目标并明确提示（不静默成功）
- 禁止把 Key 打到 stdout：只打掩码；`--debug` 也不打全量

**Magpie 静默通道的能力边界（实施期确认）**

- `magpie import -y <link>` 已可**完全静默**完成写入，无需 admin Key、不改用户 magpie 配置
- 已知代价：Key 会出现在子进程命令行（`magpie` 进程的 argv）；本机单用户场景可接受，`--verbose` 也不回显
- 若要彻底消除 argv 暴露，再走 §3.2 的 admin API（需用户在本机手动授权一把管理 Key）——列为后续增强，不在本次范围

## 9. 安全（Key 暴露面）

| 通道 | 风险 | 措施 |
|---|---|---|
| 网页深链 | Key 进浏览器历史 / 剪贴板 | UI 明示；默认推荐桥；链接按需单条生成（不一次性塞 DOM）；响应 `no-store` |
| 桥 push | Key 出现在命令行参数 | 只用 `--token`（设备 Token），订阅 Key 走 HTTPS 响应体；禁止把订阅 Key 当参数 |
| magpie CLI | Key 出现在子进程 argv | `magpie import -y`（本机单用户场景可接受，输出只打掩码）；彻底消除需 admin API（后续增强） |
| 服务端日志 | 链接/Key 泄漏 | 全部日志只输出 provider/label/maskedKey/url_hash |
| 明文导出接口 | 越权 + 权限放大 | 见下方「设备 Token 作用域」 |

**设备 Token 作用域（待确认，默认按方案 A 实现）**

- 方案 A（默认）：新建独立的「设备 Token」类型（复用 `user_api_tokens` 表，新增 `scope` 列，取值 `subscription:read` / `subscription:export`），`/export/links` 与 `/push-items` 只接受带对应 scope 的 token，**不复用 MCP 用的通用 PAT**
- 方案 B（更省事但风险高）：直接复用现有 PAT —— 不推荐，等于把「读 MCP」的凭据升级成「导出全部明文订阅 Key」
- 无论 A/B：导出接口按用户限速（60 次/小时），并在 `subscription_sync_audit` 记一条审计

## 10. 验收标准

| # | 场景 | 期望 |
|---|---|---|
| V1 | 概览勾选 1 条 → 点「CC Switch」 | 浏览器唤起 CC Switch 确认框，确认后列表出现该供应商（app 正确） |
| V2 | 勾选 3 条 → 点「Magpie」 | 队列模式逐条打开；每条 magpie 确认后 providers 增加 |
| V3 | 桥 `plan`（本机已装齐） | 云端有、本机已有的条目全部 `skip`，原因 `duplicate(url+key)` |
| V4 | 桥 `push` | Magpie 静默写入（若已 setup）或 CLI 写入；重复项 0 新增 |
| V5 | 桥 `pull` | 本机新增的中继订阅进入云端；重复项 `skipped` |
| V6 | 同 URL 不同 Key | 云端两条并存，分别同步到本机（两条） |
| V7 | 同 URL 同 Key 二次同步 | 完全不处理（无新增、无更新、label 不变） |
| V8 | 全选 23 条批量同步 | 逐条可完成，无阻塞；失败项有明确原因 |
| V9 | 未安装 CC Switch 的机器 | 明确提示未安装，不报成功 |
| V10 | 存量重复数据 | 报告页列出，未经确认不删除 |
| V11 | 两个客户端并发 push 同一 (url,key) | 一条 create、一条 skip，**无 500** |
| V12 | 存量存在同去重键重复行时启动服务 | 跳过建索引 + WARN + 重复项报告，服务正常启动 |
| V13 | 无 endpoint 且无默认值的账号 | 返回 `url=null` + warning，不生成坏链接 |

## 11. 任务拆分

| # | 任务 | 交付物 | 依赖 |
|---|---|---|---|
| T1 | 数据模型 + 归一 + 回填 | `accounts.py`（两列 + 索引 + 冲突检测降级）、`user_api_tokens.scope` 列（§4.7）、`normalize_base_url`、`scripts/backfill_base_url.py`、单测 | — |
| T2 | 统一去重器 | `dedupe.py`（唯一实现 + `QUOTA_DEDUPE_MODE`）、`subscription_sync.py` 改造、`push-items` 路由、`/subscriptions/duplicates`、单测 | T1 |
| T3 | 深链生成器 | `link_builder.py`（cc-switch/magpie 映射表 + §4.6 默认 endpoint）、`/export/links` 路由（no-store）、快照单测 | T1 |
| T4 | 前端「同步到本机」 | `LocalSyncPanel.tsx`（多选/全选/单条/批量队列/命令块）、`subscriptionQuotaApi.ts`、tab 注册、`__tests__` | T3 |
| T5 | 本地桥 CLI | `scripts/subscription_bridge.py`（plan/push/pull）、单测 | T2,T3 |
| T6 | 安全与审计 | 设备 Token scope、导出限速、审计表 `subscription_sync_audit` | T2,T3 |
| T7 | 文档 + 全量验收 | 本文件定稿、`docs/reviews/*` 台账、浏览器验收记录 | 全部 |

**审计表 `subscription_sync_audit`（T6 交付，幂等 DDL）**

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | BIGSERIAL / INTEGER PK AUTOINCREMENT | |
| `user_id` | VARCHAR(64) NOT NULL | 操作者 |
| `account_id` | VARCHAR(64) | 相关账号（可空：批量 push 时为空） |
| `target` | VARCHAR(16) NOT NULL | `ccswitch` / `magpie` / `cloud` |
| `action` | VARCHAR(16) NOT NULL | `export_link` / `create` / `skip` |
| `masked_key` | VARCHAR(32) | 只存掩码 |
| `url_hash` | VARCHAR(64) | sha256(链接) 或 sha256(base_url) |
| `created_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | |

```sql
CREATE TABLE IF NOT EXISTS subscription_sync_audit (
  id BIGSERIAL PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  account_id VARCHAR(64),
  target VARCHAR(16) NOT NULL,
  action VARCHAR(16) NOT NULL,
  masked_key VARCHAR(32),
  url_hash VARCHAR(64),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ssa_user_time ON subscription_sync_audit (user_id, created_at DESC);
```

- SQLite 方言用 `INTEGER PRIMARY KEY AUTOINCREMENT`（沿用 `_ensure_schema` 的分方言 DDL）

## 12. 风险与回滚

| 风险 | 影响 | 缓解 |
|---|---|---|
| 唯一索引与存量数据冲突 | 建索引失败 | 建索引前跑冲突检测（§4.2），有冲突则跳过建索引 + WARN + 报告，**不阻断启动**；应用层去重兜底 |
| 去重规则切换引发历史行为变化 | 同步结果与旧版不同 | `QUOTA_DEDUPE_MODE` 开关（默认 `url_key`，可切 `legacy`），切换无需改代码 |
| provider_id 漂移继续产生新 id | 展示重复 | 别名表只做展示归一，唯一性由 URL+Key 决定，不会因此重复 |
| CC Switch 每次确认 | 批量体验差 | 队列模式 + 推荐桥；不直写其 DB |
| Magpie 同 id 覆盖 | 覆盖用户已有配置 | 写入前查 `providers.json`；id 冲突则加 `-2` 后缀并提示 |
| 深链 Key 泄漏 | 凭据暴露 | 优先桥；UI 明示；日志脱敏；响应 `no-store` |
| 桥在无 Python 机器不可用 | 无法双向 | 文档注明；后续可打包 exe（不在本次范围） |

**回滚步骤（按顺序执行，每步可独立重复执行）**

1. 运行时开关：`QUOTA_DEDUPE_MODE=legacy`（环境变量），恢复旧去重行为，无需改代码
2. 前端：关闭「同步到本机」入口（配置开关 `VITE_LOCAL_SYNC=off` 或直接回退 T4 提交）
3. 数据：执行 §4.2 的 `DROP INDEX` / `DROP COLUMN` 语句（先确认无代码引用）
4. 若桥已写入本机 app：Magpie 用 `magpie provider rm <id>` 删除、CC Switch 在 UI 里删除对应条目（本工具**不自动删除**用户本机配置）

## 13. 非目标

- 不做 CC Switch / Magpie 之间的互转（它们各自已有 `ccswitchlink` 互操作）
- 不做直写 CC Switch sqlite
- 不做订阅 Key 的云端轮换/下发策略
- 不改动 Agent 切换（`AgentSwitchPanel`）与额度查询逻辑

## 14. 文档关系

- 本文件**取代** `specs/agent-subscription-sync-design.md` 中的去重规则（规则 1 / 规则 2 / 同 Key 全局唯一）；旧文件保留用于追溯「本机扫描 → 云端」的实现背景，其规则章节已标注 superseded
- 与 `docs/design/agent-subscription-merge.md`（订阅中心合并）无冲突：本文件只新增「推送/拉取通道 + 统一去重键」
- 台账：`docs/reviews/2026-11-21-agent-subscription-bridge-review.md`