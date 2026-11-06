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

# v3：远端认证自愈（fetch/push 失败时按 ~/.ssh/config IdentityFile 显式重试）与错误分类
# shellcheck source=lib-git-auth.sh
source "${SCRIPT_DIR}/lib-git-auth.sh"

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
SOURCE_FULLY_MERGED=true
SOURCE_MERGE_ERR=""
ERROR_MSG=""
DIVERGE_INFO="null"
CONFLICT_FILES="[]"
SUBMODULES="[]"
PRE_MERGE_SOURCE_HEAD=""
PRE_MERGE_TARGET_HEAD=""
TARGET_REWRITTEN_FROM=""
WORKTREE_STATUS=""
# v3：子模块强制同步结果与总闸门（见 Step 9.7）
SUBMODULE_SYNC="[]"
SUBMODULE_GATE_ALL_PASS=true
# 业务子模块指针分歧已在临时 worktree 合并时为 true：禁止再用工作区 HEAD 覆盖索引指针
AUTO_RESOLVED_GITLINKS=false
GITLINK_CONTENT_CONFLICTS="[]"

# 公共 submodule 白名单（绝对不动：禁止修改其工作区 / commit / push / amend 指针）
# 业务 submodule（web）可以正常合并；公共 submodule（devops-lib 等）必须保留原指针
PUBLIC_SUBMODULES="devops-lib"

# 辅助：判断 submodule 是否为公共/平台类
_is_public_submodule() {
    local sub_name="$1"
    [ -z "${sub_name}" ] && return 1
    echo "${PUBLIC_SUBMODULES}" | grep -qw "${sub_name}"
}

# 本地分支若是远端的祖先，快进到刚刚 fetch 的 origin/<branch>。
# 当前正检出该分支且工作区不干净时不动它，避免碰未提交文件。
_ff_local_branch_to_origin() {
    local path="$1" branch="$2" current
    git -C "${path}" show-ref --verify --quiet "refs/remotes/origin/${branch}" || return 0
    git -C "${path}" show-ref --verify --quiet "refs/heads/${branch}" || return 0
    git -C "${path}" merge-base --is-ancestor "refs/heads/${branch}" "refs/remotes/origin/${branch}" 2>/dev/null || return 0
    current="$(git -C "${path}" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
    if [ "${current}" = "${branch}" ]; then
        if [ -z "$(git -C "${path}" status --porcelain 2>/dev/null)" ]; then
            git -C "${path}" merge --ff-only "refs/remotes/origin/${branch}" >/dev/null 2>&1 || true
        fi
    else
        git -C "${path}" update-ref "refs/heads/${branch}" "refs/remotes/origin/${branch}"
    fi
}

# 合并前把子模块 source/target 的远端提交拉到本地。失败返回 1，调用方可改用已有远程引用。
_refresh_submodule_tips() {
    local path="$1"
    if ! (cd "${path}" && git_fetch_with_retry origin); then
        return 1
    fi
    _ff_local_branch_to_origin "${path}" "${TARGET_BRANCH}"
    _ff_local_branch_to_origin "${path}" "${SOURCE_BRANCH}"
    return 0
}

# 把临时 worktree 的合并结果快进推到 origin/<target>。
# 推送前以及遇到「远端基线已更新」时，先把远端 target 上多出来的提交并进 worktree，再推一次。
# 成功：stdout 只打印最终 SHA，返回 0。内容冲突返回 2。其他失败返回 1。
_push_merge_result_ff() {
    local path="$1" wt="$2"
    local attempt resolved remote
    resolved="$(git -C "${wt}" rev-parse HEAD)"
    for attempt in 1 2; do
        if ! (cd "${path}" && git_fetch_with_retry origin); then
            echo "WARN: ${path} 推送前拉取远端失败（$(classify_git_error "${GIT_NET_LAST_ERR}")）" >&2
        fi
        remote="$(git -C "${path}" rev-parse "refs/remotes/origin/${TARGET_BRANCH}" 2>/dev/null || true)"
        if [ -n "${remote}" ] && ! git -C "${path}" merge-base --is-ancestor "${remote}" "${resolved}" 2>/dev/null; then
            echo "INFO: ${path} 远端 ${TARGET_BRANCH} 比当前合并结果新，先并入再推送" >&2
            if ! git -C "${wt}" merge --no-edit "${remote}" >&2; then
                return 2
            fi
            resolved="$(git -C "${wt}" rev-parse HEAD)"
        fi
        if [ -n "${remote}" ] && git -C "${path}" merge-base --is-ancestor "${resolved}" "${remote}" 2>/dev/null; then
            printf '%s\n' "${remote}"
            return 0
        fi
        if (cd "${path}" && git_push_with_retry origin "${resolved}:refs/heads/${TARGET_BRANCH}"); then
            printf '%s\n' "${resolved}"
            return 0
        fi
        if [ "$(classify_git_error "${GIT_NET_LAST_ERR}")" != "远端基线已更新" ]; then
            return 1
        fi
        echo "INFO: ${path} 推送被拒绝，远端 ${TARGET_BRANCH} 又有新提交，重新拉取后再合并" >&2
    done
    return 1
}

