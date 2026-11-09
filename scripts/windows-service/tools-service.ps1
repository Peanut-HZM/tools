#Requires -Version 5.1
<#
.SYNOPSIS
    Tools 项目 Windows 常驻服务管理脚本（NSSM 托管）。

.DESCRIPTION
    把 Tools 项目的后端（FastAPI / uvicorn，端口 19092）与前端（Vite dev server，端口 5178）
    分别注册为 Windows 服务，实现：

      - 开机自动启动（Start = SERVICE_AUTO_START）
      - 进程崩溃自动重启（AppExit Default Restart + AppRestartDelay）
      - 标准输出/错误输出落盘并按大小轮转（logs/service-*.out.log / *.err.log）
      - 以 LocalSystem 运行，但注入真实用户目录环境变量（USERPROFILE / HOME / APPDATA /
        LOCALAPPDATA / TEMP / PATH），保证后端能读到 %USERPROFILE% 下的 Agent 数据
        （.claude / .codex / .kimi 等），与前台运行时行为一致

    端口与启动命令严格对齐项目约定（见 dev-services.py 与 frontend/vite.config.ts）：
    不额外改端口、不手搓 dev server、不使用 --reload（避免 NSSM 管不住 reload 子进程）。

.PARAMETER Action
    install    注册/更新两个服务并立即启动（需管理员）
    uninstall  停止并删除两个服务，代码与日志保留（需管理员）
    start      启动服务（需管理员）
    stop       停止服务（需管理员）
    restart    重启服务（需管理员）
    status     查看服务状态 + 端口监听 + HTTP 探活（普通权限即可）
    logs       跟踪服务日志（普通权限即可）
    update     git 拉取远程更新 + 按需安装依赖 + 重启服务（需管理员）
    verify     完整验收：服务状态 / 自启 / 端口 / HTTP / 崩溃自愈（需管理员）

.PARAMETER Target
    all（默认）| backend | frontend：限制 start / stop / restart / logs 的作用对象

.PARAMETER Force
    install：端口被其他进程占用时仍然继续注册（默认中止）

.PARAMETER SkipPortCheck
    install：完全跳过端口占用检查

.PARAMETER NoRestart
    update：只拉取更新与安装依赖，不重启服务

.PARAMETER SkipDeps
    update：跳过前端 npm install / 后端 pip install

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\windows-service\tools-service.ps1 install

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\windows-service\tools-service.ps1 status

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\windows-service\tools-service.ps1 update
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('install', 'uninstall', 'start', 'stop', 'restart', 'status', 'logs', 'update', 'verify')]
    [string]$Action = 'status',

    [Parameter(Position = 1)]
    [ValidateSet('all', 'backend', 'frontend')]
    [string]$Target = 'all',

    [switch]$Force,
    [switch]$SkipPortCheck,
    [switch]$NoRestart,
    [switch]$SkipDeps,

    # 内部使用：标记当前进程已经提权，避免重复提权
    [switch]$Elevated
)

$ErrorActionPreference = 'Stop'

# ============================================================
# 常量与路径（严格对齐项目约定，禁止改端口）
# ============================================================
$RepoRoot     = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$BackendDir   = Join-Path $RepoRoot 'backend'
$FrontendDir  = Join-Path $RepoRoot 'frontend'
$LogDir       = Join-Path $RepoRoot 'logs'
$ManageLog    = Join-Path $LogDir 'windows-service.log'

$BackendName  = 'ToolsBackend'
$FrontendName = 'ToolsFrontend'
$BackendPort  = 19092
$FrontendPort = 5178

$BackendHealth = "http://localhost:$BackendPort/api/v1/health"
$FrontendRoot  = "http://localhost:$FrontendPort/"
$ProxyHealth   = "http://localhost:$FrontendPort/api/v1/health"

$AdminActions  = @('install', 'uninstall', 'start', 'stop', 'restart', 'update', 'verify')

