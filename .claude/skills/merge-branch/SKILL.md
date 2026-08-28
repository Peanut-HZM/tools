---
name: merge-branch
description: 将当前分支（或指定源分支）合并到指定目标分支；自动同步远程、submodule、代劳型解决冲突、推送；切回原分支并恢复 stash（含未跟踪文件），禁止弄丢提交或工作区文件。 Use when merging a feature branch into dest or master, or when the user invokes /merge-branch.
---

# Merge Branch

单参数优先、兼容双分支的合并技能：把 source 分支合并到 target 分支。脚本负责确定性操作（参数解析 → fetch → 同步 → merge），AI 根据脚本输出的状态 JSON 决策后续操作（push / 冲突解决 / submodule 同步 / 回退）。

## 核心保障

1. **未提交改动前置确认**：合并前必须先跑 `git status --porcelain`；有改动时禁止直接合并，必须让用户在「先调用 /smart-multi-commit 提交 / 跳过（只合并已提交内容）/ 放弃」之间明确选择。详见「阶段 0」
2. **提交不丢失**：合并前后记录 HEAD；push 前 `git merge-base --is-ancestor`；禁止 reset --hard / rebase source / 删除分支
3. **切回原分支并恢复工作区**：所有路径最终必须运行 `scripts/restore-workspace.sh`（含未跟踪文件）。禁止只 checkout 不恢复 stash。详见 [workspace-safety.md](workspace-safety.md)
4. **submodule 同步**：主仓库合并后，对每个 submodule 做同样合并，并在 submodule 目录再跑 restore
5. **冲突交由用户**：无法自动解决的冲突必须展示给用户，由用户决定

**HARD GATE**：
- 阶段 0 未获得用户明确选择前，不得调用 `merge-branch.sh`
- 未执行 restore-workspace.sh 不得报告成功
- 禁止 `git checkout -f`、`git reset --hard`、未验证前 `stash drop`

## 触发条件

用户使用以下格式时触发：

```
/merge-branch dev                       # 单参数：source=当前分支, target=dev
/merge-branch feature-A dev             # 双参数：source=feature-A, target=dev
```

## 参数规则

- **1 个参数**：`sourceBranch = git branch --show-current`，`targetBranch = 用户输入`
- **2 个参数**：`sourceBranch = 第一个参数`，`targetBranch = 第二个参数`
- **0 个或 >2 个参数**：报错，提示正确用法
- `sourceBranch` 与 `targetBranch` 不能相同

## 分支名逐字传递（硬性，禁止改写）

调用 `merge-branch.sh` 时，分支名必须从用户 `<user_query>` **逐字复制**进 Shell 命令，禁止凭记忆重打，禁止「纠正拼写」。

已实测多次的高发误写（必须杜绝）：

| 用户实际输入 | 字母 | 含义 | 禁止传成 |
|-------------|------|------|---------|
| `dev` | d-e-v（3 个字母） | development 主干 | `dest`（d-e-s-t，destination） |
| `dest` | d-e-s-t（4 个字母） | destination | `dev` |

`dev` 与 `dest` 是两个完全不同的名字。用户写 `dev` 时，脚本参数必须是 `dev`，命令字符串里**不得**出现 `dest`。

调用脚本前自检：
1. 从 `<user_query>` 中找到 `/merge-branch` 后面的参数，原样粘贴（加引号）
2. 若用户参数是 `dev`，命令必须形如：`bash .../merge-branch.sh "dev"`
3. 不要从「target / destination」这些英文词脑补出 `dest`

脚本兜底：若误传 `dest` 且远程没有 `dest`、但有 `dev`，脚本会纠正为 `dev` 并在 stderr 警告。这不能替代逐字传参。

## 执行流程

### 阶段 0：前置检查（未提交改动检测）

在执行任何合并操作前，必须先检查工作区状态：

```bash
git status --porcelain
```

#### 判断逻辑

