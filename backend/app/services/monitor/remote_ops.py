"""
按需远程操作 - 进程列表/结束、systemd 服务管理、磁盘分区、权限检测、系统信息
本机走 subprocess，远程走 SSH 连接池
"""
import asyncio
import logging
import subprocess
import time
from typing import Dict, List, Optional

from app.services.monitor.ssh_client import SSHCommandError, pool

logger = logging.getLogger(__name__)

# 系统信息缓存（60 秒）
_sysinfo_cache: Dict[str, dict] = {}
_sysinfo_cache_time: Dict[str, float] = {}
_SYSINFO_CACHE_TTL = 60


async def _run_on_server(server: Dict, command: str, timeout: int = 10) -> str:
    """在目标上执行命令：本机 subprocess / 远程 SSH"""
    if server.get("server_type") == "local":
        return await asyncio.to_thread(_run_local_command, command, timeout)
    return await pool.run_command(server, command, timeout)


def _run_local_command(command: str, timeout: int = 10) -> str:
    """本机执行 shell 命令"""
    result = subprocess.run(command, shell=True, capture_output=True,
                            text=True, timeout=timeout)
    if result.returncode != 0:
        raise SSHCommandError(f"本地命令执行失败 (exit={result.returncode}): {result.stderr[:200]}")
    return result.stdout


# ============ 磁盘分区 ============

def _parse_df_output(output: str) -> List[Dict]:
    """解析 df -Pk 输出（1024-blocks 单位）"""
    rows = []
    for line in output.strip().splitlines()[1:]:
        parts = line.split()
        if len(parts) < 6:
            continue
        mountpoint = " ".join(parts[5:])  # 挂载点可能含空格
        capacity = parts[4].rstrip("%")
        try:
            rows.append({
                "device": parts[0],
                "mountpoint": mountpoint,
                "fstype": "",
                "total": int(parts[1]) * 1024,
                "used": int(parts[2]) * 1024,
                "free": int(parts[3]) * 1024,
                "percent": float(capacity),
            })
        except ValueError:
            continue
    return rows


async def get_partitions(server: Dict) -> List[Dict]:
    """获取磁盘分区列表（实时）"""
    out = await _run_on_server(server, "df -Pk", timeout=10)
    return _parse_df_output(out)


# ============ 进程管理 ============

def _parse_ps_output(output: str) -> List[Dict]:
    """解析 ps 输出（管道分隔）：pid|user|stat|pcpu|pmem|rss|vsz|nlwp|etime|args"""
    processes = []
    for line in output.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 9)
        if len(parts) < 10:
            continue
        pid, user, stat, pcpu, pmem, rss, vsz, nlwp, etime, args = parts
        try:
            processes.append({
                "pid": int(pid),
                "name": args.split()[0].split("/")[-1] if args.split() else "",
                "username": user,
                "status": stat,
                "cpu_percent": round(float(pcpu), 1),
                "memory_percent": round(float(pmem), 1),
                "memory_rss": int(rss) * 1024,
                "memory_vms": int(vsz) * 1024,
                "num_threads": int(nlwp),
                "create_time": etime,
                "command_line": args[:300],
                "project_type": _detect_project_type(args),
            })
        except (ValueError, IndexError):
            continue
    return processes


def _detect_project_type(args: str) -> str:
    """按命令行检测项目类型（远程简化版）"""
    args_lower = args.lower()
    if "uvicorn" in args_lower or "fastapi" in args_lower:
        return "FastAPI"
    if "django" in args_lower:
        return "Django"
    if "flask" in args_lower:
        return "Flask"
    if "celery" in args_lower:
        return "Celery"
    if "gunicorn" in args_lower:
        return "Gunicorn"
    if "spring" in args_lower or "java -jar" in args_lower:
        return "Java"
    if "node" in args_lower:
        return "Node.js"
    if "nginx" in args_lower:
        return "Nginx"
    if "mysqld" in args_lower or "/mysql" in args_lower:
        return "MySQL"
    if "postgres" in args_lower:
        return "PostgreSQL"
    if "redis" in args_lower:
        return "Redis"
    if "dockerd" in args_lower or "containerd" in args_lower:
        return "Docker"
    if "python" in args_lower:
        return "Python"
    return "Other"


