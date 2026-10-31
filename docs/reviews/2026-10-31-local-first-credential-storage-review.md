# 审查台账：本地化凭据存储设计  (2026-10-31)

## 待审清单（启动时确认）
- [x] docs/superpowers/specs/2026-10-31-local-first-credential-storage-design.md

**技术栈识别**：命中 `backend/requirements.txt`（Python）与 `frontend/package.json`（前端），但 `references/checklist-python.md` 与 `references/checklist-frontend.md` 均不存在 → 按 stack-detection.md 规则 3/4，**降级为仅执行通用核心维度 3、4**；维度 1（项目规范符合性）、维度 2（现有功能安全性）整体标记 ⊘ N/A。

## 发现表
| ID  | 维度 | 严重 | 文件:行 | 问题 | 状态 | 发现轮次 |
|-----|------|------|---------|------|------|----------|
| F01 | 4-设计 | 高 | design.md:§4.4 | 服务器侧 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` 仅给了 PG 写法，未定义 PG 与 SQLite 双方言的加列实现，而 4.3 已明确 SQLite 不支持该语法 —— 方案自相矛盾，实施时会直接失败 | 已修复 | 1 |
| F02 | 4-设计 | 高 | design.md:§6.1 | 迁移重加密流程未定义「配置被删除但目标端已写入」的失败回滚顺序，存在「本地与服务器同时存在同一 id 配置」的重复记录风险 | 已修复 | 1 |
| F03 | 4-设计 | 中 | design.md:§5.1 | `ConfigRepository` 接口的 `create/update` 签名未包含 `storage_location` 参数，但配置归属由该字段决定 —— 契约不完整，实现方无法正确路由 | 已修复 | 1 |
| F04 | 3-SQL | 中 | design.md:§4.4 | 服务器侧 `db_configs` 加列后，既有行默认值 `'SERVER'` 的回滚 SQL 未提供（清单 3.3 要求「迁移 SQL 不可逆 → 添加回滚 SQL」） | 已修复 | 1 |
| F05 | 4-设计 | 中 | design.md:§3.2 | 安全不变量声称「查询始终带 storage_location 过滤」，但本地库只有 LOCAL 行、远程库只有 SERVER 行，单边过滤无法防止跨库读取，表述容易被误实现为「只需一处过滤」 | 已修复 | 1 |
| F06 | 4-设计 | 中 | design.md:§2.4 | 未说明服务器模式下 `DATABASE_URL` 已指向远程 PG 时，本地 SQLite 引擎的创建时机（启动即建 vs 首次写入），影响启动性能与失败行为 | 已修复 | 1 |
| F07 | 4-设计 | 中 | design.md:§11.1 | 测试策略缺少「本地库中不存在服务器配置」的跨库隔离断言 —— 这是本设计最核心的安全不变量，缺少对应测试即失去回归保护 | 已修复 | 1 |
| F08 | 4-设计 | 低 | design.md:§4.1 | 密钥文件「原子写入（先写临时文件再 rename）」未说明 Windows 下 `os.rename` 覆盖已存在文件的语义差异（Windows 需先删除目标） | 已修复 | 1 |
| F09 | 4-设计 | 中 | design.md:§7.1 | 单条迁移接口未说明当配置已在目标端且源端也存在的「幂等处理」具体策略（规格只说「先删除目标旧行」），未说明删除失败时的行为 | 已修复 | 1 |
| F10 | 3-SQL | 中 | design.md:§4.3 | 本地 `db_configs` DDL 缺少 `sql_execution_history` / `db_scan_history` / `table_schema_cache` / `user_display_preferences` 四张关联表的说明 —— 这些表与配置表有外键依赖，遗漏会导致本地执行历史无法落库 | 已修复 | 1 |
| F11 | 4-设计 | 中 | design.md:§4.1 | 未定义本地库文件自身的加密密钥与「清空本地数据」入口的联动 —— 清理后密钥是否保留未说明，影响用户重装/重置语义 | 已修复 | 1 |
| F12 | 4-设计 | 低 | design.md:§12 | 实施顺序第 3 步「服务器 4 张表加 storage_location」未标注该步骤涉及 `init_db_tool.sql`（SQL 文件）与 3 个 Service 的 `_ensure_table()` 两处来源，实施时可能漏改 | 已修复 | 1 |
| F13 | 4-设计 | 高 | design.md:§5.1 | 同节自相矛盾：「Repository **不做二次判断**，直接写入该列」与下一条「校验传入值与绑定位置一致，不一致则抛错」直接冲突 | 已修复 | 2 |
| F14 | 4-设计 | 高 | design.md:§3.3 | 未区分「本地凭据库」与「主应用库 `settings.DATABASE_URL`」——桌面模式 `DATABASE_URL` 默认就是 sqlite（`backend/.env.example:12`），若把主应用库当远程存储目标会因方言不同而失败 | 已修复 | 2 |
| F15 | 4-设计 | 高 | design.md:§5.2 | `Column("storage_location", ..., default="SERVER")` 与「本地库同一份 Table 定义共用」冲突 —— 默认值写死会导致本地库新行被标成 SERVER，直接破坏安全不变量 | 已修复 | 2 |
| F16 | 4-设计 | 中 | design.md:§5.5 | 别名唯一性检查是单库内的（`database_tool_service.py:725`），双库后会出现本地/服务器各有一个同名 alias，迁移时也会撞名，未定义跨库处理 | 已修复 | 2 |
| F17 | 4-设计 | 低 | design.md:§5.2 | `Table` 定义里 `nullable=False` 但未说明本地库的 `storage_location` 默认值来源，且 `metadata` 未与引擎绑定（`metadata.create_all` 需显式指定 engine），实施细节缺失 | 已修复 | 2 |
| F18 | 4-设计 | 中 | design.md:§9 / §10 | 安全表仍写「三重保障」而 3.2 已改为四重（口径不一致）；错误处理表仍写「本地库初始化失败 → 启动即失败」，与 4.3 新增的「延迟创建」矛盾 | 已修复 | 3 |
| F19 | 4-设计 | 中 | design.md:§11.2 | 前端测试表含占位行「`fileType` 无关 | — |」（无意义内容），且未给出具体测试文件路径，无「步骤可执行」性 | 已修复 | 3 |

## 轮次日志
- 第1轮：新增 F01–F12（12 项）；修复 F01–F12；连续无发现计数 = 0
- 第2轮：新增 F13–F17（5 项）；修复 F13–F17；连续无发现计数 = 0
- 第3轮：新增 F18–F19（2 项）；修复 F18–F19；连续无发现计数 = 0
- 第4轮：新增 0；连续无发现计数 = 1
- 第5轮：新增 0；连续无发现计数 = 2 → 达到终止条件，审查结束（共 5 轮，19 项发现全部修复）