- **工作区干净**（无输出）→ 直接进入阶段 1
- **工作区有改动** → 必须停下来提示用户，禁止直接进入阶段 1

#### 有未提交改动时的提示格式

```
⚠️ 检测到当前分支 `<current_branch>` 有 N 个未提交的改动：

<列出前 10 个关键文件，超过 10 个用 "... 等 N 个文件" 概括>

这些改动 **不会** 被合并到目标分支 `<target>`。
merge-branch 只合并已提交的内容，未提交改动会被 stash 暂存，
合并完成后恢复回当前分支。

如果希望这些改动也合并到 target，需要先提交。请选择：

A. **先提交再合并**（推荐）— 调用 /smart-multi-commit 按模块拆分提交，
   commit 完成后自动继续合并
B. **只合并已提交的改动** — 继续当前流程，未提交改动保留在当前分支
C. **放弃合并** — 不做任何操作

请回复 A / B / C。
```

#### 根据用户回复处理

- **用户选 A**：
  1. 调用 `/smart-multi-commit`（该 skill 会自行处理 rebase / 拆分 / commit / push）
  2. smart-multi-commit 全部完成且用户确认后，重新进入阶段 0 检查
  3. 若工作区已干净 → 进入阶段 1；若仍有残留（如 skip 的文件）→ 再次提示用户
- **用户选 B**：进入阶段 1，脚本会按现有逻辑 stash → 合并 → 恢复
- **用户选 C**：终止，不做任何 git 操作

#### 硬性禁止

- 禁止在用户回复前直接调用 `merge-branch.sh`
- 禁止自动替用户决定「先提交」或「跳过」
- 即使用户之前说过"把改动合并到 dev"，也不等价于"把未提交的改动也带过去"，必须显式确认
- 若用户在同一轮对话中已经明确表示过"未提交改动不用管，直接合并"，可跳过此提示但报告中必须记录

### 阶段 1：运行主仓库脚本

调用本 skill 目录下的 `scripts/merge-branch.sh`：

```bash
bash skills/merge-branch/scripts/merge-branch.sh [args...]
```

路径解析：该路径相对于当前 agent 的配置根目录（Claude Code 是 `~/.claude/`，Cursor 是 `~/.cursor/`，Codex 是 `~/.codex/`）。三个 agent 的 skills/merge-branch 都是符号链接，指向同一个真实源 `~/.agents/skills/merge-branch/`，因此脚本在任何 agent 下都能找到并执行。

传参规则：
- 用户输入 1 个参数 → 脚本也传 1 个参数（参数内容必须与用户输入逐字相同）
- 用户输入 2 个参数 → 脚本也传 2 个参数（每个参数都必须逐字相同）
- **禁止**把 `dev` 改写成 `dest`，也禁止把 `dest` 改写成 `dev`

脚本 stdout 末尾会输出状态 JSON，包裹在 `===MERGE-STATUS===` 和 `===END-STATUS===` 之间。解析这个 JSON 后决定下一步。

JSON 关键字段：
- `source_branch` / `target_branch`：实际使用的分支名
- `target_rewritten_from`：若因 `dest`/`dev` 混淆纠正过，值为纠正前的名字，否则为 null
- `original_branch` / `original_head`：执行前的当前分支与 HEAD
- `stash_created` / `stash_sha` / `restore_cmd`：工作区 stash；结束后必须执行 `restore_cmd`
- `merge_result`：`success` / `already_up_to_date` / `conflict`
- `conflict_files`：冲突文件列表
- `submodules`：检测到的 submodule 路径列表（可能为空数组）
- `pre_merge_source_head`：合并前 source 的 HEAD commit hash
- `pre_merge_target_head`：合并前 target 的 HEAD commit hash

### 阶段 2：根据状态决策

#### 路径 A：`exit 1`（致命错误）

脚本已输出错误信息到 stderr 和 JSON 的 `error` 字段。