# 业务子模块 gitlink 分歧：在临时 worktree 把 source 提交合并进【子模块远端 target】，两边都保留。
# 基线是 fetch 之后的 origin/<target>，不用主仓里可能落后的 gitlink。主仓记录的旧指针若含远端没有的提交，再并入。
# 主仓索引用合并结果，不改子模块当前检出。内容冲突不写入，现场留给用户确认。
# 公共子模块（devops-lib）不处理。
_auto_resolve_diverged_gitlinks() {
    local path sm_name ours theirs resolved wt remote_target base include_ours push_rc push_out
    local remaining=0
    GITLINK_CONTENT_CONFLICTS="[]"
    while IFS= read -r path; do
        [ -z "${path}" ] && continue
        # 非 gitlink（普通文件冲突）留给用户确认
        if git ls-files -u -- "${path}" | awk '{ if ($1 != "160000") bad=1 } END { exit !bad }'; then
            remaining=1
            continue
        fi
        sm_name="$(git config --file .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null \
            | awk -v p="${path}" '$2 == p {
                n = $1; sub(/^submodule\./, "", n); sub(/\.path$/, "", n); print n; exit
            }')"
        if _is_public_submodule "${sm_name}"; then
            echo "INFO: 公共子模块 ${path} 指针冲突不自动合并" >&2
            remaining=1
            continue
        fi
        if [ ! -e "${path}/.git" ]; then
            echo "WARN: ${path} 未检出，无法自动合并指针" >&2
            remaining=1
            continue
        fi
        # stage 2 = 当前 target，stage 3 = 并入的 source
        ours="$(git ls-files -u -- "${path}" | awk '$3 == 2 { print $2; exit }')"
        theirs="$(git ls-files -u -- "${path}" | awk '$3 == 3 { print $2; exit }')"
        if [ -z "${ours}" ] || [ -z "${theirs}" ]; then
            remaining=1
            continue
        fi
        if ! _refresh_submodule_tips "${path}"; then
            echo "WARN: ${path} 合并前拉取远端失败，改用本地已有的远程引用" >&2
        fi
        if ! git -C "${path}" cat-file -e "${ours}^{commit}" 2>/dev/null \
           || ! git -C "${path}" cat-file -e "${theirs}^{commit}" 2>/dev/null; then
            echo "WARN: ${path} 缺少 gitlink 对象，无法自动合并" >&2
            remaining=1
            continue
        fi
        # 基线用子模块自己的 origin/<target>。主仓 gitlink（ours）经常落后于子模块远端。
        remote_target=""
        if git -C "${path}" show-ref --verify --quiet "refs/remotes/origin/${TARGET_BRANCH}"; then
            remote_target="$(git -C "${path}" rev-parse "refs/remotes/origin/${TARGET_BRANCH}")"
        fi
        base="${ours}"
        include_ours=false
        if [ -n "${remote_target}" ]; then
            base="${remote_target}"
            if ! git -C "${path}" merge-base --is-ancestor "${ours}" "${remote_target}" 2>/dev/null; then
                include_ours=true
            fi
        fi
        resolved=""
        wt=""
        if [ -n "${remote_target}" ] \
           && git -C "${path}" merge-base --is-ancestor "${theirs}" "${remote_target}" 2>/dev/null \
           && [ "${include_ours}" = false ]; then
            resolved="${remote_target}"
        elif git -C "${path}" merge-base --is-ancestor "${base}" "${theirs}" 2>/dev/null \
           && { [ "${include_ours}" = false ] \
                || git -C "${path}" merge-base --is-ancestor "${ours}" "${theirs}" 2>/dev/null; }; then
            resolved="${theirs}"
        else
            wt="$(mktemp -d "${TMPDIR:-/tmp}/gitlink-merge.XXXXXX")"
            if ! git -C "${path}" worktree add --detach "${wt}" "${base}" >&2; then
                echo "WARN: ${path} 无法创建临时 worktree" >&2
                rm -rf "${wt}"
                remaining=1
                continue
            fi
            if ! git -C "${wt}" merge-base --is-ancestor "${theirs}" HEAD 2>/dev/null \
               && ! git -C "${wt}" merge --no-edit "${theirs}" >&2; then
                echo "WARN: ${path} 子模块内容冲突，现场保留在 ${wt}，必须先向用户展示方案并确认后才能写入" >&2
                GITLINK_CONTENT_CONFLICTS="$(
                    jq --arg p "${path}" --arg w "${wt}" \
                       '. + [{path: $p, worktree: $w}]' <<<"${GITLINK_CONTENT_CONFLICTS}"
                )"
                remaining=1
                continue
            fi
            if [ "${include_ours}" = true ] \
               && ! git -C "${wt}" merge-base --is-ancestor "${ours}" HEAD 2>/dev/null \
               && ! git -C "${wt}" merge --no-edit "${ours}" >&2; then
                echo "WARN: ${path} 子模块内容冲突，现场保留在 ${wt}，必须先向用户展示方案并确认后才能写入" >&2
                GITLINK_CONTENT_CONFLICTS="$(
                    jq --arg p "${path}" --arg w "${wt}" \
                       '. + [{path: $p, worktree: $w}]' <<<"${GITLINK_CONTENT_CONFLICTS}"
                )"
                remaining=1
                continue
            fi
            resolved="$(git -C "${wt}" rev-parse HEAD)"
        fi
        # 结果还不在远端时再推。推送前会再拉一次，远端又前进就先并入。
        if [ -z "${remote_target}" ] \
           || ! git -C "${path}" merge-base --is-ancestor "${resolved}" "${remote_target}" 2>/dev/null; then
            if [ -z "${wt}" ]; then
                wt="$(mktemp -d "${TMPDIR:-/tmp}/gitlink-merge.XXXXXX")"
                if ! git -C "${path}" worktree add --detach "${wt}" "${resolved}" >&2; then
                    echo "WARN: ${path} 无法创建推送用临时 worktree" >&2
                    rm -rf "${wt}"
                    remaining=1
                    continue
                fi
            fi
            push_rc=0
            push_out="$(_push_merge_result_ff "${path}" "${wt}")" || push_rc=$?
            if [ "${push_rc}" -eq 2 ]; then
                echo "WARN: ${path} 并入远端新提交时发生内容冲突，现场保留在 ${wt}" >&2
                GITLINK_CONTENT_CONFLICTS="$(
                    jq --arg p "${path}" --arg w "${wt}" \
                       '. + [{path: $p, worktree: $w}]' <<<"${GITLINK_CONTENT_CONFLICTS}"
                )"
                remaining=1
                continue
            fi
            if [ "${push_rc}" -ne 0 ] || [ -z "${push_out}" ]; then
                echo "ERROR: ${path} 合并结果推送到 ${TARGET_BRANCH} 失败，现场保留在 ${wt}" >&2
                remaining=1
                continue
            fi
            resolved="${push_out}"
            _ff_local_branch_to_origin "${path}" "${TARGET_BRANCH}"
        fi
        if [ -n "${wt}" ]; then
            git -C "${path}" worktree remove "${wt}" >/dev/null 2>&1 || true
        fi
        # 只改主仓索引，不 checkout 子模块工作区（用户可能停在别的分支）
        git update-index --cacheinfo "160000,${resolved},${path}"
        AUTO_RESOLVED_GITLINKS=true
        echo "INFO: ${path} 已把 source 合并进 target，主仓指针 ${resolved}" >&2
    done < <(git ls-files -u | cut -f2 | sort -u)

    if [ "${remaining}" -eq 0 ] && ! git ls-files -u | grep -q .; then
        if git commit --no-edit >&2; then
            MERGE_RESULT="success"
            CONFLICT_FILES="[]"
            echo "INFO: 业务子模块指针分歧已自动合并，主仓 merge commit 已完成" >&2
        else
            echo "ERROR: 指针已暂存但主仓 commit 失败" >&2
        fi
    else
        CONFLICT_FILES="$(git ls-files -u | cut -f2 | sort -u | jq -R -s 'split("\n") | map(select(. != ""))')"
    fi
}

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
        --argjson smstatus "${SUBMODULE_STATUS:-[]}" \
        --argjson smsync "${SUBMODULE_SYNC}" \
        --argjson smgate "${SUBMODULE_GATE_ALL_PASS}" \
        --arg psh "${PRE_MERGE_SOURCE_HEAD}" \
        --arg pth "${PRE_MERGE_TARGET_HEAD}" \
        --arg trf "${TARGET_REWRITTEN_FROM}" \
        --argjson sfm "${SOURCE_FULLY_MERGED}" \
        --arg smerr "${SOURCE_MERGE_ERR}" \
        --argjson gcc "${GITLINK_CONTENT_CONFLICTS:-[]}" \
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
            submodule_status: $smstatus,
            submodule_sync: $smsync,
            submodule_gate_all_pass: $smgate,
            pre_merge_source_head: $psh,
            pre_merge_target_head: $pth,
            target_rewritten_from: (if $trf == "" then null else $trf end),
            source_fully_merged: $sfm,
            source_merge_error: (if $smerr == "" then null else $smerr end),
            gitlink_content_conflicts: $gcc
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
        if bash "${SCRIPT_DIR}/restore-workspace.sh"; then
            return 0
        fi
        # restore 失败 → 兜底：如果 inventory 只有 untracked 且文件都在磁盘上，强制清理
        if [ -f "${state_file}" ]; then
            local inv_non_untracked
            inv_non_untracked="$(jq -r '[.inventory[] | select(.[:2] != "??" and .[:2] != "D")] | length' "${state_file}" 2>/dev/null || echo "-1")"
            if [ "${inv_non_untracked}" = "0" ]; then
                echo "WARN: inventory 仅含 untracked 条目，文件均在磁盘，强制清理遗留状态" >&2
                rm -f "${state_file}"
                git update-ref -d refs/merge-branch/workspace-stash 2>/dev/null || true
                local leftover_sha
                leftover_sha="$(git stash list --format='%gd %H %s' | awk '/auto-stash before merge-branch/ { print $1; exit }')"
                if [ -n "${leftover_sha}" ]; then
                    git stash drop "${leftover_sha}" >/dev/null 2>&1 || true
                fi
                return 0
            fi
        fi
        fail "上次工作区恢复失败。请手动运行: bash ${SCRIPT_DIR}/restore-workspace.sh"
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
    STASH_REF="$(git stash list | sed -n '1p' | cut -d: -f1)"
    STASH_SHA="$(git rev-parse stash@{0})"
