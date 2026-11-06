# merge-branch v2：submodule SSH 协议优先 + 合并后自动 amend + needs-manual 诊断增强

- 日期：2026-09-11
- 适用技能：`~/.agents/skills/merge-branch/`
- 上游版本：v1（已完成 Step 5/8.5/9.5 + JSON submodule_status 诊断 + evals id 20/21/22）

## Context

v1 在真实 gmdos-svc 仓库验证时发现两个限制：

1. **submodule commit 对象本地不可达** — 主仓库 origin 是 SSH (`ssh://git@geekssh.glodon.com:7999/dg/gmdos-svc.git`)，但 `.gitmodules` 中 submodule URL 是 HTTPS (`https://geek.glodon.com/scm/dg/gmdos-web.git`)。主仓库没有 HTTPS 凭证，`_submodule_url` 取出的 HTTPS URL 直接 fetch 失败（`could not read Username`）。后果：Step 8.5 输出的 `submodule_status[*].objects_available=false`，所有 subject 字段全 null，AI 仍然要靠外部命令（手动 SSH fetch 或 `git ls-remote`）才能补齐诊断信息。
2. **merge 完成后 submodule 指针未自动 amend** — Step 9.5 `submodule update --init --merge --recursive` 改写了 submodule 工作树，但主仓库的指针（gitlink entry）未自动 `git add`，导致后续需要 AI 手动执行。冲突解决路径下，AI 还要在 `git update-index --cacheinfo` 后 `git commit --no-edit`，整体流程多 1-2 步。
3. **`needs-manual` 诊断信息不够丰富** — 当 source/target 不存在祖先关系时，AI 只能看 SHA 与（缺失的）subject，无法快速判断「哪个更新」「谁合并过」。

本设计针对上述三个问题，分别给出 SSH URL 推导、Step 9.6 自动 amend、`submodule_status` 诊断增强三个方案。

---

## 改动 1：SSH URL 推导（fetch 协议优先级）

### 现状

`_submodule_url()` 在 `merge-branch.sh:389` 仅返回 `.gitmodules` 中的原始 URL（通常是 HTTPS）。主仓库没有 HTTPS 凭证，fetch 失败。

### 设计

新增 `_submodule_ssh_url()` 函数：从主仓库 `origin` SSH URL 推导 submodule 的 SSH URL。

**推导规则**：

主仓 origin 形如 `ssh://git@geekssh.glodon.com:7999/dg/gmdos-svc.git`，分解为：

| 字段 | 取值 |
|------|------|
| protocol | `ssh://` |
| user | `git`（来自 origin user，缺省补 `git`） |
| host:port | `geekssh.glodon.com:7999` |
| parent_dir | `dg`（origin 路径去掉最后一段） |
| sub_name | `.gitmodules` 中 `submodule.<name>` 的 `<name>` |

合成 SSH URL：`ssh://git@geekssh.glodon.com:7999/dg/<sub_name>.git`

**特殊情况**：

- 主仓 origin 是 HTTPS（非 SSH）→ 跳过推导，使用 `.gitmodules` 原 URL
- origin URL 不含 `.git` 后缀 → 兼容（`url[:-4]` 容错）
- path 只剩 1 段（如 `repo.git`）→ parent_dir 为空，构造 `ssh://git@host:port/<sub>.git`

### fetch 优先级（Step 8.5 对象补齐）

```
for each submodule SHA in {base, source, target}:
    if object already local: skip
    else try:
        1. _submodule_ssh_url(submodule_name)        # 推导 SSH
        2. .gitmodules 原 URL                          # HTTPS fallback
    on both fail: classify error (network/auth/url-config)
```

**错误分类**（按 stderr 关键字）：

| 关键字 | 分类 | 提示 |
|--------|------|------|
| `Could not resolve host` | URL 配置错误 | "submodule URL 主机不可达，检查 `.gitmodules` 或网络" |
| `Connection refused` / `timeout` | 网络问题 | "网络/SSH 服务不可达" |
| `could not read Username` / `Permission denied (publickey)` | 凭证问题 | "submodule 凭证缺失：建议 SSH URL 已试过，仍 HTTPS fallback 失败，请配置 SSH key 或凭证" |
| 其他 | 未知 | "submodule fetch 失败：<错误摘要>" |

### 不动 `.gitmodules`

用户明确要求**不修改** `.gitmodules`。SSH URL 仅在脚本运行时推导，不写入任何配置文件。

