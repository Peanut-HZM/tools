#!/usr/bin/env bash
# lib-git-auth.sh — merge-branch 技能共用的远端认证自愈与错误分类助手。
# 设计背景（2026-09-18 事故）：非交互环境（CI / agent 沙箱）里 ssh-agent 与
# macOS Keychain 常不可用，`git fetch/push` 直接 Permission denied (publickey)。
# 且 ~/.ssh/config 常用别名块（Host geek + HostName 真实主机名），`ssh -G 真实主机`
# 解析不到块内 IdentityFile。本库：
#   1) 同时从「config 中 HostName==目标主机的块」与 `ssh -G` 结果收集候选私钥；
#   2) 默认方式失败后，逐个候选私钥以 GIT_SSH_COMMAND 显式重试。
# 本文件只定义函数，不设置 set 选项，不执行任何动作；由调用方 source。

_LIBAUTH_SSH_CONFIG="${LIBAUTH_SSH_CONFIG:-$([ -f "$HOME/.ssh/config" ] && echo "$HOME/.ssh/config")}"

# 解析 git 远端 URL 的主机名（仅 ssh 形态；https 等返回空）。
#   ssh://git@host:port/path  -> host
#   git@host:path             -> host
_libauth_url_host() {
    local url="$1"
    [ -z "${url}" ] && return 0
    case "${url}" in
        ssh://*|*@*:*)
            printf '%s\n' "${url}" | sed -E 's#^(ssh://)?([^@/]+@)?([^/:]+).*$#\3#'
            ;;
    esac
}

# 展开路径前缀 ~ 并校验私钥存在；存在才输出。
_libauth_normalize_key() {
    local key="$1"
    [ -z "${key}" ] && return 0
    key="${key/#\~/$HOME}"
    [ -f "${key}" ] && printf '%s\n' "${key}"
}

# 收集某主机的候选私钥（去重，按优先级排序）：
#   1) ~/.ssh/config 中 HostName 等于该主机的块内 IdentityFile（别名块也能命中）
#   2) `ssh -G <host>` 的 identityfile 列表（含通配 Host 块与默认值）
_libauth_identity_candidates() {
    local host="$1" conf="$_LIBAUTH_SSH_CONFIG"
    [ -z "${host}" ] && return 0
    {
        if [ -n "${conf}" ] && [ -f "${conf}" ]; then
            awk -v host="${host}" '
                tolower($1) == "host" { inblock = 0; next }
                tolower($1) == "match" { inblock = 0; next }
                tolower($1) == "hostname" && $2 == host { inblock = 1; next }
                inblock && tolower($1) == "identityfile" { print $2 }
            ' "${conf}" 2>/dev/null
        fi
        ssh -G "${host}" 2>/dev/null | awk 'tolower($1) == "identityfile" { print $2 }'
    } | awk '!seen[$0]++'
}

# 生成该远端可用的 GIT_SSH_COMMAND 前缀列表（每行一条）；无候选时输出空。
_libauth_ssh_commands() {
    local url="$1" host key
    [ -z "${url}" ] && return 0
    host="$(_libauth_url_host "${url}")"
    [ -z "${host}" ] && return 0
    while IFS= read -r key; do
        [ -z "${key}" ] && continue
        printf 'ssh -i %s -o IdentitiesOnly=yes\n' "${key}"
    done < <(_libauth_identity_candidates "${host}")
}

# 按 stderr 关键字分类 git 远端操作失败原因（供报告与决策使用）。
classify_git_error() {
    local stderr_content="$1"
    if echo "${stderr_content}" | grep -qE "Could not resolve host|fatal: unable to access"; then
        echo "URL 配置错误"
    elif echo "${stderr_content}" | grep -qE "Connection refused|timed out|Network is unreachable"; then
        echo "网络问题"
    elif echo "${stderr_content}" | grep -qE "could not read Username|Permission denied \(publickey\)|Repository not found"; then
        echo "凭证问题"
    elif echo "${stderr_content}" | grep -qE "non-fast-forward|fetch first|Updates were rejected"; then
        echo "远端基线已更新"
    else
        echo "未知"
    fi
}

# 带自愈重试的 git fetch。
# 用法：git_fetch_with_retry <remote|URL>   （在目标仓库目录内调用）
# 成功返回 0；失败把最后一次 stderr 写入全局变量 GIT_NET_LAST_ERR 并返回 1。
GIT_NET_LAST_ERR=""
git_fetch_with_retry() {
    local target="${1:-origin}" url ssh_prefix
    GIT_NET_LAST_ERR=""
    url="$(git remote get-url "${target}" 2>/dev/null || printf '%s' "${target}")"
    if GIT_NET_LAST_ERR="$(git fetch "${target}" 2>&1)"; then
        return 0
    fi
    while IFS= read -r ssh_prefix; do
        [ -z "${ssh_prefix}" ] && continue
        echo "WARN: git fetch ${target} 失败（$(classify_git_error "${GIT_NET_LAST_ERR}")），使用 ${ssh_prefix} 重试" >&2
        if GIT_NET_LAST_ERR="$(GIT_SSH_COMMAND="${ssh_prefix}" git fetch "${target}" 2>&1)"; then
            return 0
        fi
    done < <(_libauth_ssh_commands "${url}")
    return 1
}

# 带自愈重试的 git push。
# 用法：git_push_with_retry <remote|URL> <refspec>
# 成功返回 0；失败把最后一次 stderr 写入全局变量 GIT_NET_LAST_ERR 并返回 1。
git_push_with_retry() {
    local target="$1" refspec="$2" url ssh_prefix
    GIT_NET_LAST_ERR=""
    url="$(git remote get-url "${target}" 2>/dev/null || printf '%s' "${target}")"
    if GIT_NET_LAST_ERR="$(git push "${target}" "${refspec}" 2>&1)"; then
        return 0
    fi
    # 非快进不是凭证问题，换私钥重试只会把真正的拒绝原因盖掉
    if [ "$(classify_git_error "${GIT_NET_LAST_ERR}")" = "远端基线已更新" ]; then
        return 1
    fi
    while IFS= read -r ssh_prefix; do
        [ -z "${ssh_prefix}" ] && continue
        echo "WARN: git push ${target} ${refspec} 失败（$(classify_git_error "${GIT_NET_LAST_ERR}")），使用 ${ssh_prefix} 重试" >&2
        if GIT_NET_LAST_ERR="$(GIT_SSH_COMMAND="${ssh_prefix}" git push "${target}" "${refspec}" 2>&1)"; then
            return 0
        fi
    done < <(_libauth_ssh_commands "${url}")
    return 1
}
