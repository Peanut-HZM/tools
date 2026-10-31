# 审查台账：凭据本地化存储实现计划  (2026-10-31)

## 待审清单（启动时确认）
- [x] docs/superpowers/plans/2026-10-31-local-first-credential-storage.md

**技术栈识别**：命中 Python（`backend/requirements.txt`）与前端（`frontend/package.json`），但 `references/checklist-python.md` / `checklist-frontend.md` 均不存在 → 仅执行维度 3（SQL 幂等性/数据安全）与维度 4（设计完整性）；维度 1、2 标记 ⊘ N/A。

## 发现表
| ID  | 维度 | 严重 | 文件:行 | 问题 | 状态 | 发现轮次 |
|-----|------|------|---------|------|------|----------|
| P01 | 4-设计 | 高 | plans.md:Task 11 Step 3 | migration.py 草稿里留了 `_assert_alias_free` 占位函数（`raise NotImplementedError`），若实施时未删除会导致生产代码抛 NotImplementedError | 已修复 | 1 |
| P02 | 4-设计 | 中 | plans.md:Task 6 Step 4 | `_ensure_table` 里的 `conn` 类型与 `ensure_column` 期望的 `Connection` 不匹配（`_PooledRawConnection` vs SQLAlchemy `Connection`），初次草稿给了错误方案，虽在 Step 4 末尾修正但仍可能误导 | 已修复 | 1 |
| P03 | 4-设计 | 中 | plans.md:Task 5 | `ConfigRepository.__init__` 的 `tool` 校验在导入 Table 对象时可能 KeyError；`TOOL_TABLE_OBJECTS` 引用的是模块级对象，若 tool 不在 `TOOL_TABLES` 内会先抛 ValueError（正确），但需确认导入顺序 | 已修复 | 1 |
| P04 | 4-设计 | 中 | plans.md:Task 11 Step 3 | `migrate_config` 的定位源端循环每次都 `get_repository(location, tool)`，若本地仓储初始化失败会阻断定位后续位置；缺少单条失败的降级处理 | 已修复 | 1 |
| P05 | 3-SQL | 中 | plans.md:Task 3 | `local_db.py` 的 `metadata` 无 engine 绑定，`create_all` 调用需显式传 engine —— 已写但需确认测试 fixture 的 `reset_local_engine()` 在 fixture 结尾被正确调用（否则跨测试泄漏） | 已修复 | 1 |
| P06 | 4-设计 | 高 | plans.md:Task 5 | `get_with_secret` 把解密后的明文塞进字典里以 `_decrypted` 后缀返回，但 `get` / `list` 也返回同一字典 —— 若调用方误用 `list` 结果里的 `_decrypted` 字段会拿到明文，违反「列表接口永不返回明文」的安全约束 | 已修复 | 2 |
| P07 | 4-设计 | 中 | plans.md:Task 11 | `migrate_config` 里 `payload = {k: v for k, v in source_row.items() if k not in ("storage_location",) and not k.endswith("_decrypted")}` 会把 `deleted`、`created_at` 等列也拷过去 —— 若目标端表结构与源端不同（如 remote 侧有额外索引列），payload 可能包含无法 insert 的键 | 已修复 | 2 |

## 轮次日志
- 第1轮：新增 P01–P05（5 项）；修复 P01–P05；连续无发现计数 = 0
- 第2轮：新增 P06–P07（2 项）；修复 P06–P07；连续无发现计数 = 0
- 第3轮：新增 0；连续无发现计数 = 1
- 第4轮：新增 0；连续无发现计数 = 2 → 达到终止条件，审查结束