---

## 改动 2：Step 9.6 合并后自动 amend

### 现状

Step 9.5 `git submodule update --init --merge --recursive` 自动 FF 子模块指针后，工作树中的子模块 HEAD 与 gitlink entry 可能不一致（gitlink 是主仓库 index 里的 160000 条目，update --merge 不会自动改 gitlink）。需 AI 手动 `git add` + 提交。

### 设计

新增 Step 9.6，仅在 `merge_result ∈ {success, already_up_to_date}` 时执行：

```bash
# === Step 9.6: 自动提交 submodule 指针改动 ===
amended_submodules=()
for sm_path in $SUBMODULE_LIST; do
    [ -z "$sm_path" ] && continue
    # 比对 gitlink entry 与子模块当前 HEAD
    gitlink_sha="$(git ls-files --stage "$sm_path" | awk '$1=="160000"{print $2}')"
    worktree_sha="$(git -C "$sm_path" rev-parse HEAD 2>/dev/null || true)"
    if [ -n "$worktree_sha" ] && [ "$gitlink_sha" != "$worktree_sha" ]; then
        git add "$sm_path"
        amended_submodules+=("$sm_path")
    fi
done
if [ ${#amended_submodules[@]} -gt 0 ]; then
    # 安全闸：仅在 merge commit 尚未推送到 origin/<target_branch> 时 amend
    # 已推送时改为独立 commit，避免重写已发布的 commit hash
    target_published="false"
    if git rev-parse --verify "origin/${TARGET_BRANCH}" >/dev/null 2>&1; then
        if ! git merge-base --is-ancestor HEAD "origin/${TARGET_BRANCH}"; then
            # HEAD 不在 origin 上 = 尚未推送
            target_published="false"
        else
            target_published="true"
        fi
    fi
    if [ "${target_published}" = "false" ]; then
        # 未推送：amend 把指针改动合到 merge commit
        git commit --amend --no-edit
        echo "INFO: 子模块指针已合并到 merge commit（amend，未推送安全）：${amended_submodules[*]}"
    else
        # 已推送：独立 commit 保留指针改动，避免重写远端 hash
        git commit --no-edit -m "chore: update submodule pointers after merge"
        echo "INFO: 子模块指针已作为独立 commit（merge commit 已推送，避免重写）：${amended_submodules[*]}"
    fi
fi
```

**安全保证**：

1. **安全闸**：amend 仅在 merge commit 未推送到 origin/<target> 时执行；已推送时降级为独立 commit，**绝不重写已发布的 commit hash**。
2. `git commit --amend --no-edit` 只重写最后一个 commit 的 tree，不动 parent 与 message。merge commit 仍是 merge commit。
3. 仅在 `amended_submodules` 非空时 amend/独立 commit，避免空操作。
4. 不动 stash（与原 merge-branch stash 流程正交）。
5. 失败保护：`git -C <sub> rev-parse HEAD` 在 submodule 未初始化时返回空（已用 `2>/dev/null || true` 兜底），该 submodule 自动跳过；`git add` 对 gitlink 路径几乎不会失败。
6. **不会丢失任何提交**：amend 仅改 HEAD 指向新 tree，所有原 commit 仍在 reflog 可恢复（默认 90 天）。
7. **无破坏性操作全局保证**：
   - 不删除任何分支（不 `git branch -D`、不 `git tag -d`）
   - 不重写已推送的 commit hash（安全闸判定）
   - 不强制 `git push --force` / `git push --force-with-lease`
   - 不 `git reset --hard`（恢复路径走 `git merge --abort`）
   - 不动 stash（与原 merge-branch stash 流程正交）
   - 不写用户工作区文件（仅写主仓库 index / 暂存区）
   - 子模块改动限制在子模块工作区，不影响主仓库以外的任何位置

### 与冲突路径的关系

冲突路径（`merge_result=conflict`）不执行 Step 9.5/9.6。AI 解决冲突后用 `git add` + `git commit --no-edit`（merge-branch skill 已规约）。

---

## 改动 3：`submodule_status` 诊断增强

### 现状

`submodule_status[*]` 当前字段：

```json
{
  "path": "web",
  "base_commit": "f02c3e39...",
  "base_subject": null,
  "source_commit": "b78b939f...",
  "source_subject": null,  // ← 因对象不可达为空
  "target_commit": "1aebeecf...",
  "target_subject": null,
  "objects_available": false,
  "merge_strategy_hint": "needs-manual"
}
```

