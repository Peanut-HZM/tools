# 开源脱敏 + 配置统一化设计

**创建时间**：2026-08-16  
**状态**：待实施

## 概述

将当前项目准备开源到 GitHub，需要：
1. 收集所有敏感信息（服务器 IP、真实域名、数据库密码等）
2. 将敏感信息从代码中移除，统一放入 `.env` 配置文件
3. 提供 `*.env.example` 模板文件供开源用户使用
4. 部署脚本从 `.env` 读取配置，不再硬编码
5. 更新文档，明确配置步骤

## 目标

### 开源门槛
- **本地开发**：克隆后能基本跑起来（缺密钥不影响启动，只是对应功能不可用）
- **生产部署**：有清晰的文档说明如何配置

### 安全目标
- 代码中无硬编码的真实域名、IP、密码
- `.gitignore` 覆盖所有 `.env` 文件
- 部署脚本从 `.env` 读取配置

## 敏感信息清单

### 1. 真实域名（`peanuthzm.com.cn` 系列）

| 域名 | 用途 | 涉及文件 |
|------|------|---------|
| `tools.peanuthzm.com.cn` | 生产域名 | `deploy.py`, `local_deploy.sh`, `scripts/nginx_config.conf`, `scripts/setup_ssl.sh`, `backend/app/config/config.py` (CORS), `frontend/.env.production`, `mini-program/.env.*` |
| `ocr.peanuthzm.com.cn` | OCR 服务 | `backend/app/config/ocr_config.py`, `backend/app/config/asr_config.py`, `backend/.env.example` |
| `minio.peanuthzm.com.cn` | MinIO 服务 | `backend/app/config/config.py`, `backend/.env.example` |

### 2. 真实服务器 IP

| IP | 用途 | 涉及文件 |
|----|------|---------|
| `39.107.229.30` | 阿里云服务器 | `deploy.py`, `scripts/verify_deployment.sh`, `docs/README_DEPLOY.md` |

### 3. 真实数据库密码

| 密码 | 用途 | 涉及文件 |
|------|------|---------|
| `Peanut2817*#` | PostgreSQL postgres 用户密码 | 历史 spec 文档（已归档，无需处理） |

### 4. 硬编码的部署路径

| 路径 | 用途 | 涉及文件 |
|------|------|---------|
| `/data/www/tools` | 前端部署路径 | `deploy.py`, `local_deploy.sh`, `scripts/nginx_config.conf`, `scripts/setup_server.sh`, `scripts/tools-backend.service` |
| `/data/programs/tools` | 后端部署路径 | 同上 |
| `/data/programs/tools/data/users` | 用户数据 | `scripts/setup_server.sh`, `scripts/tools-backend.service` |
| `/data/programs/tools/data/history` | 历史记录 | `scripts/setup_server.sh` |
| `/data/programs/tools/temp` | 临时文件 | `scripts/setup_server.sh` |

### 5. 硬编码的服务名

| 服务名 | 用途 | 涉及文件 |
|--------|------|---------|
| `tools-backend.service` | systemd 服务名 | `deploy.py`, `local_deploy.sh`, `scripts/setup_server.sh`, `scripts/tools-backend.service`, `scripts/verify_deployment.sh` |

## 配置架构

采用**分层 `.env` 文件**方案，三个目录各管理各自的配置：

| 文件 | 位置 | 用途 | 示例内容 |
|------|------|------|---------|
| `backend/.env.example` | `backend/` | 后端配置 | JWT_SECRET_KEY, DB_ENCRYPTION_KEY, ALIYUN_OSS_*, MINIO_*, REDIS_*, CORS_ORIGINS, OCR_API_URL, ASR_API_URL, DATABASE_URL |
| `frontend/.env.example` | `frontend/` | 前端配置 | VITE_API_BASE_URL, VITE_APP_TITLE |
| `deploy.env.example` | 根目录 | 部署脚本专用 | SERVER_HOST, SERVER_USER, FRONTEND_DEPLOY_PATH, BACKEND_DEPLOY_PATH, DOMAIN, BACKEND_SERVICE, BACKEND_PORT |

### 配置加载优先级

1. **后端**：`backend/.env` → 环境变量 → 代码默认值
2. **前端**：Vite 自动加载 `.env.development` / `.env.production`
3. **部署脚本**：`deploy.env`（根目录）→ 环境变量 → 代码默认值

## 代码改造详情

