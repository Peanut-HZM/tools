---
name: merge-branch
description: 将当前分支（或指定源分支）合并到指定目标分支；只合并已提交的 commit（未提交改动自动 stash 保留在原分支，不询问、直接执行，最终报告列出未提交文件）；自动同步远程、submodule（v3 脚本内强制同步子模块并闸门校验）。业务子模块 gitlink 分歧由脚本在临时 worktree 把 source 合并进 target，两边提交都保留，主仓指针指向合并结果，不询问用户。只有普通文件冲突或子模块内容冲突才展示方案并等用户确认后写入。推送后切回原分支并恢复 stash。含 .gitmodules 的仓库禁止绕过本脚本手工 git merge。 Use when merging a feature branch into dest or master, or when the user invokes /merge-branch.
---

# Merge Branch

单参数优先、兼容双分支的合并技能：把 source 分支合并到 target 分支。脚本负责确定性操作（参数解析 → fetch → 同步 → merge → **submodule 强制同步（v3）→ gitlink 远端可达性验证（v3.1）**），AI 根据脚本输出的状态 JSON 决策后续操作（push / 冲突解决 / submodule 冲突现场处理 / 回退）。

## 核心保障

1. **未提交改动自动保留（v3.3：不询问、直接执行）**：合并前必须先跑 `git status --porcelain` 记录未提交改动清单；有改动时**直接进入合并，禁止停下来让用户选择**。脚本自动 `stash -u`（含未跟踪文件），因此**只有已提交的 commit 会参与合并**；未提交改动始终留在原分支，切回后原样恢复，并在最终报告的「未提交改动」区块告知用户。详见「阶段 0」
2. **提交不丢失**：合并前后记录 HEAD；push 前 `git merge-base --is-ancestor`；禁止 reset --hard / rebase source / 删除分支。**任何模块、任何分支、任何人的提交都不得丢失**——主仓与每个非公共子模块收尾都必须通过「origin/source 是 origin/target 祖先」校验，任一不通过即整体 ❌
3. **切回原分支并恢复工作区（未提交文件必须原样回来）**：所有路径最终必须运行 `scripts/restore-workspace.sh`（含未跟踪文件）。禁止只 checkout 不恢复 stash；恢复后未提交的文件必须逐个回到工作区（脚本按 inventory 核对文件存在，缺失即报错且不 drop stash）。详见 [workspace-safety.md](workspace-safety.md)
4. **子模块无关跳过（v3.4，用户规范 2026-10-14，最高优先级）**：若本次合并的提交对某个 submodule 的 gitlink **没有任何改动**（merge commit 相对合并前 target 在该路径上无差异，即 source 分支的提交与该子模块完全无关），则对该子模块 **不做任何处理**——不 fetch、不检查远端分支、不同步、不推送、不计入闸门（JSON 中 `result: "unchanged"`、`gate_pass: true`）。子模块工作区里他人未提交的检出状态与此合并无关，绝不能据此对共享分支做任何写操作。此规则优先于 Step 9.7/9.8 的默认同步行为。
5. **submodule 强制同步（v3）**：主仓 merge 成功（含 already_up_to_date）后，脚本 **Step 9.7 自动**对每个非公共 submodule 在**临时 detached worktree**（不触碰子模块工作区，无需 stash/checkout）里把 source 合并进 **刚刚 fetch 的 `origin/<target>`** 并推送，然后做闸门校验（submodule 的 origin/source 必须是 origin/target 祖先）。**不再依赖 AI 自觉执行阶段 3**。本地 target 能快进则先快进；禁止拿主仓里过期的 gitlink 或过期的本地分支当基线。推送前再拉一次远端，若 target 又有新提交，先并入再推，避免非快进拒绝。内容冲突时保留临时 worktree 现场，**AI 必须暂停并向用户展示冲突、等待用户指示后才能继续**
6. **内容冲突必须询问用户；业务子模块指针分歧自动合并（v3.5）**：普通文件冲突、子模块里的文件内容冲突，AI 必须分析双方意图、给出建议方案并展示给用户，**得到用户明确确认后才能写入**。没有确认，禁止编辑冲突文件、禁止 `git add` 冲突文件。业务子模块（非 `devops-lib`）的 gitlink 两边都不是对方祖先时，脚本先 fetch 子模块远端，在临时 worktree 里把 **source 提交合并进 `origin/<target>`**（不是主仓记录的旧指针）。主仓旧指针里若有远端还没有的提交，再并入，两边提交都保留。主仓索引用 `git update-index --cacheinfo` 指到这个合并结果，并先把该 SHA 推到子模块的 `origin/<target>`。推送若因远端基线又更新而被拒绝，脚本再拉一次并入后重推，不换私钥空转。这条路径不询问用户。禁止只保留一边的指针。子模块内容冲突时脚本保留临时 worktree（JSON `gitlink_content_conflicts`），这时才停下来问用户。
7. **submodule 预热机制（自动）**：合并前自动 `git fetch --recurse-submodules=on-demand` + `git submodule update --init --recursive`，让主仓库在 merge 前就拥有所有 submodule 的 gitlink commit 对象，避免 git merge 因对象缺失把 submodule 指针作为冲突抛出。merge 成功后自动 `git submodule update --init --merge --recursive`，由 git ort 策略对子模块执行三方合并（祖先关系时自动 fast-forward，无需 AI 介入）。不兼容冲突 → 抛出 conflict，由 merge-submodule.sh 接手处理。
8. **SSH 协议优先（v2）**：submodule 对象补齐时优先从主仓 origin SSH URL 推导 submodule SSH URL（`ssh://git@<host>:<port>/<parent>/<name>.git`），失败 fallback 到 `.gitmodules` 原 URL；fetch 失败按 stderr 关键字分类（URL 配置 / 网络 / 凭证），明确 WARN，不阻塞合并。
9. **Step 9.6 自动 amend（v2）**：merge 成功后若 submodule 指针发生变化，安全闸判定 merge commit 是否已推送：未推送 → `git commit --amend --no-edit` 把指针合到 merge commit；已推送 → 独立 commit。**绝不重写已发布的 commit hash**。
10. **认证自愈（v3）**：`scripts/lib-git-auth.sh` 提供 fetch/push 失败自愈——从 `~/.ssh/config` 的 HostName 匹配块与 `ssh -G` 收集候选 IdentityFile，逐个以 `GIT_SSH_COMMAND` 显式重试（覆盖 agent 沙箱/CI 里 ssh-agent 与 Keychain 不可用导致的 Permission denied）。所有推送统一用 `scripts/git-push-with-retry.sh <remote> <refspec>`。
11. **总闸门（v3）**：JSON 的 `submodule_gate_all_pass=false` 时（任一非公共子模块未同步成功 / fetch 失败 / 冲突未解决 / 推送失败），**整体必须按 ❌ 报告**，即使主仓 merge 与推送已成功——主仓成功不代表部署输入（子模块 target 分支）已更新。
12. **gitlink 远端可达性验证（v3.1）**：主仓 merge 成功且 submodule 同步完成后，**Step 9.8 自动**逐一校验每个非公共 submodule 在当前 HEAD 中的 gitlink commit 是否在 `origin/<target>` 远端可达。不可达时自动补推 `HEAD:refs/heads/<target>`；推送失败则闸门降级为 `false`，AI 必须按 ❌ 报告。**防止 CI 因 gitlink commit 未推送而 submodule update 失败**（2026-09-20 事故：up_to_date 预检只验证 origin/source HEAD，未验证 merge commit 实际引用的更新 gitlink）。

