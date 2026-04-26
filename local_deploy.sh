#!/bin/bash
# ==============================================================================
# 本地部署脚本 - 将工具箱项目部署到当前服务器
# 与 deploy.py 功能相同，但无需 SSH/SCP，直接在本地操作
# ==============================================================================

set -e

# ==============================================================================
# 配置常量
# ==============================================================================

# 项目路径（自动检测脚本所在目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"
FRONTEND_SRC="${PROJECT_ROOT}/frontend"
BACKEND_SRC="${PROJECT_ROOT}/backend"

# 部署目标路径
FRONTEND_DEPLOY="/data/www/tools"
BACKEND_DEPLOY="/data/programs/tools"

# 后端 systemd 服务名
BACKEND_SERVICE="tools-backend.service"

# 域名（用于验证）
DOMAIN="tools.peanuthzm.com.cn"

# 前端构建环境变量
FRONTEND_API_BASE_URL="https://${DOMAIN}/api"

# 后端排除模式（与 deploy.py 保持一致）
BACKEND_EXCLUDE=(
    "__pycache__"
    "*.pyc"
    ".pytest_cache"
    "venv"
    "*.db"
    "*.log"
    "temp"
    "tests"
    ".DS_Store"
    "*.egg-info"
    ".mypy_cache"
)

# 备份配置
BACKUP_DIR="/tmp/tools_backend_backups"
MAX_BACKUPS=5

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ==============================================================================
# 辅助函数
# ==============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "\n${BOLD}${CYAN}========================================${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}========================================${NC}\n"
}

log_step() {
    echo -e "${CYAN}  ▶ $1${NC}"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "需要命令 '$1'，但未找到。请先安装。"
        exit 1
    fi
}

# 检查目录是否存在
check_directory() {
    if [ ! -d "$1" ]; then
        log_error "目录不存在: $1"
        exit 1
    fi
}

# 检查文件是否存在
check_file() {
    if [ ! -f "$1" ]; then
        log_error "文件不存在: $1"
        exit 1
    fi
}

# ==============================================================================
# 前端部署
# ==============================================================================

deploy_frontend() {
    log_section "开始部署前端"

    # 1. 检查源目录
    log_step "检查前端源目录..."
    check_directory "${FRONTEND_SRC}"
    check_file "${FRONTEND_SRC}/package.json"

    # 2. 安装依赖
    log_step "安装前端依赖..."
    cd "${FRONTEND_SRC}"
    npm install --legacy-peer-deps
    log_success "前端依赖安装完成"

    # 3. 构建前端
    log_step "构建前端项目 (API: ${FRONTEND_API_BASE_URL})..."
    VITE_API_BASE_URL="${FRONTEND_API_BASE_URL}" npm run build
    log_success "前端构建完成"

    # 4. 验证构建结果
    check_directory "${FRONTEND_SRC}/dist"
    check_file "${FRONTEND_SRC}/dist/index.html"

    # 5. 原子替换部署文件
    log_step "替换前端部署文件..."
    
    # 构建到临时目录
    TEMP_DIR=$(mktemp -d /tmp/frontend_deploy.XXXXXX)
    cp -r "${FRONTEND_SRC}/dist/"* "${TEMP_DIR}/"
    
    # 验证临时目录内容
    if [ ! -f "${TEMP_DIR}/index.html" ]; then
        log_error "临时目录验证失败"
        rm -rf "${TEMP_DIR}"
        exit 1
    fi

    # 确保目标目录存在
    mkdir -p "${FRONTEND_DEPLOY}"

    # 备份当前部署（用于回滚）
    if [ "$(ls -A ${FRONTEND_DEPLOY} 2>/dev/null)" ]; then
        FRONTEND_BACKUP="/tmp/frontend_backup_$(date +%Y%m%d_%H%M%S)"
        cp -r "${FRONTEND_DEPLOY}" "${FRONTEND_BACKUP}"
        log_info "当前前端已备份到: ${FRONTEND_BACKUP}"
    fi

    # 原子替换：先清空，再复制
    rm -rf "${FRONTEND_DEPLOY:?}/"*
    cp -r "${TEMP_DIR}/"* "${FRONTEND_DEPLOY}/"
    rm -rf "${TEMP_DIR}"

    log_success "前端文件部署完成: ${FRONTEND_DEPLOY}"

    # 6. 验证部署结果
    if [ ! -f "${FRONTEND_DEPLOY}/index.html" ]; then
        log_error "前端部署验证失败: index.html 不存在"
        exit 1
    fi
    
    local file_count=$(find "${FRONTEND_DEPLOY}" -type f | wc -l)
    log_success "前端部署验证通过: ${file_count} 个文件"
}