### 1. `deploy.py` 改造

**改造前**：
```python
SERVER_HOST = "39.107.229.30"
SERVER_USER = "root"
FRONTEND_DEPLOY_PATH = "/data/www/tools"
BACKEND_DEPLOY_PATH = "/data/programs/tools"
DOMAIN = "tools.peanuthzm.com.cn"
BACKEND_SERVICE = "tools-backend.service"
```

**改造后**：
```python
from pathlib import Path
from dotenv import load_dotenv
import os

# 加载 deploy.env（可选，不存在则使用环境变量或默认值）
deploy_env = Path(__file__).parent / "deploy.env"
if deploy_env.exists():
    load_dotenv(deploy_env)

# 从环境变量读取，提供安全默认值
SERVER_HOST = os.getenv("SERVER_HOST", "")
SERVER_USER = os.getenv("SERVER_USER", "root")
FRONTEND_DEPLOY_PATH = os.getenv("FRONTEND_DEPLOY_PATH", "/data/www/tools")
BACKEND_DEPLOY_PATH = os.getenv("BACKEND_DEPLOY_PATH", "/data/programs/tools")
DOMAIN = os.getenv("DOMAIN", "localhost")
BACKEND_SERVICE = os.getenv("BACKEND_SERVICE", "tools-backend.service")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "19092"))

# 校验必填项
if not SERVER_HOST:
    print("错误: SERVER_HOST 未配置，请复制 deploy.env.example 为 deploy.env 并填入配置")
    sys.exit(1)
```

### 2. `local_deploy.sh` 改造

**改造前**：
```bash
FRONTEND_DEPLOY="/data/www/tools"
BACKEND_DEPLOY="/data/programs/tools"
DOMAIN="tools.peanuthzm.com.cn"
BACKEND_SERVICE="tools-backend.service"
```

**改造后**：
```bash
# 加载 deploy.env
if [ -f "${PROJECT_ROOT}/deploy.env" ]; then
    set -a
    source "${PROJECT_ROOT}/deploy.env"
    set +a
else
    echo "错误: 未找到 deploy.env，请复制 deploy.env.example 并填入配置"
    exit 1
fi

# 从环境变量读取，提供默认值
FRONTEND_DEPLOY="${FRONTEND_DEPLOY:-/data/www/tools}"
BACKEND_DEPLOY="${BACKEND_DEPLOY:-/data/programs/tools}"
DOMAIN="${DOMAIN:-localhost}"
BACKEND_SERVICE="${BACKEND_SERVICE:-tools-backend.service}"
FRONTEND_API_BASE_URL="https://${DOMAIN}/api"
```

### 3. `backend/app/config/config.py` 改造

**改造前**：
```python
CORS_ORIGINS: str = "http://localhost:5173,...,https://tools.peanuthzm.com.cn"
```

**改造后**：
```python
CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174,...,http://localhost:5190"
# 生产环境通过 .env 追加: https://tools.peanuthzm.com.cn
```

**注意**：保留 localhost 默认值用于开发，生产域名通过 `.env` 追加。

### 4. `backend/app/config/ocr_config.py` 改造

**改造前**：
```python
OCR_API_URL: str = "https://ocr.peanuthzm.com.cn/umi-ocr"
```

**改造后**：
```python
OCR_API_URL: str = ""  # 默认为空，生产环境通过 .env 配置
```

### 5. `backend/app/config/asr_config.py` 改造

**改造前**：
```python
ASR_API_URL: str = "https://ocr.peanuthzm.com.cn"
```

**改造后**：
```python
ASR_API_URL: str = ""  # 默认为空，生产环境通过 .env 配置
```

### 6. `backend/.env.example` 更新

**补充缺失项**：
```bash
# JWT 密钥（生产环境必须修改！运行: python scripts/generate_keys.py）
JWT_SECRET_KEY=dev-jwt-secret-change-me
DB_ENCRYPTION_KEY=dev-db-encryption-change-me

# MinIO（如使用 minio 则必填）
MINIO_ENDPOINT=minio.example.com  # 改为占位符
MINIO_API_ENDPOINT=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET_NAME=tools-files
MINIO_SECURE=true

# OCR / ASR 服务（可选，如使用则必填）
OCR_API_URL=
OCR_API_KEY=
OCR_API_SECRET=
ASR_API_URL=
ASR_API_KEY=
```

### 7. `frontend/.env.example` 创建

