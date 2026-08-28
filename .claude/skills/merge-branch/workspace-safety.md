# 工作区与提交零丢失

merge-branch 切 `dev`/`master` 前会 `git stash push -u`（**含未跟踪文件**）。若切回原分支后不恢复，工作区会变成干净的，看起来像文件被删。这是本技能必须防止的事故。

## HARD GATE

所有路径的**最后一步**必须运行（主仓工作区）：

```bash
bash skills/merge-branch/scripts/restore-workspace.sh
```

submodule 处理完后，在**该 submodule 目录内**再跑一次同一命令。

**禁止**用 `git checkout <original>` + 可选 `stash pop` 凑合：

- `stash pop` 会 pop 错条目（连续合 dest 再合 master 时，第二次工作区已干净，第一次 stash 被遗忘）
- 报告 ✅ 但未跑 `restore-workspace.sh` = 技能执行失败

冲突未结束时（存在 `MERGE_HEAD`）脚本会拒绝切走。先 `git add` + `git commit --no-edit`，或用户明确要求后 `git merge --abort`。

## 脚本会做什么

| 时机 | 行为 |
|------|------|
| 新合并开始 | 若发现上次 json / `refs/merge-branch/workspace-stash` / 遗留 stash，先自愈恢复，恢复不了则拒绝开跑 |
| stash | `-u` 含未跟踪；记录 SHA 到 `refs/merge-branch/workspace-stash` 和 `.git/merge-branch-restore.json` |
| 失败 / 分叉 exit 1·2 | 脚本自己 `--abort-merge` 并恢复原分支+文件 |
| 成功 / 已是最新 / 冲突已提交 | AI 在 push 之后必须再跑 restore 脚本 |
| 恢复 | `git stash apply <sha>`，按 inventory 核对文件存在，**通过后才 drop** |

## 绝对禁止

- `git checkout -f` / `git checkout --force`
- `git reset --hard`（分叉时只是**建议用户**的选项，技能不得代执行）
- 验证通过前 `git stash drop`
- 改写 / 删除 source 分支
- rebase source 分支
- 完整性验证失败后仍 push

## 提交完整性

push 前：

```bash
git merge-base --is-ancestor <pre_merge_source_head> HEAD
```

切回后：`original_head` 必须仍是当前 `original_branch` 的祖先（允许 source 被 ff-only 快进，禁止回退）。

## JSON 字段

- `stash_created` / `stash_sha` / `stash_restored`
- `restore_cmd`：直接复制执行
- `original_branch` / `original_head`
