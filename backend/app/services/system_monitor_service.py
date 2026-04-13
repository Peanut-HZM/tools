"""
系统性能监控服务 - 使用 psutil 获取系统信息和进程列表
"""

import logging
import socket
import platform
import time
from typing import List, Dict, Optional
from datetime import datetime

import psutil

logger = logging.getLogger(__name__)

# 系统信息缓存（30 秒），因为硬件信息不会频繁变化
_system_info_cache: Dict = {}
_system_info_cache_time: float = 0
_SYSTEM_INFO_CACHE_TTL = 30  # 秒


def get_system_info() -> Dict:
    """获取系统基本信息（带 30 秒缓存）"""
    global _system_info_cache, _system_info_cache_time
    now = time.time()
    if _system_info_cache and (now - _system_info_cache_time) < _SYSTEM_INFO_CACHE_TTL:
        # 只更新运行时间（会变化）
        cached = dict(_system_info_cache)
        cached["uptime"] = _format_uptime(psutil.boot_time())
        return cached

    boot_time = datetime.fromtimestamp(psutil.boot_time())
    result = {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "os_version": platform.version(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
        "uptime": _format_uptime(psutil.boot_time()),
        "cpu": {
            "model": _get_cpu_model(),
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "frequency": _get_cpu_frequency(),
        },
        "memory": {
            "total": psutil.virtual_memory().total,
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        },
        "disk": {
            "total": psutil.disk_usage("/").total,
            "total_gb": round(psutil.disk_usage("/").total / (1024**3), 2),
        },
    }
    _system_info_cache.clear()
    _system_info_cache.update(result)
    _system_info_cache_time = now
    return result


def get_resource_usage() -> Dict:
    """获取实时资源占用情况"""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    cpu_percent = psutil.cpu_percent(interval=0.5)

    # 网络 I/O
    net_io = psutil.net_io_counters()

    # 磁盘 I/O
    disk_io = psutil.disk_io_counters()
    if disk_io is None:
        logger.warning("磁盘 I/O 计数器不可用（某些系统/容器环境不支持）")

    # 各 CPU 核心占用
    per_cpu = psutil.cpu_percent(interval=0.5, percpu=True)

    # 所有磁盘分区使用情况
    partitions = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            partitions.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total": usage.total,
                "total_gb": round(usage.total / (1024**3), 2),
                "used": usage.used,
                "used_gb": round(usage.used / (1024**3), 2),
                "free": usage.free,
                "free_gb": round(usage.free / (1024**3), 2),
                "percent": usage.percent,
            })
        except (PermissionError, OSError):
            continue

    return {
        "cpu": {
            "percent": cpu_percent,
            "per_cpu": per_cpu,
        },
        "memory": {
            "total": mem.total,
            "total_gb": round(mem.total / (1024**3), 2),
            "available": mem.available,
            "available_gb": round(mem.available / (1024**3), 2),
            "used": mem.used,
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
        },
        "swap": {
            "total": swap.total,
            "total_gb": round(swap.total / (1024**3), 2),
            "used": swap.used,
            "used_gb": round(swap.used / (1024**3), 2),
            "free": swap.free,
            "free_gb": round(swap.free / (1024**3), 2),
            "percent": swap.percent,
        },
        "disk": {
            "total": disk.total,
            "total_gb": round(disk.total / (1024**3), 2),
            "used": disk.used,
            "used_gb": round(disk.used / (1024**3), 2),
            "free": disk.free,
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": disk.percent,
            "partitions": partitions,
        },
        "network": {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
        },
        "disk_io": {
            "read_bytes": disk_io.read_bytes if disk_io else 0,
            "write_bytes": disk_io.write_bytes if disk_io else 0,
            "read_count": disk_io.read_count if disk_io else 0,
            "write_count": disk_io.write_count if disk_io else 0,
        },
        "gpu": _get_gpu_info(),
    }