- 不要继续
- 脚本在 exit 1 时已尝试 `restore-workspace.sh --abort-merge`
- 若 JSON `stash_restored` 为 false：立即再跑 `restore_cmd`，不得报告文件已丢
- 输出合并报告（失败格式）

#### 路径 B：`exit 2`（target 本地与远程分叉）

JSON 的 `diverge_info` 含双方独有提交。

- 不要继续
- 脚本在 exit 2 时已尝试恢复工作区；若未恢复则立即执行 `restore_cmd`
- 输出合并报告（失败格式），列出本地/远程独有提交
- 给用户提供 3 个建议选项（由用户执行，技能不得代跑 reset --hard）：
  1. `git reset --hard origin/<target>` 丢弃本地
  2. `git pull --rebase origin <target>` 保留本地
  3. 手动处理后重新执行
- 脚本已尝试恢复工作区；确认 `stash_restored` 或再跑 `restore_cmd`

#### 路径 C：`merge_result: "already_up_to_date"`

- 运行 `restore_cmd`（切回原分支 + 按 SHA 恢复 stash）。禁止只 checkout
- pop/apply 冲突 → 报告缺失文件，stash 备份仍在 `refs/merge-branch/workspace-stash`
- 输出合并报告（ℹ️ 已是最新格式）

#### 路径 D：`merge_result: "success"`

脚本已完成合并，当前在 target 分支。后续操作由 AI 执行：

1. **提交完整性验证**（必须执行）：
   ```bash
   # 验证 source 的所有提交都在 target 历史中
   git merge-base --is-ancestor <pre_merge_source_head> HEAD
   ```
   - 如果验证失败：立即停止，不推送，运行 restore-workspace.sh
   - 如果验证成功：继续

2. `git push origin <target_branch>`
   - 成功：继续
   - 失败（远程有新提交）：报告失败，建议用户重新 fetch，**仍要运行 restore-workspace.sh**

3. **处理 submodule**（如果 JSON 中 `submodules` 非空）：
   - 对每个 submodule 执行「阶段 3：submodule 同步」（见下）
   - submodule 全部处理完后，回到主仓库目录

4. **恢复工作区**（必须执行，不可跳过）：
   ```bash
   bash skills/merge-branch/scripts/restore-workspace.sh
   ```
   不要手写 `git checkout` + `git stash pop`。

5. 输出合并报告（✅ 成功格式）。restore 失败则报告 ❌，不得称成功。

#### 路径 E：`merge_result: "conflict"`（核心：代劳型冲突解决）

脚本已完成 merge 但触发冲突，当前在 target 分支，工作区含冲突 markers。进入「冲突解决流程」（见下）。

### 阶段 3：submodule 同步

当主仓库 JSON 中 `submodules` 数组非空时，对每个 submodule 执行以下操作。

对每个 submodule 路径 `<sub_path>`：

1. 调用 submodule 脚本：
   ```bash
   bash skills/merge-branch/scripts/merge-submodule.sh <sub_path> <source_branch> <target_branch>
   ```

2. 解析输出 JSON（包裹在 `===SUBMODULE-STATUS===` 和 `===END-SUBMODULE-STATUS===` 之间）

3. 根据 `merge_result` 处理：

   **`already_up_to_date`**：
   - 在 submodule 内运行 `restore_cmd`
   - 回到主仓库：`cd ..`

   **`success`**：
   - **完整性验证**：`cd <sub_path> && git merge-base --is-ancestor <pre_merge_source_head> HEAD`
   - 推送：`cd <sub_path> && git push origin <target_branch>`
   - 在 submodule 内运行 `restore_cmd`（禁止 checkout -f）
   - 回到主仓库：`cd ..`
   - 在主仓库中提交 submodule 引用更新：
     ```bash
     git add <sub_path>
     git commit -m "chore: update submodule <sub_path> to track <target_branch>"
     ```
     注意：这个 commit 只在有实际引用变更时才做

   **`conflict`**：
   - 进入 submodule 冲突解决流程（与主仓库冲突解决流程相同）
   - 解决后推送、切回原分支
   - 回到主仓库提交 submodule 引用更新

   **`error` / `exit 1` / `exit 2`**：
   - 报告 submodule 处理失败
   - 脚本已尝试恢复；若未恢复则在 submodule 内跑 `restore_cmd`
   - 回到主仓库
   - 询问用户是否继续处理其他 submodule 或中止