```bash
# 开发环境配置
# 使用 npm run dev 时自动加载

# API 地址（Vite 开发服务器代理目标）
VITE_API_PROXY_TARGET=http://127.0.0.1:19092

# 前端标题
VITE_APP_TITLE=工具箱开发
```

### 8. `frontend/.env.production.example` 创建（可选）

```bash
# 生产环境配置
# 使用 npm run build 时自动加载
# 注意：deploy.py 部署时会通过环境变量覆盖此配置

# API 地址（生产环境使用绝对地址，根据实际域名修改）
VITE_API_BASE_URL=https://your-domain.com/api

# 前端标题
VITE_APP_TITLE=工具箱
```

### 9. `deploy.env.example` 创建（根目录）

```bash
# 部署脚本配置文件
# 复制此文件为 deploy.env 并填入实际配置

# 服务器配置
SERVER_HOST=your-server-ip
SERVER_USER=root

# 部署路径
FRONTEND_DEPLOY_PATH=/data/www/tools
BACKEND_DEPLOY_PATH=/data/programs/tools

# 域名（用于前端构建和验证）
DOMAIN=your-domain.com

# 后端服务配置
BACKEND_SERVICE=tools-backend.service
BACKEND_PORT=19092
```

## `.gitignore` 更新

```gitignore
# 真实配置文件（绝不提交）
.env
.env.local
.env.*.local
backend/.env
frontend/.env
deploy.env
mini-program/.env

# 部署相关（可选，如果不想暴露部署配置）
deploy.env
```

**保留**：
```gitignore
# 示例配置文件（提交到仓库）
*.env.example
```

## 文档更新

### 1. `README.md` 更新

在"快速开始"章节前添加"配置"章节：

```markdown
## 🔧 配置

### 1. 复制配置文件

```bash
# 后端配置
cd backend
cp .env.example .env
# 编辑 .env，填入你的配置（JWT 密钥、数据库、OSS/MinIO 等）

# 前端配置（可选，开发环境使用默认值即可）
cd ../frontend
cp .env.example .env  # 如需要修改
```

### 2. 生成密钥（生产环境）

```bash
cd backend
python scripts/generate_keys.py
# 将生成的密钥填入 .env
```

### 3. 启动服务

```bash
# 回到项目根目录
cd ..
python dev-services.py
```

## 📦 生产部署

详见 [DEPLOYMENT.md](DEPLOYMENT.md)
```

### 2. `DEPLOYMENT.md` 更新

添加"配置部署脚本"章节：

```markdown
## 3. 配置部署脚本

在本地开发机器上，复制部署配置模板：

```bash
cp deploy.env.example deploy.env
# 编辑 deploy.env，填入你的服务器 IP、域名、部署路径等
```

### 4. 执行部署

```bash
# 远程部署（SSH）
python deploy.py

# 本地部署（在服务器上执行）
./local_deploy.sh
```
```

### 3. 删除或归档敏感文档

- `docs/README_DEPLOY.md`：包含真实 IP、域名、路径，**必须删除或重写**
- `docs/README_DEPLOY.md` 中的示例命令包含真实 IP，需要替换为占位符

## 实施步骤

### 阶段 1：配置文件改造

1. **创建 `deploy.env.example`**（根目录）
   - 定义所有部署相关配置项
   - 添加注释说明

2. **更新 `backend/.env.example`**
   - 补充缺失项（JWT_SECRET_KEY 等）
   - 将真实域名改为占位符

3. **创建 `frontend/.env.example`**
   - 定义前端配置项

4. **更新 `.gitignore`**
   - 确保覆盖所有 `.env` 文件
   - 保留 `*.env.example`

### 阶段 2：代码脱敏

5. **改造 `deploy.py`**
   - 从 `deploy.env` 读取配置
   - 移除硬编码的 IP、域名、路径
   - 添加配置校验

6. **改造 `local_deploy.sh`**
   - 从 `deploy.env` 读取配置
   - 移除硬编码的域名、路径、服务名

7. **改造 `backend/app/config/config.py`**
   - CORS 中移除真实域名
   - 保留 localhost 默认值

8. **改造 `backend/app/config/ocr_config.py`**
   - 默认 URL 改为空字符串

9. **改造 `backend/app/config/asr_config.py`**
   - 默认 URL 改为空字符串

