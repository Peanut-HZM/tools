#!/usr/bin/env bash
set -euo pipefail

# merge-submodule.sh — submodule 同步合并脚本
# 用法：merge-submodule.sh <submodule_path> <source_branch> <target_branch>
# 失败路径自动 restore-workspace.sh；成功/冲突由 AI 在 submodule 目录再跑一次。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

SUBMODULE_PATH="$1"
SOURCE_BRANCH="$2"
TARGET_BRANCH="$3"

SUBMODULE_ERROR=""
SUBMODULE_ORIGINAL_BRANCH=""
SUBMODULE_ORIGINAL_HEAD=""
SUBMODULE_STASH_CREATED=false
SUBMODULE_STASH_SHA=""
SUBMODULE_STASH_RESTORED=false
SUBMODULE_MERGE_RESULT=""
SUBMODULE_CONFLICT_FILES="[]"
SUBMODULE_DIVERGE_INFO="null"
SUB_WORKTREE=""
SUB_STASH_MSG=""
SUB_ENTERED=false

restore_sub_on_abort() {
    if [ "${SUB_ENTERED}" != true ]; then
        return 0
    fi
    if [ -f "$(git rev-parse --git-path merge-branch-restore.json 2>/dev/null || echo /n)" ]; then
        if bash "${SCRIPT_DIR}/restore-workspace.sh" --abort-merge; then
            SUBMODULE_STASH_RESTORED=true
        else
            SUBMODULE_ERROR="${SUBMODULE_ERROR}；submodule 工作区自动恢复失败，请在 ${SUBMODULE_PATH} 内运行 restore-workspace.sh"
        fi
    fi
}

fail_sub() {
    echo "ERROR [submodule ${SUBMODULE_PATH}]: $1" >&2
    SUBMODULE_ERROR="$1"
    restore_sub_on_abort
    print_sub_status
    exit 1
}

print_sub_status() {
    jq -n \
        --arg sp "${SUBMODULE_PATH}" \
        --arg sb "${SOURCE_BRANCH}" \
        --arg tb "${TARGET_BRANCH}" \
        --arg ob "${SUBMODULE_ORIGINAL_BRANCH}" \
        --arg oh "${SUBMODULE_ORIGINAL_HEAD}" \
        --argjson sc "${SUBMODULE_STASH_CREATED}" \
        --argjson srest "${SUBMODULE_STASH_RESTORED}" \
        --arg ss "${SUBMODULE_STASH_SHA}" \
        --arg rcmd "bash ${SCRIPT_DIR}/restore-workspace.sh" \
        --arg mr "${SUBMODULE_MERGE_RESULT}" \
        --argjson cf "${SUBMODULE_CONFLICT_FILES}" \
        --arg err "${SUBMODULE_ERROR}" \
        --argjson di "${SUBMODULE_DIVERGE_INFO}" \
        '{
            submodule_path: $sp,
            source_branch: $sb,
            target_branch: $tb,
            original_branch: $ob,
            original_head: $oh,
            stash_created: $sc,
            stash_restored: $srest,
            stash_sha: $ss,
            restore_cmd: $rcmd,
            merge_result: $mr,
            conflict_files: $cf,
            error: (if $err == "" then null else $err end),
            diverge_info: $di
        }' | sed '1s/^/===SUBMODULE-STATUS===\n/' | sed '$a\
===END-SUBMODULE-STATUS==='
}

# === 校验参数 ===
if [ -z "${SUBMODULE_PATH}" ] || [ -z "${SOURCE_BRANCH}" ] || [ -z "${TARGET_BRANCH}" ]; then
    echo "用法: merge-submodule.sh <submodule_path> <source_branch> <target_branch>" >&2
    exit 1
fi

# === 进入 submodule 目录 ===
if [ ! -d "${SUBMODULE_PATH}/.git" ] && [ ! -f "${SUBMODULE_PATH}/.git" ]; then
    fail_sub "目录 ${SUBMODULE_PATH} 不是一个有效的 git 仓库（submodule）"
fi

cd "${SUBMODULE_PATH}"
SUB_ENTERED=true

# === 记录原分支 ===
SUBMODULE_ORIGINAL_BRANCH="$(git branch --show-current)" || fail_sub "无法获取 submodule 当前分支（detached HEAD？）"
if [ -z "${SUBMODULE_ORIGINAL_BRANCH}" ]; then
    fail_sub "submodule 处于 detached HEAD 状态，无法安全操作"
fi
SUBMODULE_ORIGINAL_HEAD="$(git rev-parse HEAD)"

write_sub_restore_state() {
    local git_dir
    git_dir="$(git rev-parse --git-dir)"
    jq -n \
        --arg ob "${SUBMODULE_ORIGINAL_BRANCH}" \
        --arg oh "${SUBMODULE_ORIGINAL_HEAD}" \
        --argjson sc "${SUBMODULE_STASH_CREATED}" \
        --arg ss "${SUBMODULE_STASH_SHA}" \
        --arg sm "${SUB_STASH_MSG}" \
        --arg inv "${SUB_WORKTREE}" \
        '{
            original_branch: $ob,
            original_head: $oh,
            stash_created: $sc,
            stash_sha: $ss,
            stash_message: $sm,
            inventory: ($inv | split("\n") | map(select(. != "")))
        }' > "${git_dir}/merge-branch-restore.json"
    if [ -n "${SUBMODULE_STASH_SHA}" ]; then
        git update-ref refs/merge-branch/workspace-stash "${SUBMODULE_STASH_SHA}"
    fi
}