# ==============================================================================
# 后端部署
# ==============================================================================

deploy_backend() {
    log_section "开始部署后端"

    # 1. 检查源目录
    log_step "检查后端源目录..."
    check_directory "${BACKEND_SRC}"
    check_file "${BACKEND_SRC}/requirements.txt"
    check_directory "${BACKEND_SRC}/app"

    # 2. 确保部署目录存在
    mkdir -p "${BACKEND_DEPLOY}"

    # 3. 创建备份
    log_step "创建后端备份..."
    mkdir -p "${BACKUP_DIR}"
    local backup_name="backup_$(date +%Y%m%d_%H%M%S)"
    local backup_path="${BACKUP_DIR}/${backup_name}"
    
    if [ -d "${BACKEND_DEPLOY}/app" ]; then
        cp -r "${BACKEND_DEPLOY}" "${backup_path}"
        log_success "后端已备份: ${backup_path}"
    else
        log_warn "后端部署目录为空，跳过备份（首次部署）"
    fi

    # 4. 清理旧备份（保留最近 MAX_BACKUPS 个）
    cleanup_old_backups

    # 5. 准备排除列表
    log_step "准备文件排除列表..."
    local rsync_exclude=""
    for pattern in "${BACKEND_EXCLUDE[@]}"; do
        rsync_exclude="${rsync_exclude}--exclude=${pattern} "
    done

    # 6. 同步文件（排除不需要的文件）
    log_step "同步后端文件到部署目录..."
    rsync -avz --delete \
        ${rsync_exclude} \
        "${BACKEND_SRC}/" \
        "${BACKEND_DEPLOY}/"
    
    log_success "后端文件同步完成"

    # 7. 写入部署时间戳
    log_step "写入部署时间戳..."
    local deploy_timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S")
    echo "{\"timestamp\": \"${deploy_timestamp}\"}" > "${BACKEND_DEPLOY}/.deploy_timestamp"
    log_success "部署时间戳已记录: ${deploy_timestamp}"

    # 8. 安装 Python 依赖
    log_step "安装 Python 依赖..."
    cd "${BACKEND_DEPLOY}"
    
    # 检查并使用现有虚拟环境
    local venv_python=""
    if [ -f "venv/bin/python" ]; then
        venv_python="venv/bin/python"
        log_info "使用现有虚拟环境: venv/bin/python"
    elif [ -f "/usr/bin/python3" ]; then
        # 没有 venv，创建一个新的
        log_warn "未找到虚拟环境，正在创建..."
        python3 -m venv venv
        venv_python="venv/bin/python"
    else
        log_error "未找到 Python3，无法安装依赖"
        exit 1
    fi

    # 升级 pip 并安装依赖
    "${venv_python}" -m pip install --upgrade pip
    "${venv_python}" -m pip install -r requirements.txt
    log_success "Python 依赖安装完成"

    # 8. 清理 Python 缓存
    log_step "清理 Python 缓存..."
    find "${BACKEND_DEPLOY}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "${BACKEND_DEPLOY}" -type f -name "*.pyc" -delete 2>/dev/null || true
}