# ============================================================
# 日志与输出
# ============================================================
function Initialize-LogDir {
    if (-not (Test-Path -LiteralPath $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }
    # 管理日志超过 5MB 时轮转一次，避免长期运行无限增长
    if (Test-Path -LiteralPath $ManageLog) {
        $size = (Get-Item -LiteralPath $ManageLog).Length
        if ($size -gt 5242880) {
            Move-Item -LiteralPath $ManageLog -Destination "$ManageLog.1" -Force
        }
    }
}

function Write-ManageLog {
    param([string]$Text)
    if (-not (Test-Path -LiteralPath $LogDir)) { return }
    Add-Content -LiteralPath $ManageLog -Value ("[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Text) -Encoding UTF8
}

function Write-Step {
    param([string]$Text)
    Write-Host ''
    Write-Host ">>> $Text" -ForegroundColor Cyan
    Write-ManageLog ">>> $Text"
}

function Write-Ok {
    param([string]$Text)
    Write-Host "  [OK]   $Text" -ForegroundColor Green
    Write-ManageLog "    [OK]   $Text"
}

function Write-WarnMsg {
    param([string]$Text)
    Write-Host "  [WARN] $Text" -ForegroundColor Yellow
    Write-ManageLog "    [WARN] $Text"
}

function Write-Fail {
    param([string]$Text)
    Write-Host "  [FAIL] $Text" -ForegroundColor Red
    Write-ManageLog "    [FAIL] $Text"
}

# ============================================================
# 基础工具
# ============================================================
function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-ElevatedSelf {
    $argList = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', "`"$PSCommandPath`"",
        $Action, $Target, '-Elevated'
    )
    if ($Force) { $argList += '-Force' }
    if ($SkipPortCheck) { $argList += '-SkipPortCheck' }
    if ($NoRestart) { $argList += '-NoRestart' }
    if ($SkipDeps) { $argList += '-SkipDeps' }

    Write-Host ''
    Write-Host "当前动作 [$Action] 需要管理员权限，正在请求提权，请在 UAC 窗口中点击「是」..." -ForegroundColor Yellow

    # 记录提权前的日志行数，提权结束后只回显本次新增的行，避免把历史 [FAIL] 混进本次输出
    $linesBefore = 0
    if (Test-Path -LiteralPath $ManageLog) {
        $linesBefore = @(Get-Content -LiteralPath $ManageLog -Encoding UTF8).Count
    }

    try {
        $proc = Start-Process -FilePath 'powershell.exe' -Verb RunAs -Wait -PassThru -ArgumentList $argList
    }
    catch {
        Write-Host "提权失败或被取消：$($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }

    if (Test-Path -LiteralPath $ManageLog) {
        $all = @(Get-Content -LiteralPath $ManageLog -Encoding UTF8)
        $new = if ($all.Count -gt $linesBefore) { $all[$linesBefore..($all.Count - 1)] } else { @() }
        if ($new.Count -gt 0) {
            Write-Host ''
            Write-Host "===== 提权进程输出（本次新增 $($new.Count) 行） =====" -ForegroundColor Cyan
            $new | ForEach-Object { Write-Host $_ }
        }
    }
    exit $proc.ExitCode
}

function Get-NssmPath {
    $cmd = Get-Command nssm -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw '未找到 nssm，请先执行：scoop install nssm'
    }
    return $cmd.Source
}

function Resolve-RealPython {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) { throw '未找到 python，请先执行：scoop install python312' }
    $exe = $cmd.Source
    if ($exe -match '\\shims\\') {
        $real = (& $exe -c "import sys; print(sys.executable)" 2>$null)
        if ($real) { $exe = $real.Trim() }
    }
    if (-not (Test-Path -LiteralPath $exe)) { throw "Python 解释器不存在：$exe" }
    return $exe
}

function Resolve-RealNode {
    $cmd = Get-Command node -ErrorAction SilentlyContinue
    if (-not $cmd) { throw '未找到 node，请先执行：scoop install nodejs22' }
    $exe = $cmd.Source
    if ($exe -match '\\shims\\') {
        Write-WarnMsg "node 解析到 shim（$exe），服务启动会多一层进程；建议用 where node 确认实际路径"
    }
    if (-not (Test-Path -LiteralPath $exe)) { throw "Node 解释器不存在：$exe" }
    return $exe
}

function Build-ServicePath {
    param([string]$PythonExe, [string]$NodeExe)
    $pythonDir = Split-Path -Parent $PythonExe
    $nodeDir = Split-Path -Parent $NodeExe
    $parts = @(
        $pythonDir,
        (Join-Path $pythonDir 'Scripts'),
        $nodeDir,
        'D:\Scoop\shims',
        $env:PATH
    )
    return (($parts | Where-Object { $_ } | Select-Object -Unique) -join ';')
}

function Get-PortOwner {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $conn) { return $null }
    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    return [pscustomobject]@{
        Pid  = [int]$conn.OwningProcess
        Name = if ($proc) { $proc.ProcessName } else { 'unknown' }
    }
}

