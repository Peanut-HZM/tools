#!/usr/bin/env bash
set -euo pipefail

# restore-workspace.sh — 切回原分支并按 SHA 恢复 merge-branch stash（含未跟踪文件）
# 禁止：git checkout -f、git reset --hard、验证通过前 git stash drop
#
# 用法：
#   bash restore-workspace.sh [--abort-merge]
# 读取 $(git rev-parse --git-dir)/merge-branch-restore.json
# 以及 refs/merge-branch/workspace-stash 作为 stash 备份。

ABORT_MERGE=false
if [ "${1:-}" = "--abort-merge" ]; then
    ABORT_MERGE=true
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ERROR: 当前目录不是 git 仓库" >&2
    exit 1
fi

GIT_DIR="$(git rev-parse --git-dir)"
STATE_FILE="${GIT_DIR}/merge-branch-restore.json"

ORIGINAL_BRANCH=""
ORIGINAL_HEAD=""
STASH_CREATED=false
STASH_SHA=""
INVENTORY_JSON="[]"

if [ -f "${STATE_FILE}" ]; then
    ORIGINAL_BRANCH="$(jq -r '.original_branch // ""' "${STATE_FILE}")"
    ORIGINAL_HEAD="$(jq -r '.original_head // ""' "${STATE_FILE}")"
    STASH_CREATED="$(jq -r '.stash_created // false' "${STATE_FILE}")"
    STASH_SHA="$(jq -r '.stash_sha // ""' "${STATE_FILE}")"
    INVENTORY_JSON="$(jq -c '.inventory // []' "${STATE_FILE}")"
fi

if [ -z "${STASH_SHA}" ] && git rev-parse --verify refs/merge-branch/workspace-stash >/dev/null 2>&1; then
    STASH_SHA="$(git rev-parse refs/merge-branch/workspace-stash)"
    STASH_CREATED=true
fi

# 兼容旧事故：只有 stash list 条目、没有 json（AI 切回原分支后忘了 pop）
if [ -z "${ORIGINAL_BRANCH}" ]; then
        LEFTOVER_LINE="$(git stash list | grep -E 'auto-stash before (merge-branch|submodule merge)' | head -n1 || true)"
        if [ -n "${LEFTOVER_LINE}" ]; then
            ORIGINAL_BRANCH="$(git branch --show-current || true)"
            STASH_CREATED=true
            STASH_SHA="$(git stash list --format='%gd %H %s' | awk '/auto-stash before (merge-branch|submodule merge)/ { print $2; exit }')"
        echo "WARN: 无 restore json，按 stash 列表恢复 merge-branch 工作区 ${STASH_SHA}" >&2
    fi
fi

if [ -z "${ORIGINAL_BRANCH}" ]; then
    echo "INFO: 无待恢复状态（无 merge-branch-restore.json / 遗留 stash），跳过" >&2
    exit 0
fi

# 未结束的 merge：默认拒绝切走，避免弄丢冲突文件。失败回退路径可 --abort-merge。
if [ -f "${GIT_DIR}/MERGE_HEAD" ]; then
    if [ "${ABORT_MERGE}" = true ]; then
        git merge --abort || {
            echo "ERROR: git merge --abort 失败，拒绝切分支以免丢失冲突文件" >&2
            exit 1
        }
    else
        echo "ERROR: 合并冲突尚未结束（存在 MERGE_HEAD）。先完成 commit 或 git merge --abort，再恢复工作区。" >&2
        exit 1
    fi
fi

# 禁止 -f：工作区若有不属于「待恢复 stash」的改动，让 checkout 自然失败
if ! git checkout "${ORIGINAL_BRANCH}"; then
    echo "ERROR: 切回 ${ORIGINAL_BRANCH} 失败（未使用 --force）。请勿 reset --hard。处理工作区后再跑本脚本。" >&2
    exit 1
fi

# original 分支提交：只允许快进（source 同步时 ff-only），禁止被回退
if [ -n "${ORIGINAL_HEAD}" ] && git rev-parse --verify "${ORIGINAL_HEAD}" >/dev/null 2>&1; then
    if ! git merge-base --is-ancestor "${ORIGINAL_HEAD}" HEAD; then
        echo "ERROR: ${ORIGINAL_BRANCH} 的 HEAD 不再包含开始合并时的提交 ${ORIGINAL_HEAD}，拒绝继续以免丢失提交" >&2
        exit 1
    fi
fi

apply_stash() {
    local sha="$1"
    if [ -z "${sha}" ] || [ "${sha}" = "null" ]; then
        return 0
    fi
    if ! git cat-file -e "${sha}^{commit}" 2>/dev/null; then
        echo "ERROR: stash commit ${sha} 不存在，无法恢复工作区文件" >&2
        return 1
    fi
    set +e
    APPLY_OUT="$(git stash apply --index "${sha}" 2>&1)"
    APPLY_EXIT=$?
    set -e
    if [ ${APPLY_EXIT} -ne 0 ]; then
        echo "WARN: git stash apply 未干净成功：${APPLY_OUT}" >&2
        if [ "${INVENTORY_JSON}" = "[]" ]; then
            return 1
        fi
        return 0
    fi
    return 0
}

if [ "${STASH_CREATED}" = true ] && [ -n "${STASH_SHA}" ]; then
    apply_stash "${STASH_SHA}" || exit 1
fi

MISSING="$(python3 -c '
import json, os, sys
inv = json.loads(sys.argv[1])
missing = []
for row in inv:
    line = row.rstrip("\n")
    if len(line) < 4:
        continue
    code = line[:2]
    path = line[3:]
    if path.startswith("\"") and path.endswith("\""):
        path = bytes(path[1:-1], "utf-8").decode("unicode_escape")
    # 工作区删除记录：文件本就不该存在
    if code.strip() == "D":
        continue
    if not os.path.lexists(path):
        missing.append(path)
print("\n".join(missing))
' "${INVENTORY_JSON}")"

if [ -n "${MISSING}" ]; then
    echo "ERROR: 恢复后仍缺失以下文件（stash 未 drop，可重试）：" >&2
    echo "${MISSING}" >&2
    exit 1
fi

# 验证通过才 drop 对应 stash，绝不 drop 其它条目
if [ -n "${STASH_SHA}" ]; then
    STASH_IDX="$(git stash list --format='%gd %H' | awk -v s="${STASH_SHA}" '$2 == s { print $1; exit }')"
    if [ -n "${STASH_IDX}" ]; then
        git stash drop "${STASH_IDX}" >/dev/null
    fi
    git update-ref -d refs/merge-branch/workspace-stash 2>/dev/null || true
fi

rm -f "${STATE_FILE}"

echo "OK: 已切回 ${ORIGINAL_BRANCH} 并恢复工作区文件（inventory=$(jq -r 'length' <<<"${INVENTORY_JSON}"))"
exit 0