### 设计

v2 在每个 commit 旁新增 3 个字段：

```json
{
  "source_commit": "b78b939f...",
  "source_subject": "fix：表头深色反压制ruoyi全局!important白底",
  "source_commit_time": "2026-09-11T13:36:11+08:00",
  "source_author": "huazm <huazm@glodon.com>"
}
```

字段含义：

- `*_commit_time`：ISO 8601 格式（`%cI` 占位符），便于 AI 比较新旧
- `*_author`：`%an <%ae>` 格式
- `*_subject`：commit subject（v1 fetch 失败时为空，v2 配合改动 1 后多数情况可填充）

**输出约束**：

- 对象不可达时，三个新字段均为 `null`（与现有 subject 行为一致）
- `jq` 模板同步更新

---

## 改动 4：evals.json 追加用例

v1 已加 id 20/21/22（submodule 对象缺失场景）。v2 追加 4 个用例：

- `id: 23`「submodule URL 是 HTTPS，主仓 origin 是 SSH」— 期望 Step 8.5 推导 SSH URL 并补齐对象，`objects_available=true`，subject 全填充
- `id: 24`「submodule URL 主机不可达」— 期望 WARN 含 "Could not resolve host" 关键字，分类为 URL 配置错误
- `id: 25`「merge 成功且 submodule 指针被 update --merge 改动，且 merge commit 未推送」— 期望 Step 9.6 安全闸判定为「未推送」，自动 `git add` + `git commit --amend --no-edit`，merge commit 包含指针改动
- `id: 26`「merge 成功但 submodule 指针未变」— 期望 Step 9.6 不 amend（无操作），输出明确 "无指针变更"
- `id: 27`「merge 成功但 merge commit 已推送（模拟 origin/<target> 已包含 HEAD）」— 期望 Step 9.6 安全闸判定为「已推送」，降级为独立 commit，绝不 amend

---

## 不做（YAGNI）

- **不写 URL 迁移脚本**（用户已确认不需，submodule URL 保持 HTTPS，脚本运行时推导 SSH）
- **不做共同 descendant 探测**（v1 已通过 ort 策略处理祖先关系；非祖先 case 由 needs-manual + 增强诊断覆盖）
- **不做交互式提问**（用户偏好自动决策 + AI 据诊断判断，交互提问违反 merge-branch 自动合并原则）
- **不改 merge-submodule.sh**（已正确处理子模块内部合并；v1/v2 的 submodule_status 字段已经够 AI 在主仓层面决策）
- **不动 `.gitmodules` / `.git/config`**（用户明确要求 URL 推导而非持久化重写）

---

## 全局硬约束（不可破坏）

### 不动公共 submodule

**判定标准**：submodule path 在 `.gitmodules` 中命名属于**公共/平台类**基础设施的，禁止在主仓库合并过程中**修改其工作区或提交任何改动**。具体规则：

- **业务 submodule**（如 `web`）：可以修改、提交、推送、合并
- **公共/平台 submodule**（如 `devops-lib`、CI/CD 脚本库、共享工具库）：**绝对禁止修改工作区**、**绝对禁止在其内部 commit / push**、**绝对禁止在主仓库 amend 它的指针**

**v2 实现要点**：

1. `merge-branch.sh` 在 submodule 合并前，按 `.gitmodules` 中 submodule name 与内置「公共 submodule 白名单」比对：
   - 白名单：`devops-lib`
   - 命中 → Step 9.5 / 9.6 跳过该 submodule
2. 主仓库的 gitlink entry 保留公共 submodule 的原指针（master 的 `c780ce72` 不动）
3. 合并报告必须明确列出「跳过的公共 submodule：devops-lib」

### 提交不丢失（双重保障）

**主仓库层**：

- 任何已合并到 target 分支的 commit 必须保留在 git history
- `git merge-base --is-ancestor <pre_merge_source_head> HEAD` 验证必须通过
- 任何 amend 仅在未推送时执行；已推送时降级为独立 commit
- 不 `git reset --hard`；不 `git push --force`

**submodule 层**：

- 业务 submodule（web）的 source/target/base 三个 commit 在合并前已存在的，**必须保留**
- submodule 内部合并用 `merge-submodule.sh`，若其内部发生 commit，必须保留到目标分支
- 公共 submodule（devops-lib）绝对禁止内部 commit / push