function Wait-ServiceState {
    param([string]$Name, [string[]]$States, [int]$TimeoutSec = 60)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
        if ($svc -and ($States -contains $svc.Status.ToString())) { return $svc }
        Start-Sleep -Milliseconds 500
    }
    return (Get-Service -Name $Name -ErrorAction SilentlyContinue)
}

function Test-Http {
    param([string]$Url, [int]$TimeoutSec = 10)
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
        return [pscustomobject]@{ Ok = $true; Status = [int]$resp.StatusCode; Body = [string]$resp.Content }
    }
    catch {
        $status = 0
        if ($_.Exception.Response) { $status = [int]$_.Exception.Response.StatusCode }
        return [pscustomobject]@{ Ok = $false; Status = $status; Body = $_.Exception.Message }
    }
}

function Get-TargetServices {
    switch ($Target) {
        'backend'  { return @($BackendName) }
        'frontend' { return @($FrontendName) }
        default    { return @($BackendName, $FrontendName) }
    }
}

# 各服务的探活规格：服务状态变成 Running 时应用可能还没开始监听，
# 必须等 HTTP 探活真正通过，否则紧接的 status 会误报“未监听/探活失败”。
function Get-ProbeSpec {
    param([string]$Name)
    if ($Name -eq $BackendName) {
        return @{ Url = $BackendHealth; Expected = '"status"\s*:\s*"healthy"'; Label = '后端健康检查' }
    }
    return @{ Url = $FrontendRoot; Expected = 'id="root"'; Label = '前端首页' }
}

function Wait-ServiceReady {
    param([string]$Name, [int]$TimeoutSec = 150)

    $spec = Get-ProbeSpec -Name $Name
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $last = '未探测'
    while ((Get-Date) -lt $deadline) {
        $probeResult = Test-Http -Url $spec.Url -TimeoutSec 8
        if ($probeResult.Ok -and ($probeResult.Body -match $spec.Expected)) {
            Write-Ok "$Name $($spec.Label)就绪（HTTP $($probeResult.Status)）"
            return $true
        }
        $last = if ($probeResult.Ok) { "HTTP $($probeResult.Status) 内容不匹配" } else { "失败：$($probeResult.Body)" }
        Start-Sleep -Milliseconds 1000
    }

    Write-Fail "$Name 在 $TimeoutSec 秒内未就绪（$($spec.Label) 最后结果：$last）"
    return $false
}

# ============================================================
# 服务注册
# ============================================================
function Register-ToolsService {
    param(
        [string]$Name,
        [string]$DisplayName,
        [string]$Description,
        [string]$Application,
        [string]$Arguments,
        [string]$WorkDirectory,
        [string[]]$EnvironmentExtra,
        [string]$LogPrefix
    )

    $nssm = Get-NssmPath
    $existing = Get-Service -Name $Name -ErrorAction SilentlyContinue

    if ($existing) {
        Write-Step "更新已存在的服务 $Name"
        & $nssm set $Name Application $Application | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "nssm set $Name Application 失败（exit=$LASTEXITCODE）" }
        & $nssm set $Name AppParameters $Arguments | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "nssm set $Name AppParameters 失败（exit=$LASTEXITCODE）" }
    }
    else {
        Write-Step "注册新服务 $Name"
        & $nssm install $Name $Application $Arguments | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "nssm install $Name 失败（exit=$LASTEXITCODE）" }
    }

    & $nssm set $Name AppDirectory $WorkDirectory | Out-Null
    & $nssm set $Name DisplayName $DisplayName | Out-Null
    & $nssm set $Name Description $Description | Out-Null
    & $nssm set $Name ObjectName LocalSystem | Out-Null

    # 环境变量：先清空再写入，保证重复安装不会叠加脏数据
    & $nssm reset $Name AppEnvironmentExtra 2>$null | Out-Null
    & $nssm set $Name AppEnvironmentExtra $EnvironmentExtra | Out-Null

    # 日志：stdout/stderr 分文件，10MB 轮转
    & $nssm set $Name AppStdout (Join-Path $LogDir "$LogPrefix.out.log") | Out-Null
    & $nssm set $Name AppStderr (Join-Path $LogDir "$LogPrefix.err.log") | Out-Null
    & $nssm set $Name AppRotateFiles 1 | Out-Null
    & $nssm set $Name AppRotateOnline 1 | Out-Null
    & $nssm set $Name AppRotateBytes 10485760 | Out-Null

    # 停止策略：先发 Ctrl+C（15s 优雅退出），再兜底
    & $nssm set $Name AppStopMethodConsole 15000 | Out-Null
    & $nssm set $Name AppStopMethodWindow 5000 | Out-Null
    & $nssm set $Name AppStopMethodThreads 5000 | Out-Null

    # 崩溃自动重启
    & $nssm set $Name AppExit Default Restart | Out-Null
    & $nssm set $Name AppRestartDelay 5000 | Out-Null
    & $nssm set $Name AppThrottle 1500 | Out-Null

    # 开机自启
    & $nssm set $Name Start SERVICE_AUTO_START | Out-Null

    if ($LASTEXITCODE -ne 0) { throw "服务 $Name 配置写入失败（exit=$LASTEXITCODE）" }
    Write-Ok "服务 $Name 配置完成"
}

