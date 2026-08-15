"""
监控指标存储 - PostgreSQL 时序表写入/查询/聚合/清理
"""
import logging
from typing import Dict, List, Optional

from app.config.database import get_pooled_db_connection, release_db_connection

logger = logging.getLogger(__name__)

# 时间范围（秒）
RANGE_SECONDS = {"1h": 3600, "6h": 21600, "24h": 86400, "7d": 604800}


def ensure_tables() -> None:
    """确保指标表存在"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS monitor_metrics (
                id BIGSERIAL PRIMARY KEY,
                server_id VARCHAR(64) NOT NULL,
                collected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                cpu_percent FLOAT,
                cpu_per_core JSONB,
                load_avg JSONB,
                mem_total BIGINT,
                mem_used BIGINT,
                mem_percent FLOAT,
                swap_total BIGINT,
                swap_used BIGINT,
                swap_percent FLOAT,
                disk_total BIGINT,
                disk_used BIGINT,
                disk_percent FLOAT,
                net_recv_rate FLOAT,
                net_sent_rate FLOAT,
                disk_read_rate FLOAT,
                disk_write_rate FLOAT,
                process_count INT,
                uptime_seconds BIGINT
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_monitor_metrics_server_time ON monitor_metrics(server_id, collected_at)"
        )
        conn.commit()
    finally:
        cursor.close()
        release_db_connection(conn)


def insert_metric(server_id: str, m: Dict) -> None:
    """写入一条指标"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO monitor_metrics (
                server_id, cpu_percent, cpu_per_core, load_avg,
                mem_total, mem_used, mem_percent,
                swap_total, swap_used, swap_percent,
                disk_total, disk_used, disk_percent,
                net_recv_rate, net_sent_rate, disk_read_rate, disk_write_rate,
                process_count, uptime_seconds
            ) VALUES (
                %s, %s, %s::jsonb, %s::jsonb,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s
            )
            """,
            (
                server_id, m["cpu_percent"],
                __import__("json").dumps(m["cpu_per_core"]),
                __import__("json").dumps(m["load_avg"]),
                m["mem_total"], m["mem_used"], m["mem_percent"],
                m["swap_total"], m["swap_used"], m["swap_percent"],
                m["disk_total"], m["disk_used"], m["disk_percent"],
                m["net_recv_rate"], m["net_sent_rate"],
                m["disk_read_rate"], m["disk_write_rate"],
                m["process_count"], m["uptime_seconds"],
            ),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error("监控指标写入失败: server=%s 错误=%s", server_id, str(e))
        raise
    finally:
        cursor.close()
        release_db_connection(conn)


def _row_to_metric(row) -> Dict:
    """数据库行转指标 dict"""
    return {
        "collected_at": row.get("collected_at"),
        "cpu_percent": row.get("cpu_percent"),
        "cpu_per_core": row.get("cpu_per_core"),
        "load_avg": row.get("load_avg"),
        "mem_total": row.get("mem_total"),
        "mem_used": row.get("mem_used"),
        "mem_percent": row.get("mem_percent"),
        "swap_total": row.get("swap_total"),
        "swap_used": row.get("swap_used"),
        "swap_percent": row.get("swap_percent"),
        "disk_total": row.get("disk_total"),
        "disk_used": row.get("disk_used"),
        "disk_percent": row.get("disk_percent"),
        "net_recv_rate": row.get("net_recv_rate"),
        "net_sent_rate": row.get("net_sent_rate"),
        "disk_read_rate": row.get("disk_read_rate"),
        "disk_write_rate": row.get("disk_write_rate"),
        "process_count": row.get("process_count"),
        "uptime_seconds": row.get("uptime_seconds"),
    }


def get_latest_metric(server_id: str) -> Optional[Dict]:
    """获取最近一条指标"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM monitor_metrics WHERE server_id = %s ORDER BY collected_at DESC LIMIT 1",
            (server_id,),
        )
        row = cursor.fetchone()
    finally:
        cursor.close()
        release_db_connection(conn)
    return _row_to_metric(row) if row else None


def query_metrics(server_id: str, range_key: str) -> List[Dict]:
    """查询历史指标；range_key ∈ {1h, 6h, 24h, 7d}；7d 按小时聚合降采样"""
    seconds = RANGE_SECONDS.get(range_key, RANGE_SECONDS["1h"])
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        if range_key == "7d":
            # 按小时聚合
            cursor.execute(
                """
                SELECT date_trunc('hour', collected_at) AS t,
                       avg(cpu_percent) AS cpu_percent,
                       avg(mem_percent) AS mem_percent,
                       avg(disk_percent) AS disk_percent,
                       avg(net_recv_rate) AS net_recv_rate,
                       avg(net_sent_rate) AS net_sent_rate,
                       avg(disk_read_rate) AS disk_read_rate,
                       avg(disk_write_rate) AS disk_write_rate,
                       avg((load_avg->>0)::float) AS load1
                FROM monitor_metrics
                WHERE server_id = %s AND collected_at >= now() - interval '604800 seconds'
                GROUP BY t ORDER BY t
                """,
                (server_id,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "collected_at": r["t"],
                    "cpu_percent": round(r["cpu_percent"], 1) if r["cpu_percent"] is not None else None,
                    "mem_percent": round(r["mem_percent"], 1) if r["mem_percent"] is not None else None,
                    "disk_percent": round(r["disk_percent"], 1) if r["disk_percent"] is not None else None,
                    "net_recv_rate": r["net_recv_rate"],
                    "net_sent_rate": r["net_sent_rate"],
                    "disk_read_rate": r["disk_read_rate"],
                    "disk_write_rate": r["disk_write_rate"],
                    "load_avg": [r["load1"]],
                }
                for r in rows
            ]
        cursor.execute(
            """
            SELECT * FROM monitor_metrics
            WHERE server_id = %s AND collected_at >= now() - make_interval(secs => %s)
            ORDER BY collected_at
            """,
            (server_id, seconds),
        )
        rows = cursor.fetchall()
        return [_row_to_metric(r) for r in rows]
    finally:
        cursor.close()
        release_db_connection(conn)


def delete_expired_metrics(seconds: int = 604800) -> int:
    """删除超过保留期的指标，返回删除数量"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM monitor_metrics WHERE collected_at < now() - make_interval(secs => %s)",
            (seconds,),
        )
        conn.commit()
        count = cursor.rowcount
        if count:
            logger.info("监控指标清理: 删除 %d 条过期数据", count)
        return count
    except Exception as e:
        conn.rollback()
        logger.error("监控指标清理失败: %s", str(e))
        return 0
    finally:
        cursor.close()
        release_db_connection(conn)