# ==============================================================================
# 服务管理
# ==============================================================================

restart_backend_service() {
    log_section "重启后端服务"

    log_step "检查 systemd 服务..."
    
    if systemctl list-unit-files | grep -q "${BACKEND_SERVICE}"; then
        log_step "重启 ${BACKEND_SERVICE}..."
        systemctl restart "${BACKEND_SERVICE}"
        sleep 3
        
        # 检查服务状态
        if systemctl is-active --quiet "${BACKEND_SERVICE}"; then
            log_success "后端服务运行正常"
            systemctl status "${BACKEND_SERVICE}" --no-pager -l
        else
            log_error "后端服务启动失败！"
            log_error "请检查日志: journalctl -u ${BACKEND_SERVICE} -n 50 --no-pager"
            exit 1
        fi
    else
        log_warn "systemd 服务 ${BACKEND_SERVICE} 未找到"
        log_warn "可能需要手动启动后端服务"
    fi
}

# ==============================================================================
# 部署验证
# ==============================================================================

verify_deployment() {
    log_section "验证部署"

    local errors=0

    # 1. 检查前端文件
    log_step "检查前端部署..."
    if [ -f "${FRONTEND_DEPLOY}/index.html" ]; then
        log_success "前端 index.html 存在"
    else
        log_error "前端 index.html 不存在"
        errors=$((errors + 1))
    fi

    # 2. 检查后端文件
    log_step "检查后端部署..."
    if [ -f "${BACKEND_DEPLOY}/app/main.py" ]; then
        log_success "后端 main.py 存在"
    else
        log_error "后端 main.py 不存在"
        errors=$((errors + 1))
    fi

    if [ -f "${BACKEND_DEPLOY}/requirements.txt" ]; then
        log_success "后端 requirements.txt 存在"
    else
        log_error "后端 requirements.txt 不存在"
        errors=$((errors + 1))
    fi

    # 3. 检查后端服务状态
    log_step "检查后端服务状态..."
    if systemctl is-active --quiet "${BACKEND_SERVICE}" 2>/dev/null; then
        log_success "后端服务运行中"
    else
        log_warn "后端服务未运行（可能未配置 systemd 服务）"
    fi

    # 4. 检查 Nginx 配置
    log_step "检查 Nginx 配置..."
    if command -v nginx &> /dev/null; then
        if nginx -t 2>/dev/null; then
            log_success "Nginx 配置正常"
        else
            log_error "Nginx 配置有错误！"
            errors=$((errors + 1))
        fi
    else
        log_warn "Nginx 未安装（可能使用其他反向代理）"
    fi

    # 5. 测试 API 端点
    log_step "测试 API 端点..."
    local api_response=$(curl -s -o /dev/null -w "%{http_code}" "https://${DOMAIN}/api/tools" --insecure 2>/dev/null || echo "000")
    if [ "${api_response}" = "200" ]; then
        log_success "API 端点响应正常 (HTTP ${api_response})"
    else
        log_warn "API 端点响应异常 (HTTP ${api_response})"
    fi

    # 6. 测试前端访问
    log_step "测试前端访问..."
    local web_response=$(curl -s -o /dev/null -w "%{http_code}" "https://${DOMAIN}/" --insecure 2>/dev/null || echo "000")
    if [ "${web_response}" = "200" ]; then
        log_success "前端访问正常 (HTTP ${web_response})"
    else
        log_warn "前端访问异常 (HTTP ${web_response})"
    fi

    # 总结
    echo ""
    if [ ${errors} -eq 0 ]; then
        log_success "部署验证全部通过！"
    else
        log_error "发现 ${errors} 个错误，请检查上述日志"
    fi
}

# ==============================================================================
# 备份清理
# ==============================================================================