fi
write_restore_state

# === Step 5: fetch 远程 ===
git fetch origin >/dev/null 2>&1 || fail "git fetch origin 失败（网络或权限问题）"

# submodule 预热：让主仓库在 merge 前拥有子模块的 gitlink commit 对象。
# 旧逻辑用 `git submodule foreach 'git fetch origin'`，但 submodule 未初始化时
# foreach 静默跳过，实际什么也没 fetch，导致主仓库 merge 时三方比对失败、
# submodule 指针以冲突形式抛出。新逻辑用官方 --recurse-submodules + --init，
# 即使 submodule 未初始化也能补齐对象。
if [ -f .gitmodules ]; then
    # 1) 主动拉取已被引用的子模块新提交（只 fetch 被引用的，按需）
    git fetch origin --recurse-submodules=on-demand >/dev/null 2>&1 \
        || echo "WARN: git fetch --recurse-submodules 部分失败，合并仍继续但 submodule 冲突概率升高" >&2
    # 2) 初始化未初始化的子模块；已初始化的不动。递归处理所有嵌套子模块。
    git submodule update --init --recursive >/dev/null 2>&1 \
        || echo "WARN: git submodule update --init 部分失败（可能是子模块远程不可达或 URL 配置问题），合并仍继续但 submodule 冲突概率升高" >&2
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

