"""
内嵌 bash 采集脚本 - 无外部依赖（仅 bash 内建 + cat/awk/df/sleep），输出单行 JSON
"""
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

BASH_SCRIPT = r'''#!/bin/bash
# 服务器监控采集脚本：两次采样计算 CPU/网络/磁盘速率，输出单行 JSON
interval=0.2
BEGIN='MONITOR_DATA_BEGIN'
END='MONITOR_DATA_END'

# --- CPU（总 + 各核心），基于 /proc/stat 两次采样 ---
prev_file=$(mktemp)
curr_file=$(mktemp)
grep '^cpu' /proc/stat > "$prev_file"
sleep "$interval"
grep '^cpu' /proc/stat > "$curr_file"
cpu_info=$(awk -v itv="$interval" '
NR==FNR {
  if ($1 ~ /^cpu[0-9]+$/) {
    key=$1; n[key]=NF
    for (i=2; i<=NF; i++) p[key,i]=$i
  }
  if ($1 == "cpu") {
    for (i=2; i<=NF; i++) pt[i]=$i
  }
  next
}
{
  if ($1 ~ /^cpu[0-9]+$/) {
    key=$1
    pidle = p[key,5] + p[key,6]
    cidle = $5 + $6
    ptotal = 0; ctotal = 0
    for (i=2; i<=NF; i++) { ptotal += p[key,i]; ctotal += $i }
    idled = cidle - pidle; totald = ctotal - ptotal
    if (totald <= 0) { pct = 0 } else { pct = 100 * (1 - idled / totald) }
    if (pct < 0) pct = 0
    if (pct > 100) pct = 100
    printf "%s:%.1f,", key, pct
  }
  if ($1 == "cpu") {
    pidle = pt[5] + pt[6]; cidle = $5 + $6
    ptotal = 0; ctotal = 0
    for (i=2; i<=NF; i++) { ptotal += pt[i]; ctotal += $i }
    idled = cidle - pidle; totald = ctotal - ptotal
    if (totald <= 0) { total = 0 } else { total = 100 * (1 - idled / totald) }
    if (total < 0) total = 0
    if (total > 100) total = 100
    total_out = sprintf("TOTAL:%.1f", total)
  }
}
END { printf "%s", total_out }' "$prev_file" "$curr_file")
rm -f "$prev_file" "$curr_file"

# --- 内存 / 交换分区，基于 /proc/meminfo ---
mem_info=$(awk '
/^MemTotal:/ { t=$2 }
/^MemAvailable:/ { a=$2 }
/^SwapTotal:/ { st=$2 }
/^SwapFree:/ { sf=$2 }
END {
  t=t*1024; a=a*1024; st=st*1024; sf=sf*1024
  used = t - a
  if (used < 0) used = 0
  mempct = t > 0 ? used / t * 100 : 0
  swpct = st > 0 ? (st - sf) / st * 100 : 0
  printf "%d|%d|%.1f|%d|%d|%.1f", t, used, mempct, st, st - sf, swpct
}' /proc/meminfo)

# --- 负载与运行时长 ---
load_info=$(awk '{printf "%s|%s|%s", $1, $2, $3}' /proc/loadavg)
uptime_s=$(awk '{printf "%d", $1}' /proc/uptime)

# --- 磁盘容量（df -Pk，根分区） ---
disk_info=$(df -Pk / | awk 'NR==2 {printf "%d|%d|%.1f", $2*1024, ($2-$4)*1024, $5}' | sed 's/%$//')
disk_pct=$(echo "$disk_info" | awk -F'|' '{if ($3 > 100) $3 = 100; print $3}')

# --- 网络速率（/proc/net/dev 两次采样，排除 loopback） ---
net_before=$(mktemp)
net_after=$(mktemp)
awk 'NR>2 && $1 != "lo:" {gsub(":", "", $1); r += $2; t += $10} END {printf "%d %d", r, t}' /proc/net/dev > "$net_before"
sleep "$interval"
awk 'NR>2 && $1 != "lo:" {gsub(":", "", $1); r += $2; t += $10} END {printf "%d %d", r, t}' /proc/net/dev > "$net_after"
net_info=$(awk -v itv="$interval" '
NR==FNR { br=$1; bt=$2; next }
{ dr=$1-br; dt=$2-bt; if (dr<0) dr=0; if (dt<0) dt=0; printf "%.1f %.1f", dr/itv, dt/itv }
' "$net_before" "$net_after")
rm -f "$net_before" "$net_after"

# --- 磁盘 IO 速率（/proc/diskstats，排除分区与 loop/ram 设备） ---
io_before=$(mktemp)
io_after=$(mktemp)
awk 'NR>1 && $3 !~ /loop|ram/ && $3 ~ /^[a-z]+$/ && $3 !~ /[0-9]$/ {r += $6; w += $10} END {printf "%d %d", r, w}' /proc/diskstats > "$io_before"
sleep "$interval"
awk 'NR>1 && $3 !~ /loop|ram/ && $3 ~ /^[a-z]+$/ && $3 !~ /[0-9]$/ {r += $6; w += $10} END {printf "%d %d", r, w}' /proc/diskstats > "$io_after"
io_info=$(awk -v itv="$interval" '
NR==FNR { br=$1; bw=$2; next }
{ dr=$1-br; dw=$2-bw; if (dr<0) dr=0; if (dw<0) dw=0; printf "%.1f %.1f", dr*512/itv, dw*512/itv }
' "$io_before" "$io_after")
rm -f "$io_before" "$io_after"

# --- 进程数 ---
proc_count=$(ls /proc 2>/dev/null | grep -cE '^[0-9]+$')

echo "${BEGIN}$(cat <<JSON
{"cpu_percent": $(echo "$cpu_info" | sed -n 's/.*TOTAL:\([0-9.]*\)$/\1/p'),
 "cpu_per_core": [$(echo "$cpu_info" | grep -oE 'cpu[0-9]+:[0-9.]+' | sed 's/^cpu[0-9]*://' | paste -sd, -)],
 "load_avg": [$(echo "$load_info" | awk -F'|' '{print $1", "$2", "$3}')],
 "mem_total": $(echo "$mem_info" | cut -d'|' -f1),
 "mem_used": $(echo "$mem_info" | cut -d'|' -f2),
 "mem_percent": $(echo "$mem_info" | cut -d'|' -f3),
 "swap_total": $(echo "$mem_info" | cut -d'|' -f4),
 "swap_used": $(echo "$mem_info" | cut -d'|' -f5),
 "swap_percent": $(echo "$mem_info" | cut -d'|' -f6),
 "disk_total": $(echo "$disk_info" | cut -d'|' -f1),
 "disk_used": $(echo "$disk_info" | cut -d'|' -f2),
 "disk_percent": ${disk_pct:-0},
 "net_recv_rate": $(echo "$net_info" | cut -d' ' -f1),
 "net_sent_rate": $(echo "$net_info" | cut -d' ' -f2),
 "disk_read_rate": $(echo "$io_info" | cut -d' ' -f1),
 "disk_write_rate": $(echo "$io_info" | cut -d' ' -f2),
 "process_count": ${proc_count:-0},
 "uptime_seconds": ${uptime_s:-0}}
JSON
)${END}"
'''