**HARD GATE**：
- **子模块无关跳过（v3.4）**：合并未改动某 submodule 的 gitlink 时，该子模块必须被完全跳过（脚本自动判定，`result: "unchanged"`），不得因「远程没有 source 分支」之类的无关原因判 ❌；同时严禁依据子模块工作区的他人未提交状态向共享分支推送任何内容。
- **含 `.gitmodules` 的仓库（如 gmdos-svc 的 web/devops-lib），合并必须且只能通过调用 `merge-branch.sh` 完成。AI 直接手工执行 `git merge` / cherry-pick 完成合并属于违规——主仓 merge 结构性地不会合并子模块内部的分支与推送（git 只移动 gitlink 指针），事后补 `chore：同步 web 子模块` 指针就是漏合并的证据**
- **内容冲突（主仓文件或子模块文件内容）必须先把双方意图与建议方案展示给用户、得到明确确认后才能写入**。未确认前禁止 Edit 冲突文件、禁止 `git add` 冲突文件。业务子模块 gitlink 分歧由脚本自动合并两边，不要改成只留一边，也不要为此停下来问用户
- **合并收尾必须通过不丢失校验**：主仓与每个非公共子模块均满足「origin/source 是 origin/target 的祖先」，且 gitlink 在 origin/<target> 远端可达；任一不满足即整体 ❌，不得称成功
- **工作区有未提交改动时禁止停下来询问（v3.3）**：记录清单后直接执行合并，未提交改动由 stash 机制自动保留在原分支，最终报告列出清单
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