# ============================================================
# 各动作实现
# ============================================================
function Do-Install {
    Initialize-LogDir
    Write-Step "安装/更新 Tools Windows 服务（${BackendName}:${BackendPort} / ${FrontendName}:${FrontendPort}）"

    $nssm = Get-NssmPath
    $python = Resolve-RealPython
    $node = Resolve-RealNode
    $viteJs = Join-Path $FrontendDir 'node_modules\vite\bin\vite.js'

    Write-Ok "nssm     : $nssm"
    Write-Ok "python   : $python"
    Write-Ok "node     : $node"
    Write-Ok "仓库根目录: $RepoRoot"

    if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir 'node_modules'))) {
        throw "前端依赖未安装：$FrontendDir\node_modules 不存在，请先在该目录执行 npm install"
    }
    if (-not (Test-Path -LiteralPath $viteJs)) {
        throw "前端 vite 入口不存在：$viteJs，请先在 frontend 目录执行 npm install"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $BackendDir '.env'))) {
        Write-WarnMsg 'backend/.env 不存在：后端可能缺少配置（该文件不入库，属本地配置）'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir '.env'))) {
        Write-WarnMsg 'frontend/.env 不存在：前端代理将回退到默认 127.0.0.1:19092'
    }

    # 已存在的服务先停掉，避免重新配置时端口被自己占用
    foreach ($name in @($BackendName, $FrontendName)) {
        $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
        if ($svc -and $svc.Status -ne 'Stopped') {
            Write-Step "停止已存在的服务 $name"
            Stop-Service -Name $name -Force -ErrorAction SilentlyContinue
            $null = Wait-ServiceState -Name $name -States @('Stopped') -TimeoutSec 40
        }
    }

    if (-not $SkipPortCheck) {
        foreach ($port in @($BackendPort, $FrontendPort)) {
            $owner = Get-PortOwner -Port $port
            if ($owner) {
                if ($Force) {
                    Write-WarnMsg "端口 $port 已被 PID $($owner.Pid)（$($owner.Name)）占用，已指定 -Force，继续安装（服务可能启动失败）"
                }
                else {
                    throw "端口 $port 已被 PID $($owner.Pid)（$($owner.Name)）占用，请先停止该进程，或使用 -Force 强制安装"
                }
            }
            else {
                Write-Ok "端口 $port 空闲"
            }
        }
    }

    $userProfile = $env:USERPROFILE
    if (-not $userProfile) { throw '当前环境缺少 USERPROFILE，无法确定真实用户目录，拒绝安装（后端会读不到 Agent 数据）' }

    $servicePath = Build-ServicePath -PythonExe $python -NodeExe $node

    $commonEnv = @(
        "USERPROFILE=$userProfile",
        "HOME=$userProfile",
        "HOMEDRIVE=$($env:HOMEDRIVE)",
        "HOMEPATH=$($env:HOMEPATH)",
        "APPDATA=$($env:APPDATA)",
        "LOCALAPPDATA=$($env:LOCALAPPDATA)",
        "TEMP=$($env:TEMP)",
        "TMP=$($env:TEMP)",
        "PATH=$servicePath"
    )

    $backendEnv = $commonEnv + @(
        "USERNAME=$($env:USERNAME)",
        'PYTHONIOENCODING=utf-8',
        'PYTHONUTF8=1'
    )

    Register-ToolsService `
        -Name $BackendName `
        -DisplayName 'Tools 后端 (FastAPI/uvicorn)' `
        -Description "Tools 项目后端服务，监听 127.0.0.1:$BackendPort（工作目录：$BackendDir）" `
        -Application $python `
        -Arguments "-m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort" `
        -WorkDirectory $BackendDir `
        -EnvironmentExtra $backendEnv `
        -LogPrefix 'service-backend'

    Register-ToolsService `
        -Name $FrontendName `
        -DisplayName 'Tools 前端 (Vite dev server)' `
        -Description "Tools 项目前端服务，监听 127.0.0.1:$FrontendPort（工作目录：$FrontendDir）" `
        -Application $node `
        -Arguments "`"$viteJs`" --port $FrontendPort --strictPort" `
        -WorkDirectory $FrontendDir `
        -EnvironmentExtra $commonEnv `
        -LogPrefix 'service-frontend'

    Write-Step '启动服务'
    foreach ($item in @(
        @{ Name = $BackendName; Port = $BackendPort },
        @{ Name = $FrontendName; Port = $FrontendPort }
    )) {
        $svc = Get-Service -Name $item.Name -ErrorAction SilentlyContinue
        if ($svc.Status -ne 'Running') {
            Start-Service -Name $item.Name
        }
        $svc = Wait-ServiceState -Name $item.Name -States @('Running') -TimeoutSec 40
        if (-not $svc -or $svc.Status -ne 'Running') {
            throw "服务 $($item.Name) 启动失败，请查看 $LogDir\service-$($item.Name.ToLower()).err.log"
        }
        Write-Ok "服务 $($item.Name) 已运行"
        if (-not (Wait-ServiceReady -Name $item.Name -TimeoutSec 150)) {
            Write-WarnMsg "服务 $($item.Name) 已启动但探活未通过，请查看 $LogDir 下的日志"
        }
    }

    return (Do-Status)
}