def _get_gpu_info() -> Optional[Dict]:
    """获取 GPU 信息（仅 NVIDIA GPU，通过 nvidia-smi）"""
    if platform.system() == "Darwin":
        # macOS 无 nvidia-smi，跳过
        return None
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return None
        gpus = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6:
                gpus.append({
                    "name": parts[0],
                    "utilization": float(parts[1]) if parts[1] else 0,
                    "memory_used_mb": float(parts[2]) if parts[2] else 0,
                    "memory_total_mb": float(parts[3]) if parts[3] else 0,
                    "temperature": int(parts[4]) if parts[4] else 0,
                    "power_w": float(parts[5]) if parts[5] else 0,
                })
        return {"gpus": gpus} if gpus else None
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return None


def get_process_list(
    sort_by: str = "cpu_percent",
    sort_order: str = "desc",
    search: Optional[str] = None,
    project_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Dict:
    """获取进程列表，支持排序、搜索、项目类型过滤、分页"""

    processes = []
    for proc in psutil.process_iter(["pid", "name", "username", "status", "create_time",
                                       "cpu_percent", "memory_percent", "memory_info", "num_threads"]):
        try:
            info = proc.info
            if info is None:
                continue

            # 项目类型检测
            pt = _detect_project_type(info.get("name", ""), proc)

            # 项目类型过滤
            if project_type and project_type != "all" and pt != project_type:
                continue

            # 搜索过滤
            if search:
                search_lower = search.lower()
                if search_lower not in info.get("name", "").lower():
                    continue

            mem_info = info.get("memory_info")
            processes.append({
                "pid": info.get("pid"),
                "name": info.get("name", ""),
                "username": info.get("username", ""),
                "status": info.get("status", ""),
                "cpu_percent": round(info.get("cpu_percent", 0) or 0, 1),
                "memory_percent": round(info.get("memory_percent", 0) or 0, 1),
                "memory_rss": mem_info.rss if mem_info else 0,
                "memory_vms": mem_info.vms if mem_info else 0,
                "num_threads": info.get("num_threads", 0),
                "create_time": _format_process_time(info.get("create_time")),
                "command_line": _get_cmdline(proc),
                "project_type": pt,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # 聚合进程类型统计（基于全量数据，排序前）
    type_map: Dict[str, Dict] = {}
    for p in processes:
        pt = p["project_type"]
        if pt == "Other":
            continue
        if pt not in type_map:
            type_map[pt] = {"count": 0, "cpu_percent": 0.0, "memory_percent": 0.0, "memory_rss": 0}
        type_map[pt]["count"] += 1
        type_map[pt]["cpu_percent"] += p["cpu_percent"]
        type_map[pt]["memory_percent"] += p["memory_percent"]
        type_map[pt]["memory_rss"] += p["memory_rss"]

    # 过滤：只返回 count > 1 或 cpu_percent > 0.1 的类型，按 CPU 降序
    type_summary = sorted(
        [
            {
                "type": t,
                "count": v["count"],
                "cpu_percent": round(v["cpu_percent"], 1),
                "memory_percent": round(v["memory_percent"], 1),
                "memory_rss": v["memory_rss"],
            }
            for t, v in type_map.items()
            if v["count"] > 1 or v["cpu_percent"] > 0.1
        ],
        key=lambda x: x["cpu_percent"],
        reverse=True,
    )

    # 排序
    reverse = sort_order == "desc"
    sort_key = sort_by if sort_by in ("cpu_percent", "memory_percent", "pid", "memory_rss", "num_threads", "name") else "cpu_percent"
    processes.sort(key=lambda p: p.get(sort_key, 0) if sort_key != "name" else (p.get("name", "") or "").lower(), reverse=reverse)

    total = len(processes)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    offset = (page - 1) * page_size
    page_data = processes[offset:offset + page_size]

    return {
        "processes": page_data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "type_summary": type_summary,
    }


def _get_cpu_model() -> str:
    """获取 CPU 型号"""
    if platform.system() == "Darwin":
        import subprocess
        try:
            result = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                                    capture_output=True, text=True, timeout=5)
            return result.stdout.strip()
        except Exception:
            return platform.processor()
    elif platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except Exception:
            pass
    return platform.processor() or "Unknown"


def _get_cpu_frequency() -> Optional[float]:
    """获取 CPU 频率 (MHz)"""
    freq = psutil.cpu_freq()
    if freq:
        return round(freq.current, 1)
    return None


def _format_uptime(boot_time_timestamp: float) -> str:
    """格式化运行时间"""
    now = time.time()
    diff = now - boot_time_timestamp
    days = int(diff // 86400)
    hours = int((diff % 86400) // 3600)
    minutes = int((diff % 3600) // 60)
    parts = []
    if days:
        parts.append(f"{days}天")
    if hours:
        parts.append(f"{hours}小时")
    parts.append(f"{minutes}分钟")
    return "".join(parts)


def _format_process_time(timestamp: Optional[float]) -> str:
    """格式化进程启动时间"""
    if not timestamp:
        return ""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


def _get_cmdline(proc) -> str:
    """获取进程命令行"""
    try:
        cmdline = proc.cmdline()
        if cmdline:
            return " ".join(cmdline[:10])  # 限制长度
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        pass
    return ""


def _detect_project_type(name: str, proc) -> str:
    """检测进程的项目类型"""
    name_lower = name.lower()

    # Python 项目
    if name_lower in ("python", "python3", "python3.10", "python3.11", "python3.12"):
        try:
            cmdline = " ".join(proc.cmdline()).lower()
            if "uvicorn" in cmdline or "fastapi" in cmdline:
                return "FastAPI"
            if "django" in cmdline:
                return "Django"
            if "flask" in cmdline:
                return "Flask"
            if "celery" in cmdline:
                return "Celery"
            if "gunicorn" in cmdline:
                return "Gunicorn"
            return "Python"
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return "Python"

    # Java 项目
    if name_lower in ("java", "javaw"):
        try:
            cmdline = " ".join(proc.cmdline()).lower()
            if "spring" in cmdline:
                return "Spring Boot"
            if "tomcat" in cmdline:
                return "Tomcat"
            if "jetty" in cmdline:
                return "Jetty"
            return "Java"
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return "Java"

    # Node.js / 前端项目
    if name_lower in ("node", "nodejs"):
        try:
            cmdline = " ".join(proc.cmdline()).lower()
            if "vite" in cmdline:
                return "Vite"
            if "next" in cmdline:
                return "Next.js"
            if "nuxt" in cmdline:
                return "Nuxt"
            if "webpack" in cmdline:
                return "Webpack"
            if "npm" in cmdline:
                return "npm"
            if "yarn" in cmdline:
                return "Yarn"
            if "pnpm" in cmdline:
                return "pnpm"
            return "Node.js"
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return "Node.js"

    # Nginx
    if name_lower in ("nginx",):
        return "Nginx"

    # MySQL
    if name_lower in ("mysqld", "mysql"):
        return "MySQL"

    # PostgreSQL
    if name_lower in ("postgres", "postgresql"):
        return "PostgreSQL"

    # Redis
    if name_lower in ("redis-server", "redis"):
        return "Redis"

    # Docker
    if name_lower in ("docker", "dockerd", "containerd"):
        return "Docker"

    # Go
    if name_lower.endswith(".go") or name_lower.startswith("go"):
        return "Go"

    # Ruby
    if name_lower in ("ruby",):
        return "Ruby"

    return "Other"


def kill_process(pid: int) -> bool:
    """终止指定进程"""
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=3)
        return True
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied:
        # 权限不足时尝试强制 kill
        try:
            proc = psutil.Process(pid)
            proc.kill()
            proc.wait(timeout=3)
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    except psutil.TimeoutExpired:
        # terminate 超时后强制 kill
        try:
            proc = psutil.Process(pid)
            proc.kill()
            proc.wait(timeout=3)
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