# === Step 8.5: 收集 submodule 三方 commit 诊断信息 ===
# 此刻 source 与 target HEAD 都已同步到本地，三方 gitlink 都可读。
# 目的：让 AI 在冲突解决阶段能看到每个 submodule 的 base/source/target commit 信息
# 与 merge 策略建议（auto-ff-from-source / auto-ff-from-target / needs-manual）。
# 注：submodule commit 对象可能本地缺失，诊断时若不可达则 commit 字段为 null，
#     提示信息照常输出，AI 可据此决定是否需要额外 fetch。
SUBMODULE_STATUS="[]"
if [ -f .gitmodules ] && [ -n "${SUBMODULE_LIST}" ]; then
    MB_SUB="$(git merge-base "${SOURCE_BRANCH}" "${TARGET_BRANCH}" 2>/dev/null || true)"

    # 辅助：从某 ref 的 tree 中读 submodule 路径对应的 gitlink commit SHA
    # git ls-tree 输出用 TAB 分隔：mode<TAB>type<TAB>object<TAB>file
    _gitlink_sha() {
        git ls-tree "$1" "$2" 2>/dev/null \
            | awk -v want="$2" '$1 == "160000" && $4 == want { print $3; exit }'
    }

    # 辅助：拿 submodule 路径对应的 URL（解析 .gitmodules）
    # POSIX awk 不支持 match(..., array)，改用 split + 拼接提取 name
    _submodule_url() {
        local path="$1"
        git config --file .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null \
            | awk -v p="${path}" '
                $2 == p {
                    # $1 = "submodule.<name>.path"
                    n = $1
                    sub(/^submodule\./, "", n)
                    sub(/\.path$/, "", n)
                    print n
                    exit
                }
            ' \
            | while IFS= read -r name; do
                [ -z "${name}" ] && continue
                git config --file .gitmodules --get "submodule.${name}.url" 2>/dev/null
                break
            done
    }

    # 辅助：从主仓 origin SSH URL 推导 submodule 的 SSH URL
    # 推导规则：取 origin 的 protocol/user/host/port + path 的父目录 + <sub_name>.git
    # 主仓 origin 非 SSH 时返回空字符串（fallback 仍走 .gitmodules 原 URL）
    _submodule_ssh_url() {
        local sub_name="$1"
        [ -z "${sub_name}" ] && return 0
        local origin_url
        origin_url="$(git remote get-url origin 2>/dev/null || true)"
        [ -z "${origin_url}" ] && return 0
        # 仅处理 ssh:// 协议
        case "${origin_url}" in
            ssh://*) ;;
            *) return 0 ;;
        esac
        # 去掉末尾 .git（若有）
        local clean="${origin_url%.git}"
        # 找到最后一段 / 之前的部分（path 的父目录）
        local without_proto="${clean#ssh://}"
        # without_proto 形如 git@geekssh.glodon.com:7999/dg/gmdos-svc
        # 拆分 host:port 与 path：先找最后一个 /
        local last_slash="${without_proto##*/}"
        local prefix="${without_proto%/*}"
        # prefix 形如 git@geekssh.glodon.com:7999/dg
        echo "${prefix}/${sub_name}.git"
    }

    # 辅助：按 stderr 关键字分类 git fetch 错误
    # 返回 stderr 第一行匹配的分类标签
    _classify_fetch_error() {
        local stderr_content="$1"
        if echo "${stderr_content}" | grep -qE "Could not resolve host|fatal: unable to access"; then
            echo "URL 配置错误"
        elif echo "${stderr_content}" | grep -qE "Connection refused|timed out|Network is unreachable"; then
            echo "网络问题"
        elif echo "${stderr_content}" | grep -qE "could not read Username|Permission denied \(publickey\)|Repository not found"; then
            echo "凭证问题"
        else
            echo "未知"
        fi
    }

    while IFS= read -r sm_path; do
        [ -z "${sm_path}" ] && continue
        sm_url="$( _submodule_url "${sm_path}" )"
        base_sha="$( _gitlink_sha "${MB_SUB}" "${sm_path}" )"
        src_sha="$(  _gitlink_sha "${SOURCE_BRANCH}" "${sm_path}" )"
        tgt_sha="$(  _gitlink_sha "${TARGET_BRANCH}" "${sm_path}" )"

        # 主动 fetch 三方 submodule commit 对象，让祖先关系判定可执行；
        # 若对象仍不可达，merge-base --is-ancestor 会失败 → 降级为 needs-manual。
        # 从 submodule 自己的 URL 拉取（不是主仓库 origin），失败静默不影响合并。
        # 协议优先级：SSH 推导 → HTTPS 原 URL；失败分类 warn
        sm_name="$(git config --file .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null | awk -v p="${sm_path}" '$2 == p { n=$1; sub(/^submodule\./, "", n); sub(/\.path$/, "", n); print n; exit }')"
        ssh_url="$( _submodule_ssh_url "${sm_name}" )"
        for s in "${base_sha}" "${src_sha}" "${tgt_sha}"; do
            [ -z "${s}" ] && continue
            git cat-file -e "${s}^{commit}" 2>/dev/null && continue
            fetched=false
            if [ -n "${ssh_url}" ]; then
                err="$(git fetch "${ssh_url}" "${s}" 2>&1)" && fetched=true
            fi
            if [ "${fetched}" = false ] && [ -n "${sm_url}" ]; then
                err="$(git fetch "${sm_url}" "${s}" 2>&1)" && fetched=true
            fi
            if [ "${fetched}" = false ]; then
                warn_class="$( _classify_fetch_error "${err}" )"
                echo "WARN: submodule ${sm_path} commit ${s:0:7} 不可达（${warn_class}）；SSH=${ssh_url:-<无>} HTTPS=${sm_url:-<无>}" >&2
            fi
        done

        # 至少一个对象本地可达即视为 objects_available=true
        obj_avail="false"
        for s in "${base_sha}" "${src_sha}" "${tgt_sha}"; do
            [ -z "${s}" ] && continue
            if git cat-file -e "${s}^{commit}" 2>/dev/null; then
                obj_avail="true"
                break
            fi
        done

        # commit subject（对象不可达时为空字符串，jq 转为 null）
        base_sub="$(git log -1 --format='%s' "${base_sha}" 2>/dev/null || true)"
        src_sub="$( git log -1 --format='%s' "${src_sha}"  2>/dev/null || true)"
        tgt_sub="$( git log -1 --format='%s' "${tgt_sha}"  2>/dev/null || true)"

        # commit time（ISO 8601）与 author（对象不可达时为空字符串，jq 转为 null）
        base_time="$(git log -1 --format='%cI' "${base_sha}" 2>/dev/null || true)"
        src_time="$( git log -1 --format='%cI' "${src_sha}"  2>/dev/null || true)"
        tgt_time="$( git log -1 --format='%cI' "${tgt_sha}"  2>/dev/null || true)"
        base_author="$(git log -1 --format='%an <%ae>' "${base_sha}" 2>/dev/null || true)"
        src_author="$( git log -1 --format='%an <%ae>' "${src_sha}"  2>/dev/null || true)"
        tgt_author="$( git log -1 --format='%an <%ae>' "${tgt_sha}"  2>/dev/null || true)"

        # merge 策略建议：祖先关系时自动 FF，否则需要人工
        hint="needs-manual"
        if [ -n "${src_sha}" ] && [ -n "${tgt_sha}" ]; then
            if git merge-base --is-ancestor "${src_sha}" "${tgt_sha}" 2>/dev/null; then
                hint="auto-ff-from-target"  # target 已包含 source 的 submodule 指针
            elif git merge-base --is-ancestor "${tgt_sha}" "${src_sha}" 2>/dev/null; then
                hint="auto-ff-from-source"   # source 的指针更新
            fi
        fi

        SUBMODULE_STATUS="$(
            jq --arg p "${sm_path}" \
               --arg b "${base_sha}"  --arg bs "${base_sub}" --arg bt "${base_time}" --arg ba "${base_author}" \
               --arg s "${src_sha}"   --arg ss "${src_sub}"  --arg st "${src_time}"  --arg sa "${src_author}" \
               --arg t "${tgt_sha}"   --arg ts "${tgt_sub}"  --arg tt "${tgt_time}"  --arg ta "${tgt_author}" \
               --argjson oa "${obj_avail}" \
               --arg h "${hint}" \
               '. + [{
                   path: $p,
                   base_commit:      (if $b  == "" then null else $b  end),
                   base_subject:     (if $bs == "" then null else $bs end),
                   base_commit_time: (if $bt == "" then null else $bt end),
                   base_author:      (if $ba == "" then null else $ba end),
                   source_commit:    (if $s  == "" then null else $s  end),
                   source_subject:   (if $ss == "" then null else $ss end),
                   source_commit_time:(if $st == "" then null else $st end),
                   source_author:    (if $sa == "" then null else $sa end),
                   target_commit:    (if $t  == "" then null else $t  end),
                   target_subject:   (if $ts == "" then null else $ts end),
                   target_commit_time:(if $tt == "" then null else $tt end),
                   target_author:    (if $ta == "" then null else $ta end),
                   objects_available: $oa,
                   merge_strategy_hint: $h
               }]' <<<"${SUBMODULE_STATUS}"
        )"
    done <<<"${SUBMODULE_LIST}"
