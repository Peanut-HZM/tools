# Tools 项目 Windows 常驻服务（NSSM）

把 Tools 项目的**后端**（FastAPI / uvicorn，端口 `19092`）与**前端**（Vite dev server，端口 `5178`）
分别注册为 Windows 服务，实现：

- 开机自动启动（`Start = SERVICE_AUTO_START`）
- 进程崩溃后自动拉起（`AppExit Default Restart` + `AppRestartDelay 5000`）
- 标准输出/错误输出落盘并按大小轮转
- 以 `LocalSystem` 运行，但注入真实用户目录环境变量，保证后端能读到 `%USERPROFILE%` 下的 Agent 数据

访问地址：**<http://localhost:5178/>**

---

## 1. 为什么是两个服务，而不是一个 `dev-services.py`

| 方案 | 问题 |
| --- | --- |
| 把 `dev-services.py` 整体托管给 NSSM | `dev-services.py` 会再 `subprocess` 派生子进程；NSSM 只能管住父进程，服务停止/重启时会留下脱离管控的孤儿进程，端口被占导致下次启动失败 |
| **后端、前端各注册一个服务（本方案）** | NSSM 直接托管真正的业务进程（`python -m uvicorn` / `node vite.js`），停止即停、崩溃即重启，无孤儿进程 |

配套约束：

- 后端**不用** `--reload`：uvicorn 的 reloader 会派生 reload 子进程，NSSM 管不住，且服务场景不需要热重载后端代码（更新走 `update` 动作重启）。
- 前端**用** Vite dev server：前端源码修改靠 Vite HMR 自动生效，无需重启服务。
- 端口严格对齐项目约定（`frontend/vite.config.ts` 中 `port: 5178`、`strictPort: true`），不另改端口。

---

## 2. 前置条件

| 依赖 | 说明 |
| --- | --- |
| NSSM | `scoop install nssm`（本机位于 `D:\Scoop\shims\nssm.exe`） |
| Python | `scoop install python312`，脚本会自动把 shim 解析成真实 `python.exe` |
| Node.js | `scoop install nodejs22` |
| 前端依赖 | `cd frontend; npm install`（`node_modules\vite\bin\vite.js` 必须存在） |
| 后端配置 | `backend/.env`（不入库，本地配置，缺失时脚本只告警不阻断） |

> 环境问题一律走 Scoop，不要手工下载解压。

---

## 3. 命令

脚本：`scripts\windows-service\tools-service.ps1`

```powershell
# 安装 / 更新服务配置并立即启动（需管理员，会弹 UAC）
powershell -ExecutionPolicy Bypass -File scripts\windows-service\tools-service.ps1 install

# 查看状态 + 端口 + 探活（普通权限即可）
powershell -ExecutionPolicy Bypass -File scripts\windows-service\tools-service.ps1 status

# 完整验收：服务状态 / 开机自启 / 端口 / HTTP / 崩溃自愈（需管理员）
powershell -ExecutionPolicy Bypass -File scripts\windows-service\tools-service.ps1 verify

# 日常控制
powershell -ExecutionPolicy Bypass -File scripts\windows-service\tools-service.ps1 start
powershell -ExecutionPolicy Bypass -File scripts\windows-service\tools-service.ps1 stop
powershell -ExecutionPolicy Bypass -File scripts\windows-service\tools-service.ps1 restart
powershell -ExecutionPolicy Bypass -File scripts\windows-service\tools-service.ps1 restart backend
powershell -ExecutionPolicy Bypass -File scripts\windows-service\tools-service.ps1 logs frontend

# 拉取远程更新 + 按需安装依赖 + 重启（需管理员）
powershell -ExecutionPolicy Bypass -File scripts\windows-service\tools-service.ps1 update

# 卸载服务（代码、日志、backend/.env 全部保留）
powershell -ExecutionPolicy Bypass -File scripts\windows-service\tools-service.ps1 uninstall
```

可选参数：

| 参数 | 作用 |
| --- | --- |
| `-Target all\|backend\|frontend` | 限定 `start` / `stop` / `restart` / `logs` 的作用对象，默认 `all` |
| `-Force` | `install` 时端口被其他进程占用仍然继续注册（默认中止） |
| `-SkipPortCheck` | `install` 时完全跳过端口占用检查 |
| `-NoRestart` | `update` 只拉代码/装依赖，不重启（新代码暂不生效） |
| `-SkipDeps` | `update` 跳过 `npm install` / `pip install` |

### 关于 UAC

`install` / `uninstall` / `start` / `stop` / `restart` / `update` / `verify` 需要管理员权限。
脚本会自己用 `Start-Process -Verb RunAs` 提权并在提权进程结束后，把管理日志尾部回显到当前控制台，
所以**普通终端里也能看到完整输出**，只需在弹出的 UAC 窗口点「是」。

`status` / `logs` 不需要提权。

---

## 4. 运行身份与环境变量