async def get_processes(
    server: Dict, sort_by: str = "cpu_percent", sort_order: str = "desc",
    search: Optional[str] = None, project_type: Optional[str] = None,
    page: int = 1, page_size: int = 50,
) -> Dict:
    """获取远程进程列表（ps 命令 + 服务端过滤/排序/分页）"""
    ps_cmd = (
        "ps axo pid=,user=,stat=,pcpu=,pmem=,rss=,vsz=,nlwp=,etime=,args= "
        "| awk '{pid=$1;user=$2;stat=$3;pcpu=$4;pmem=$5;rss=$6;vsz=$7;nlwp=$8;"
        "rest=\"\"; for(i=9;i<=NF;i++) rest=rest \" \" $i; "
        "print pid \"|\" user \"|\" stat \"|\" pcpu \"|\" pmem \"|\" rss \"|\" vsz \"|\" nlwp \"|\" etime \"|\" rest}'"
    )
    out = await _run_on_server(server, ps_cmd, timeout=15)
    processes = _parse_ps_output(out)

    if project_type and project_type != "all":
        processes = [p for p in processes if p["project_type"] == project_type]
    if search:
        search_lower = search.lower()
        processes = [
            p for p in processes
            if search_lower in p["name"].lower() or search_lower in p["command_line"].lower()
        ]

    reverse = sort_order == "desc"
    sort_keys = {"cpu_percent", "memory_percent", "pid", "memory_rss", "num_threads", "name"}
    if sort_by in sort_keys:
        key_fn = (lambda p: str(p[sort_by]).lower()) if sort_by == "name" else (lambda p: p[sort_by])
        processes.sort(key=key_fn, reverse=reverse)

    total = len(processes)
    offset = (page - 1) * page_size
    return {
        "processes": processes[offset:offset + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    }


async def kill_process(server: Dict, pid: int) -> bool:
    """结束远程进程（先 TERM 后 KILL）"""
    try:
        await _run_on_server(server, f"kill {pid}", timeout=10)
        return True
    except Exception:
        try:
            await _run_on_server(server, f"kill -9 {pid}", timeout=10)
            return True
        except Exception:
            return False


# ============ 服务管理 ============

def _parse_services_output(units_output: str, files_output: str) -> List[Dict]:
    """解析 systemctl 输出"""
    enabled_map = {}
    for line in files_output.strip().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            enabled_map[parts[0]] = parts[1]
    services = []
    for line in units_output.strip().splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5 or not parts[0].endswith(".service"):
            continue
        name, load, active, state, desc = parts
        services.append({
            "name": name,
            "load": load,
            "active": active,
            "state": state,
            "description": desc,
            "enabled": enabled_map.get(name) == "enabled",
        })
    return services


async def get_services(server: Dict) -> List[Dict]:
    """获取 systemd 服务列表"""
    units_cmd = "systemctl list-units --type=service --all --no-pager --no-legend --plain"
    files_cmd = "systemctl list-unit-files --type=service --no-pager --no-legend --plain"
    try:
        units_out, files_out = await asyncio.gather(
            _run_on_server(server, units_cmd, timeout=15),
            _run_on_server(server, files_cmd, timeout=15),
        )
    except Exception as e:
        logger.warning("获取服务列表失败: %s", str(e))
        return []
    return _parse_services_output(units_out, files_out)


async def service_action(server: Dict, unit: str, action: str) -> Dict:
    """执行服务启停（优先 sudo -n，失败回退直接 systemctl）"""
    for cmd in (f"sudo -n systemctl {action} {unit}", f"systemctl {action} {unit}"):
        try:
            await _run_on_server(server, cmd, timeout=20)
            logger.info("服务操作成功: %s %s on %s", action, unit, server.get("name"))
            return {"success": True, "message": f"{action} 成功"}
        except SSHCommandError as e:
            last_error = str(e)
        except Exception as e:
            last_error = str(e)
    if "sudo" in last_error and "root" in last_error.lower():
        message = "需要 root 或无密码 sudo 权限"
    else:
        message = last_error[:200]
    return {"success": False, "message": message}


async def check_privileges(server: Dict) -> Dict:
    """检测 sudo 可用性"""
    try:
        out = await _run_on_server(server, "sudo -n true; echo EXIT:$?", timeout=10)
        return {"sudo_available": "EXIT:0" in out}
    except Exception:
        return {"sudo_available": False}


# ============ 系统信息 ============

async def get_system_info(server: Dict) -> Dict:
    """获取系统信息（本机 psutil / 远程命令，带 60s 缓存）"""
    server_id = server.get("id")
    now = time.time()
    if server_id in _sysinfo_cache and now - _sysinfo_cache_time.get(server_id, 0) < _SYSINFO_CACHE_TTL:
        return _sysinfo_cache[server_id]
    if server.get("server_type") == "local":
        from app.services.system_monitor_service import get_system_info as get_local_info
        info = get_local_info()
    else:
        cmd = (
            "hostname; cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '\"'; "
            "uname -r; uptime -p"
        )
        try:
            out = await _run_on_server(server, cmd, timeout=10)
            lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
            info = {
                "hostname": lines[0] if len(lines) > 0 else server.get("host", ""),
                "os": lines[1] if len(lines) > 1 else "Linux",
                "kernel": lines[2] if len(lines) > 2 else "",
                "uptime_text": lines[3] if len(lines) > 3 else "",
                "platform": "Linux",
            }
        except Exception as e:
            logger.warning("远程系统信息获取失败: %s", str(e))
            info = {"hostname": server.get("host", ""), "os": "Linux",
                    "kernel": "", "uptime_text": "", "platform": "Linux"}
    _sysinfo_cache[server_id] = info
    _sysinfo_cache_time[server_id] = now
    return info