fi

# === Step 8.9: 合并前再次把远端 target 快进到本地 ===
# 诊断子模块可能耗时，远端 target 在这期间可能已有新提交。按过期基线合并后再推会被拒绝。
echo "INFO: 合并前再次同步远端 ${TARGET_BRANCH}" >&2
set +e
PULL_ERR="$(git pull --ff-only origin "${TARGET_BRANCH}" 2>&1)"
PULL_RC=$?
set -e
if [ "${PULL_RC}" -ne 0 ]; then
    MB="$(git merge-base "${TARGET_BRANCH}" "origin/${TARGET_BRANCH}" 2>/dev/null || true)"
    LH="$(git rev-parse "${TARGET_BRANCH}")"
    RH="$(git rev-parse "origin/${TARGET_BRANCH}" 2>/dev/null || true)"
    if [ -n "${MB}" ] && [ -n "${RH}" ]; then
        LOC="$(git rev-list "${MB}..${LH}" --count)"
        REM="$(git rev-list "${MB}..${RH}" --count)"
        if [ "${LOC}" -gt 0 ] && [ "${REM}" -gt 0 ]; then
            LOC_LIST="$(git log --format="%h %s" "${MB}..${LH}")"
            REM_LIST="$(git log --format="%h %s" "${MB}..${RH}")"
            DIVERGE_INFO=$(jq -n \
                --arg lo "${LOC_LIST}" \
                --arg ro "${REM_LIST}" \
                '{
                    local_only: ($lo | split("\n") | map(select(. != ""))),
                    remote_only: ($ro | split("\n") | map(select(. != "")))
                }')
            ERROR_MSG="合并前 target 分支本地与远程分叉"
            restore_on_abort
            print_status
            exit 2
        fi
    fi
    fail "合并前同步 ${TARGET_BRANCH} 失败：${PULL_ERR}"
fi
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
        # 业务子模块指针分歧自动合并（两边提交都保留）；内容冲突仍停在 conflict
        _auto_resolve_diverged_gitlinks
    else
        fail "git merge 失败但非冲突：${MERGE_OUTPUT}"
    fi
fi

# === Step 9.5: submodule 自动合并（ort 策略） ===
# 仅在主仓库 merge 成功（success/already_up_to_date）时执行；conflict 路径走人工解决。
# 指针已在临时 worktree 合并时跳过：submodule update --merge 会改用户当前检出的分支。
# 官方依据：merge-strategies(5) ort 策略对 gitlink 的三方合并：
#   "if the submodule commit used on one side of the merge is a descendant of the
#    submodule commit used on the other side of the merge, Git attempts to
#    fast-forward to the descendant."
# 这一步覆盖绝大多数 submodule 指针冲突，无需人工 git add。
# 失败/部分冲突：仅 warn，由 merge-submodule.sh 在阶段 3 接手处理（方案需经用户确认）。
if [ "${MERGE_RESULT}" = "success" ] || [ "${MERGE_RESULT}" = "already_up_to_date" ]; then
    if [ -f .gitmodules ]; then
        # 跳过公共 submodule（白名单内的绝对不动）
        public_skipped=""
        filtered_submodules=""
        while IFS= read -r sm_path; do
            [ -z "${sm_path}" ] && continue
            sm_name="$(git config --file .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null \
                | awk -v p="${sm_path}" '$2 == p {
                    n = $1; sub(/^submodule\./, "", n); sub(/\.path$/, "", n); print n; exit
                }')"
            if _is_public_submodule "${sm_name}"; then
                public_skipped="${public_skipped:+${public_skipped} }${sm_name}"
            else
                filtered_submodules="${filtered_submodules:+${filtered_submodules} }${sm_path}"
            fi
        done <<<"${SUBMODULE_LIST}"
        if [ -n "${public_skipped}" ]; then
            echo "INFO: 跳过公共 submodule（绝对不动）：${public_skipped}" >&2
        fi

        # 仅对非公共 submodule 执行 ort 自动 merge。
        # 指针已在临时 worktree 合并时跳过：update --merge 会把结果合进用户当前检出的分支。
        if [ "${AUTO_RESOLVED_GITLINKS}" = "true" ]; then
            echo "INFO: 业务子模块指针已在临时 worktree 合并，跳过 submodule update --merge" >&2
        elif [ -n "${filtered_submodules}" ]; then
            echo "${filtered_submodules}" | xargs git submodule update --init --merge 2>/dev/null \
                || echo "WARN: submodule update --merge 部分冲突，将由 merge-submodule.sh 接手处理" >&2
        fi
    fi
fi

