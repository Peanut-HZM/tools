#!/usr/bin/env bash
set -euo pipefail

# git-push-with-retry.sh — 带认证自愈的推送（merge-branch 技能所有推送步骤统一走这里）
# 用法：git-push-with-retry.sh <remote> <refspec>
#   例：git-push-with-retry.sh origin dev
# 逻辑：先普通 push；失败且 ~/.ssh/config 能解析出该主机 IdentityFile 时，
#       用 GIT_SSH_COMMAND="ssh -i <file> -o IdentitiesOnly=yes" 显式重试。
#       仍失败 → stderr 输出分类后的错误并 exit 1。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib-git-auth.sh
source "${SCRIPT_DIR}/lib-git-auth.sh"

REMOTE="${1:-}"
REFSPEC="${2:-}"
if [ -z "${REMOTE}" ] || [ -z "${REFSPEC}" ]; then
    echo "用法: git-push-with-retry.sh <remote> <refspec>" >&2
    exit 1
fi

if git_push_with_retry "${REMOTE}" "${REFSPEC}"; then
    exit 0
fi

echo "ERROR: git push ${REMOTE} ${REFSPEC} 失败（$(classify_git_error "${GIT_NET_LAST_ERR}")）" >&2
echo "${GIT_NET_LAST_ERR}" >&2
exit 1