两个服务都以 `LocalSystem` 运行，但由 NSSM 注入下列环境变量，使其行为与前台运行时一致：

| 变量 | 值 | 原因 |
| --- | --- | --- |
| `USERPROFILE` / `HOME` | 安装时的真实用户目录（如 `C:\Users\<user>`） | `config.py` 的 `REAL_HOME` 与 `agent_readers/base.py` 的 `real_home()` 依赖 `%USERPROFILE%` 读取 `.claude` / `.codex` / `.kimi` 等 Agent 数据 |
| `HOMEDRIVE` / `HOMEPATH` | 拆分后的盘符与路径 | 同上，兼容 `expanduser("~")` |
| `APPDATA` / `LOCALAPPDATA` | 真实用户目录下 | 读取用户级工具数据（OpenCode、Codex 等） |
| `TEMP` / `TMP` | 真实用户临时目录 | 避免 SYSTEM 的 `C:\Windows\Temp` 权限差异 |
| `PATH` | Python / Node 真实目录 + `D:\Scoop\shims` + 原 PATH | 子进程能找到 `npm`、`nssm` 等命令 |
| `PYTHONIOENCODING` / `PYTHONUTF8` | `utf-8` / `1`（仅后端） | 中文日志不乱码 |

> 这解决了「服务以 SYSTEM 运行时 `Path.home()` 指向 `C:\Windows\system32\config\systemprofile`、
> 导致 Token 消耗统计读不到本机 Agent 数据」的问题。

---

## 5. 日志

| 文件 | 内容 |
| --- | --- |
| `logs\windows-service.log` | 脚本自身的每个动作与探测过程（含崩溃自愈逐次探测） |
| `logs\service-backend.out.log` / `.err.log` | 后端 stdout / stderr |
| `logs\service-frontend.out.log` / `.err.log` | 前端 stdout / stderr |

- NSSM 在 10MB 时自动轮转（`AppRotateFiles 1`、`AppRotateOnline 1`、`AppRotateBytes 10485760`）。
- `logs/` 与 `*.log` 已被 `.gitignore` 忽略，不会进仓库。

---

## 6. 更新流程（`update`）

1. `git fetch --all --prune`
2. 若 `HEAD..origin/master` 有提交：`git pull --rebase --autostash origin master`（自动暂存并恢复本地未提交改动）
3. 对比更新前后差异，判断是否需要装依赖：
   - `frontend/package.json` 或 `frontend/package-lock.json` 变化 → `npm install`
   - `backend/requirements.txt` 变化 → `pip install -r requirements.txt`
4. 重启服务（`-NoRestart` 可跳过）

失败即中止并保留服务当前状态，不会带着半截代码重启。

---

## 7. 验收（`verify`）

`verify` 会依次检查 5 组，全部通过才返回 `0`：

1. 两个服务存在、`Running`、`StartType=Automatic`、崩溃策略为 `Restart`
2. 端口 `19092` / `5178` 监听
3. 后端直连 `http://localhost:19092/api/v1/health` 返回 `healthy`
4. 前端首页返回 HTML，且 `http://localhost:5178/api/v1/health`（经 Vite 代理）返回 `healthy`
5. **崩溃自愈**：强杀端口对应进程，等待服务自动拉起并恢复 HTTP 探活

> 探活统一使用 `http://localhost:...`：Vite 默认只监听 `::1`（IPv6 回环），
> 用 `127.0.0.1` 会连不上；uvicorn 监听 `127.0.0.1`，`localhost` 同样可达。
>
> 崩溃自愈判定以「服务 `Running` + HTTP 探活通过」为准，不强制要求 `Get-NetTCPConnection`
> 立刻查到监听（实测存在瞬时查不到、但端口已可访问的情况）。

---

## 8. 故障排查

| 现象 | 排查 |
| --- | --- |
| `install` 报端口被占用 | `Get-NetTCPConnection -LocalPort 5178 -State Listen` 查 PID；先停掉占用进程（可能是遗留的 dev server），或 `-Force` 强制安装 |
| 服务 `Running` 但页面打不开 | 看 `logs\service-frontend.err.log`；确认 `frontend\node_modules` 完整 |
| 后端启动失败 | 看 `logs\service-backend.err.log`，常见为 `backend/.env` 缺失或 Python 依赖未装 |
| Token 统计读不到本机数据 | `nssm get ToolsBackend AppEnvironmentExtra` 确认 `USERPROFILE` 是真实用户目录；若是 SYSTEM 默认值，重新执行 `install` |
| 前端只监听 `::1` | 正常现象（Vite 默认 `host: localhost`），访问用 `http://localhost:5178/`，不要用 `127.0.0.1` |

---

## 9. 与 Linux 部署的关系

`scripts/tools-backend.service` 是 Linux systemd 版本（服务器部署用），本目录脚本是**本机 Windows 常驻**版本，
两者互不影响，端口与启动命令保持一致。