### 阶段 0：前置检查（未提交改动自动保留，不询问）

在执行任何合并操作前，先检查工作区状态：

```bash
git status --porcelain
```

#### 判断逻辑

- **工作区干净**（无输出）→ 直接进入阶段 1
- **工作区有改动** → **记录改动清单（逐个文件），直接进入阶段 1，禁止停下来询问用户**

#### 行为约定（v3.3）

1. **只合并已提交的 commit**：merge-branch.sh 在合并前自动 `git stash push -u`（含未跟踪文件），未提交改动不参与合并，无论用户是否要求
2. **未提交改动留在原分支，不许弄丢**：合并完成后 `restore-workspace.sh` 切回原分支并按 SHA 恢复 stash，未提交的文件必须原样回到工作区；脚本按 inventory 逐个核对，缺失即报错且不 drop stash
3. **切回后必须验证**：restore 成功后跑 `git status --porcelain` 确认未提交改动清单与合并前一致（文件集合、状态码一致）；不一致按恢复失败处理并报告
4. **最终报告必须列出未提交改动清单**：在报告的「未提交改动」区块告知用户哪些文件未参与本次合并（格式见「报告格式」）

#### 硬性禁止

- **禁止**在合并前因工作区不干净而停下来询问「先提交 / 跳过 / 放弃」——直接执行，这是默认行为，不需要用户确认
- **禁止**自动替用户提交：不调用 /smart-multi-commit、不执行任何 `git add` / `git commit`（冲突解决流程中用户已确认的写入除外）
- **禁止**以「用户说过把改动合并到 dev」为由把未提交改动带进合并——只有 commit 会参与合并，未提交改动一律留在原分支
- 阶段 0 的作用是**记录**与**告知**，不是**询问**；前置检查完成后必须调用 `merge-branch.sh` 完成合并——禁止以「只是简单合并」为由绕过脚本手工执行 `git merge`（手工合并结构性漏掉 submodule 的分支合并与推送，2026-09 多次事故根源）

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
- `submodule_sync`（v3）：脚本 Step 9.7 对每个非公共 submodule 的自动同步结果数组，每项含
  - `path` / `result`：`synced`（已合并并推送）/ `up_to_date`（远端已包含 source）/ `conflict`（子模块内容冲突）/ `push_failed` / `error`
  - `pushed_head`：已推送的 target commit SHA（synced 时非空）
  - `worktree`：`conflict`/`push_failed` 时保留的临时 worktree 绝对路径（AI 在此处理，处理后必须 `git -C <sub> worktree remove <path>` 清理）
  - `gate_pass`：闸门是否通过（origin/target 包含 origin/source）
  - `error`：失败原因（含分类标签）