# === Step 9.6: 自动提交 submodule 指针改动 ===
# 仅当 merge_result ∈ {success, already_up_to_date} 且至少一个 submodule 指针发生变化
# 安全闸：merge commit 未推送 → amend；已推送 → 独立 commit（绝不重写远端 hash）
if [ "${MERGE_RESULT}" = "success" ] || [ "${MERGE_RESULT}" = "already_up_to_date" ]; then
    if [ -f .gitmodules ]; then
        amended_submodules=""
        # filtered_submodules 已排除公共 submodule（Task 0），无需再检查
        # filtered_submodules 是空格分隔，先转换为换行分隔以便 while read 逐项处理
        while IFS= read -r sm_path; do
            [ -z "${sm_path}" ] && continue
            gitlink_sha="$(git ls-files --stage "${sm_path}" 2>/dev/null | awk '$1=="160000"{print $2}')"
            worktree_sha="$(git -C "${sm_path}" rev-parse HEAD 2>/dev/null || true)"
            # 工作区停在别的分支时禁止 git add：那会用当前检出覆盖刚合并好的指针，丢掉另一边的提交
            if [ -n "${worktree_sha}" ] && [ -n "${gitlink_sha}" ] && [ "${gitlink_sha}" != "${worktree_sha}" ] \
               && git -C "${sm_path}" merge-base --is-ancestor "${gitlink_sha}" "${worktree_sha}" 2>/dev/null; then
                git add "${sm_path}" 2>/dev/null || true
                amended_submodules="${amended_submodules:+${amended_submodules} }${sm_path}"
            elif [ -n "${worktree_sha}" ] && [ "${gitlink_sha}" != "${worktree_sha}" ]; then
                echo "INFO: ${sm_path} 工作区不是索引指针的后代，保留索引中的合并指针" >&2
            fi
        done <<<"$(echo "${filtered_submodules}" | tr ' ' '\n')"

        if [ -n "${amended_submodules}" ]; then
            target_published="false"
            if git rev-parse --verify "origin/${TARGET_BRANCH}" >/dev/null 2>&1; then
                if git merge-base --is-ancestor HEAD "origin/${TARGET_BRANCH}"; then
                    target_published="true"
                fi
            fi
            if [ "${target_published}" = "false" ]; then
                git commit --amend --no-edit 2>/dev/null || true
                echo "INFO: 子模块指针已合并到 merge commit（amend，未推送安全）：${amended_submodules}" >&2
            else
                git commit --no-edit -m "chore: update submodule pointers after merge" 2>/dev/null || true
                echo "INFO: 子模块指针已作为独立 commit（merge commit 已推送，避免重写 hash）：${amended_submodules}" >&2
            fi
        fi
    fi
fi

# === Step 9.7: 子模块强制同步（v3：worktree 隔离 + 自动推送 + 闸门校验） ===
# 背景（2026-09-18 事故）：v2 的阶段 3 依赖 AI 自觉执行且失败被降级为软失败，
# 导致主仓推送成功而 web 等 submodule target 分支落后 64 个提交时整体被误报成功。
# v3 行为：success / already_up_to_date 路径都对每个非公共 submodule 自动执行：
#   1) fetch（带 IdentityFile 自愈重试）
#   2) origin/target 已包含 source → up_to_date（顺手 ff 本地 target 分支引用）
#   3) 否则在临时 detached worktree 中 ff 到 origin/target 后合并 source
#   4) 合并成功 → 推送 target → 闸门校验（source 必须是 origin/target 祖先）→ 清理 worktree
#   5) 子模块内容冲突 → 保留临时 worktree 并在 JSON 给出路径，AI 展示方案并等用户确认后解决推送
# 任一非公共子模块闸门不通过 → submodule_gate_all_pass=false，AI 必须按 ❌ 报告。
SUBMODULE_SYNC="[]"
SUBMODULE_GATE_ALL_PASS=true
if [ "${MERGE_RESULT}" = "success" ] || [ "${MERGE_RESULT}" = "already_up_to_date" ]; then
    if [ -f .gitmodules ] && [ -n "${SUBMODULE_LIST}" ]; then
        SYNC_ROWS=""
        while IFS= read -r sm_path; do
            [ -z "${sm_path}" ] && continue
            sm_name="$(git config --file .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null \
                | awk -v p="${sm_path}" '$2 == p { n=$1; sub(/^submodule\./, "", n); sub(/\.path$/, "", n); print n; exit }')"
            _is_public_submodule "${sm_name}" && continue

            # v3.4（用户规范 2026-10-14）：本次合并未改动该 submodule 的 gitlink
            # （source 分支的提交与该子模块无关，merge commit 相对合并前 target 无差异）
            # → 完全跳过：不 fetch、不检查远端分支、不同步、不推送、不参与闸门。
            # 指针未被本合并移动时，子模块的分支状态与本仓库无关，任何处理都是多余风险。
            if [ -n "${PRE_MERGE_TARGET_HEAD}" ] \
               && git diff --quiet "${PRE_MERGE_TARGET_HEAD}" HEAD -- "${sm_path}" 2>/dev/null; then
                SYNC_ROWS="${SYNC_ROWS}$(jq -n --arg p "${sm_path}" --arg r "unchanged" \
                    '{path:$p, result:$r, pushed_head:null, worktree:null, gate_pass:true, error:null}')
"
                continue
            fi

            sync_result="error"
            sync_err=""
            sync_wt=""
            sync_head=""
            gate="false"

            # 1) 子模块未初始化：无法同步，闸门不通过
            if [ ! -e "${sm_path}/.git" ]; then
                sync_err="submodule 未初始化，无法自动同步"
                echo "WARN: [submodule ${sm_path}] ${sync_err}" >&2
                SYNC_ROWS="${SYNC_ROWS}$(jq -n --arg p "${sm_path}" --arg r "error" --arg e "${sync_err}" --argjson g false \
                    '{path:$p, result:$r, pushed_head:null, worktree:null, gate_pass:$g, error:$e}')
"
                continue
            fi

            # 2) fetch（带认证自愈）
            if ! (cd "${sm_path}" && git_fetch_with_retry origin); then
                sync_err="fetch 失败（$(classify_git_error "${GIT_NET_LAST_ERR}")）"
                echo "WARN: [submodule ${sm_path}] ${sync_err}" >&2
                SYNC_ROWS="${SYNC_ROWS}$(jq -n --arg p "${sm_path}" --arg r "error" --arg e "${sync_err}" --argjson g false \
                    '{path:$p, result:$r, pushed_head:null, worktree:null, gate_pass:$g, error:$e}')
"
                continue
            fi
            # 能快进的本地分支先对齐远端，后续合并只用 origin/<target>，不读过期本地指针
            _ff_local_branch_to_origin "${sm_path}" "${TARGET_BRANCH}"
            _ff_local_branch_to_origin "${sm_path}" "${SOURCE_BRANCH}"

            # 3) 远端分支存在性
            branch_missing=""
            for sm_branch in "${SOURCE_BRANCH}" "${TARGET_BRANCH}"; do
                if ! git -C "${sm_path}" ls-remote --exit-code --heads origin "refs/heads/${sm_branch}" >/dev/null 2>&1; then
                    branch_missing="${sm_branch}"
                    break
                fi
            done
            if [ -n "${branch_missing}" ]; then
                sync_err="远程没有分支 ${branch_missing}"
                echo "WARN: [submodule ${sm_path}] ${sync_err}" >&2
                SYNC_ROWS="${SYNC_ROWS}$(jq -n --arg p "${sm_path}" --arg r "error" --arg e "${sync_err}" --argjson g false \
                    '{path:$p, result:$r, pushed_head:null, worktree:null, gate_pass:$g, error:$e}')