if [ -f "$(git rev-parse --git-path merge-branch-restore.json)" ] || git rev-parse --verify refs/merge-branch/workspace-stash >/dev/null 2>&1 || git stash list | grep -q 'auto-stash before submodule merge'; then
    echo "WARN: [submodule ${SUBMODULE_PATH}] 发现未恢复工作区，先 restore" >&2
    bash "${SCRIPT_DIR}/restore-workspace.sh" || fail_sub "submodule 上次工作区未恢复"
fi

# === 工作区检查 & stash ===
SUB_WORKTREE="$(git status --porcelain)"
if [ -n "${SUB_WORKTREE}" ]; then
    SUB_STASH_MSG="auto-stash before submodule merge ${SOURCE_BRANCH} to ${TARGET_BRANCH} at $(date +%s) pid=$$"
    git stash push -u -m "${SUB_STASH_MSG}" >/dev/null || fail_sub "submodule stash 失败"
    SUBMODULE_STASH_CREATED=true
    SUBMODULE_STASH_SHA="$(git rev-parse stash@{0})"
fi
write_sub_restore_state

# === fetch ===
git fetch origin >/dev/null 2>&1 || fail_sub "submodule fetch 失败"

# === 辅助：检查远程分支 ===
remote_has_branch() {
    git ls-remote --exit-code --heads origin "$1" >/dev/null 2>&1
}

# === 同步 source 分支 ===
if ! remote_has_branch "${SOURCE_BRANCH}"; then
    fail_sub "远程没有分支 ${SOURCE_BRANCH}（source）"
fi

if git show-ref --verify --quiet "refs/heads/${SOURCE_BRANCH}"; then
    git checkout "${SOURCE_BRANCH}" >/dev/null || fail_sub "checkout ${SOURCE_BRANCH} 失败"
    if ! git pull --ff-only origin "${SOURCE_BRANCH}" >/dev/null 2>&1; then
        fail_sub "submodule ${SOURCE_BRANCH} 本地与远程分叉，无法快进同步"
    fi
else
    git checkout -b "${SOURCE_BRANCH}" --track "origin/${SOURCE_BRANCH}" >/dev/null || fail_sub "创建跟踪分支 ${SOURCE_BRANCH} 失败"
fi

# === 同步 target 分支 ===
if ! remote_has_branch "${TARGET_BRANCH}"; then
    fail_sub "远程没有分支 ${TARGET_BRANCH}（target）"
fi

if git show-ref --verify --quiet "refs/heads/${TARGET_BRANCH}"; then
    git checkout "${TARGET_BRANCH}" >/dev/null || fail_sub "checkout ${TARGET_BRANCH} 失败"
    if ! git pull --ff-only origin "${TARGET_BRANCH}" >/dev/null 2>&1; then
        MB="$(git merge-base "${TARGET_BRANCH}" "origin/${TARGET_BRANCH}")"
        LH="$(git rev-parse "${TARGET_BRANCH}")"
        RH="$(git rev-parse "origin/${TARGET_BRANCH}")"
        LOC="$(git rev-list "${MB}..${LH}" --count)"
        REM="$(git rev-list "${MB}..${RH}" --count)"
        if [ "${LOC}" -gt 0 ] && [ "${REM}" -gt 0 ]; then
            LOC_LIST="$(git log --format="%h %s" "${MB}..${LH}")"
            REM_LIST="$(git log --format="%h %s" "${MB}..${RH}")"
            SUBMODULE_DIVERGE_INFO=$(jq -n \
                --arg lo "${LOC_LIST}" \
                --arg ro "${REM_LIST}" \
                '{local_only: ($lo | split("\n") | map(select(. != ""))), remote_only: ($ro | split("\n") | map(select(. != "")))}')
            SUBMODULE_ERROR="submodule target 本地与远程分叉"
            restore_sub_on_abort
            print_sub_status
            exit 2
        else
            fail_sub "submodule ${TARGET_BRANCH} 无法快进同步"
        fi
    fi
else
    git checkout -b "${TARGET_BRANCH}" --track "origin/${TARGET_BRANCH}" >/dev/null || fail_sub "创建跟踪分支 ${TARGET_BRANCH} 失败"
fi

# === 执行 merge ===
set +e
MERGE_OUTPUT="$(LC_ALL=C git merge "${SOURCE_BRANCH}" --no-edit 2>&1)"
MERGE_EXIT=$?
set -e

if [ ${MERGE_EXIT} -eq 0 ]; then
    if echo "${MERGE_OUTPUT}" | grep -q "Already up to date"; then
        SUBMODULE_MERGE_RESULT="already_up_to_date"
    else
        SUBMODULE_MERGE_RESULT="success"
    fi
else
    if git ls-files -u | grep -q .; then
        SUBMODULE_MERGE_RESULT="conflict"
        SUBMODULE_CONFLICT_FILES="$(git ls-files -u | cut -f2 | sort -u | jq -R -s 'split("\n") | map(select(. != ""))')"
    else
        fail_sub "merge 失败但非冲突：${MERGE_OUTPUT}"
    fi
fi

# === 输出状态 ===
print_sub_status
exit 0