- `submodule_gate_all_pass`（v3）：所有非公共 submodule 闸门是否全部通过；**为 false 时整体必须按 ❌ 报告**
- `submodule_status`：每个 submodule 的三方 commit 诊断数组，每项含
  - `path` / `base_commit` / `source_commit` / `target_commit`（gitlink 指向的 commit SHA）
  - `base_subject` / `source_subject` / `target_subject`（commit subject）
  - `base_commit_time` / `source_commit_time` / `target_commit_time`（ISO 8601 时间，便于判断新旧）
  - `base_author` / `source_author` / `target_author`（`name <email>` 格式）
  - `objects_available`：本地是否已有任一 gitlink commit 对象
  - `merge_strategy_hint`：`auto-ff-from-source` / `auto-ff-from-target` / `needs-manual`（祖先关系时给出建议）
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

- **Step 9.7 已对 submodule 执行强制同步与闸门校验**（v3：主仓 up-to-date ≠ 子模块 target up-to-date）。检查 `submodule_sync` 与 `submodule_gate_all_pass`：为 false 时按「子模块冲突/失败处理流程」处理，整体按 ❌ 报告
- 运行 `restore_cmd`（切回原分支 + 按 SHA 恢复 stash）。禁止只 checkout
- pop/apply 冲突 → 报告缺失文件，stash 备份仍在 `refs/merge-branch/workspace-stash`
- 闸门通过时输出合并报告（ℹ️ 已是最新格式）；闸门不通过按 ❌ 格式

#### 路径 D：`merge_result: "success"`

脚本已完成合并（含 Step 9.7 子模块自动同步与闸门校验），当前在 target 分支。后续操作由 AI 执行：

1. **提交完整性验证**（必须执行）：
   ```bash
   # 验证 source 的所有提交都在 target 历史中
   git merge-base --is-ancestor <pre_merge_source_head> HEAD
   ```
   - 如果验证失败：立即停止，不推送，运行 restore-workspace.sh
   - 如果验证成功：继续

2. `bash scripts/git-push-with-retry.sh origin <target_branch>`（认证失败自动按 IdentityFile 重试）
   - 成功：继续
   - 失败：报告失败（含分类），**仍要运行 restore-workspace.sh**

3. **检查子模块同步结果**（v3：同步已在 Step 9.7 自动完成）：
   - `submodule_gate_all_pass=true` → 继续
   - 存在 `result: "conflict"` 或 `push_failed` 的子模块 → 按「阶段 3：子模块冲突/推送失败处理」处理
   - 存在 `result: "error"` 的子模块 → 报告原因，整体按 ❌

4. **恢复工作区**（必须执行，不可跳过）：
   ```bash
   bash skills/merge-branch/scripts/restore-workspace.sh
   ```
   不要手写 `git checkout` + `git stash pop`。

5. 输出合并报告（✅ 成功格式）。restore 失败或 `submodule_gate_all_pass=false` 则报告 ❌，不得称成功。

#### 路径 E：`merge_result: "conflict"`（只剩内容冲突才询问用户）

脚本已尝试自动合并业务子模块指针。若 JSON 仍是 `conflict`：

- `gitlink_content_conflicts` 非空：子模块文件内容冲突，现场在列出的 `worktree`。按「冲突解决流程」展示方案，**等用户确认后才写入**。
- `conflict_files` 里是普通文件，或公共子模块（`devops-lib`）指针：同样展示方案并等确认。禁止对公共子模块自动合并。
- 不要把已经自动合并成功的业务子模块指针改回只保留 source 或只保留 target。

脚本在指针分歧能干净合并时会自己完成主仓 commit，此时 `merge_result` 是 `success`，走路径 D，不要再问用户。

### 阶段 3：子模块冲突 / 推送失败处理（v3）

v3 起 Step 9.7 已自动完成子模块同步与推送；**只有** `submodule_sync[]` 中出现 `result: "conflict"` 或 `result: "push_failed"` 时 AI 才介入：