function Do-Uninstall {
    Initialize-LogDir
    Write-Step '卸载 Tools Windows 服务'
    $nssm = Get-NssmPath

    foreach ($name in @($BackendName, $FrontendName)) {
        $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
        if (-not $svc) {
            Write-Ok "服务 $name 不存在，跳过"
            continue
        }
        if ($svc.Status -ne 'Stopped') {
            Write-Step "停止 $name"
            Stop-Service -Name $name -Force -ErrorAction SilentlyContinue
            $null = Wait-ServiceState -Name $name -States @('Stopped') -TimeoutSec 40
        }
        Write-Step "删除服务 $name"
        & $nssm remove $name confirm | Out-Null
        if ($LASTEXITCODE -ne 0) { Write-Fail "删除 $name 失败（exit=$LASTEXITCODE）" }
        else { Write-Ok "服务 $name 已删除" }
    }

    Write-Ok '卸载完成：代码、日志、backend/.env 均未删除'
}

function Do-Start {
    foreach ($name in (Get-TargetServices)) {
        $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
        if (-not $svc) { Write-WarnMsg "服务 $name 未安装，跳过"; continue }
        if ($svc.Status -eq 'Running') { Write-Ok "$name 已在运行"; continue }
        Write-Step "启动 $name"
        Start-Service -Name $name
        $svc = Wait-ServiceState -Name $name -States @('Running') -TimeoutSec 40
        if ($svc -and $svc.Status -eq 'Running') {
            Write-Ok "$name 已启动"
            $null = Wait-ServiceReady -Name $name -TimeoutSec 150
        }
        else { Write-Fail "$name 启动失败，请查看 $LogDir" }
    }
    return (Do-Status)
}

function Do-Stop {
    foreach ($name in (Get-TargetServices)) {
        $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
        if (-not $svc) { Write-WarnMsg "服务 $name 未安装，跳过"; continue }
        if ($svc.Status -eq 'Stopped') { Write-Ok "$name 已停止"; continue }
        Write-Step "停止 $name"
        Stop-Service -Name $name -Force -ErrorAction SilentlyContinue
        $svc = Wait-ServiceState -Name $name -States @('Stopped') -TimeoutSec 40
        if ($svc -and $svc.Status -eq 'Stopped') { Write-Ok "$name 已停止" }
        else { Write-Fail "$name 停止超时（当前状态：$($svc.Status)）" }
    }
    $null = Do-Status
}

function Do-Restart {
    foreach ($name in (Get-TargetServices)) {
        $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
        if (-not $svc) { Write-WarnMsg "服务 $name 未安装，跳过"; continue }
        Write-Step "重启 $name"
        Restart-Service -Name $name -Force
        $svc = Wait-ServiceState -Name $name -States @('Running') -TimeoutSec 60
        if ($svc -and $svc.Status -eq 'Running') {
            Write-Ok "$name 已重启"
            $null = Wait-ServiceReady -Name $name -TimeoutSec 150
        }
        else { Write-Fail "$name 重启后状态异常：$($svc.Status)" }
    }
}