"
                continue
            fi

            sub_src_head="$(git -C "${sm_path}" rev-parse "refs/remotes/origin/${SOURCE_BRANCH}" 2>/dev/null || true)"

            # 4) 闸门预检：origin/target 已包含 source → up_to_date，顺手 ff 本地 target 引用
            if [ -n "${sub_src_head}" ] && git -C "${sm_path}" merge-base --is-ancestor "${sub_src_head}" "refs/remotes/origin/${TARGET_BRANCH}" 2>/dev/null; then
                git -C "${sm_path}" fetch origin "refs/heads/${TARGET_BRANCH}:refs/heads/${TARGET_BRANCH}" >/dev/null 2>&1 || true
                gate="true"
                sync_result="up_to_date"
                SYNC_ROWS="${SYNC_ROWS}$(jq -n --arg p "${sm_path}" --arg r "up_to_date" --arg h "${sub_src_head}" --argjson g true \
                    '{path:$p, result:$r, pushed_head:$h, worktree:null, gate_pass:$g, error:null}')
"
                continue
            fi

            # 5) 临时 detached worktree：基于 origin/target（fetch 后必存在，不依赖本地分支）
            #    合并 origin/source —— 不用本地分支引用，避免本地分支陈旧导致合并旧代码
            SM_WT="$(mktemp -d "${TMPDIR:-/tmp}/merge-branch-sub-XXXXXX")"
            if ! git -C "${sm_path}" worktree add --detach "${SM_WT}" "refs/remotes/origin/${TARGET_BRANCH}" >/dev/null 2>&1; then
                rmdir "${SM_WT}" 2>/dev/null || true
                sync_err="创建临时 worktree 失败"
                echo "WARN: [submodule ${sm_path}] ${sync_err}" >&2
                SYNC_ROWS="${SYNC_ROWS}$(jq -n --arg p "${sm_path}" --arg r "error" --arg e "${sync_err}" --argjson g false \
                    '{path:$p, result:$r, pushed_head:null, worktree:null, gate_pass:$g, error:$e}')
"
                continue
            fi

            in_conflict=false
            if git -C "${SM_WT}" merge --no-edit "refs/remotes/origin/${SOURCE_BRANCH}" >/dev/null 2>&1; then
                sync_result="synced"
            elif git -C "${SM_WT}" ls-files -u 2>/dev/null | grep -q .; then
                in_conflict=true
                sync_result="conflict"
                sync_wt="${SM_WT}"
                sync_err="子模块内容冲突，已在临时 worktree 中保留冲突现场，必须向用户展示冲突并等确认后解决"
                echo "WARN: [submodule ${sm_path}] ${sync_err}: ${SM_WT}" >&2
            else
                sync_err="target 无法快进到 origin/target 且合并失败（可能本地 target 与远程分叉）"
            fi

            if [ "${in_conflict}" = true ]; then
                SYNC_ROWS="${SYNC_ROWS}$(jq -n --arg p "${sm_path}" --arg r "conflict" --arg w "${SM_WT}" --arg e "${sync_err}" --argjson g false \
                    '{path:$p, result:$r, pushed_head:null, worktree:$w, gate_pass:$g, error:$e}')
"
                continue
            fi

            if [ "${sync_result}" != "synced" ]; then
                git -C "${sm_path}" worktree remove --force "${SM_WT}" >/dev/null 2>&1 || rm -rf "${SM_WT}"
                echo "WARN: [submodule ${sm_path}] ${sync_err}" >&2
                SYNC_ROWS="${SYNC_ROWS}$(jq -n --arg p "${sm_path}" --arg r "error" --arg e "${sync_err}" --argjson g false \
                    '{path:$p, result:$r, pushed_head:null, worktree:null, gate_pass:$g, error:$e}')
"
                continue
            fi

            # 6) 推到远端 target。推送前再拉一次；远端又有新提交就先并入，避免非快进拒绝。
            push_rc=0
            push_out="$(_push_merge_result_ff "${sm_path}" "${SM_WT}")" || push_rc=$?
            if [ "${push_rc}" -eq 0 ] && [ -n "${push_out}" ]; then
                sync_head="${push_out}"
                _ff_local_branch_to_origin "${sm_path}" "${TARGET_BRANCH}"
                if git -C "${sm_path}" merge-base --is-ancestor "${sub_src_head}" "refs/remotes/origin/${TARGET_BRANCH}" 2>/dev/null \
                   || git -C "${sm_path}" merge-base --is-ancestor "${sub_src_head}" "${sync_head}" 2>/dev/null; then
                    gate="true"
                else
                    sync_err="推送成功但闸门校验未通过（origin/target 未包含 source）"
                fi
                git -C "${sm_path}" worktree remove "${SM_WT}" >/dev/null 2>&1 || rm -rf "${SM_WT}"
                sync_wt=""
                echo "INFO: [submodule ${sm_path}] 已同步并推送 ${TARGET_BRANCH} → ${sync_head:0:9}（gate=${gate}）" >&2
            elif [ "${push_rc}" -eq 2 ]; then
                sync_result="conflict"
                sync_wt="${SM_WT}"
                sync_err="并入远端新提交时发生内容冲突，现场保留在 ${SM_WT}，必须向用户展示并等确认后写入"
                echo "WARN: [submodule ${sm_path}] ${sync_err}" >&2
            else
                sync_err="推送 target 失败（$(classify_git_error "${GIT_NET_LAST_ERR}")）；合并现场已保留在 ${SM_WT}"
                sync_wt="${SM_WT}"
                sync_result="push_failed"
                echo "WARN: [submodule ${sm_path}] ${sync_err}" >&2
            fi

            SYNC_ROWS="${SYNC_ROWS}$(jq -n --arg p "${sm_path}" --arg r "${sync_result}" --arg h "${sync_head}" \
                --arg w "${sync_wt}" --arg e "${sync_err}" --argjson g "${gate}" \
                '{path:$p, result:$r, pushed_head:$h, worktree:(if $w == "" then null else $w end), gate_pass:$g, error:(if $e == "" then null else $e end)}')