4. **submodule 处理完毕后**，回到主仓库目录，确认当前仍在 target 分支

### 阶段 4：submodule 冲突解决

与主仓库冲突解决流程完全一致（读取冲突文件 → 分析 → 编辑 → 分类 → 展示 → 等用户确认 → commit → push → 切回原分支）。

唯一区别：所有 git 操作在 submodule 目录内执行，操作完毕后必须切回 submodule 的 `original_branch`。

## 冲突解决流程（代劳型）

### Step A：读取每个冲突文件

对 JSON 中 `conflict_files` 列出的每个文件，使用 Read 工具读取。git 在冲突文件中留下标准 markers：

```
<<<<<<< HEAD
  // target 分支的内容
=======
  // source 分支的内容
>>>>>>> <source_branch>
```

### Step B：分析每个冲突区域

对每个冲突文件中的每个冲突区域（可能多个），分析三方：
- **base**（共同祖先）：原来是什么
- **ours/HEAD**（target 分支）：target 想改成什么，意图是什么
- **theirs/source**（source 分支）：source 想改成什么，意图是什么

分析维度：
- 双方是否改了同一行？
- 双方改动是否互斥（一边删了一边改了）？
- 双方改动是否独立（可融合）？
- 是否涉及重命名、删除等结构性变更？

### Step C：编辑文件写入合并结果

用 Edit 工具直接替换冲突区域，写入合并结果。**约束**：
- 必须保留双方意图（除非明确冲突无法融合）
- 不能默默删除任何一方的改动
- 不能引入与冲突无关的修改
- 必须去除所有 `<<<<<<<`、`=======`、`>>>>>>>` markers

### Step D：分类每个冲突区域

| 类别 | 含义 | 处理 |
|------|------|------|
| **auto-resolved** | 双方意图清晰可融合 | AI 直接编辑，只展示结果 |
| **needs-review** | 可解决但需确认（如删除 vs 修改） | AI 推荐方案 + 理由，等用户确认 |
| **undecidable** | 语义无法判断 / 二进制文件 | 列出双方原意 + 选项，让用户选择 |

### Step E：展示合并摘要

格式示例：

```markdown
## 冲突解决方案

共 N 个文件冲突，M 个冲突区域。

### 文件 1: `path/to/file.java`

#### 冲突区域 1 [auto-resolved]
- **target 意图**：给 login() 添加日志
- **source 意图**：给 login() 添加参数校验
- **合并结果**：两者都保留
```diff
 public void login(String user, String pass) {
+    if (user == null) throw new IllegalArgumentException();
+    logger.info("login attempt: {}", user);
     ...
 }
```

#### 冲突区域 2 [needs-review]
- **target 意图**：删除了 legacyAuth() 方法
- **source 意图**：修改了 legacyAuth() 的参数
- **AI 推荐**：保留删除（target 方向），因为已无调用方
- **备选**：保留 source 修改版

### 文件 2: `path/to/another.java`

#### 冲突区域 1 [undecidable]
- **target 意图**：订单状态枚举新增 REFUNDED
- **source 意图**：订单状态枚举新增 SHIPPING
- **选项**：
  - A. 两个都保留
  - B. 只保留 REFUNDED
  - C. 只保留 SHIPPING
  - D. 你来定

请确认/调整后回复"确认"。
```

### Step F：等待用户确认

