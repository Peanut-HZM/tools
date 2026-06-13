"""
Author: Peanut
Created: 2026-04-26
Purpose: 通用服务管理脚本 — 在任意项目目录下自动发现、启动、停止、重启各类服务
         支持 Vite 前端、Python 后端 (FastAPI/Flask/Django)、Node.js 后端 (Express/NestJS)、
         Java Spring Boot (Maven/Gradle)。
         用法: python ~/.claude/dev-services.py [命令] [选项]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import psutil
except ImportError:
    print("错误: 需要 psutil 库，请运行: pip install psutil")
    sys.exit(1)

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ============================================================
# 常量
# ============================================================

SCRIPT_DIR = Path(__file__).parent.resolve()
CWD = Path.cwd()
LOG_DIR = CWD / "logs"
LOG_DIR.mkdir(exist_ok=True)
SCRIPT_LOG = LOG_DIR / "dev-services.log"

MAX_SCAN_DEPTH = 3
SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", "venv", ".venv", "target", "build",
    "dist", ".omc", ".next", ".nuxt", "coverage", "e2e", ".worktrees",
}
AUXILIARY_DIRS = {"tools", "scripts", "script", "bin", ".superpowers", ".gstack"}

# 默认排除的服务目录（仅当用户显式 --include 或 --all 时才扫描）
DEFAULT_EXCLUDE_DIRS = {"mini-program", "tools-mini-program"}

# 框架默认端口
DEFAULT_PORTS = {
    "vite": 5173,
    "uniapp": 5173,
    "taro": 5173,
    "next": 3000,
    "node-backend": 3000,
    "python": 8000,
    "spring-boot": 8080,
    "spring-boot-gradle": 8080,
}

# ANSI 颜色
COLORS = {
    "INFO": "\033[37m",
    "SUCCESS": "\033[32m",
    "WARN": "\033[33m",
    "ERROR": "\033[31m",
    "DEBUG": "\033[36m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "DIM": "\033[2m",
}

if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 日志
# ============================================================

def log(msg: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = COLORS.get(level, COLORS["INFO"])
    reset = COLORS["RESET"]
    print(f"{color}[{timestamp}] [{level}]{reset} {msg}")
    try:
        with open(SCRIPT_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{level}] {msg}\n")
    except Exception:
        pass


def log_separator():
    print(f"\n{COLORS['DIM']}{'=' * 60}{COLORS['RESET']}\n")


def log_section(title: str):
    print(f"\n{COLORS['BOLD']}  {title}{COLORS['RESET']}")
    print(f"{COLORS['DIM']}{'-' * 50}{COLORS['RESET']}")


# ============================================================
# 服务抽象
# ============================================================

@dataclass
class Service:
    name: str
    project_type: str
    project_dir: Path
    port: int
    start_cmd: list
    health_keyword: str
    health_url: str
    health_timeout: int = 30
    keyword_timeout: int = 30
    log_file: Optional[Path] = None

    @property
    def log_path(self) -> Path:
        if self.log_file:
            return self.log_file
        return LOG_DIR / f"{self.name.lower().replace(' ', '_')}.log"

    def type_label(self) -> str:
        labels = {
            "vite": "Vite 前端",
            "uniapp": "UniApp H5",
            "taro": "Taro H5",
            "next": "Next.js",
            "node-backend": "Node.js 后端",
            "python": "Python 后端",
            "spring-boot": "Spring Boot (Maven)",
            "spring-boot-gradle": "Spring Boot (Gradle)",
        }
        return labels.get(self.project_type, self.project_type)


# ============================================================
# 项目发现
# ============================================================

def discover_services(root_dir: Optional[Path] = None, max_depth: int = MAX_SCAN_DEPTH) -> list[Service]:
    """递归扫描目录，发现所有服务"""
    base = root_dir or CWD
    services = []
    _scan_directory(base, base, max_depth, services)
    return services


def _scan_directory(current: Path, root: Path, max_depth: int, services: list, exclude_dirs: Optional[set[str]] = None):
    """递归扫描，跳过黑名单目录"""
    rel_depth = len(current.relative_to(root).parts)
    if rel_depth > max_depth:
        return

    # 跳过黑名单
    if current != root and (current.name in SKIP_DIRS or current.name in AUXILIARY_DIRS):
        return

    # 跳过用户排除的目录
    if exclude_dirs and current != root and current.name.lower() in exclude_dirs:
        return

    # 尝试发现服务
    svc = _detect_service(current)
    if svc:
        services.append(svc)
        # 如果找到服务，不再深入其子目录（避免重复发现）
        return

    # 递归子目录
    try:
        for child in sorted(current.iterdir()):
            if child.is_dir():
                _scan_directory(child, root, max_depth, services)
    except PermissionError:
        pass


def _detect_service(directory: Path) -> Optional[Service]:
    """检测目录是否是项目根目录，返回 Service 或 None"""

    # 1. Java Spring Boot 优先于 Python 检测，避免辅助脚本导致误判
    pom = directory / "pom.xml"
    if pom.exists():
        svc = _build_spring_boot_maven_service(directory, pom)
        if svc:
            return svc

    gradle = directory / "build.gradle"
    gradle_kts = directory / "build.gradle.kts"
    if gradle.exists() or gradle_kts.exists():
        svc = _build_spring_boot_gradle_service(directory, gradle if gradle.exists() else gradle_kts)
        if svc:
            return svc

    # 2. Vite 前端
    pkg = directory / "package.json"
    if pkg.exists():
        try:
            pkg_data = json.loads(pkg.read_text(encoding="utf-8"))
            deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
            scripts = pkg_data.get("scripts", {})

            if _is_uniapp_project(deps, scripts):
                return _build_uniapp_service(directory, pkg_data)
            if _is_taro_project(deps, scripts):
                return _build_taro_service(directory, pkg_data)
            # Vite
            if "vite" in deps:
                return _build_vite_service(directory, pkg_data)
            # Next.js
            if "next" in deps:
                return _build_next_service(directory, pkg_data)
            # Node.js 后端 (Express / NestJS / Koa)
            if any(k in deps for k in ["express", "@nestjs/core", "koa"]):
                return _build_node_backend_service(directory, pkg_data)
        except (json.JSONDecodeError, Exception):
            pass

    # 3. Python 后端
    req_file = directory / "requirements.txt"
    pyproject = directory / "pyproject.toml"
    has_python_deps = req_file.exists() or pyproject.exists()

    # 只把明确的 Python Web 项目入口当作 Python 服务，普通 src 目录不代表 Python
    has_python_entry = (
        (directory / "main.py").exists()
        or (directory / "manage.py").exists()
        or (directory / "app.py").exists()
        or (directory / "app").is_dir()
    )

    if has_python_deps or has_python_entry:
        svc = _build_python_service(directory)
        if svc:
            return svc

    return None


# ============================================================
# 配置解析
# ============================================================

def _read_env_file(directory: Path) -> dict:
    """读取 .env 或 .env.development，返回键值对（合并所有找到的环境文件）"""
    env_data = {}
    for env_name in [".env.development", ".env.local", ".env"]:
        env_path = directory / env_name
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        env_data[key.strip()] = value.strip().strip('"').strip("'")
            except Exception:
                pass
    return env_data


def _extract_port_from_env(directory: Path) -> Optional[int]:
    """从 .env 文件中提取端口号"""
    env_data = _read_env_file(directory)
    for key in ["VITE_PORT", "VITE_APP_PORT", "PORT", "SERVER_PORT", "APP_PORT", "BACKEND_PORT"]:
        if key in env_data:
            try:
                return int(env_data[key])
            except ValueError:
                continue
    return None


def _extract_port_from_vite_config(directory: Path) -> Optional[int]:
    """从 vite.config.ts/js 中提取 server.port"""
    for conf_name in ["vite.config.ts", "vite.config.js"]:
        conf_path = directory / conf_name
        if conf_path.exists():
            try:
                content = conf_path.read_text(encoding="utf-8")
                # 匹配 port: 5178 或 port:5173
                match = re.search(r'port\s*:\s*(\d+)', content)
                if match:
                    return int(match.group(1))
            except Exception:
                pass
    return None


def _extract_port_from_scripts(pkg_data: dict) -> Optional[int]:
    """从 package.json scripts 中提取 --port 参数"""
    scripts = pkg_data.get("scripts", {})
    for script_name in ["dev:h5", "h5", "dev", "start"]:
        script = scripts.get(script_name, "")
        match = re.search(r'--port(?:=|\s+)(\d+)', script)
        if match:
            return int(match.group(1))
    return None


def _service_has_explicit_port(svc: Service) -> bool:
    if _extract_port_from_env(svc.project_dir) is not None:
        return True
    if svc.project_type in {"vite", "uniapp", "taro", "next"}:
        return _extract_port_from_vite_config(svc.project_dir) is not None
    return False


def _update_service_port(svc: Service, port: int):
    old_port = svc.port
    if old_port == port:
        return

    svc.port = port
    svc.health_url = re.sub(r":\d+", f":{port}", svc.health_url, count=1)
    updated = []
    skip_next = False
    for index, part in enumerate(svc.start_cmd):
        if skip_next:
            skip_next = False
            continue
        if part == "--port" and index + 1 < len(svc.start_cmd):
            updated.extend([part, str(port)])
            skip_next = True
        elif part.startswith("--port="):
            updated.append(f"--port={port}")
        elif f"--server.port={old_port}" in part:
            updated.append(part.replace(f"--server.port={old_port}", f"--server.port={port}"))
        else:
            updated.append(part)
    svc.start_cmd = updated


def assign_unique_ports(services: list[Service]) -> list[Service]:
    reserved = {svc.port for svc in services if _service_has_explicit_port(svc)}
    used = set()
    for svc in services:
        port = svc.port
        if port in used or (port in reserved and not _service_has_explicit_port(svc)):
            while port in used or port in reserved:
                port += 1
            log(f"{svc.name} 端口 {svc.port} 与其他服务冲突，自动调整为 {port}", "WARN")
            _update_service_port(svc, port)
        used.add(svc.port)
    return services


def _extract_port_from_pom(pom_path: Path) -> Optional[int]:
    """从 pom.xml 提取 server.port"""
    try:
        content = pom_path.read_text(encoding="utf-8")
        # 查找 <server.port>1234</server.port> 或 <properties><server.port>1234</server.port></properties>
        match = re.search(r'<server\.port>\s*(\d+)\s*</server\.port>', content)
        if match:
            return int(match.group(1))
        # 查找 <properties><port>1234</port></properties>
        match = re.search(r'<properties>.*?<port>\s*(\d+)\s*</port>.*?</properties>', content, re.DOTALL)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return None


def _extract_port_from_spring_boot_yaml(directory: Path) -> Optional[int]:
    """从 Spring Boot application*.yml 提取 server.port

    1. 优先检查目录根下的 application.yml
    2. 检查直接子目录中的 src/main/resources/application*.yml（多模块 Maven 项目）
    3. 最后递归搜索其他子目录（跳过构建产物）
    """
    if not HAS_YAML:
        return None

    # 1. 检查目录根
    for name in ["application.yml", "application.yaml"]:
        port = _extract_port_from_single_yaml(directory / name)
        if port is not None:
            return port

    # 2. 优先检查直接子目录中的 src/main/resources（多模块 Maven 项目常见布局）
    try:
        for subdir in sorted(directory.iterdir()):
            if subdir.is_dir():
                resources_dir = subdir / "src" / "main" / "resources"
                if resources_dir.exists():
                    for name in [
                        "application.yml", "application.yaml",
                        "application-local.yml", "application-local.yaml",
                        "application-dev.yml", "application-dev.yaml",
                        "application-prod.yml", "application-prod.yaml",
                        "application-test.yml", "application-test.yaml",
                    ]:
                        port = _extract_port_from_single_yaml(resources_dir / name)
                        if port is not None:
                            return port
    except Exception:
        pass

    # 3. 递归搜索其他子目录（跳过构建产物）
    try:
        for child in directory.rglob("application*.yml"):
            parts = set(child.parts)
            if parts & {"target", "build", "dist", "node_modules"}:
                continue
            depth = len(child.relative_to(directory).parts)
            if depth > 10:
                continue
            port = _extract_port_from_single_yaml(child)
            if port is not None:
                return port
        for child in directory.rglob("application*.yaml"):
            parts = set(child.parts)
            if parts & {"target", "build", "dist", "node_modules"}:
                continue
            depth = len(child.relative_to(directory).parts)
            if depth > 10:
                continue
            port = _extract_port_from_single_yaml(child)
            if port is not None:
                return port
    except Exception:
        pass

    return None


def _extract_spring_boot_context_path(directory: Path) -> str:
    """从 Spring Boot application*.yml 提取 servlet context-path"""
    value = _extract_spring_boot_yaml_value(directory, ("server", "servlet", "context-path"))
    return _normalize_url_path(value) if value else ""


def _extract_spring_boot_management_base_path(directory: Path) -> str:
    """从 Spring Boot application*.yml 提取 actuator base-path"""
    value = _extract_spring_boot_yaml_value(directory, ("management", "endpoints", "web", "base-path"))
    return _normalize_url_path(value) if value else "/actuator"


def _build_spring_boot_health_url(port: int, directory: Path) -> str:
    """根据 Spring Boot 上下文路径构建健康检查 URL"""
    context_path = _extract_spring_boot_context_path(directory)
    actuator_base_path = _extract_spring_boot_management_base_path(directory)
    health_path = _join_url_paths(context_path, actuator_base_path, "health")
    return f"http://localhost:{port}{health_path}"


def _extract_spring_boot_yaml_value(directory: Path, keys: tuple[str, ...]) -> Optional[str]:
    """按优先级从 Spring Boot application*.yml/yaml 中读取嵌套配置值"""
    if not HAS_YAML:
        return None

    for yml_path in _iter_spring_boot_yaml_files(directory):
        value = _extract_value_from_single_yaml(yml_path, keys)
        if value is not None:
            return str(value)
    return None


def _iter_spring_boot_yaml_files(directory: Path) -> list[Path]:
    """按稳定优先级列出 Spring Boot YAML 配置文件"""
    candidates = []

    for name in ["application.yml", "application.yaml"]:
        candidates.append(directory / name)

    try:
        for subdir in sorted(directory.iterdir()):
            if subdir.is_dir():
                resources_dir = subdir / "src" / "main" / "resources"
                if resources_dir.exists():
                    for name in [
                        "application.yml", "application.yaml",
                        "application-local.yml", "application-local.yaml",
                        "application-dev.yml", "application-dev.yaml",
                        "application-prod.yml", "application-prod.yaml",
                        "application-test.yml", "application-test.yaml",
                    ]:
                        candidates.append(resources_dir / name)
    except Exception:
        pass

    try:
        for pattern in ["application*.yml", "application*.yaml"]:
            for child in directory.rglob(pattern):
                parts = set(child.parts)
                if parts & {"target", "build", "dist", "node_modules"}:
                    continue
                depth = len(child.relative_to(directory).parts)
                if depth <= 10:
                    candidates.append(child)
    except Exception:
        pass

    seen = set()
    result = []
    for path in candidates:
        if path in seen or not path.exists():
            continue
        seen.add(path)
        result.append(path)
    return result


def _extract_value_from_single_yaml(yml_path: Path, keys: tuple[str, ...]) -> Optional[object]:
    """从单个 YAML 文件中读取嵌套配置值"""
    if not HAS_YAML:
        return None
    try:
        content = yml_path.read_text(encoding="utf-8")
        content = re.sub(r'@\w[\w.\-]*@', '""', content)
        for doc in yaml.safe_load_all(content):
            current = doc
            for key in keys:
                if not isinstance(current, dict) or key not in current:
                    current = None
                    break
                current = current[key]
            if current is not None:
                return current
    except Exception:
        pass
    return None


def _normalize_url_path(value: str) -> str:
    """规范化 URL 路径片段"""
    path = str(value).strip()
    if not path or path == "/":
        return ""
    return "/" + path.strip("/")


def _join_url_paths(*parts: str) -> str:
    """拼接 URL 路径，避免重复斜杠"""
    cleaned = [str(part).strip("/") for part in parts if str(part).strip("/")]
    return "/" + "/".join(cleaned)


def _extract_port_from_single_yaml(yml_path: Path) -> Optional[int]:
    """从单个 YAML 文件提取 server.port

    自动处理 Maven @placeholder@ 占位符（替换为空字符串）。
    """
    if not HAS_YAML:
        return None
    try:
        content = yml_path.read_text(encoding="utf-8")
        # 移除 Maven 占位符: @xxx@ -> ""
        content = re.sub(r'@\w[\w.\-]*@', '""', content)
        for doc in yaml.safe_load_all(content):
            if isinstance(doc, dict):
                server = doc.get("server", {})
                if isinstance(server, dict) and "port" in server:
                    return int(server["port"])
    except Exception:
        pass
    return None


def _extract_port_from_gradle(gradle_path: Path) -> Optional[int]:
    """从 build.gradle 提取 server.port"""
    try:
        content = gradle_path.read_text(encoding="utf-8")
        match = re.search(r'server\.port\s*=\s*["\']?(\d+)["\']?', content)
        if match:
            return int(match.group(1))
        match = re.search(r'serverPort\s*=\s*["\']?(\d+)["\']?', content)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return None


def _has_spring_boot(pom_path: Path) -> bool:
    """检查 pom.xml 是否包含 Spring Boot 依赖"""
    try:
        content = pom_path.read_text(encoding="utf-8")
        return "spring-boot" in content.lower() or "springboot" in content.lower()
    except Exception:
        return False


def _has_spring_boot_gradle(gradle_path: Path) -> bool:
    """检查 build.gradle 是否包含 Spring Boot 插件"""
    try:
        content = gradle_path.read_text(encoding="utf-8")
        return "spring-boot" in content.lower() or "org.springframework.boot" in content
    except Exception:
        return False


def _find_python_entry(directory: Path) -> Optional[Path]:
    """查找 Python 入口文件"""
    candidates = ["main.py", "app.py", "app/main.py", "src/main.py", "manage.py", "wsgi.py", "asgi.py"]
    for c in candidates:
        p = directory / c
        if p.exists():
            return p
    return None


# ============================================================
# 服务构建
# ============================================================

def _is_uniapp_project(deps: dict, scripts: dict) -> bool:
    dep_names = set(deps.keys())
    return (
        any(name.startswith("@dcloudio/") for name in dep_names)
        or "uni-app" in dep_names
        or any("uni " in value or value.startswith("uni") for value in scripts.values())
    )


def _is_taro_project(deps: dict, scripts: dict) -> bool:
    dep_names = set(deps.keys())
    return (
        any(name.startswith("@tarojs/") for name in dep_names)
        or any("taro " in value or value.startswith("taro") for value in scripts.values())
    )


def _get_package_manager(directory: Path) -> str:
    if (directory / "pnpm-lock.yaml").exists():
        return shutil.which("pnpm") or "pnpm"
    if (directory / "yarn.lock").exists():
        return shutil.which("yarn") or "yarn"
    return shutil.which("npm") or "npm"


def _choose_h5_script(scripts: dict) -> str:
    for name in ["dev:h5", "h5", "dev"]:
        if name in scripts:
            return name
    return "dev"


def _get_npm_cmd(directory: Path) -> list:
    """获取可用的包管理器命令，返回 [cmd, args...] 列表"""
    # 优先通过 node 直接执行 vite.js（避免 .cmd 的 shell 问题）
    vite_js = directory / "node_modules" / "vite" / "bin" / "vite.js"
    if vite_js.exists():
        node_exe = shutil.which("node") or "node"
        return [node_exe, str(vite_js)]

    # Windows: 尝试 .cmd
    if sys.platform == "win32":
        vite_cmd = directory / "node_modules" / ".bin" / "vite.cmd"
        if vite_cmd.exists():
            return [str(vite_cmd)]
    else:
        vite_bin = directory / "node_modules" / ".bin" / "vite"
        if vite_bin.exists():
            return [str(vite_bin)]

    for pkg_cmd in ["pnpm", "npm", "yarn"]:
        found = shutil.which(pkg_cmd)
        if found:
            return [found]
    return ["npx"]


def _build_uniapp_service(directory: Path, pkg_data: dict) -> Service:
    name = pkg_data.get("name", "uniapp")
    if "/" in name:
        name = name.split("/")[-1]
    scripts = pkg_data.get("scripts", {})
    port = (_extract_port_from_env(directory)
            or _extract_port_from_scripts(pkg_data)
            or _extract_port_from_vite_config(directory)
            or DEFAULT_PORTS["uniapp"])
    script = _choose_h5_script(scripts)
    cmd = [_get_package_manager(directory), "run", script, "--", "--host", "127.0.0.1", "--port", str(port)]

    return Service(
        name=f"{name.capitalize()} 前端",
        project_type="uniapp",
        project_dir=directory,
        port=port,
        start_cmd=cmd,
        health_keyword="",
        health_url=f"http://localhost:{port}",
        health_timeout=120,
        keyword_timeout=0,
    )


def _build_taro_service(directory: Path, pkg_data: dict) -> Service:
    name = pkg_data.get("name", "taro")
    if "/" in name:
        name = name.split("/")[-1]
    scripts = pkg_data.get("scripts", {})
    port = (_extract_port_from_env(directory)
            or _extract_port_from_scripts(pkg_data)
            or _extract_port_from_vite_config(directory)
            or DEFAULT_PORTS["taro"])
    script = _choose_h5_script(scripts)
    cmd = [_get_package_manager(directory), "run", script, "--", "--host", "127.0.0.1", "--port", str(port)]

    return Service(
        name=f"{name.capitalize()} 前端",
        project_type="taro",
        project_dir=directory,
        port=port,
        start_cmd=cmd,
        health_keyword="",
        health_url=f"http://localhost:{port}",
        health_timeout=120,
        keyword_timeout=0,
    )


def _build_vite_service(directory: Path, pkg_data: dict) -> Service:
    name = pkg_data.get("name", "前端")
    if "/" in name:
        name = name.split("/")[-1]
    port = (_extract_port_from_env(directory)
            or _extract_port_from_vite_config(directory)
            or _extract_port_from_scripts(pkg_data)
            or DEFAULT_PORTS["vite"])
    npm_cmd = _get_npm_cmd(directory)

    # 判断是否是直接指向 vite 可执行文件（node+vite.js 或 vite.bin）
    cmd_str = " ".join(npm_cmd).lower()
    is_direct_vite = "vite" in cmd_str and "npx" not in cmd_str

    if is_direct_vite:
        cmd = npm_cmd + ["--port", str(port)]
    elif npm_cmd[0] in ("pnpm", "npm", "yarn"):
        cmd = npm_cmd + ["run", "dev", "--", "--port", str(port)]
    else:
        cmd = ["npx", "vite", "--port", str(port)]

    return Service(
        name=f"{name.capitalize()} 前端",
        project_type="vite",
        project_dir=directory,
        port=port,
        start_cmd=cmd,
        health_keyword="ready in",
        health_url=f"http://localhost:{port}",
        health_timeout=30,
        keyword_timeout=30,
    )


def _build_next_service(directory: Path, pkg_data: dict) -> Service:
    name = pkg_data.get("name", "Next.js")
    if "/" in name:
        name = name.split("/")[-1]
    port = _extract_port_from_env(directory) or _extract_port_from_scripts(pkg_data) or DEFAULT_PORTS["next"]

    return Service(
        name=f"{name.capitalize()} Next.js",
        project_type="next",
        project_dir=directory,
        port=port,
        start_cmd=["npx", "next", "dev", "--port", str(port)],
        health_keyword="started server",
        health_url=f"http://localhost:{port}",
        health_timeout=30,
        keyword_timeout=30,
    )


def _build_node_backend_service(directory: Path, pkg_data: dict) -> Service:
    name = pkg_data.get("name", "Node.js 后端")
    if "/" in name:
        name = name.split("/")[-1]
    port = _extract_port_from_env(directory) or _extract_port_from_scripts(pkg_data) or DEFAULT_PORTS["node-backend"]
    scripts = pkg_data.get("scripts", {})

    # 尝试使用 start/dev script
    if "start" in scripts:
        cmd = [shutil.which("npm") or "npm", "run", "start"]
    elif "dev" in scripts:
        cmd = [shutil.which("npm") or "npm", "run", "dev"]
    else:
        # 查找入口文件
        entry = directory / "src" / "index.ts"
        if not entry.exists():
            entry = directory / "src" / "index.js"
        if not entry.exists():
            entry = directory / "index.ts"
        if not entry.exists():
            entry = directory / "index.js"

        if entry.exists():
            if entry.suffix == ".ts":
                cmd = ["npx", "ts-node", str(entry.relative_to(directory))]
            else:
                cmd = ["node", str(entry.relative_to(directory))]
        else:
            cmd = [shutil.which("npm") or "npm", "run", "start"]

    return Service(
        name=f"{name.capitalize()} 后端",
        project_type="node-backend",
        project_dir=directory,
        port=port,
        start_cmd=cmd,
        health_keyword="listening",
        health_url=f"http://localhost:{port}",
        health_timeout=30,
        keyword_timeout=30,
    )


def _build_python_service(directory: Path) -> Optional[Service]:
    """检测并构建 Python 服务"""
    req_file = directory / "requirements.txt"
    has_fastapi = False
    has_flask = False
    has_django = False

    if req_file.exists():
        try:
            content = req_file.read_text(encoding="utf-8").lower()
            has_fastapi = "fastapi" in content
            has_flask = "flask" in content
            has_django = "django" in content
        except Exception:
            pass

    # 检查 pyproject.toml
    pyproject = directory / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8").lower()
            has_fastapi = has_fastapi or "fastapi" in content
            has_flask = has_flask or "flask" in content
            has_django = has_django or "django" in content
        except Exception:
            pass

    if not (has_fastapi or has_flask or has_django):
        # 检查目录名或入口文件内容
        entry = _find_python_entry(directory)
        if entry:
            try:
                content = entry.read_text(encoding="utf-8").lower()
                has_fastapi = "fastapi" in content or "uvicorn" in content
                has_flask = "flask" in content
                has_django = "django" in content
            except Exception:
                pass

        # 如果没有明确框架，避免把辅助脚本误判成 FastAPI 服务
        if not (has_fastapi or has_flask or has_django):
            return None

    port = _extract_port_from_env(directory) or DEFAULT_PORTS["python"]
    dir_name = directory.name

    if has_django:
        manage = directory / "manage.py"
        if manage.exists():
            cmd = [sys.executable, "manage.py", "runserver", f"127.0.0.1:{port}"]
        else:
            cmd = [sys.executable, "-m", "django", "runserver", f"127.0.0.1:{port}"]
        keyword = "Starting development server"
    elif has_flask:
        env_data = _read_env_file(directory)
        app_module = env_data.get("FLASK_APP", "")
        if app_module:
            cmd = [sys.executable, "-m", "flask", "run", "--port", str(port), "--host", "127.0.0.1"]
        else:
            cmd = [sys.executable, "-m", "flask", "run", "--port", str(port), "--host", "127.0.0.1"]
        keyword = "Running on"
    else:
        # FastAPI / uvicorn
        # 查找 ASGI 入口
        asgi_found = False
        if (directory / "main.py").exists() or (directory / "app" / "main.py").exists():
            asgi_found = True

        if asgi_found and (directory / "app").is_dir() and (directory / "app" / "main.py").exists():
            module = "app.main:app"
        elif (directory / "main.py").exists():
            module = "main:app"
        elif (directory / "app.py").exists():
            module = "app:app"
        else:
            entry = _find_python_entry(directory)
            if entry:
                module = entry.stem + ":app"
            else:
                module = "main:app"

        python_exe = sys.executable
        # 尝试使用项目 venv
        for venv_path in [directory / "venv", directory / ".venv"]:
            venv_py = venv_path / "Scripts" / "python.exe" if sys.platform == "win32" else venv_path / "bin" / "python"
            if venv_py.exists():
                python_exe = str(venv_py)
                break

        cmd = [python_exe, "-m", "uvicorn", module, "--reload", "--port", str(port), "--host", "127.0.0.1"]
        keyword = "Application startup complete"

    return Service(
        name=f"{dir_name.capitalize()} 后端",
        project_type="python",
        project_dir=directory,
        port=port,
        start_cmd=cmd,
        health_keyword=keyword,
        health_url=f"http://127.0.0.1:{port}",
        health_timeout=30,
        keyword_timeout=60 if has_fastapi else 30,
    )


def _build_spring_boot_maven_service(directory: Path, pom_path: Path) -> Optional[Service]:
    if not _has_spring_boot(pom_path):
        return None

    port = (
        _extract_port_from_pom(pom_path)
        or _extract_port_from_spring_boot_yaml(directory)
        or _extract_port_from_env(directory)
        or DEFAULT_PORTS["spring-boot"]
    )
    dir_name = directory.name

    # 尝试提取 artifactId 作为名称
    try:
        content = pom_path.read_text(encoding="utf-8")
        match = re.search(r'<artifactId>\s*(.+?)\s*</artifactId>', content)
        if match:
            dir_name = match.group(1)
    except Exception:
        pass

    mvn_cmd = shutil.which("mvnw")
    if not mvn_cmd:
        mvnw = directory / "mvnw"
        if mvnw.exists():
            mvn_cmd = str(mvnw)
        else:
            mvn_cmd = shutil.which("mvn") or "mvn"

    return Service(
        name=f"{dir_name} 服务",
        project_type="spring-boot",
        project_dir=directory,
        port=port,
        start_cmd=[mvn_cmd, "spring-boot:run", f"-Dspring-boot.run.arguments=--server.port={port}"],
        health_keyword="Started ",
        health_url=_build_spring_boot_health_url(port, directory),
        health_timeout=60,
        keyword_timeout=120,
    )


def _build_spring_boot_gradle_service(directory: Path, gradle_path: Path) -> Optional[Service]:
    if not _has_spring_boot_gradle(gradle_path):
        return None

    port = _extract_port_from_gradle(gradle_path) or _extract_port_from_env(directory) or DEFAULT_PORTS["spring-boot-gradle"]
    dir_name = directory.name

    gradlew = directory / "gradlew"
    gradle_cmd = str(gradlew) if gradlew.exists() else (shutil.which("gradle") or "gradle")

    return Service(
        name=f"{dir_name} 服务",
        project_type="spring-boot-gradle",
        project_dir=directory,
        port=port,
        start_cmd=[gradle_cmd, "bootRun", "--args='--server.port=" + str(port) + "'"],
        health_keyword="Started ",
        health_url=f"http://localhost:{port}/actuator/health",
        health_timeout=60,
        keyword_timeout=120,
    )


# ============================================================
# 进程管理
# ============================================================

def _get_pids_by_port_fallback(port: int) -> list:
    """macOS/Linux: 通过 lsof 获取端口占用 PID"""
    pids = []
    try:
        result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                try:
                    pids.append(int(line.strip()))
                except ValueError:
                    continue
    except Exception:
        pass
    return pids


def check_port(port: int) -> tuple:
    """检查端口占用，返回 (是否占用, PID列表)"""
    pids = []
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                if conn.pid:
                    pids.append(conn.pid)
    except psutil.AccessDenied:
        pids = _get_pids_by_port_fallback(port)
    except Exception:
        pids = _get_pids_by_port_fallback(port)

    return (bool(pids), pids) if pids else (False, [])


def _pid_alive(pid: int) -> bool:
    try:
        psutil.Process(pid)
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def get_active_pid_on_port(port: int) -> Optional[int]:
    in_use, pids = check_port(port)
    if not in_use:
        return None
    for pid in pids:
        if _pid_alive(pid):
            return pid
    return pids[0] if pids else None


def find_process_by_port(port: int) -> list:
    """查找占用端口的存活进程"""
    pids = set()
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr and conn.laddr.port == port and conn.pid and conn.pid != os.getpid():
                try:
                    psutil.Process(conn.pid)
                    pids.add(conn.pid)
                except psutil.NoSuchProcess:
                    continue
    except psutil.AccessDenied:
        for pid in _get_pids_by_port_fallback(port):
            if pid != os.getpid():
                try:
                    psutil.Process(pid)
                    pids.add(pid)
                except psutil.NoSuchProcess:
                    continue
    except Exception:
        for pid in _get_pids_by_port_fallback(port):
            if pid != os.getpid():
                try:
                    psutil.Process(pid)
                    pids.add(pid)
                except psutil.NoSuchProcess:
                    continue
    return sorted(pids)


def verify_belongs_to_service(pid: int, svc: Service) -> bool:
    """验证 PID 是否属于指定的服务。任一验证通过即返回 True，全部失败返回 False。"""
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied:
        log(f"无法验证 PID {pid}（权限不足），跳过", "WARN")
        return False

    project_dir = svc.project_dir.resolve()

    # 第一层：cwd 验证
    try:
        cwd = Path(proc.cwd()).resolve()
        if cwd == project_dir or project_dir in cwd.parents:
            return True
    except (psutil.AccessDenied, OSError):
        pass

    # 第二层：cmdline 特征验证（排除通用参数，避免误匹配）
    try:
        cmdline = " ".join(proc.cmdline())
        GENERIC_ARGS = {"--port", "--host", "--reload", "-m", "--workers", "--loop", "--http"}
        for part in svc.start_cmd:
            if part in GENERIC_ARGS:
                continue
            if part in cmdline:
                return True
        if svc.project_type == "python":
            indicators = [k for k in ["uvicorn", "fastapi", "app.main", "gunicorn", "flask", "django"] if k in cmdline]
            if len(indicators) >= 2:
                return True
        if svc.project_type in ["vite", "uniapp", "taro"]:
            if "vite" in cmdline and str(project_dir) in cmdline:
                return True
    except (psutil.AccessDenied, OSError):
        pass

    # 第三层：端口验证
    try:
        for conn in proc.connections(kind='inet'):
            if conn.laddr and conn.laddr.port == svc.port:
                return True
    except (psutil.AccessDenied, OSError):
        pass

    return False


def kill_process(pid: int, graceful: bool = True, use_taskkill: bool = True):
    """终止进程，支持跨平台降级。注意：此函数只应接收已通过身份验证的 PID。"""
    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
    except psutil.NoSuchProcess:
        log(f"进程 {pid} 已不存在", "INFO")
        return

    if graceful:
        try:
            proc.terminate()
            proc.wait(timeout=3)
            log(f"{proc_name} (PID {pid}) 已停止", "SUCCESS")
            return
        except psutil.AccessDenied:
            log(f"终止 {proc_name} (PID {pid}) 权限不足，尝试系统级强制终止", "WARN")
        except (psutil.TimeoutExpired, ChildProcessError, psutil.NoSuchProcess):
            pass  # 继续到强制终止

    # 强制终止阶段
    killed = False
    try:
        proc.kill()
        killed = True  # kill 信号已成功发送
        proc.wait(timeout=2)
    except psutil.AccessDenied:
        log(f"强制终止 {proc_name} (PID {pid}) 权限不足", "WARN")
    except (psutil.TimeoutExpired, ChildProcessError, psutil.NoSuchProcess):
        pass  # 进程已在终止中或已消失

    if not killed and use_taskkill:
        # 跨平台系统级强制终止
        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    killed = True
                else:
                    stderr = result.stderr.decode("utf-8", errors="ignore") if result.stderr else ""
                    # 进程不存在说明已被终止，视为成功
                    if "not found" in stderr.lower() or "无法找到" in stderr or "找不到" in stderr:
                        killed = True
                    else:
                        log(f"taskkill 失败 (PID {pid}): {stderr}", "ERROR")
            except Exception as e:
                log(f"taskkill 执行异常 (PID {pid}): {e}", "ERROR")
        else:
            try:
                result = subprocess.run(
                    ["kill", "-9", str(pid)],
                    capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    killed = True
                else:
                    stderr = result.stderr.decode("utf-8", errors="ignore") if result.stderr else ""
                    # 进程不存在说明已被终止，视为成功
                    if "no such process" in stderr.lower() or "not found" in stderr.lower():
                        killed = True
                    else:
                        log(f"kill -9 失败 (PID {pid}): {stderr}", "ERROR")
            except Exception as e:
                log(f"kill -9 执行异常 (PID {pid}): {e}", "ERROR")

    # 兜底检查：进程已消失则视为成功终止（可能已被之前的信号终止）
    if not killed:
        try:
            psutil.Process(pid)
        except psutil.NoSuchProcess:
            killed = True

    if killed:
        log(f"{proc_name} (PID {pid}) 已强制终止", "WARN")
    else:
        log(f"无法终止 {proc_name} (PID {pid})，请手动处理", "ERROR")


def _iter_child_processes(pid: int) -> list:
    """递归获取子进程列表，子进程优先用于关闭进程树。"""
    try:
        proc = psutil.Process(pid)
        return proc.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []


def kill_process_tree(pid: int, graceful: bool = True, use_taskkill: bool = True):
    """终止进程树，避免 uvicorn --reload 子进程残留并继续占用数据库连接。"""
    children = _iter_child_processes(pid)
    def _depth(proc):
        try:
            return len(proc.parents())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0

    for child in sorted(children, key=_depth, reverse=True):
        if child.pid == os.getpid():
            continue
        kill_process(child.pid, graceful=graceful, use_taskkill=use_taskkill)
    kill_process(pid, graceful=graceful, use_taskkill=use_taskkill)


def cleanup_orphan_python_children(project_dir: Path):
    """清理当前项目下父进程已消失的 Python reload 子进程。"""
    project_dir = project_dir.resolve()
    cleaned = 0
    for proc in psutil.process_iter(["pid", "ppid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if "multiprocessing.spawn" not in cmdline:
                continue
            parent_pid = int(proc.info.get("ppid") or 0)
            if parent_pid and _pid_alive(parent_pid):
                continue
            cwd = Path(proc.cwd()).resolve()
            if project_dir == cwd or project_dir in cwd.parents:
                kill_process(proc.pid, graceful=False, use_taskkill=True)
                cleaned += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            continue
    if cleaned:
        log(f"已清理 {cleaned} 个孤儿 Python reload 子进程", "WARN")


def stop_service(svc: Service):
    """优雅停止指定服务，带身份验证"""
    log(f"停止 {svc.name} (端口 {svc.port})...", "INFO")
    pids = find_process_by_port(svc.port)
    if not pids:
        log(f"{svc.name} 未运行", "INFO")
        return

    verified = []
    for pid in pids:
        if verify_belongs_to_service(pid, svc):
            verified.append(pid)
        else:
            log(f"PID {pid} 不属于 {svc.name}，跳过", "WARN")

    if not verified:
        log(f"端口 {svc.port} 被占用，但未找到属于 {svc.name} 的进程", "WARN")
        return

    for pid in verified:
        kill_process_tree(pid, graceful=True)


def kill_service(svc: Service):
    """强制终止指定服务，带身份验证"""
    log(f"强制终止 {svc.name} (端口 {svc.port})...", "WARN")
    pids = find_process_by_port(svc.port)
    if not pids:
        log(f"{svc.name} 未运行", "INFO")
        return

    verified = []
    for pid in pids:
        if verify_belongs_to_service(pid, svc):
            verified.append(pid)
        else:
            log(f"PID {pid} 不属于 {svc.name}，跳过", "WARN")

    if not verified:
        log(f"端口 {svc.port} 被占用，但未找到属于 {svc.name} 的进程", "WARN")
        return

    for pid in verified:
        kill_process_tree(pid, graceful=False)


# ============================================================
# 健康检查
# ============================================================

def wait_for_log_keyword(log_file: Path, keyword: str, timeout: int = 30) -> bool:
    """轮询日志文件等待关键字"""
    log(f'等待日志关键字: "{keyword}"', "DEBUG")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            if log_file.exists():
                break
            time.sleep(0.5)
        except KeyboardInterrupt:
            log("用户中断等待", "WARN")
            return False

    try:
        time.sleep(2)  # 等待进程开始写日志
    except KeyboardInterrupt:
        log("用户中断等待", "WARN")
        return False

    while time.time() - start_time < timeout:
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if keyword in content:
                    return True
        except KeyboardInterrupt:
            log("用户中断等待", "WARN")
            return False
        except Exception:
            pass
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            log("用户中断等待", "WARN")
            return False

    return False


def http_get(url: str, timeout: int = 10) -> bool:
    """HTTP GET 请求"""
    if HAS_REQUESTS:
        try:
            resp = _requests.get(url, timeout=timeout)
            return resp.status_code == 200
        except Exception:
            return False
    else:
        try:
            from urllib.request import urlopen
            resp = urlopen(url, timeout=timeout)
            return resp.status == 200
        except Exception:
            return False


def http_health_check(url: str, timeout: int = 10) -> bool:
    """HTTP 健康检查"""
    log(f"HTTP 健康检查: {url}", "DEBUG")
    start_time = time.time()
    while time.time() - start_time < timeout:
        if http_get(url):
            return True
        time.sleep(0.5)
    return False


def check_service_health(svc: Service) -> bool:
    """两阶段健康检查"""
    log(f"健康检查开始: {svc.name}", "INFO")
    log_file = svc.log_path

    if not svc.health_keyword:
        log(f"[1/2] Log keyword skipped: {svc.name}", "INFO")
    elif wait_for_log_keyword(log_file, svc.health_keyword, svc.keyword_timeout):
        log(f"[1/2] 日志就绪: {svc.name}", "SUCCESS")
    else:
        log(f"[1/2] 日志关键字超时: {svc.name}", "WARN")
        if http_health_check(svc.health_url, svc.health_timeout):
            log(f"[2/2] HTTP ready: {svc.name} ({svc.health_url})", "SUCCESS")
            return True
        _print_log_tail(svc.name, log_file)
        return False

    if http_health_check(svc.health_url, svc.health_timeout):
        log(f"[2/2] HTTP ready: {svc.name} ({svc.health_url})", "SUCCESS")
        return True
    else:
        log(f"[2/2] HTTP 健康检查失败: {svc.name}", "ERROR")
        _print_log_tail(svc.name, log_file)
        return False


def _print_log_tail(name: str, log_file: Path):
    """输出日志最后 20 行"""
    if log_file.exists():
        try:
            lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()[-20:]
            if lines:
                log(f"{name} 日志最后 20 行:", "WARN")
                for line in lines:
                    print(f"  {line}")
        except Exception:
            pass


# ============================================================
# 依赖安装
# ============================================================

def _parse_requirements_packages(req_file: Path) -> list[str]:
    """从 requirements.txt 中提取包名列表（去掉版本约束）。"""
    packages = []
    if not req_file.exists():
        return packages
    try:
        text = req_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return packages
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # 去掉行内注释
        if " #" in line:
            line = line.split(" #")[0].strip()
        # 提取纯包名
        pkg = re.split(r"[=~!<>,;\[\]]", line)[0].strip()
        if pkg:
            packages.append(pkg)
    return packages


def _check_python_import(python_exe: str, package: str) -> bool:
    """检查指定 Python 解释器是否可以导入某个包。"""
    try:
        result = subprocess.run(
            [python_exe, "-c", f"import {package}"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _get_service_python(svc: Service) -> str:
    """获取服务对应的 Python 解释器路径。"""
    if svc.project_type == "python":
        # 优先从启动命令中提取
        if svc.start_cmd and svc.start_cmd[0].lower().endswith(("python.exe", "python")):
            exe = Path(svc.start_cmd[0])
            if exe.exists():
                return str(exe)
        # 从项目目录找 venv/.venv 中的 Python
        for venv_name in ("venv", ".venv"):
            venv_dir = svc.project_dir / venv_name
            if venv_dir.exists():
                if sys.platform == "win32":
                    py = venv_dir / "Scripts" / "python.exe"
                else:
                    py = venv_dir / "bin" / "python"
                if py.exists():
                    return str(py)
    # 回退到当前解释器
    return sys.executable


def _install_python_dependencies(svc: Service) -> bool:
    """检查并安装 Python 缺失依赖。"""
    req_file = svc.project_dir / "requirements.txt"
    if not req_file.exists():
        log(f"[{svc.name}] 未找到 requirements.txt，跳过依赖检查", "DEBUG")
        return True

    packages = _parse_requirements_packages(req_file)
    if not packages:
        log(f"[{svc.name}] requirements.txt 为空，跳过依赖检查", "DEBUG")
        return True

    python_exe = _get_service_python(svc)
    # 检查前 10 个包（平衡速度和覆盖率）
    check_pkgs = packages[:10]
    missing = [pkg for pkg in check_pkgs if not _check_python_import(python_exe, pkg)]

    if not missing:
        log(f"[{svc.name}] Python 依赖已满足", "DEBUG")
        return True

    log(f"[{svc.name}] 检测到缺失依赖: {', '.join(missing)}，开始安装...", "INFO")
    try:
        result = subprocess.run(
            [python_exe, "-m", "pip", "install", "-r", str(req_file)],
            cwd=str(svc.project_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=120,
        )
        if result.returncode == 0:
            log(f"[{svc.name}] 依赖安装成功", "SUCCESS")
            return True
        else:
            err = result.stderr.strip()[-200:] if result.stderr else "未知错误"
            log(f"[{svc.name}] 依赖安装失败: {err}", "WARN")
            return False
    except subprocess.TimeoutExpired:
        log(f"[{svc.name}] 依赖安装超时 (120s)", "WARN")
        return False
    except Exception as e:
        log(f"[{svc.name}] 依赖安装异常: {e}", "WARN")
        return False


def _install_node_dependencies(svc: Service) -> bool:
    """检查并安装 Node.js 缺失依赖。"""
    node_modules = svc.project_dir / "node_modules"
    if node_modules.exists() and any(node_modules.iterdir()):
        log(f"[{svc.name}] node_modules 已存在，跳过依赖安装", "DEBUG")
        return True

    pkg_manager = _get_package_manager(svc.project_dir)
    log(f"[{svc.name}] node_modules 缺失，开始执行 {pkg_manager} install...", "INFO")
    try:
        result = subprocess.run(
            [pkg_manager, "install"],
            cwd=str(svc.project_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=300,
        )
        if result.returncode == 0:
            log(f"[{svc.name}] 依赖安装成功", "SUCCESS")
            return True
        else:
            err = result.stderr.strip()[-200:] if result.stderr else "未知错误"
            log(f"[{svc.name}] 依赖安装失败: {err}", "WARN")
            return False
    except subprocess.TimeoutExpired:
        log(f"[{svc.name}] 依赖安装超时 (300s)", "WARN")
        return False
    except Exception as e:
        log(f"[{svc.name}] 依赖安装异常: {e}", "WARN")
        return False


def install_dependencies(svc: Service) -> bool:
    """根据服务类型安装缺失的依赖。返回 True 表示依赖已满足（或无需安装），
    False 表示安装失败（但不阻断启动）。"""
    if svc.project_type == "python":
        return _install_python_dependencies(svc)
    if svc.project_type in ("vite", "taro", "uniapp", "next", "node-backend"):
        return _install_node_dependencies(svc)
    if svc.project_type in ("spring-boot", "spring-boot-gradle"):
        return True
    return True


def _retry_after_missing_module(svc: Service) -> bool:
    """启动失败后，检查日志中的 ModuleNotFoundError，自动安装缺失模块并重试一次。"""
    log_file = svc.log_path
    if not log_file.exists():
        return False

    try:
        content = log_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    # 匹配 ModuleNotFoundError: No module named 'xxx'
    match = re.search(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]", content)
    if not match:
        return False

    module_name = match.group(1)
    # 模块名通常等于 pip 包名（如 apscheduler）
    # 但有一些例外（如 PIL -> Pillow），先尝试直接用模块名安装
    pip_package = module_name.split(".")[0]  # apscheduler.schedulers -> apscheduler

    # 安全校验：防止命令注入 / 参数走私
    if not pip_package or not re.fullmatch(r"[A-Za-z0-9_\-]+", pip_package):
        log(f"[{svc.name}] 模块名 '{pip_package}' 包含非法字符，跳过自动安装", "WARN")
        return False
    if pip_package.startswith("-"):
        log(f"[{svc.name}] 模块名 '{pip_package}' 以 '-' 开头，跳过自动安装", "WARN")
        return False

    python_exe = _get_service_python(svc)
    log(f"[{svc.name}] 检测到缺失模块 '{module_name}'，尝试自动安装 '{pip_package}' 后重试...", "INFO")

    try:
        result = subprocess.run(
            [python_exe, "-m", "pip", "install", "--", pip_package],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=120,
        )
        if result.returncode == 0:
            log(f"[{svc.name}] 模块 '{pip_package}' 安装成功，重新启动...", "SUCCESS")
            # 重试启动：停止当前进程（如果有），重新启动
            stop_service_wrapper(svc)
            time.sleep(2)
            return start_service(svc)
        else:
            err = result.stderr.strip()[-200:] if result.stderr else "未知错误"
            log(f"[{svc.name}] 模块 '{pip_package}' 安装失败: {err}", "WARN")
            return False
    except subprocess.TimeoutExpired:
        log(f"[{svc.name}] 模块 '{pip_package}' 安装超时 (120s)", "WARN")
        return False
    except Exception as e:
        log(f"[{svc.name}] 模块 '{pip_package}' 安装异常: {e}", "WARN")
        return False


# ============================================================
# 启动/停止
# ============================================================

def start_service(svc: Service) -> bool:
    """启动单个服务"""
    log_section(f"启动 {svc.name} ({svc.type_label()})")

    # 确保目录存在
    if not svc.project_dir.exists():
        log(f"项目目录不存在: {svc.project_dir}", "ERROR")
        return False

    if svc.project_type == "python":
        cleanup_orphan_python_children(svc.project_dir)

    # 检查端口占用
    in_use, pids = check_port(svc.port)
    if in_use:
        alive_pids = [pid for pid in pids if _pid_alive(pid)]
        if alive_pids:
            log(f"端口 {svc.port} 已被占用 (PID: {', '.join(map(str, alive_pids))})，先停止...", "WARN")
            kill_service(svc)
            time.sleep(3)
        else:
            log(f"端口 {svc.port} 有残留连接 (PID 已不存在)，直接启动...", "WARN")

    # 【新增】安装缺失依赖（失败不阻断启动）
    install_dependencies(svc)

    # 启动进程
    cmd = svc.start_cmd
    log(f"启动命令: {' '.join(cmd)}", "DEBUG")

    try:
        with open(svc.log_path, "w", encoding="utf-8") as f:
            popen_kwargs = _background_process_options()
            proc = subprocess.Popen(
                cmd,
                cwd=str(svc.project_dir),
                stdout=f,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                **popen_kwargs,
            )
        log(f"{svc.name} 进程已启动 (PID: {proc.pid})", "INFO")
    except FileNotFoundError as e:
        log(f"{svc.name} 启动失败: 命令不存在 — {e}", "ERROR")
        _suggest_runtime_install(svc)
        return False
    except Exception as e:
        log(f"{svc.name} 启动失败: {e}", "ERROR")
        return False

    # 健康检查
    if check_service_health(svc):
        log(f"{svc.name} 已就绪 {svc.health_url}", "SUCCESS")
        return True
    else:
        # 启动失败时，检查是否因 Python 模块缺失导致，尝试自动修复后重试一次
        if svc.project_type == "python":
            if _retry_after_missing_module(svc):
                return True
        log(f"{svc.name} 启动失败", "ERROR")
        return False


def _background_process_options() -> dict:
    """获取跨平台后台启动参数"""
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        if hasattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB"):
            creationflags |= subprocess.CREATE_BREAKAWAY_FROM_JOB
        return {
            "creationflags": creationflags,
            "startupinfo": startupinfo,
        }

    return {
        "start_new_session": True,
    }


def _suggest_runtime_install(svc: Service):
    """给出运行时环境安装建议"""
    suggestions = {
        "vite": "请确保已安装 Node.js，并在项目目录下运行: npm install 或 pnpm install",
        "next": "请确保已安装 Node.js，并在项目目录下运行: npm install",
        "node-backend": "请确保已安装 Node.js，并在项目目录下运行: npm install",
        "python": "请确保已安装 Python，并在项目目录下运行: pip install -r requirements.txt",
        "spring-boot": "请确保已安装 Java JDK 和 Maven",
        "spring-boot-gradle": "请确保已安装 Java JDK 和 Gradle",
    }
    tip = suggestions.get(svc.project_type, "")
    if tip:
        log(tip, "WARN")


def stop_service_wrapper(svc: Service):
    """停止单个服务"""
    log_section(f"停止 {svc.name}")
    stop_service(svc)
    if svc.project_type == "python":
        cleanup_orphan_python_children(svc.project_dir)


def restart_service(svc: Service) -> bool:
    """重启单个服务"""
    stop_service_wrapper(svc)
    time.sleep(2)
    return start_service(svc)


# ============================================================
# 状态查询
# ============================================================

def status_services(services: list[Service]):
    """查看所有服务状态"""
    log_section("服务状态")

    if not services:
        log("未发现任何服务", "WARN")
        log("请确保当前目录下存在可识别的项目（包含 package.json / requirements.txt / pom.xml / build.gradle）", "INFO")
        log_separator()
        return

    for svc in services:
        pid = get_active_pid_on_port(svc.port)
        if pid:
            try:
                proc = psutil.Process(pid)
                cpu = proc.cpu_percent(interval=0.1)
                mem = proc.memory_info().rss / 1024 / 1024
                status_icon = "运行中"
                color = COLORS["SUCCESS"]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                cpu = mem = 0
                status_icon = "异常"
                color = COLORS["ERROR"]
        else:
            cpu = mem = 0
            status_icon = "未运行"
            color = COLORS["INFO"]

        reset = COLORS["RESET"]
        cpu_str = f"{cpu:.1f}%" if cpu else "-"
        mem_str = f"{mem:.1f}MB" if mem else "-"
        dir_rel = svc.project_dir.relative_to(CWD) if svc.project_dir.is_relative_to(CWD) else svc.project_dir
        print(f"  {color}[{svc.name}]{reset}  类型: {svc.type_label()}  端口: {svc.port}  状态: {status_icon}  目录: {dir_rel}")
        if pid:
            print(f"    PID: {pid}  CPU: {cpu_str}  内存: {mem_str}")

    log_separator()
    print(f"  {COLORS['BOLD']}访问地址:{COLORS['RESET']}")
    for svc in services:
        print(f"    {svc.name}: {COLORS['SUCCESS']}{svc.health_url}{COLORS['RESET']}")
    log_separator()
    print(f"  {COLORS['BOLD']}日志目录:{COLORS['RESET']}")
    print(f"    {LOG_DIR}")
    log_separator()


# ============================================================
# 日志查看
# ============================================================

def tail_logs(target: str, services: list[Service]):
    """查看日志"""
    if target == "all":
        _tail_multi([svc.log_path for svc in services])
        return

    # 按名称或类型匹配
    matched = [s for s in services if target.lower() in s.name.lower() or target.lower() in s.project_type.lower()]
    if len(matched) == 1:
        log_file = matched[0].log_path
    elif len(matched) > 1:
        _tail_multi([s.log_path for s in matched])
        return
    else:
        # 尝试直接匹配文件
        log_file = LOG_DIR / f"{target}.log"
        if not log_file.exists():
            log(f"未找到日志: {target}", "ERROR")
            return

    if not log_file.exists():
        log(f"日志文件不存在: {log_file}", "ERROR")
        return

    log(f"实时查看日志 (Ctrl+C 退出)...", "INFO")

    if sys.platform == "win32":
        try:
            subprocess.run(["powershell", "-Command", f"Get-Content -Wait -Tail 50 '{log_file}'"], check=True)
        except KeyboardInterrupt:
            pass
        except Exception:
            _tail_python(log_file)
    else:
        try:
            subprocess.run(["tail", "-f", str(log_file)], check=True)
        except KeyboardInterrupt:
            pass


def _tail_multi(log_files: list):
    """多日志同时查看"""
    positions = {lf: 0 for lf in log_files}
    log("实时查看所有日志 (Ctrl+C 退出)...", "INFO")
    try:
        while True:
            new_output = False
            for lf in log_files:
                try:
                    with open(lf, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(positions[lf])
                        lines = f.readlines()
                        positions[lf] = f.tell()
                        for line in lines:
                            prefix = f"{lf.stem[:3]} "
                            print(f"{prefix}{line.rstrip()}")
                            new_output = True
                except Exception:
                    pass
            if not new_output:
                time.sleep(1)
    except KeyboardInterrupt:
        pass


def _tail_python(log_file: Path):
    """Python tail -f"""
    position = 0
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(0, 2)
            position = f.tell()
            f.seek(0)
            lines = f.readlines()
            for line in lines[-50:]:
                print(line.rstrip())

        while True:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(position)
                lines = f.readlines()
                position = f.tell()
                for line in lines:
                    print(line.rstrip())
            if not lines:
                time.sleep(1)
    except KeyboardInterrupt:
        pass


# ============================================================
# 服务过滤
# ============================================================

def filter_services(services: list[Service], svc_type: Optional[str] = None, port: Optional[int] = None) -> list[Service]:
    """按类型或端口过滤服务"""
    result = services
    if svc_type:
        result = [s for s in result if s.project_type == svc_type or svc_type.lower() in s.project_type.lower()]
    if port:
        result = [s for s in result if s.port == port]
    return result


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="通用服务管理脚本 — 自动发现并管理项目中的各类服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
可用命令:
  start       发现并启动所有服务（默认）
  stop        停止所有服务
  restart     重启所有服务
  status      查看发现的服务及运行状态
  discover    仅列出发现的服务（不启动）
  kill        强制终止服务
  logs        实时查看日志

选项:
  --type      按类型过滤: vite | python | spring-boot | node-backend | next
  --port      按端口号过滤
  --foreground, -f  前台模式运行（Ctrl+C 停止）

使用示例:
  dev-services                      发现并启动所有服务
  dev-services discover             仅列出发现的服务
  dev-services discover server      只列出 server 目录下的服务
  dev-services start frontend       只启动前端服务
  dev-services restart server       只重启后端服务
  dev-services status               查看所有服务状态
  dev-services status web           只查看大屏服务状态
  dev-services stop                 停止所有服务
  dev-services kill all             强制终止所有服务
  dev-services logs all             实时查看所有日志

支持的服务类型:
  Vite 前端          检测到 package.json + vite 依赖
  Next.js            检测到 package.json + next 依赖
  Node.js 后端       检测到 Express / NestJS / Koa
  Python 后端        检测到 FastAPI / Flask / Django
  Spring Boot        检测到 pom.xml + spring-boot 依赖
  Spring Boot Gradle 检测到 build.gradle + spring-boot 插件

端口提取:
  1. 优先从 .env / .env.development 提取
  2. 从 vite.config.ts / pom.xml / build.gradle 提取
  3. 从 application*.yml 提取 server.port（Spring Boot）
  4. 使用框架默认值

安装方式:
  脚本位于 ~/.claude/dev-services.py
  通过 PATH 中的 dev-services 命令调用
  (Windows: %USERPROFILE%\\bin\\dev-services.cmd)
""",
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="start",
        choices=["start", "stop", "restart", "status", "kill", "logs", "discover"],
        help="操作: start|stop|restart|status|kill|logs|discover (默认: start)",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="目标服务 (kill/logs) 或指定服务目录 (其他命令)",
    )
    parser.add_argument("--type", dest="svc_type", default=None, help="服务类型过滤: vite|python|spring-boot|node-backend")
    parser.add_argument("--port", dest="port", type=int, default=None, help="端口号过滤")
    parser.add_argument("--foreground", "-f", action="store_true", help="前台模式运行")

    args = parser.parse_args()

    # 解析 target：如果是存在的目录，作为服务发现的根目录；否则作为 kill/logs 的目标
    root_dir = None
    if args.target and args.action not in ("kill", "logs"):
        target_path = Path(args.target)
        if not target_path.is_absolute():
            target_path = CWD / target_path
        if target_path.is_dir():
            root_dir = target_path
        else:
            log(f"目标路径不存在: {args.target}", "ERROR")
            return

    # 发现服务
    services = discover_services(root_dir=root_dir)
    services = filter_services(services, args.svc_type, args.port)
    services = assign_unique_ports(services)

    if args.action == "discover":
        log_section(f"发现的服务 (目录: {root_dir or CWD})")
        if not services:
            log("未发现任何服务", "WARN")
            log("支持的类型: Vite 前端, Next.js, Node.js 后端, Python (FastAPI/Flask/Django), Spring Boot (Maven/Gradle)", "INFO")
        else:
            for i, svc in enumerate(services, 1):
                dir_rel = svc.project_dir.relative_to(CWD) if svc.project_dir.is_relative_to(CWD) else svc.project_dir
                print(f"  {COLORS['SUCCESS']}[{i}]{COLORS['RESET']} {COLORS['BOLD']}{svc.name}{COLORS['RESET']}")
                print(f"     类型: {svc.type_label()}  端口: {svc.port}")
                print(f"     目录: {dir_rel}")
                print(f"     命令: {' '.join(svc.start_cmd)}")
                print()
        log_separator()
        return

    if args.action == "status":
        status_services(services)
        return

    if args.action == "kill":
        target = args.target or "all"
        log_section("强制终止服务")
        if not services:
            log("未发现任何服务", "WARN")
        else:
            for svc in services:
                if target in ("all", svc.name.lower(), svc.project_type.lower()):
                    kill_service(svc)
        log_separator()
        return

    if args.action == "logs":
        target = args.target or "all"
        if not services:
            log("未发现任何服务，无法查看日志", "WARN")
            return
        tail_logs(target, services)
        return

    if args.action == "stop":
        if not services:
            log("未发现任何服务", "WARN")
            return
        for svc in services:
            stop_service_wrapper(svc)
        log_separator()
        log("所有服务已停止", "SUCCESS")
        return

    if args.action in ("start", "restart"):
        if not services:
            log("未发现任何服务", "WARN")
            log("支持的类型: Vite 前端, Next.js, Node.js 后端, Python (FastAPI/Flask/Django), Spring Boot (Maven/Gradle)", "INFO")
            log(f"扫描目录: {CWD} (最多 {MAX_SCAN_DEPTH} 层)", "DEBUG")
            return

        if args.action == "restart":
            for svc in services:
                restart_service(svc)
        else:
            # start
            if args.foreground:
                _run_foreground(services)
            else:
                log_separator()
                log(f"通用服务管理器 (目录: {CWD})", "INFO")
                log_separator()

                results = []
                for svc in services:
                    ok = start_service(svc)
                    results.append((svc, ok))

                log_separator()
                if all(ok for _, ok in results):
                    log("所有服务已就绪", "SUCCESS")
                    for svc, ok in results:
                        print(f"  {COLORS['SUCCESS']}✓ {svc.name}{COLORS['RESET']}: {svc.health_url}")
                elif any(ok for _, ok in results):
                    log("部分服务启动失败，请检查日志", "WARN")
                    for svc, ok in results:
                        icon = f"{COLORS['SUCCESS']}✓{COLORS['RESET']}" if ok else f"{COLORS['ERROR']}✗{COLORS['RESET']}"
                        print(f"  {icon} {svc.name}")
                else:
                    log("所有服务启动失败", "ERROR")
                    return
                log_separator()
        return


def _run_foreground(services: list[Service]):
    """前台模式运行"""
    procs = []

    def cleanup():
        log("正在停止服务...", "WARN")
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        for p in procs:
            try:
                p.wait(timeout=3)
            except Exception:
                p.kill()
        log("所有服务已停止", "INFO")

    import signal
    def handle_signal(signum, frame):
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, handle_signal)

    for svc in services:
        log_section(f"启动 {svc.name} (前台模式)")
        cmd = svc.start_cmd
        try:
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            proc = subprocess.Popen(
                cmd,
                cwd=str(svc.project_dir),
                creationflags=creationflags,
            )
            procs.append(proc)
        except Exception as e:
            log(f"{svc.name} 启动失败: {e}", "ERROR")

    log_separator()
    log("按 Ctrl+C 停止所有服务", "INFO")
    log_separator()

    for p in procs:
        p.wait()


if __name__ == "__main__":
    main()