**`conflict`（子模块内容冲突）**：
1. 脚本已在临时 worktree（JSON `worktree` 字段路径）保留合并现场（detached HEAD + MERGE_HEAD + 冲突 markers）
2. 按下方「冲突解决流程」：读取 → 分析 → 拟方案 → 展示全部方案 → **等用户确认** → 才写入（顺序不可颠倒）
3. 确认后在 worktree 内：`git add <文件>` + `git commit --no-edit`
4. **推送必须从子模块目录推 SHA**（worktree 里解析不了子模块的相对路径 origin）：
   `cd <sub_path> && bash scripts/git-push-with-retry.sh origin $(git -C <worktree路径> rev-parse HEAD):refs/heads/<target_branch>`
5. 推送成功后清理现场：`git -C <sub_path> worktree remove <worktree路径>`
6. 重新校验闸门：`git -C <sub_path> fetch origin && git -C <sub_path> merge-base --is-ancestor origin/<source> origin/<target>`；通过 → 更正报告为 ✅，仍失败 → 报告 ❌

**`push_failed`**：
- 现场同样保留在 worktree；先处理 `error` 中的失败分类（凭证问题按核心保障 9 的自愈机制；网络/URL 问题报告用户）
- 修复后**从子模块目录推 worktree HEAD 的 SHA**：`cd <sub_path> && bash scripts/git-push-with-retry.sh origin <pushed_head 或 worktree HEAD>:refs/heads/<target_branch>`，成功后清理 worktree 并重校验闸门

**`error`**：
- 报告分类原因（submodule 未初始化 / fetch 失败 / 远程缺分支 / target 分叉等），整体按 ❌；不阻塞其他子模块，但闸门不会通过

处理完毕后回到主仓库目录，确认当前仍在 target 分支。旧脚本 `merge-submodule.sh` 保留用于手工兜底（已内置 fetch 认证自愈），v3 常规流程不再依赖它。

## 冲突解决流程（v3.2：任何冲突必须询问用户）

**铁律**：冲突文件的解决结果在用户明确确认前不得写入。正确顺序是「读取 → 分析 → 分类定方案 → 展示全部方案 → **等用户确认** → 才编辑写入」。禁止分析完就直接编辑「只展示结果」的旧口径。

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

### Step C：为每个冲突区域拟定解决方案（此时禁止编辑文件）

| 类别 | 含义 | 处理 |
|------|------|------|
| **auto-resolved** | 双方意图清晰可融合 | AI 拟定合并结果，**与其他区域一并展示，仍需用户确认** |
| **needs-review** | 可解决但需确认（如删除 vs 修改） | AI 推荐方案 + 理由，等用户选择 |
| **undecidable** | 语义无法判断 / 二进制文件 | 列出双方原意 + 选项，让用户选择 |

此步骤只输出文字方案（合并预览 diff），**不得**用 Edit 写入冲突文件、不得 `git add`。

### Step D：展示全部冲突方案，等待用户确认

把 Step C 的所有方案（**包括 auto-resolved**）按下方格式完整展示，并明确询问：
「以上冲突处理方案是否可以执行？也可以对任意区域单独指定处理方式（保留 target / 保留 source / 人工合并）。请确认后我再写入。」

格式示例：

```markdown
## 冲突解决方案（待确认）

共 N 个文件冲突，M 个冲突区域。**确认后才会写入文件。**

### 文件 1: `path/to/file.java`

#### 冲突区域 1 [auto-resolved]
- **target 意图**：给 login() 添加日志
- **source 意图**：给 login() 添加参数校验
- **拟合并结果**：两者都保留
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

### Step F：等待用户确认（写入前必须完成）

- 用户回复"确认"或"OK" → 进入 Step F2 写入解决结果
- 用户对 needs-review 给出选择 → AI 按选择更新方案，再次确认
- 用户对 undecidable 给出指示 → AI 按指示更新方案，再次确认
- 用户要求重新处理某文件 → AI 重新分析、重新展示
- 用户说"放弃" → 进入回退流程

**禁止跳过确认**。即使用户说"你看着办"，也要展示完整方案后再等明确回复。
**在 Step F 完成前，禁止 Edit 冲突文件、禁止 `git add` 冲突文件**（读取/分析不受限）。

### Step F2：用户确认后写入解决结果

用 Edit 工具替换冲突区域，写入确认过的合并结果。**约束**：
- 只写入用户确认过的方案；用户单独指定处理方式的区域按指示写入
- 必须保留双方意图（除非用户明确选择只保留一方）
- 不能默默删除任何一方的改动
- 不能引入与冲突无关的修改
- 必须去除所有 `<<<<<<<`、`=======`、`>>>>>>>` markers

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

合并完成后（路径 D），在推送前必须验证主仓，且收尾必须复核所有非公共子模块：

```bash
# 主仓：验证 source 分支的所有提交都在当前 target 历史中
git merge-base --is-ancestor <pre_merge_source_head> HEAD

