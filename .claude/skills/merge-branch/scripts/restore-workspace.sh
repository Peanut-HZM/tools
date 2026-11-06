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

# 应用 stash；返回 0=成功/软失败（untracked-only），1=tracked 文件真正冲突
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
    if [ ${APPLY_EXIT} -eq 0 ]; then
        return 0
    fi
    # stash apply 失败 → 区分 untracked-only 冲突 vs tracked 文件冲突
    if echo "${APPLY_OUT}" | grep -q 'CONFLICT'; then
        echo "ERROR: stash apply 存在 tracked 文件冲突，需手动解决" >&2
        echo "${APPLY_OUT}" >&2
        return 1
    fi
    if echo "${APPLY_OUT}" | grep -q 'already exists, no checkout'; then
        # untracked 文件已存在 → 软失败，由后续 check_missing_files 判定
        echo "WARN: git stash apply 因 untracked 文件已存在而报告失败（非真正错误）" >&2
        return 0
    fi
    # 其他未知失败
    echo "ERROR: git stash apply 未知失败" >&2
    echo "${APPLY_OUT}" >&2
    return 1
}

# 检查 inventory 中的文件是否都在磁盘上；返回 0=完整，1=有缺失
check_missing_files() {
    local missing
    missing="$(python3 -c '
import json, os, re, sys
inv = json.loads(sys.argv[1])
missing = []

def decode_git_path(s):
    """解码 git status --porcelain 中的路径（八进制转义 + 引号包裹）"""
    if s.startswith("\"") and s.endswith("\""):
        s = s[1:-1]
        # git 用 \\NNN 八进制转义非 ASCII 字节
        def _repl(m):
            return bytes([int(m.group(1), 8)])
        return re.sub(rb"\\([0-7]{3})", _repl, s.encode()).decode("utf-8", errors="replace")
    return s

for row in inv:
    line = row.rstrip("\n")
    if len(line) < 4:
        continue
    code = line[:2]
    path = decode_git_path(line[3:])
    # 工作区删除记录：文件本就不该存在
    if code.strip() == "D":
        continue
    # CONFLICT 状态码（UU/AA/DD/AU/UA/DU/UD）：文件存在但需手动解决
    stripped = code.strip()
    if stripped in ("UU", "AA", "DD", "AU", "UA", "DU", "UD"):
        continue
    if not os.path.lexists(path):
        missing.append(path)
print("\n".join(missing))
' "${INVENTORY_JSON}" 2>/dev/null || true)"
    if [ -n "${missing}" ]; then
        echo "ERROR: 恢复后仍缺失以下文件（stash 未 drop，可重试）：" >&2
        echo "${missing}" >&2
        return 1
    fi
    return 0
}

# 检查 inventory 是否只有 untracked (??) 条目
inventory_has_only_untracked() {
    [ "${INVENTORY_JSON}" = "[]" ] && return 1
    python3 -c '
import json, sys
inv = json.loads(sys.argv[1])
for row in inv:
    line = row.rstrip("\n")
    if len(line) < 4: continue
    if line[:2].strip() != "??":
        sys.exit(1)
sys.exit(0)
' "${INVENTORY_JSON}" 2>/dev/null
}

if [ "${STASH_CREATED}" = true ] && [ -n "${STASH_SHA}" ]; then
    apply_stash "${STASH_SHA}" || exit 1
fi

check_missing_files || exit 1

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
