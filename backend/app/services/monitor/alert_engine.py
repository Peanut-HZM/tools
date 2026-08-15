"""
告警引擎 - 规则 CRUD、采样后评估、触发去重与恢复、站内通知记录
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from app.config.database import get_pooled_db_connection, release_db_connection
from app.models.monitor_models import AlertRuleCreateRequest, AlertRuleUpdateRequest
from app.services.monitor import webhook_notify
from app.services.monitor.server_service import MonitorServerService

logger = logging.getLogger(__name__)

# 内存触发状态：(rule_id, server_id) -> 连续命中次数
_firing_counts: Dict[tuple, int] = {}
# (rule_id, server_id) -> 当前是否处于触发态（触发态内不重复通知）
_firing_active: Dict[tuple, bool] = {}

_METRIC_LABELS = {
    "cpu_percent": "CPU 使用率",
    "memory_percent": "内存使用率",
    "disk_percent": "磁盘使用率",
    "load_avg": "负载（1分钟）",
    "net_recv_rate": "网络接收速率",
    "net_sent_rate": "网络发送速率",
}

_OPERATORS = {">": lambda v, t: v > t, ">=": lambda v, t: v >= t,
              "<": lambda v, t: v < t, "<=": lambda v, t: v <= t}


def ensure_tables() -> None:
    """确保告警表存在"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS monitor_alerts (
                id VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                server_id VARCHAR(64) NOT NULL DEFAULT 'all',
                metric VARCHAR(32) NOT NULL,
                operator VARCHAR(8) NOT NULL,
                threshold FLOAT NOT NULL,
                duration INT NOT NULL DEFAULT 3,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_monitor_alerts_user ON monitor_alerts(user_id)")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS monitor_alert_logs (
                id BIGSERIAL PRIMARY KEY,
                rule_id VARCHAR(64) NOT NULL,
                server_id VARCHAR(64) NOT NULL,
                server_name VARCHAR(64) NOT NULL,
                metric VARCHAR(32) NOT NULL,
                actual_value FLOAT NOT NULL,
                status VARCHAR(16) NOT NULL,
                is_read BOOLEAN NOT NULL DEFAULT FALSE,
                notified_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_monitor_alert_logs_user ON monitor_alert_logs(server_id, notified_at)")
        conn.commit()
    finally:
        cursor.close()
        release_db_connection(conn)


# ============ 规则 CRUD ============

def get_rules(user_id: str) -> List[Dict]:
    """获取用户告警规则"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM monitor_alerts WHERE user_id = %s ORDER BY created_at",
            (user_id,),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        cursor.close()
        release_db_connection(conn)


def create_rule(user_id: str, req: AlertRuleCreateRequest) -> Dict:
    """新建告警规则"""
    rule_id = str(uuid.uuid4())
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO monitor_alerts (id, user_id, server_id, metric, operator, threshold, duration, enabled)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (rule_id, user_id, req.server_id, req.metric, req.operator, req.threshold, req.duration, req.enabled),
        )
        conn.commit()
        logger.info("告警规则创建: user=%s metric=%s threshold=%s", user_id, req.metric, req.threshold)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        release_db_connection(conn)
    return _get_rule(user_id, rule_id)


def _get_rule(user_id: str, rule_id: str) -> Optional[Dict]:
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM monitor_alerts WHERE id = %s AND user_id = %s",
            (rule_id, user_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        cursor.close()
        release_db_connection(conn)


def update_rule(user_id: str, rule_id: str, req: AlertRuleUpdateRequest) -> Optional[Dict]:
    """更新告警规则"""
    if not _get_rule(user_id, rule_id):
        return None
    fields, values = [], []
    for key in ("server_id", "metric", "operator", "threshold", "duration", "enabled"):
        value = getattr(req, key, None)
        if value is not None:
            fields.append(f"{key} = %s")
            values.append(value)
    if not fields:
        return _get_rule(user_id, rule_id)
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        values.append(rule_id)
        cursor.execute(f"UPDATE monitor_alerts SET {', '.join(fields)} WHERE id = %s", values)
        conn.commit()
        # 规则变更后重置该规则触发状态
        for key in list(_firing_counts.keys()):
            if key[0] == rule_id:
                _firing_counts.pop(key, None)
                _firing_active.pop(key, None)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        release_db_connection(conn)
    return _get_rule(user_id, rule_id)


def delete_rule(user_id: str, rule_id: str) -> bool:
    """删除告警规则"""
    if not _get_rule(user_id, rule_id):
        return False
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM monitor_alerts WHERE id = %s", (rule_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        release_db_connection(conn)
    for key in list(_firing_counts.keys()):
        if key[0] == rule_id:
            _firing_counts.pop(key, None)
            _firing_active.pop(key, None)
    return True


# ============ 触发记录 ============

def _insert_log(rule_id, server_id, server_name, metric, actual_value, status) -> None:
    """写入触发记录（站内通知载体）"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO monitor_alert_logs (rule_id, server_id, server_name, metric, actual_value, status)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (rule_id, server_id, server_name, metric, actual_value, status),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error("告警日志写入失败: %s", str(e))
    finally:
        cursor.close()
        release_db_connection(conn)