10. **更新 `scripts/` 目录下的配置模板**
    - `scripts/nginx_config.conf`：域名改为占位符
    - `scripts/setup_server.sh`：路径改为可配置
    - `scripts/tools-backend.service`：路径改为可配置
    - `scripts/verify_deployment.sh`：从环境变量读取

11. **删除或重写 `docs/README_DEPLOY.md`**
    - 移除所有真实 IP、域名
    - 或完全重写为通用部署指南

### 阶段 3：文档更新

12. **更新 `README.md`**
    - 添加"配置"章节
    - 添加"生产部署"链接

13. **更新 `DEPLOYMENT.md`**
    - 添加"配置部署脚本"章节
    - 说明如何使用 `deploy.env`

14. **更新 `mini-program/.env.*`**
    - 域名改为占位符

### 阶段 4：验证

15. **本地验证**
    - 克隆仓库到新目录
    - 复制 `.env.example` 为 `.env`
    - 启动服务，验证能正常运行

16. **脱敏验证**
    - `grep -r "peanuthzm" .` 确认无真实域名
    - `grep -r "39.107.229" .` 确认无真实 IP
    - `grep -r "Peanut2817" .` 确认无真实密码

17. **Git 历史清理（可选）**
    - 使用 `git filter-repo` 清理历史提交中的敏感信息
    - 或创建新仓库，只提交当前代码

## 验证清单

- [ ] 代码中无硬编码域名 `peanuthzm.com.cn`
- [ ] 代码中无硬编码 IP `39.107.229.30`
- [ ] 代码中无硬编码密码 `Peanut2817*#`
- [ ] `.gitignore` 覆盖所有 `.env` 文件
- [ ] 提供 `*.env.example` 模板
- [ ] 部署脚本从 `.env` 读取配置
- [ ] README 说明配置步骤
- [ ] DEPLOYMENT.md 说明部署步骤
- [ ] 本地能基本运行（缺密钥不影响启动）
- [ ] 生产部署文档清晰

## 风险与注意事项

### 1. 历史提交泄露

**风险**：即使当前代码已脱敏，历史提交中仍可能包含敏感信息。

**解决方案**：
- 方案 A：使用 `git filter-repo` 清理历史（复杂，可能破坏其他分支）
- 方案 B：创建新仓库，只提交当前代码（简单，丢失历史）
- 方案 C：保持现状，但在 README 中说明"历史提交包含敏感信息，仅供参考"

**推荐**：方案 B（创建新仓库）

### 2. 配置兼容性

**风险**：改造后，现有部署可能无法正常工作。

**解决方案**：
- 在 README 中说明配置步骤
- 提供迁移指南（从旧配置到新配置）
- 部署脚本添加配置校验，缺失时给出明确提示

### 3. 开发体验

**风险**：开源用户克隆后无法立即运行。

**解决方案**：
- 确保默认配置能让服务启动（即使部分功能不可用）
- README 明确说明"复制 .env.example 为 .env"
- 提供开发环境快速启动指南

## 附录

### A. 配置文件对照表

| 配置项 | 旧位置 | 新位置 |
|--------|--------|--------|
| `SERVER_HOST` | `deploy.py` 硬编码 | `deploy.env` |
| `SERVER_USER` | `deploy.py` 硬编码 | `deploy.env` |
| `DOMAIN` | `deploy.py`, `local_deploy.sh` 硬编码 | `deploy.env` |
| `FRONTEND_DEPLOY_PATH` | `deploy.py`, `local_deploy.sh` 硬编码 | `deploy.env` |
| `BACKEND_DEPLOY_PATH` | `deploy.py`, `local_deploy.sh` 硬编码 | `deploy.env` |
| `BACKEND_SERVICE` | `deploy.py`, `local_deploy.sh` 硬编码 | `deploy.env` |
| `JWT_SECRET_KEY` | `backend/.env` | `backend/.env`（保留） |
| `CORS_ORIGINS` | `backend/app/config/config.py` 硬编码域名 | `backend/.env` 追加 |
| `OCR_API_URL` | `backend/app/config/ocr_config.py` 硬编码 | `backend/.env` |
| `ASR_API_URL` | `backend/app/config/asr_config.py` 硬编码 | `backend/.env` |

### B. 脱敏检查命令

```bash
# 检查真实域名
grep -r "peanuthzm" . --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=venv

# 检查真实 IP
grep -r "39.107.229" . --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=venv

# 检查真实密码
grep -r "Peanut2817" . --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=venv
```