function Do-Status {
    Initialize-LogDir
    Write-Step '服务状态'
    $fail = 0

    foreach ($item in @(
        @{ Name = $BackendName; Port = $BackendPort; Probe = $BackendHealth },
        @{ Name = $FrontendName; Port = $FrontendPort; Probe = $FrontendRoot }
    )) {
        $svc = Get-Service -Name $item.Name -ErrorAction SilentlyContinue
        if (-not $svc) {
            Write-Fail "$($item.Name)：未安装"
            $fail++
            continue
        }
        $owner = Get-PortOwner -Port $item.Port
        $pidText = if ($owner) { "$($owner.Pid)（$($owner.Name)）" } else { '无' }
        $portText = if ($owner) { "监听中" } else { "未监听" }
        # 注意：变量名不能叫 $probe/$Probe 之外的短名造成覆盖，这里用 $probeResult
        $probeResult = Test-Http -Url $item.Probe -TimeoutSec 8
        $probeText = if ($probeResult.Ok) { "HTTP $($probeResult.Status) 正常" } else { "失败：HTTP $($probeResult.Status) $($probeResult.Body)" }

        $line = "$($item.Name): 状态=$($svc.Status) 启动类型=$($svc.StartType) 端口$($item.Port)=$portText PID=$pidText 探活=$probeText"
        if ($svc.Status -eq 'Running' -and $owner -and $probeResult.Ok) { Write-Ok $line }
        else { Write-Fail $line; $fail++ }
    }

    $proxy = Test-Http -Url $ProxyHealth -TimeoutSec 10
    if ($proxy.Ok -and $proxy.Body -match '"status"\s*:\s*"healthy"') {
        Write-Ok "前端代理链路：$ProxyHealth -> HTTP $($proxy.Status) healthy"
    }
    else {
        Write-Fail "前端代理链路异常：$ProxyHealth -> HTTP $($proxy.Status) $($proxy.Body)"
        $fail++
    }

    Write-Host ''
    Write-Host "日志目录：$LogDir" -ForegroundColor DarkGray
    return $fail
}

function Do-Logs {
    Initialize-LogDir
    $files = @()
    if ($Target -in @('all', 'backend')) {
        $files += (Join-Path $LogDir 'service-backend.out.log')
        $files += (Join-Path $LogDir 'service-backend.err.log')
    }
    if ($Target -in @('all', 'frontend')) {
        $files += (Join-Path $LogDir 'service-frontend.out.log')
        $files += (Join-Path $LogDir 'service-frontend.err.log')
    }
    $files = $files | Where-Object { Test-Path -LiteralPath $_ }
    if (-not $files) {
        Write-WarnMsg "未找到日志文件（$LogDir），服务可能尚未启动过"
        return
    }

    foreach ($file in $files) {
        Write-Host ''
        Write-Host "===== $file（最后 40 行） =====" -ForegroundColor Cyan
        Get-Content -LiteralPath $file -Tail 40 -Encoding UTF8
    }
    Write-Host ''
    Write-Host '进入实时跟踪（Ctrl+C 退出）...' -ForegroundColor Yellow
    Get-Content -LiteralPath $files -Tail 0 -Wait -Encoding UTF8
}