### 验收标准：合并到 dev 分支

**v2 实施完成后，本地验收步骤**：在 gmdos-svc 仓库跑 `bash ~/.agents/skills/merge-branch/scripts/merge-branch.sh dev`（从 agent-roi-dashboard 合并到 dev）。

**期望结果**：

| 项 | 期望 |
|------|------|
| merge_result | `success`（无冲突）或 `conflict`（冲突由 AI 代劳型解决） |
| `git ls-tree dev web` | 指向 `b78b939f`（与 agent-roi-dashboard 一致） |
| `git ls-tree dev devops-lib` | 与合并前一致（dev 分支原指针，绝不变动） |
| `git show dev -- web` | 包含本次合并的 web 指针更新 |
| merge commit | 存在；message 形如 `Merge branch 'agent-roi-dashboard' into dev` |
| 跳过列表 | 「跳过的公共 submodule：devops-lib」出现在合并报告 |

---

## 验证步骤

1. **真实场景验证（合并到 dev 分支）**（gmdos-svc 仓库）：
   - 在 agent-roi-dashboard 分支
   - 跑 `bash ~/.agents/skills/merge-branch/scripts/merge-branch.sh dev`
   - 期望：JSON `submodule_status[*].objects_available=true`，subject/time/author 全填充
   - 期望：merge commit 存在
   - 期望：merge 后 `git ls-tree dev web` 指向 `b78b939f`
   - 期望：合并报告含「跳过的公共 submodule：devops-lib」
   - 期望：`git ls-tree dev devops-lib` 与合并前一致（devops-lib 指针未变）
2. **错误分类验证**：在 .gitmodules 里临时把 web URL 改成 `https://nonexistent.example.com/x.git`
   - 期望：WARN 含 "Could not resolve host"，分类正确
3. **evals 用例**：跑 id 23-26 用例描述的场景（不需 fixture，纯描述性）
4. **回归测试**：不带 submodule 的合并行为应与 v1 完全一致
5. **commit 消息审查**：merge commit message 保持 git 自动生成（`Merge branch 'agent-roi-dashboard' into dev`），不被 amend 修改
6. **公共 submodule 不被改动**：
   - 合并前 `cd devops-lib && git log -1 --format=%H` 记录原 HEAD
   - 合并后 `cd devops-lib && git log -1 --format=%H` 必须等于原 HEAD
   - `devops-lib` 内部无任何 commit（`git log origin/devops-lib..HEAD` 为空）
   - 主仓库 `git ls-tree dev devops-lib` 与合并前一致

---

## 实施顺序

1. `merge-branch.sh` 改动：
   - 新增 `_submodule_ssh_url()` 函数（紧邻现有 `_submodule_url`）
   - 改写 Step 8.5 fetch 块为协议优先级 + 错误分类
   - 新增 Step 9.6 amend 逻辑
   - `print_status` JSON 增加 `*_commit_time` / `*_author` 字段
2. `SKILL.md` 同步更新：
   - JSON 字段说明补充 v2 新增字段
   - 「submodule 预热机制」段落补充 SSH 协议优先级与错误分类
   - 「注意事项」新增 v2 amend 说明
3. `evals/evals.json` 追加 id 23-26
4. 在 gmdos-svc 跑真实场景验证（不能推送，只看本地合并结果）
5. 测试无误后**不提交**（等用户确认推送）

---

## 关键风险

| 风险 | 对策 |
|------|------|
| SSH URL 推导错误（路径格式异常） | 在推导后用 `git ls-remote <url> HEAD` 做 sanity check；若失败静默 fallback 到 HTTPS |
| amend 改写 merge commit 引发完整性验证失败 | `git merge-base --is-ancestor <pre_merge_source_head> HEAD` 在 amend 后仍成立（amend 不改 parent）；已有合并报告步骤会重新验证 |
| `git -C <sub> rev-parse HEAD` 在未初始化子模块失败 | 用 `2>/dev/null` 吞错，未初始化的 submodule 自动跳过 |
| 时间/作者字段可能泄露敏感信息 | 仅在主仓库层 fetch/commit 信息，无新增敏感数据；与现有 `*_subject` 同样仅显示 author 名字与 email |
| HTTPS fallback 也失败 | 改动 1 的错误分类给出明确提示，AI 仍可据 `merge_strategy_hint` 与 SHA 决策 |
