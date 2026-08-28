#!/usr/bin/env bash
set -euo pipefail

# merge-branch.sh — 确定性操作脚本
# 用法：merge-branch.sh [source] target
#   1 个参数：source = 当前分支，target = 参数
#   2 个参数：source = 第一个参数，target = 第二个参数
#
# 工作区：切分支前 stash -u，SHA 写入 refs/merge-branch/workspace-stash。
# 失败/分叉路径由本脚本调用 restore-workspace.sh 自动恢复。
# 成功/冲突路径停留在 target，AI 结束后必须再跑 restore-workspace.sh。
# 禁止 checkout -f / reset --hard。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 状态变量（最终输出为 JSON）
SOURCE_BRANCH=""
TARGET_BRANCH=""
SOURCE_FROM=""
ORIGINAL_BRANCH=""
ORIGINAL_HEAD=""
STASH_CREATED=false
STASH_REF=""
STASH_SHA=""
STASH_RESTORED=false
TARGET_BASELINE=""
MERGE_RESULT=""
ERROR_MSG=""
DIVERGE_INFO="null"
CONFLICT_FILES="[]"
SUBMODULES="[]"
PRE_MERGE_SOURCE_HEAD=""
PRE_MERGE_TARGET_HEAD=""
TARGET_REWRITTEN_FROM=""
WORKTREE_STATUS=""

# 失败/分叉：先恢复原分支+stash，再输出 JSON。成功路径不在这里恢复。
restore_on_abort() {
    if [ ! -f "${SCRIPT_DIR}/restore-workspace.sh" ]; then
        return 0
    fi
    local git_path
    git_path="$(git rev-parse --git-path merge-branch-restore.json 2>/dev/null || true)"
    if [ -n "${git_path}" ] && [ -f "${git_path}" ]; then
        if bash "${SCRIPT_DIR}/restore-workspace.sh" --abort-merge; then
            STASH_RESTORED=true
        else
            ERROR_MSG="${ERROR_MSG}；自动恢复工作区失败，请立即运行: bash ${SCRIPT_DIR}/restore-workspace.sh --abort-merge"
        fi
    fi
}

# 辅助：输出错误信息到 stderr，exit 1
fail() {
    echo "ERROR: $1" >&2
    ERROR_MSG="$1"
    restore_on_abort
    print_status
    exit 1
}

# 辅助：输出状态 JSON（用 jq 保证合法 JSON，避免字符串拼接破坏转义）
print_status() {
    jq -n \
        --arg sb "${SOURCE_BRANCH}" \
        --arg tb "${TARGET_BRANCH}" \
        --arg sf "${SOURCE_FROM}" \
        --arg ob "${ORIGINAL_BRANCH}" \
        --arg oh "${ORIGINAL_HEAD}" \
        --argjson sc "${STASH_CREATED}" \
        --argjson srest "${STASH_RESTORED}" \
        --arg sr "${STASH_REF}" \
        --arg ss "${STASH_SHA}" \
        --arg rcmd "bash ${SCRIPT_DIR}/restore-workspace.sh" \
        --arg tbl "${TARGET_BASELINE}" \
        --arg mr "${MERGE_RESULT}" \
        --argjson cf "${CONFLICT_FILES}" \
        --arg err "${ERROR_MSG}" \
        --argjson di "${DIVERGE_INFO}" \
        --argjson subs "${SUBMODULES}" \
        --arg psh "${PRE_MERGE_SOURCE_HEAD}" \
        --arg pth "${PRE_MERGE_TARGET_HEAD}" \
        --arg trf "${TARGET_REWRITTEN_FROM}" \
        '{
            source_branch: $sb,
            target_branch: $tb,
            source_from: $sf,
            original_branch: $ob,
            original_head: $oh,
            stash_created: $sc,
            stash_restored: $srest,
            stash_ref: $sr,
            stash_sha: $ss,
            restore_cmd: $rcmd,
            target_baseline: $tbl,
            merge_result: $mr,
            conflict_files: $cf,
            error: (if $err == "" then null else $err end),
            diverge_info: $di,
            submodules: $subs,
            pre_merge_source_head: $psh,
            pre_merge_target_head: $pth,
            target_rewritten_from: (if $trf == "" then null else $trf end)
        }' | sed '1s/^/===MERGE-STATUS===\n/' | sed '$a\
===END-STATUS==='
}