"
        done <<<"${SUBMODULE_LIST}"

        SUBMODULE_SYNC="$(jq -s '[.[]]' <<<"${SYNC_ROWS}")"
        if [ -n "${SYNC_ROWS}" ]; then
            SUBMODULE_GATE_ALL_PASS="$(jq -e 'all(.[]; .gate_pass == true)' <<<"${SUBMODULE_SYNC}" >/dev/null 2>&1 && echo true || echo false)"
        fi
        if [ "${SUBMODULE_GATE_ALL_PASS}" != "true" ]; then
            echo "WARN: 子模块同步闸门未全部通过（submodule_gate_all_pass=false），AI 必须按 ❌ 报告并处理" >&2
        fi
    fi
fi

# === Step 9.8: gitlink 远端可达性验证（v3.1 安全补丁） ===
# 背景（2026-09-20 事故）：Step 9.7 的 up_to_date 预检只验证 origin/source HEAD
# 是否被 origin/target 包含，但 merge commit 的 gitlink 指针可能指向比 origin/source
# 更新的本地 commit（如 merge 后 submodule 内部又有新提交未推送）。
# CI 执行 git submodule update 时会因找不到该 commit 而失败。
# 本步骤在 JSON 输出前逐一校验每个非公共 submodule 的 gitlink commit 是否在远端可达，
# 不可达时自动尝试推送当前分支；推送失败则闸门不通过。
SUBMODULE_GITLINK_ERRORS=""
if [ "${MERGE_RESULT}" = "success" ] || [ "${MERGE_RESULT}" = "already_up_to_date" ]; then
    if [ -f .gitmodules ] && [ -n "${SUBMODULE_LIST}" ]; then
        while IFS= read -r sm_path; do
            [ -z "${sm_path}" ] && continue
            sm_name="$(git config --file .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null \
                | awk -v p="${sm_path}" '$2 == p { n=$1; sub(/^submodule\./, "", n); sub(/\.path$/, "", n); print n; exit }')"
            _is_public_submodule "${sm_name}" && continue
            # v3.4：合并未改动 gitlink 的子模块直接跳过可达性验证（指针未被本合并移动，
            # 子模块工作区现状可能来自他人未提交的检出状态，绝不据此推送共享分支）
            if [ -n "${PRE_MERGE_TARGET_HEAD}" ] \
               && git diff --quiet "${PRE_MERGE_TARGET_HEAD}" HEAD -- "${sm_path}" 2>/dev/null; then
                continue
            fi
            [ ! -e "${sm_path}/.git" ] && continue

            # 读取主仓 merge commit 记录的 gitlink，不用子模块工作区 HEAD（用户可能停在别的分支）
            gitlink_sha="$(git rev-parse "HEAD:${sm_path}" 2>/dev/null || true)"
            [ -z "${gitlink_sha}" ] && continue

            # 校验 gitlink 是否在远端 target 可达；不可达则只推这个 SHA，不推工作区 HEAD
            if ! git -C "${sm_path}" merge-base --is-ancestor "${gitlink_sha}" "refs/remotes/origin/${TARGET_BRANCH}" 2>/dev/null; then
                echo "WARN: [submodule ${sm_path}] gitlink ${gitlink_sha:0:9} 不在远端 ${TARGET_BRANCH}，补推该提交..." >&2
                if (cd "${sm_path}" && git_push_with_retry origin "${gitlink_sha}:refs/heads/${TARGET_BRANCH}"); then
                    echo "INFO: [submodule ${sm_path}] 已补推 gitlink ${gitlink_sha:0:9} 到 ${TARGET_BRANCH}" >&2
                else
                    SUBMODULE_GITLINK_ERRORS="${SUBMODULE_GITLINK_ERRORS}${sm_path}:${gitlink_sha:0:9} "
                    echo "ERROR: [submodule ${sm_path}] 补推 gitlink 失败：$(classify_git_error "${GIT_NET_LAST_ERR}")" >&2
                fi
            fi
        done <<<"${SUBMODULE_LIST}"
    fi
fi
if [ -n "${SUBMODULE_GITLINK_ERRORS}" ]; then
    echo "ERROR: 以下 submodule gitlink 未推送到远端，CI 将失败：${SUBMODULE_GITLINK_ERRORS}" >&2
    if [ "${SUBMODULE_GATE_ALL_PASS}" = "true" ]; then
        SUBMODULE_GATE_ALL_PASS=false
        echo "WARN: 因 gitlink 不可达，闸门已降级为 false" >&2
    fi
fi

# === Step 9.9: 不丢提交总闸门（v3.2） ===
# 背景（2026-09-24 复盘）：脚本子模块同步逻辑完备，但 AI 多次绕过脚本手工 merge，
# 导致 web 等 submodule 的分支合并与推送被整体漏掉，事后只能手工补指针提交。
# 本步骤在 JSON 输出前对主仓做最终校验：合并结果 HEAD 必须包含 origin/source 的全部提交；
# 冲突时输出显式标记：任何冲突解决都必须先询问用户，禁止 AI 自行取舍。
SOURCE_FULLY_MERGED=true
SOURCE_MERGE_ERR=""
if [ "${MERGE_RESULT}" = "success" ] || [ "${MERGE_RESULT}" = "already_up_to_date" ]; then
    if ! git merge-base --is-ancestor "refs/remotes/origin/${SOURCE_BRANCH}" HEAD 2>/dev/null; then
        SOURCE_FULLY_MERGED=false
        SOURCE_MERGE_ERR="主仓 HEAD 未包含 origin/${SOURCE_BRANCH} 的全部提交（疑似丢提交），禁止推送，必须报告用户"
        echo "ERROR: ${SOURCE_MERGE_ERR}" >&2
    fi
fi
if [ "${MERGE_RESULT}" = "conflict" ]; then
    echo "WARN: 仍有冲突：普通文件与子模块内容冲突必须向用户展示双方意图，得到确认后才能写入；禁止自行取舍。业务子模块指针分歧已自动合并，不要改回只保留一边。" >&2
fi

# === Step 10: 输出状态 JSON ===
print_status
exit 0