function Do-Update {
    Initialize-LogDir
    Write-Step '拉取远程更新'

    $changed = @()
    Push-Location $RepoRoot
    try {
        & git fetch --all --prune | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'git fetch 失败，已中止（服务未重启）' }

        $head = (& git rev-parse --short HEAD).Trim()
        $behind = [int]((& git rev-list --count 'HEAD..origin/master').Trim())
        if ($behind -eq 0) {
            Write-Ok "本地已是最新（$head）"
        }
        else {
            Write-Step "发现 $behind 个新提交，执行 rebase 更新（自动暂存/恢复本地未提交改动）"
            $before = (& git rev-parse HEAD).Trim()
            & git pull --rebase --autostash origin master
            if ($LASTEXITCODE -ne 0) {
                throw 'git pull 失败，已中止（服务未重启），请手动解决冲突后重试'
            }
            $after = (& git rev-parse HEAD).Trim()
            $changed = @(& git diff --name-only $before $after)
            Write-Ok "代码已更新：$before -> $after"
            & git log -1 --oneline
        }
    }
    finally {
        Pop-Location
    }

    if ($SkipDeps) {
        Write-WarnMsg '已指定 -SkipDeps，跳过依赖安装'
    }
    else {
        $needFrontend = ($changed -contains 'frontend/package.json') -or
                        ($changed -contains 'frontend/package-lock.json') -or
                        (-not (Test-Path -LiteralPath (Join-Path $FrontendDir 'node_modules')))
        if ($needFrontend) {
            Write-Step '前端依赖有变化，执行 npm install'
            Push-Location $FrontendDir
            try {
                & npm install
                if ($LASTEXITCODE -ne 0) { Write-WarnMsg "npm install 失败（exit=$LASTEXITCODE），服务将按现有依赖重启" }
                else { Write-Ok '前端依赖安装完成' }
            }
            finally { Pop-Location }
        }
        else {
            Write-Ok '前端依赖无变化，跳过 npm install'
        }

        if ($changed -contains 'backend/requirements.txt') {
            Write-Step '后端依赖有变化，执行 pip install -r requirements.txt'
            $python = Resolve-RealPython
            Push-Location $BackendDir
            try {
                & $python -m pip install -r requirements.txt
                if ($LASTEXITCODE -ne 0) { Write-WarnMsg "pip install 失败（exit=$LASTEXITCODE），服务将按现有依赖重启" }
                else { Write-Ok '后端依赖安装完成' }
            }
            finally { Pop-Location }
        }
        else {
            Write-Ok '后端依赖无变化，跳过 pip install'
        }
    }

    if ($NoRestart) {
        Write-WarnMsg '已指定 -NoRestart，跳过服务重启（新代码尚未生效）'
        return 0
    }

    $null = Do-Restart
    return (Do-Status)
}

function Test-CrashRestart {
    param([string]$Name, [int]$Port, [string]$ProbeUrl, [string]$Expected)

    Write-Step "崩溃自愈测试：$Name（强杀进程，验证服务自动拉起）"
    $owner = Get-PortOwner -Port $Port
    if (-not $owner) { Write-Fail "$Name 端口 $Port 未监听，无法测试"; return 1 }

    $oldPid = $owner.Pid
    try {
        Stop-Process -Id $oldPid -Force -ErrorAction Stop
    }
    catch {
        Write-Fail "终止进程 $oldPid 失败：$($_.Exception.Message)"; return 1
    }
    Write-Ok "已强制终止 $Name 进程 PID $oldPid（模拟崩溃）"

    # 判定标准：服务回到 Running 且 HTTP 探活恢复
    # 注意：不再强制要求 Get-NetTCPConnection 立刻查到监听（实测存在瞬时查不到、
    # 但端口实际已可访问的情况，用它当必要条件会误判为“未恢复”）
    $deadline = (Get-Date).AddSeconds(180)
    $attempt = 0
    $lastState = ''
    $lastProbe = '未探测'
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 2
        $attempt++

        $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
        $state = if ($svc) { $svc.Status.ToString() } else { 'NotFound' }
        $newOwner = Get-PortOwner -Port $Port
        $newPid = if ($newOwner) { $newOwner.Pid } else { 0 }
        # 注意：变量名不能叫 $probe， PowerShell 变量名大小写不敏感，会覆盖参数 $ProbeUrl 之前的 $Probe
        $probeResult = Test-Http -Url $ProbeUrl -TimeoutSec 10
        $healthy = ($probeResult.Ok -and ($probeResult.Body -match $Expected))
        $lastState = $state
        $lastProbe = if ($probeResult.Ok) { "HTTP $($probeResult.Status)" } else { "失败：$($probeResult.Body)" }
        Write-ManageLog ("    第{0}次探测：服务状态={1} 端口PID={2} 探活={3}" -f $attempt, $state, $newPid, $lastProbe)

        if ($state -eq 'Running' -and $healthy) {
            $pidText = if ($newPid -and $newPid -ne $oldPid) { "新 PID $newPid" } else { '进程已恢复' }
            Write-Ok "$Name 已自动重启（$pidText），探活正常"
            return 0
        }
    }

    Write-Fail "$Name 未在 180 秒内自动恢复（最后状态=$lastState，最后探活=$lastProbe）"
    return 1
}