def get_logs(user_id: str, page: int = 1, page_size: int = 20) -> Dict:
    """获取触发记录（分页），附带未读数"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        # 通过用户拥有的服务器过滤日志
        cursor.execute(
            """SELECT COUNT(*) AS total,
                      COUNT(*) FILTER (WHERE l.is_read = FALSE) AS unread
               FROM monitor_alert_logs l
               JOIN monitor_servers s ON s.id = l.server_id
               WHERE s.user_id = %s AND s.deleted = FALSE""",
            (user_id,),
        )
        summary = cursor.fetchone()
        offset = (page - 1) * page_size
        cursor.execute(
            """SELECT l.* FROM monitor_alert_logs l
               JOIN monitor_servers s ON s.id = l.server_id
               WHERE s.user_id = %s AND s.deleted = FALSE
               ORDER BY l.notified_at DESC LIMIT %s OFFSET %s""",
            (user_id, page_size, offset),
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
        release_db_connection(conn)
    total = summary["total"] if summary else 0
    return {
        "logs": [dict(r) for r in rows],
        "total": total,
        "unread_count": summary["unread"] if summary else 0,
        "page": page,
        "page_size": page_size,
    }


def mark_logs_read(user_id: str) -> None:
    """标记用户的告警记录全部已读"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """UPDATE monitor_alert_logs l SET is_read = TRUE
               FROM monitor_servers s
               WHERE s.id = l.server_id AND s.user_id = %s""",
            (user_id,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        release_db_connection(conn)


# ============ 评估 ============

def _get_webhook_url(user_id: str) -> str:
    """获取用户 Webhook 地址"""
    settings = MonitorServerService.get_settings(user_id)
    return settings.get("webhook_url") or ""


def _evaluate_rule(rule: Dict, m: Dict) -> Optional[float]:
    """规则命中返回当前值，否则 None"""
    if rule["metric"] == "load_avg":
        value = m.get("load_avg")
        if not value:
            return None
        value = value[0]
    else:
        value = m.get(rule["metric"])
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    op = _OPERATORS.get(rule["operator"])
    if not op:
        return None
    return value if op(value, float(rule["threshold"])) else None


def evaluate(server: Dict, m: Dict) -> None:
    """每次采样后评估该服务器的所有告警规则"""
    try:
        rules = get_rules(server["user_id"])
    except Exception as e:
        logger.error("加载告警规则失败: server=%s 错误=%s", server.get("id"), str(e))
        return
    webhook_url = _get_webhook_url(server["user_id"])
    for rule in rules:
        if not rule["enabled"]:
            continue
        if rule["server_id"] not in ("all", server["id"]):
            continue
        key = (rule["id"], server["id"])
        value = _evaluate_rule(rule, m)
        if value is None:
            # 条件不满足：计数清零；若在触发态则写恢复记录
            _firing_counts[key] = 0
            if _firing_active.get(key):
                _firing_active[key] = False
                logger.info("告警恢复: rule=%s server=%s value=%s", rule["id"], server.get("name"), value)
                _insert_log(rule_id=rule["id"], server_id=server["id"],
                            server_name=server.get("name") or "",
                            metric=rule["metric"],
                            actual_value=value if value is not None else 0,
                            status="recovered")
            continue
        # 触发态内冻结计数，不重复通知（规则去重）
        if _firing_active.get(key):
            continue
        count = _firing_counts.get(key, 0) + 1
        _firing_counts[key] = count
        if count < rule["duration"]:
            continue
        # 达到连续次数且未在触发态 → 触发
        _firing_active[key] = True
        _insert_log(rule_id=rule["id"], server_id=server["id"],
                    server_name=server.get("name") or "",
                    metric=rule["metric"], actual_value=value, status="firing")
        label = _METRIC_LABELS.get(rule["metric"], rule["metric"])
        if webhook_url:
            content = (
                f"## 服务器监控告警\n"
                f"- 服务器: {server.get('name')}\n"
                f"- 指标: {label}\n"
                f"- 条件: {rule['operator']} {rule['threshold']}\n"
                f"- 当前值: {value}\n"
                f"- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            webhook_notify.send_webhook(webhook_url, f"监控告警 - {server.get('name')}", content)
        logger.warning("告警触发: rule=%s server=%s metric=%s value=%s",
                       rule["id"], server.get("name"), rule["metric"], value)