# 每个非公共子模块（web 等）：验证远端 target 已包含远端 source（Step 9.7 闸门已做，收尾复核）
git -C <sub_path> merge-base --is-ancestor origin/<source_branch> origin/<target_branch>
```

- 主仓 exit 0：验证通过，继续推送
- 主仓 exit 1：验证失败，说明合并过程中丢失了提交
- 任一子模块校验失败：整体按 ❌（Step 9.7 闸门 `submodule_gate_all_pass=false` 同样口径）

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
| 0 | 前置检查（未提交改动）| ✅ 工作区干净 / ✅ 记录 N 个未提交改动，stash 保留在原分支 |
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

### 未提交改动（保留在原分支，必填区块）

合并开始时若有未提交改动，**必须**在此列出（恢复自 stash，仍在 `<original_branch>` 工作区）：

| 状态 | 文件 |
|------|------|
| M | `path/to/modified.java` |
| ?? | `path/to/untracked.ts` |

> 以上 N 个文件在合并开始时未提交，**未包含在本次合并**（merge-branch 只合并已提交的 commit），已原样恢复到 `<original_branch>`。如需带入 `<target>`，请先提交后再执行 /merge-branch。

工作区干净时此区块写：`无未提交改动，全部内容已包含在本次合并中。`
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

### 未提交改动（保留在原分支）
（同 ✅ 格式：有未提交改动时列出清单，工作区干净时写「无未提交改动」）
```

### ℹ️ 已是最新