function Do-Verify {
    Initialize-LogDir
    Write-Step '开始完整验收 Tools Windows 服务'
    $fail = 0

    Write-Step '1/5 服务注册、运行状态与开机自启'
    foreach ($item in @(
        @{ Name = $BackendName; Port = $BackendPort },
        @{ Name = $FrontendName; Port = $FrontendPort }
    )) {
        $svc = Get-Service -Name $item.Name -ErrorAction SilentlyContinue
        if (-not $svc) { Write-Fail "服务 $($item.Name) 不存在"; $fail++; continue }
        if ($svc.Status -eq 'Running') { Write-Ok "$($item.Name) 运行中" }
        else { Write-Fail "$($item.Name) 状态=$($svc.Status)（应为 Running）"; $fail++ }
        if ($svc.StartType -eq 'Automatic') { Write-Ok "$($item.Name) 启动类型=Automatic（开机自启）" }
        else { Write-Fail "$($item.Name) 启动类型=$($svc.StartType)（应为 Automatic）"; $fail++ }

        $nssm = Get-NssmPath
        $exitMode = (& $nssm get $item.Name AppExit Default 2>$null) -join ''
        if ($exitMode -match 'Restart') { Write-Ok "$($item.Name) 崩溃策略=Restart" }
        else { Write-Fail "$($item.Name) 崩溃策略=$exitMode（应为 Restart）"; $fail++ }
    }

    Write-Step '2/5 端口监听'
    foreach ($port in @($BackendPort, $FrontendPort)) {
        $owner = Get-PortOwner -Port $port
        if ($owner) { Write-Ok "端口 $port 监听中（PID $($owner.Pid) $($owner.Name)）" }
        else { Write-Fail "端口 $port 未监听"; $fail++ }
    }

    Write-Step '3/5 后端直连健康检查'
    $h1 = Test-Http -Url $BackendHealth -TimeoutSec 15
    if ($h1.Ok -and $h1.Body -match '"status"\s*:\s*"healthy"') {
        Write-Ok "$BackendHealth -> HTTP $($h1.Status) $($h1.Body.Trim())"
    }
    else { Write-Fail "$BackendHealth -> HTTP $($h1.Status) $($h1.Body)"; $fail++ }

    Write-Step '4/5 前端页面与前端->后端代理链路'
    $h2 = Test-Http -Url $FrontendRoot -TimeoutSec 15
    if ($h2.Ok -and $h2.Body -match 'id="root"') { Write-Ok "$FrontendRoot -> HTTP $($h2.Status)（返回前端 HTML）" }
    else { Write-Fail "$FrontendRoot -> HTTP $($h2.Status) $($h2.Body)"; $fail++ }

    $h3 = Test-Http -Url $ProxyHealth -TimeoutSec 20
    if ($h3.Ok -and $h3.Body -match '"status"\s*:\s*"healthy"') { Write-Ok "$ProxyHealth -> HTTP $($h3.Status)（代理到后端成功）" }
    else { Write-Fail "$ProxyHealth -> HTTP $($h3.Status) $($h3.Body)"; $fail++ }

    Write-Step '5/5 崩溃自愈（强杀进程后服务自动拉起）'
    $fail += Test-CrashRestart -Name $BackendName -Port $BackendPort -ProbeUrl $BackendHealth -Expected '"status"\s*:\s*"healthy"'
    $fail += Test-CrashRestart -Name $FrontendName -Port $FrontendPort -ProbeUrl $FrontendRoot -Expected 'id="root"'

    Write-Step '验收结论'
    if ($fail -eq 0) {
        Write-Ok '全部通过：服务运行 / 开机自启 / 端口监听 / HTTP 探活 / 崩溃自愈'
        Write-Host ''
        Write-Host "访问地址：http://localhost:$FrontendPort/" -ForegroundColor Green
        return 0
    }
    Write-Fail "共 $fail 项检查未通过，详见上方输出与 $LogDir 下的日志"
    return 1
}

# ============================================================
# 入口
# ============================================================
if (($AdminActions -contains $Action) -and (-not (Test-Admin)) -and (-not $Elevated)) {
    Invoke-ElevatedSelf
}

$exitCode = 0
switch ($Action) {
    'install'   { $exitCode = Do-Install }
    'uninstall' { Do-Uninstall }
    'start'     { $exitCode = Do-Start }
    'stop'      { Do-Stop }
    'restart'   { $null = Do-Restart; $exitCode = Do-Status }
    'status'    { $exitCode = Do-Status }
    'logs'      { Do-Logs }
    'update'    { $exitCode = Do-Update }
    'verify'    { $exitCode = Do-Verify }
}

exit $exitCode