- 用户回复"确认"或"OK" → 进入 Step G
- 用户对 needs-review 给出选择 → AI 按选择编辑，再次确认
- 用户对 undecidable 给出指示 → AI 按指示编辑，再次确认
- 用户要求重新处理某文件 → AI 重新分析
- 用户说"放弃" → 进入回退流程

**禁止跳过确认**。即使用户说"你看着办"，也要展示完整方案后再等明确回复。

### Step G：提交合并

```bash
git add <所有冲突文件>
git commit --no-edit   # 使用 git merge 自动生成的合并提交信息
```

### Step H：推送 target

```bash
git push origin <target_branch>
```

- 失败（远程有新提交）：报告失败，建议用户重新 fetch

### Step I：推送后恢复工作区（必须执行）

```bash
bash skills/merge-branch/scripts/restore-workspace.sh
```

无论成功/失败/用户放弃，这一步都必须执行。禁止 `checkout -f` / `reset --hard`。详见 [workspace-safety.md](workspace-safety.md)。

### Step J：stash 由 restore 脚本按 SHA apply

不要 `git stash pop`。脚本核对 inventory 后才 drop；失败则 stash 与 `refs/merge-branch/workspace-stash` 仍在。

## 提交完整性验证

合并完成后（路径 D），在推送前必须验证：

```bash
# 验证 source 分支的所有提交都在当前 target 历史中
git merge-base --is-ancestor <pre_merge_source_head> HEAD
```

- exit 0：验证通过，继续推送
- exit 1：验证失败，说明合并过程中丢失了提交

验证失败时的处理：
1. **不推送**
2. 记录当前状态：`git log --oneline -5`
3. 报告异常给用户，包含：
   - 合并前 source HEAD
   - 合并前 target HEAD
   - 当前 target HEAD
   - 建议用户检查并手动处理
4. 切回原分支并运行 restore-workspace.sh；禁止 reset --hard
5. 如果 stash 未恢复，保留 `refs/merge-branch/workspace-stash` 并报告，不得称文件已丢且不可恢复

## 切回原分支与工作区恢复

**所有路径最终都必须运行 `scripts/restore-workspace.sh`。** 不得停留在 target，不得留下未 apply 的 merge-branch stash。

失败路径由 merge-branch.sh 在 exit 1/2 时自动调用 `--abort-merge`。成功/冲突解决后由 AI 再跑一次（无 MERGE_HEAD 时）。连续第二次 `/merge-branch` 前脚本会先自愈遗留 stash。

## 回退机制

三个层级：

1. **`git merge --abort`** — 完全回退合并（用户说"放弃" / AI 无法解决时）
2. **`git checkout -- <file>`** — 单文件回退到冲突状态（用户说"这个文件我自己来"）
3. **保留 stash 不动** — 任何失败路径绝不自动 pop

回退后必须切回原分支。

## 报告格式

### ✅ 无冲突成功

```markdown
## 合并报告 ✅

### 合并状态
| 步骤 | 操作 | 状态 |
|------|------|------|
| 0 | 前置检查（未提交改动）| ✅ 工作区干净 / ✅ 用户选 A 先提交 / ✅ 用户选 B 跳过 |
| 1 | 参数解析 | ✅ source=`<source>`(当前分支) → target=`<target>` |
| 2 | 工作区检查 | ✅ 无需 stash / ✅ 已 stash |
| 3 | 同步 source | ✅ |
| 4 | 同步 target | ✅ |
| 5 | 合并 | ✅ 无冲突 |
| 6 | 完整性验证 | ✅ |
| 7 | 推送 target | ✅ |
| 8 | Submodule 同步 | ✅ N 个 / 无 submodule |
| 9 | 切回并恢复工作区 | ✅ restore-workspace.sh |

### 变更统计
- 共 N 个提交，X 个文件变更，+X / -X 行

### 提交日志
| 提交信息 | 作者 |
|---------|------|

### Submodule 状态（如有）
| Submodule | 操作 | 状态 |
|-----------|------|------|
| `<path>` | merge + push | ✅ |
```