```markdown
## 合并报告 ℹ️

目标分支 `<target>` 已包含 `<source>` 的全部内容，无需合并和推送。
已运行 restore-workspace.sh，回到 `<original_branch>` 且工作区文件已恢复。

### 未提交改动（保留在原分支）
（同 ✅ 格式：有未提交改动时列出清单，工作区干净时写「无未提交改动」）
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
- 未提交改动清单必须与合并前一致；有差异时列出缺失文件与对应 stash SHA
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
13. **submodule 同步失败即整体失败（v3）**：`submodule_gate_all_pass=false` 时整体按 ❌ 报告——主仓推送成功不代表子模块 target 已更新；v2 的「软失败不阻塞」是 2026-09-18 事故（web dev 落后 64 提交导致部署空白页）的直接根因
14. **gitlink 远端可达性兜底（v3.1）**：Step 9.7 的 `up_to_date` 预检只验证 `origin/source` HEAD，但 merge commit 的 gitlink 指针可能指向比 `origin/source` 更新的本地 commit。Step 9.8 在 JSON 输出前逐一校验 gitlink 是否在 `origin/<target>` 可达，不可达则自动补推；补推失败闸门降级为 `false`。这是 2026-09-20 事故（CI 报 `not our ref e2c9e55`）的直接修复。
15. 子模块**内容**冲突走「冲突解决流程」，必须展示方案并等用户确认后才写入。业务子模块指针分歧由脚本自动合并，不在此询问
16. 无法解决的冲突必须报告给用户，提供方案选项，由用户决定
17. 用户输入 `dev` 时，Shell 实参必须是 `dev`（d-e-v），禁止写成 `dest`（d-e-s-t）
18. **必须先执行阶段 0 前置检查**：记录未提交改动清单后**直接进入阶段 1**，禁止因工作区不干净而询问「先提交 / 跳过 / 放弃」或暂停等待用户
19. **未提交改动不参与合并**：merge-branch 只合并已提交的 commit；未提交改动经 stash → 切回恢复 → 报告「未提交改动」区块告知用户，全程不需用户确认，但任何文件都不许弄丢
20. **submodule 对象预热是默认行为**：merge-branch.sh 会自动 `git fetch --recurse-submodules=on-demand` + `git submodule update --init --recursive`，无需 AI 手动执行；只有脚本 Step 5 全部失败后才需要 AI 介入
21. **业务子模块指针分歧自动合并（v3.5）**：`merge_strategy_hint=needs-manual` 且冲突路径是非公共 gitlink 时，脚本先 fetch，在临时 worktree 把 source 合并进子模块的 `origin/<target>`（主仓 gitlink 更旧时不拿它当基线），两边提交都保留，主仓指针改为合并结果并推到子模块 `origin/<target>`。推送前若远端又前进，先并入再推。不询问用户。只有子模块内容冲突（`gitlink_content_conflicts`）或普通文件冲突才展示方案并等确认。禁止 `git add <子模块>` 用当前工作区 HEAD 覆盖该指针（工作区可能仍停在 source 分支）。公共子模块 `devops-lib` 仍不自动合并
22. **v2 amend 安全闸**：Step 9.6 用 `git merge-base --is-ancestor HEAD origin/<target>` 判定 merge commit 是否已推送。已推送时降级为独立 commit（`chore: update submodule pointers after merge`），**绝不** amend 已发布 hash。若安全闸误判（远端 fetch 失败导致 HEAD 不在 origin 上），脚本会按"未推送"处理 amend，本地可立即 `git reset --hard origin/<target>` 回退（reflog 90 天可恢复原 commit）。
23. **v2 SSH URL 推导适用范围**：仅在主仓 origin 是 `ssh://` 协议时推导；HTTPS origin / 无 origin 时直接 fallback 到 `.gitmodules` 原 URL。推导规则：取 origin 的 user@host:port + path 的父目录 + `<sub_name>.git`，**不动** `.gitmodules` / `.git/config`。
24. **公共 submodule 白名单（v2 硬约束）**：脚本内置白名单 `PUBLIC_SUBMODULES="devops-lib"`，合并过程中**绝对不动**白名单内的 submodule——禁止修改其工作区 / commit / push / amend 指针。Step 9.5 与 Step 9.6 命中白名单时直接跳过；合并报告必须含「跳过的公共 submodule：devops-lib」。公共 vs 业务判定：业务 submodule（如 `web`）允许合并；公共 submodule（如 `devops-lib` / `*-lib` / `*-tools` / `*-common` / `*-shared`）保留原指针。判定不明时按公共处理。
25. **所有推送走 git-push-with-retry.sh（v3）**：主仓与子模块的推送统一用 `scripts/git-push-with-retry.sh <remote> <refspec>`，禁止裸 `git push`（无认证自愈）。
26. **子模块合并使用临时 detached worktree（v3）**：Step 9.7 在 `$(mktemp -d)` 的临时 worktree 里合并，**不 stash、不 checkout 子模块现有工作区**——多 Agent 并发场景下子模块工作区的未提交文件全程不受影响。冲突/推送失败保留的 worktree 处理完毕后必须 `git -C <sub> worktree remove <path>` 清理。
27. **report 的 Submodule 状态表（v3）**：以 `submodule_sync` 为准逐行列出 path / result / pushed_head / gate_pass；`submodule_gate_all_pass=false` 时报告整体为 ❌。
28. **合并前必须对齐远端基线（2026-10-14）**：主仓在 `git merge` 之前再执行一次 `git pull --ff-only origin <target>`。业务子模块的合并基线是 fetch 之后的 `origin/<target>`，本地分支能快进就先快进。推送被「non-fast-forward」拒绝时，先把远端新提交并入临时 worktree 再推，禁止换 SSH 私钥重试这一类失败。
