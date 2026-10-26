"""
敏感数据存量加密迁移脚本（一次性，可重复执行）

背景：
    数据加密整改前，部分敏感数据以明文入库。本次迁移把存量明文统一转为
    密文 / 脱敏形态，并保证脚本幂等（重复执行不产生二次加密、不破坏数据）。

处理项：
    1. sql_execution_history.sql_statement / error_message / result_data
       —— 落库前脱敏（保持可读，遮蔽其中的密钥/口令/私钥）
    2. openclaw_configs.token
       —— Fernet 密文（与运行时 openclaw_config_service.encrypt_value 同一密钥）
    3. cross_share_messages.content
       —— enc:v1: 密文（与运行时 secure_storage.encrypt_text 同一主密钥）
    4. http_requests.auth_config / headers
       —— enc:v1: 密文（JSON 字符串形态，列类型不变）
    5. http_environments.variables
       —— enc:v1: 密文（JSON 字符串形态，列类型不变）
    6. http_request_history.request_data
       —— enc:v1: 密文（含实际请求头，可能带 Authorization）
       http_request_history.response_data
       —— 脱敏（保持可读，遮蔽响应体中的凭据）

安全约束：
    * 所有 UPDATE 都带精确 WHERE（按 id / config_key），不做宽条件更新
    * 每项处理前后各打印一次 COUNT，便于核对
    * 只处理「尚未加密」的行，天然幂等

用法：
    cd backend && python -m scripts.migrate_sensitive_data_encryption [--dry-run]
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import psycopg2
from psycopg2.extras import RealDictCursor

from app.utils.sensitive_redactor import redact_sensitive, redact_structure
from app.utils.secure_storage import CIPHER_PREFIX, decrypt_text, encrypt_text
from app.services.openclaw_config_service import encrypt_value as openclaw_encrypt

DRY_RUN = "--dry-run" in sys.argv


def log(msg: str):
    print(msg, flush=True)


def count_rows(cur, table: str, where: str = "", params=()) -> int:
    sql = f"SELECT COUNT(*) AS c FROM {table}"
    if where:
        sql += f" WHERE {where}"
    cur.execute(sql, params)
    return cur.fetchone()["c"]


def migrate_sql_history(cur, conn):
    """1. SQL 执行历史脱敏"""
    log("\n=== [1/6] sql_execution_history 脱敏 ===")
    cur.execute("SELECT id, sql_statement, error_message, result_data FROM sql_execution_history")
    rows = cur.fetchall()
    before = len(rows)
    changed = 0
    for row in rows:
        new_sql = redact_sensitive(row["sql_statement"]) if row["sql_statement"] else row["sql_statement"]
        new_err = redact_sensitive(row["error_message"]) if row["error_message"] else row["error_message"]
        new_data = row["result_data"]
        if row["result_data"]:
            try:
                parsed = json.loads(row["result_data"])
                new_data = json.dumps(redact_structure(parsed), ensure_ascii=False, default=str)
            except (TypeError, ValueError):
                new_data = redact_sensitive(row["result_data"])
        if new_sql != row["sql_statement"] or new_err != row["error_message"] or new_data != row["result_data"]:
            changed += 1
            if not DRY_RUN:
                cur.execute(
                    "UPDATE sql_execution_history "
                    "SET sql_statement = %s, error_message = %s, result_data = %s WHERE id = %s",
                    (new_sql, new_err, new_data, row["id"]),
                )
    if not DRY_RUN:
        conn.commit()
    log(f"  处理前 {before} 行 → 需变更 {changed} 行（dry_run={DRY_RUN}）")
    return changed


def migrate_openclaw_token(cur, conn):
    """2. openclaw_configs.token 加密"""
    log("\n=== [2/6] openclaw_configs.token 加密 ===")
    cur.execute("SELECT config_key, config_value FROM openclaw_configs WHERE config_key = 'token'")
    row = cur.fetchone()
    if not row:
        log("  token 配置不存在，跳过")
        return 0
    value = row["config_value"] or ""
    if value.startswith("gAAAAA"):
        log("  已是 Fernet 密文，跳过")
        return 0
    if not value:
        log("  token 为空，跳过")
        return 0
    if not DRY_RUN:
        cur.execute(
            "UPDATE openclaw_configs SET config_value = %s, updated_at = CURRENT_TIMESTAMP WHERE config_key = 'token'",
            (openclaw_encrypt(value),),
        )
        conn.commit()
    log("  明文 token 已加密（dry_run=%s）" % DRY_RUN)
    return 1


def migrate_cross_share(cur, conn):
    """3. cross_share_messages.content 加密"""
    log("\n=== [3/6] cross_share_messages.content 加密 ===")
    cur.execute("SELECT id, content FROM cross_share_messages WHERE content IS NOT NULL AND content <> ''")
    rows = cur.fetchall()
    changed = 0
    for row in rows:
        content = row["content"]
        if content.startswith(CIPHER_PREFIX):
            continue
        changed += 1
        if not DRY_RUN:
            cur.execute(
                "UPDATE cross_share_messages SET content = %s, is_encrypted = TRUE WHERE id = %s",
                (encrypt_text(content), row["id"]),
            )
    if not DRY_RUN:
        conn.commit()
    log(f"  共 {len(rows)} 行，需加密 {changed} 行（dry_run={DRY_RUN}）")
    return changed


def _encode_secret_json(value):
    if value is None:
        return None
    if value == "" or value == {} or value == []:
        return json.dumps(value)
    return json.dumps(encrypt_text(json.dumps(value, ensure_ascii=False, default=str)), ensure_ascii=False)


def _is_encrypted_json(raw):
    """判断是否已是本模块产出的密文

    JSON/JSONB 列读出来时，psycopg2 会把 JSON 字符串解析为 Python str，
    密文形态是「不带引号的 enc:v1:...」；对象/数组形态则是 dict/list。
    """
    if raw is None:
        return False
    if isinstance(raw, str):
        return raw.startswith(CIPHER_PREFIX)
    if isinstance(raw, (dict, list)):
        # 空集合无需加密；非空对象/数组视为明文
        return len(raw) == 0
    return True


def _parse_json_value(raw):
    """把 JSON 列的值解析为 Python 对象；无法解析时返回 None"""
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def migrate_http_requests(cur, conn):
    """4. http_requests.auth_config / headers 加密"""
    log("\n=== [4/6] http_requests.auth_config / headers 加密 ===")
    cur.execute("SELECT id, auth_config, headers FROM http_requests")
    rows = cur.fetchall()
    changed = 0
    for row in rows:
        updates = {}
        for col in ("auth_config", "headers"):
            raw = row[col]
            if raw is None or _is_encrypted_json(raw):
                continue
            parsed = _parse_json_value(raw)
            if parsed is None:
                continue
            updates[col] = _encode_secret_json(parsed)
        if updates:
            changed += 1
            if not DRY_RUN:
                sets = ", ".join(f"{c} = %s" for c in updates)
                cur.execute(
                    f"UPDATE http_requests SET {sets} WHERE id = %s",
                    (*updates.values(), row["id"]),
                )
    if not DRY_RUN:
        conn.commit()
    log(f"  共 {len(rows)} 行，需加密 {changed} 行（dry_run={DRY_RUN}）")
    return changed


def migrate_http_environments(cur, conn):
    """5. http_environments.variables 加密"""
    log("\n=== [5/6] http_environments.variables 加密 ===")
    cur.execute("SELECT id, variables FROM http_environments")
    rows = cur.fetchall()
    changed = 0
    for row in rows:
        raw = row["variables"]
        if raw is None or _is_encrypted_json(raw):
            continue
        parsed = _parse_json_value(raw)
        if parsed is None:
            continue
        changed += 1
        if not DRY_RUN:
            cur.execute(
                "UPDATE http_environments SET variables = %s WHERE id = %s",
                (_encode_secret_json(parsed), row["id"]),
            )
    if not DRY_RUN:
        conn.commit()
    log(f"  共 {len(rows)} 行，需加密 {changed} 行（dry_run={DRY_RUN}）")
    return changed


def migrate_http_history(cur, conn):
    """6. http_request_history 加密 request_data / 脱敏 response_data"""
    log("\n=== [6/6] http_request_history 加密 request_data / 脱敏 response_data ===")
    cur.execute("SELECT id, request_data, response_data FROM http_request_history")
    rows = cur.fetchall()
    changed_req = 0
    changed_resp = 0
    for row in rows:
        req = row["request_data"]
        resp = row["response_data"]
        new_req = req
        new_resp = resp
        if req is not None and not _is_encrypted_json(req):
            parsed = _parse_json_value(req)
            if parsed is not None:
                new_req = _encode_secret_json(parsed)
                changed_req += 1
        if resp is not None:
            parsed = _parse_json_value(resp)
            if parsed is not None:
                redacted = redact_structure(parsed)
                # 用语义比较而非字符串比较：jsonb 不保留 key 顺序，
                # 直接比字符串会导致每次重跑都判定为「有变化」
                if redacted != parsed:
                    changed_resp += 1
                    new_resp = json.dumps(redacted, ensure_ascii=False, default=str)
        if not DRY_RUN and (new_req != req or new_resp != resp):
            # jsonb 列传 Python str 时 psycopg2 会当 JSON 文本解析，
            # 密文形态必须显式包成 JSON 字符串字面量才能写入
            req_param = new_req if isinstance(new_req, (dict, list)) else json.dumps(new_req, ensure_ascii=False)
            resp_param = new_resp if isinstance(new_resp, (dict, list)) else json.dumps(new_resp, ensure_ascii=False)
            cur.execute(
                "UPDATE http_request_history SET request_data = %s, response_data = %s WHERE id = %s",
                (req_param, resp_param, row["id"]),
            )
    if not DRY_RUN:
        conn.commit()
    log(f"  共 {len(rows)} 行，request_data 需加密 {changed_req} 行，response_data 需脱敏 {changed_resp} 行（dry_run={DRY_RUN}）")
    return changed_req + changed_resp


def verify(cur):
    """迁移后复核：确认库中不再残留明文凭据"""
    log("\n=== 迁移后复核 ===")
    # 真实 key 形态：sk- 后接 13 位以上 base62 字符。
    # 用 Python 正则而非 SQL LIKE —— LIKE 无法表达「至少 N 位」
    key_re = re.compile(r"sk-[A-Za-z0-9]{13,}")
    checks = [
        ("sql_execution_history", "sql_statement"),
        ("sql_execution_history", "error_message"),
        ("sql_execution_history", "result_data"),
        ("cross_share_messages", "content"),
    ]
    for table, col in checks:
        cur.execute(f"SELECT {col} AS v FROM {table} WHERE {col} IS NOT NULL")
        hits = [r["v"] for r in cur.fetchall() if r["v"] and key_re.search(str(r["v"]))]
        status = "OK" if not hits else "!! 仍有残留"
        log(f"  [{status}] {table}.{col} 含明文 key 形态：{len(hits)} 行")

    cur.execute("SELECT config_value FROM openclaw_configs WHERE config_key = 'token'")
    row = cur.fetchone()
    if row:
        v = row["config_value"] or ""
        log(f"  [{'OK' if v.startswith('gAAAAA') else '!!'}] openclaw_configs.token 密文形态：{v[:8]}...")

    cur.execute("SELECT COUNT(*) AS c FROM cross_share_messages WHERE content LIKE %s", (f"%{CIPHER_PREFIX}%",))
    log(f"  跨设备消息已加密数：{cur.fetchone()['c']}")

    cur.execute("SELECT COUNT(*) AS c FROM http_environments WHERE variables::text LIKE %s", (f"%{CIPHER_PREFIX}%",))
    log(f"  HTTP 环境变量已加密数：{cur.fetchone()['c']}")

    cur.execute("SELECT COUNT(*) AS c FROM http_request_history WHERE request_data::text LIKE %s", (f"%{CIPHER_PREFIX}%",))
    log(f"  HTTP 请求历史已加密数：{cur.fetchone()['c']}")


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor(cursor_factory=RealDictCursor)
    log(f"开始迁移（dry_run={DRY_RUN}）")

    total = 0
    total += migrate_sql_history(cur, conn)
    total += migrate_openclaw_token(cur, conn)
    total += migrate_cross_share(cur, conn)
    total += migrate_http_requests(cur, conn)
    total += migrate_http_environments(cur, conn)
    total += migrate_http_history(cur, conn)

    log(f"\n共变更 {total} 处")
    if not DRY_RUN:
        verify(cur)
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