### ✅ 含冲突解决成功

```markdown
## 合并报告 ✅（含冲突解决）

### 合并状态
（含 "AI 冲突解决" + "用户确认" 步骤）

### 冲突解决摘要
- [auto] <文件>: <简述>
- [needs-review] <文件>: <用户选择>
- [undecidable] <文件>: <用户选择>

### Submodule 状态（如有）
| Submodule | 操作 | 状态 |
|-----------|------|------|
```

### ℹ️ 已是最新

```markdown
## 合并报告 ℹ️

目标分支 `<target>` 已包含 `<source>` 的全部内容，无需合并和推送。
已运行 restore-workspace.sh，回到 `<original_branch>` 且工作区文件已恢复。
```

### ❌ 失败

```markdown
## 合并报告 ❌

### 失败原因
（描述）

### 详情
（列出独有提交 / 错误信息）

### 建议
（处理选项）

### 工作区状态
- 已运行 restore-workspace.sh（或脚本已在 abort 时恢复）
- 若仍有 `auto-stash before merge-branch`，明确写出 SHA 与恢复命令，不得暗示文件已永久丢失
- target 分支未做任何修改（如适用）
```

## 模块识别规则（用于报告分组）

| 文件路径模式 | 模块名称 |
|-------------|---------|
| `**/law/**` 或 `**/sign*` | 签章管理 |
| `**/team*dashboard*/**` 或 `**/snapshot*/**` | 团队看板 |
| `**/attendance*/**` | 考勤 |
| `**/login*` 或 `**/auth*/**` 或 `**/permission*` | 认证授权 |
| `**/oa*/**` | OA 集成 |
| `web/app-system-web/**` | 前端系统 |
| `**/portal*/**` | 门户 |
| `**/test/**` 或 `**/*Test.java` | 测试 |
| `*.md` 或 `docs/**` | 文档 |
| `*.sh` 或 `scripts/**` | 脚本 |
| `*.yml` / `*.yaml` / `.github/**` / `nacos*/**` | 配置 |
| 其他 | 其他变更 |

## 注意事项

1. 只推送 target 分支，不推送 source
2. 不使用 `--strategy-option` 等覆盖合并策略的选项
3. 不执行多段链式合并（需用户分多次执行）
4. commit 信息用 git 自动生成的，AI 不自创（submodule 引用更新除外）
5. 禁止 `checkout -f` / `reset --hard` / 未验证前 `stash drop`
6. 冲突解决不能丢弃任何一方的改动——除非用户明确指示
7. 二进制文件冲突一律降级让用户处理
8. AI 编辑冲突文件后如果引入语法错误，立即停止并报告
9. 报告中的分支名必须来自脚本 JSON 的 `target_branch`（若存在 `target_rewritten_from`，必须写明曾把 `dest` 纠正为 `dev`）
10. 不在 merge 之外做额外 commit（submodule 引用更新除外）
11. **所有路径最终必须运行 restore-workspace.sh**，不可停留在 target，不可遗留 stash
12. **合并后必须做完整性验证**，确认 source 提交未丢失
13. submodule 处理失败不阻塞主仓库流程，但必须报告并恢复该 submodule 工作区
14. submodule 冲突同样走代劳型冲突解决流程，需用户确认
15. 无法解决的冲突必须报告给用户，提供方案选项，由用户决定
16. 用户输入 `dev` 时，Shell 实参必须是 `dev`（d-e-v），禁止写成 `dest`（d-e-s-t）
17. **必须先执行阶段 0 前置检查**：工作区有未提交改动时禁止直接进入阶段 1，必须等用户在「先提交 / 跳过 / 放弃」之间明确选择
18. 用户选择「先提交」时，调用 /smart-multi-commit，完成后重新回到阶段 0 再判断一次