# === Step 1: 参数解析 ===
if [ $# -eq 1 ]; then
    TARGET_BRANCH="$1"
    SOURCE_FROM="current"
elif [ $# -eq 2 ]; then
    SOURCE_BRANCH="$1"
    TARGET_BRANCH="$2"
    SOURCE_FROM="explicit"
else
    echo "用法: merge-branch.sh [source] target" >&2
    echo "  1 个参数: source=当前分支, target=参数" >&2
    echo "  2 个参数: source=第一个参数, target=第二个参数" >&2
    exit 1
fi

# 校验 source != target（1 个参数时由 current 推导，理论上不会相同，但仍检查）
if [ "${SOURCE_FROM}" = "explicit" ] && [ "${SOURCE_BRANCH}" = "${TARGET_BRANCH}" ]; then
    fail "源分支与目标分支不能相同：${SOURCE_BRANCH}"
fi

# 校验不在非法字符（分支名基本合法性）
if [[ ! "${TARGET_BRANCH}" =~ ^[a-zA-Z0-9._/@-]+$ ]]; then
    fail "目标分支名非法：${TARGET_BRANCH}"
fi
if [ "${SOURCE_FROM}" = "explicit" ] && [[ ! "${SOURCE_BRANCH}" =~ ^[a-zA-Z0-9._/@-]+$ ]]; then
    fail "源分支名非法：${SOURCE_BRANCH}"
fi

# === Step 2: 当前分支获取（单参数模式） ===
if [ "${SOURCE_FROM}" = "current" ]; then
    ORIGINAL_BRANCH="$(git branch --show-current)" || fail "无法获取当前分支（可能处于 detached HEAD）"
    if [ -z "${ORIGINAL_BRANCH}" ]; then
        fail "当前不在任何分支上（detached HEAD）"
    fi
    SOURCE_BRANCH="${ORIGINAL_BRANCH}"
else
    ORIGINAL_BRANCH="$(git branch --show-current || true)"
fi

# === 前置检查：必须在 git 仓库内 ===
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    fail "当前目录不是 git 仓库"
fi

write_restore_state() {
    local git_dir
    git_dir="$(git rev-parse --git-dir)"
    jq -n \
        --arg ob "${ORIGINAL_BRANCH}" \
        --arg oh "${ORIGINAL_HEAD}" \
        --argjson sc "${STASH_CREATED}" \
        --arg ss "${STASH_SHA}" \
        --arg sm "${STASH_MSG:-}" \
        --arg inv "${WORKTREE_STATUS}" \
        '{
            original_branch: $ob,
            original_head: $oh,
            stash_created: $sc,
            stash_sha: $ss,
            stash_message: $sm,
            inventory: ($inv | split("\n") | map(select(. != "")))
        }' > "${git_dir}/merge-branch-restore.json"
    if [ -n "${STASH_SHA}" ]; then
        git update-ref refs/merge-branch/workspace-stash "${STASH_SHA}"
    fi
}

# 上次合并若没恢复工作区：先自愈恢复，再拒绝带着遗留 stash 开新一轮
heal_leftover_workspace() {
    local state_file ref_exists leftover_stash
    state_file="$(git rev-parse --git-path merge-branch-restore.json)"
    ref_exists=false
    leftover_stash=false
    git rev-parse --verify refs/merge-branch/workspace-stash >/dev/null 2>&1 && ref_exists=true
    git stash list | grep -q 'auto-stash before merge-branch' && leftover_stash=true
    if [ -f "${state_file}" ] || [ "${ref_exists}" = true ] || [ "${leftover_stash}" = true ]; then
        echo "WARN: 发现上次未恢复的 merge-branch 工作区，先执行 restore-workspace.sh" >&2
        bash "${SCRIPT_DIR}/restore-workspace.sh" || fail "上次工作区恢复失败。请手动运行: bash ${SCRIPT_DIR}/restore-workspace.sh"
    fi
    if [ -f "${state_file}" ] || git rev-parse --verify refs/merge-branch/workspace-stash >/dev/null 2>&1 || git stash list | grep -q 'auto-stash before merge-branch'; then
        fail "工作区遗留仍在，拒绝开始新合并以免再次藏起文件。请先: bash ${SCRIPT_DIR}/restore-workspace.sh"
    fi
}
heal_leftover_workspace

ORIGINAL_HEAD="$(git rev-parse HEAD)"

# === Step 3: 工作区检查 ===
WORKTREE_STATUS="$(git status --porcelain)"

# === Step 4: 必要时 stash（含未跟踪文件）；用 SHA 备份，禁止依赖 stash@{0} ===
if [ -n "${WORKTREE_STATUS}" ]; then
    STASH_MSG="auto-stash before merge-branch ${SOURCE_BRANCH} to ${TARGET_BRANCH} at $(date +%s) pid=$$"
    git stash push -u -m "${STASH_MSG}" >/dev/null || fail "git stash 失败"
    STASH_CREATED=true
    STASH_REF="$(git stash list | head -n1 | cut -d: -f1)"
    STASH_SHA="$(git rev-parse stash@{0})"
fi
write_restore_state

# === Step 5: fetch 远程 ===
git fetch origin >/dev/null 2>&1 || fail "git fetch origin 失败（网络或权限问题）"
# 同时 fetch 所有 submodule
if [ -f .gitmodules ]; then
    git submodule foreach --recursive 'git fetch origin >/dev/null 2>&1 || true' >/dev/null 2>&1 || true
fi

# 辅助：检查远程是否有某分支
remote_has_branch() {
    git ls-remote --exit-code --heads origin "$1" >/dev/null 2>&1
}

# 辅助：列出与 wanted 编辑距离 <=1 的远程分支（用于拼写提示）
suggest_similar_remote_branches() {
    local wanted="$1"
    git ls-remote --heads origin 2>/dev/null | awk '{print $2}' | sed 's#^refs/heads/##' | python3 -c '
import sys
wanted = sys.argv[1]
names = [line.strip() for line in sys.stdin if line.strip()]

def dist(a, b):
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return 99
    prev = list(range(lb + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(prev[j] + 1, curr[j-1] + 1, prev[j-1] + (ca != cb)))
        prev = curr
    return prev[lb]

hits = [n for n in names if dist(wanted, n) <= 2 and n != wanted]
print(", ".join(hits[:8]))
' "${wanted}" 2>/dev/null || true
}

# === Step 5.4: 纠正 LLM 把 development 主干误打成 destination 缩写 ===
# 用户要的是三字母 d-e-v；模型常写成四字母 d-e-s-t。脚本在远程没有后者、但有前者时纠正。
DEV_NAME="$(printf '%s%s%s' d e v)"
DEST_NAME="$(printf '%s%s%s%s' d e s t)"
if [ "${TARGET_BRANCH}" = "${DEST_NAME}" ]; then
    if ! remote_has_branch "${DEST_NAME}" && remote_has_branch "${DEV_NAME}"; then
        echo "WARN: 收到目标分支 '${DEST_NAME}'（四字母 d-e-s-t，destination）。远程不存在，但存在 '${DEV_NAME}'（三字母 d-e-v，development）。已纠正为 '${DEV_NAME}'。" >&2
        TARGET_REWRITTEN_FROM="${TARGET_BRANCH}"
        TARGET_BRANCH="${DEV_NAME}"
    fi
fi

# === Step 5.5: 检测 submodule ===
if [ -f .gitmodules ]; then
    SUBMODULE_LIST="$(git config --file .gitmodules --get-regexp 'submodule\..*\.path' | awk '{print $2}' | sort)"
    if [ -n "${SUBMODULE_LIST}" ]; then
        SUBMODULES="$(echo "${SUBMODULE_LIST}" | jq -R -s 'split("\n") | map(select(. != ""))')"
    fi
fi


# 纠正后再校验 source != target（单参数模式下 source 此时已确定）
if [ -n "${SOURCE_BRANCH}" ] && [ "${SOURCE_BRANCH}" = "${TARGET_BRANCH}" ]; then
    fail "源分支与目标分支不能相同：${SOURCE_BRANCH}"
fi

# === Step 6: 同步 source（ff-only 失败直接 fail） ===
if ! remote_has_branch "${SOURCE_BRANCH}"; then
    SIMILAR="$(suggest_similar_remote_branches "${SOURCE_BRANCH}")"
    if [ -n "${SIMILAR}" ]; then
        fail "远程仓库没有分支 ${SOURCE_BRANCH}（source）。相近远程分支: ${SIMILAR}"
    fi
    fail "远程仓库没有分支 ${SOURCE_BRANCH}（source，请检查拼写）"
fi

if git show-ref --verify --quiet "refs/heads/${SOURCE_BRANCH}"; then
    git checkout "${SOURCE_BRANCH}" >/dev/null || fail "git checkout ${SOURCE_BRANCH} 失败（未使用 --force）"
    if ! git pull --ff-only origin "${SOURCE_BRANCH}" >/dev/null 2>&1; then
        fail "本地 ${SOURCE_BRANCH} 与远程分叉，无法快进同步（source）。请先处理本地未推送的提交"
    fi
else
    git checkout -b "${SOURCE_BRANCH}" --track "origin/${SOURCE_BRANCH}" >/dev/null || fail "创建跟踪分支 ${SOURCE_BRANCH} 失败"
fi

# 记录 source 同步后的 HEAD（用于后续完整性校验）
PRE_MERGE_SOURCE_HEAD="$(git rev-parse "${SOURCE_BRANCH}")"

# === Step 7: 同步 target（ff-only 失败时分叉检查 → exit 2） ===
if ! remote_has_branch "${TARGET_BRANCH}"; then
    SIMILAR="$(suggest_similar_remote_branches "${TARGET_BRANCH}")"
    if [ -n "${SIMILAR}" ]; then
        fail "远程仓库没有分支 ${TARGET_BRANCH}（target）。相近远程分支: ${SIMILAR}"
    fi
    fail "远程仓库没有分支 ${TARGET_BRANCH}（target，请检查拼写）"
fi

if git show-ref --verify --quiet "refs/heads/${TARGET_BRANCH}"; then
    git checkout "${TARGET_BRANCH}" >/dev/null || fail "git checkout ${TARGET_BRANCH} 失败（未使用 --force）"
    if ! git pull --ff-only origin "${TARGET_BRANCH}" >/dev/null 2>&1; then
        # ff-only 失败 → 判断分叉
        MB="$(git merge-base "${TARGET_BRANCH}" "origin/${TARGET_BRANCH}")"
        LH="$(git rev-parse "${TARGET_BRANCH}")"
        RH="$(git rev-parse "origin/${TARGET_BRANCH}")"
        LOC="$(git rev-list "${MB}..${LH}" --count)"
        REM="$(git rev-list "${MB}..${RH}" --count)"
        if [ "${LOC}" -gt 0 ] && [ "${REM}" -gt 0 ]; then
            # 双方都有对方没有的提交 = 分叉，exit 2
            LOC_LIST="$(git log --format="%h %s" "${MB}..${LH}")"
            REM_LIST="$(git log --format="%h %s" "${MB}..${RH}")"
            DIVERGE_INFO=$(jq -n \
                --arg lo "${LOC_LIST}" \
                --arg ro "${REM_LIST}" \
                '{
                    local_only: ($lo | split("\n") | map(select(. != ""))),
                    remote_only: ($ro | split("\n") | map(select(. != "")))
                }')
            ERROR_MSG="target 分支本地与远程分叉"
            restore_on_abort
            print_status
            exit 2
        else
            fail "本地 ${TARGET_BRANCH} 与远程无法快进同步"
        fi
    fi
else
    git checkout -b "${TARGET_BRANCH}" --track "origin/${TARGET_BRANCH}" >/dev/null || fail "创建跟踪分支 ${TARGET_BRANCH} 失败"
fi

# === Step 8: 记录 target baseline（合并前） ===
TARGET_BASELINE="$(git rev-parse "${TARGET_BRANCH}")"
PRE_MERGE_TARGET_HEAD="${TARGET_BASELINE}"

# === Step 9: 执行 merge（当前在 target 分支上） ===
set +e
MERGE_OUTPUT="$(LC_ALL=C git merge "${SOURCE_BRANCH}" --no-edit 2>&1)"
MERGE_EXIT=$?
set -e

if [ ${MERGE_EXIT} -eq 0 ]; then
    # 合并成功（可能是 fast-forward 或 merge commit，也可能是 already-up-to-date）
    if echo "${MERGE_OUTPUT}" | grep -q "Already up to date"; then
        MERGE_RESULT="already_up_to_date"
    else
        MERGE_RESULT="success"
    fi
    CONFLICT_FILES="[]"
else
    # 检查是否是冲突
    if git ls-files -u | grep -q .; then
        MERGE_RESULT="conflict"
        # 列出冲突文件（去重）
        CONFLICT_FILES="$(git ls-files -u | cut -f2 | sort -u | jq -R -s 'split("\n") | map(select(. != ""))')"
    else
        fail "git merge 失败但非冲突：${MERGE_OUTPUT}"
    fi
fi

# === Step 10: 输出状态 JSON ===
print_status
exit 0