cleanup_old_backups() {
    if [ ! -d "${BACKUP_DIR}" ]; then
        return
    fi

    local backup_count=$(ls -1d "${BACKUP_DIR}"/backup_* 2>/dev/null | wc -l)
    if [ ${backup_count} -gt ${MAX_BACKUPS} ]; then
        log_step "清理旧备份（保留最近 ${MAX_BACKUPS} 个）..."
        ls -1d "${BACKUP_DIR}"/backup_* | sort | head -n $((backup_count - MAX_BACKUPS)) | xargs rm -rf
        log_success "旧备份已清理"
    fi
}

# ==============================================================================
# 主函数
# ==============================================================================

main() {
    # 解析参数
    local frontend_only=false
    local backend_only=false
    local no_restart=false
    local dry_run=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --frontend-only)
                frontend_only=true
                shift
                ;;
            --backend-only)
                backend_only=true
                shift
                ;;
            --no-restart)
                no_restart=true
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            -h|--help)
                echo "用法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  --frontend-only    仅部署前端"
                echo "  --backend-only     仅部署后端"
                echo "  --no-restart       部署后不重启服务"
                echo "  --dry-run          模拟运行（不实际操作）"
                echo "  -h, --help         显示帮助"
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done

    # 标题
    log_section "工具箱本地部署"
    echo -e "  ${BOLD}项目目录:${NC} ${PROJECT_ROOT}"
    echo -e "  ${BOLD}前端部署:${NC} ${FRONTEND_DEPLOY}"
    echo -e "  ${BOLD}后端部署:${NC} ${BACKEND_DEPLOY}"
    echo -e "  ${BOLD}域名:${NC} https://${DOMAIN}"
    echo ""

    # Dry Run 模式
    if [ "${dry_run}" = true ]; then
        log_warn "=== 模拟运行模式（不会执行实际操作） ==="
        echo ""
        echo "  将执行的操作:"
        [ "${frontend_only}" = false ] && echo "    - 安装前端依赖并构建"
        [ "${frontend_only}" = false ] && echo "    - 替换 ${FRONTEND_DEPLOY} 内容"
        [ "${backend_only}" = false ] && echo "    - 备份 ${BACKEND_DEPLOY} 到 ${BACKUP_DIR}"
        [ "${backend_only}" = false ] && echo "    - 同步后端文件（排除: ${BACKEND_EXCLUDE[*]}）"
        [ "${backend_only}" = false ] && echo "    - 安装 Python 依赖"
        [ "${no_restart}" = false ] && [ "${backend_only}" = false ] && echo "    - 重启 ${BACKEND_SERVICE}"
        echo "    - 验证部署状态"
        echo ""
        log_success "模拟运行完成。如需实际部署，请移除 --dry-run 参数"
        exit 0
    fi

    # 检查必要命令
    log_step "检查必要命令..."
    check_command "npm"
    check_command "rsync"
    check_command "curl"

    # 开始部署
    local start_time=$(date +%s)

    # 部署前端
    if [ "${backend_only}" = false ]; then
        deploy_frontend
    fi

    # 部署后端
    if [ "${frontend_only}" = false ]; then
        deploy_backend
        
        # 重启服务
        if [ "${no_restart}" = false ]; then
            restart_backend_service
        else
            log_warn "跳过服务重启（--no-restart）"
        fi
    fi

    # 验证部署
    verify_deployment

    # 完成信息
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_section "部署完成"
    echo -e "  ${BOLD}耗时:${NC} ${duration} 秒"
    echo -e "  ${BOLD}前端:${NC} https://${DOMAIN}"
    echo -e "  ${BOLD}后端 API:${NC} https://${DOMAIN}/api"
    echo -e "  ${BOLD}API 文档:${NC} https://${DOMAIN}/docs"
    echo ""
    
    if [ "${no_restart}" = false ] && [ "${backend_only}" = false ]; then
        log_info "如需查看后端日志: journalctl -u ${BACKEND_SERVICE} -f"
    fi
}

# 执行主函数
main "$@"