_REQUIRED_KEYS = [
    "cpu_percent", "cpu_per_core", "load_avg",
    "mem_total", "mem_used", "mem_percent",
    "swap_total", "swap_used", "swap_percent",
    "disk_total", "disk_used", "disk_percent",
    "net_recv_rate", "net_sent_rate",
    "disk_read_rate", "disk_write_rate",
    "process_count", "uptime_seconds",
]


def parse_script_output(raw_output: str) -> Optional[Dict]:
    """解析采集脚本输出，失败返回 None"""
    try:
        start = raw_output.find("MONITOR_DATA_BEGIN")
        end = raw_output.find("MONITOR_DATA_END")
        if start == -1 or end == -1 or end <= start:
            return None
        data = json.loads(raw_output[start + len("MONITOR_DATA_BEGIN"):end])
        if not isinstance(data, dict):
            return None
        for key in _REQUIRED_KEYS:
            if key not in data:
                logger.warning("采集数据缺少字段: %s", key)
                return None
        # 数值收敛：百分比限制 0-100，速率/容量非负
        for pct_key in ("cpu_percent", "mem_percent", "swap_percent", "disk_percent"):
            data[pct_key] = max(0.0, min(100.0, float(data[pct_key])))
        data["cpu_per_core"] = [max(0.0, min(100.0, float(x))) for x in data["cpu_per_core"]]
        data["load_avg"] = [max(0.0, float(x)) for x in data["load_avg"]]
        for rate_key in ("net_recv_rate", "net_sent_rate", "disk_read_rate", "disk_write_rate"):
            data[rate_key] = max(0.0, float(data[rate_key]))
        for int_key in ("mem_total", "mem_used", "swap_total", "swap_used",
                        "disk_total", "disk_used", "process_count", "uptime_seconds"):
            data[int_key] = max(0, int(float(data[int_key])))
        data["cpu_percent"] = float(data["cpu_percent"])
        return data
    except (ValueError, TypeError, KeyError) as e:
        logger.warning("采集数据解析失败: %s", str(e))
        return None
