"""
应用级密钥存储（key-in-DB）

背景与目标：
    此前 API Key 等敏感数据用「各环境 .env 里的 DB_ENCRYPTION_KEY」加密，
    而密文存放在共享的远程 PostgreSQL。多设备/多部署各自持钥，任何环境
    先写入的密文在其他环境永远解不开（AES-GCM InvalidTag），且事前无法
    发现。根治方案：主密钥本身入库 —— 首次访问时生成随机密钥写入
    app_secrets 表，所有共享该库的环境读到同一把密钥，密文天然互通，
    新设备只需配置 DATABASE_URL 即可，零额外配置。

逃生舱：
    环境变量 TOOLBOX_APP_SECRET_HEX（64 位 hex = 32 字节）设置后跳过
    数据库，所有 key_id 统一使用该值 —— 供单元测试 / 无库 CI / 显式
    固定密钥的特殊部署场景使用。

注意：
    密钥一经生成不可更改（更改等于销毁所有用它加密的数据）；进程内
    缓存，修改数据库中的密钥后需重启服务才生效。
"""
import logging
import os
import threading

logger = logging.getLogger(__name__)

_lock = threading.Lock()
# 仅缓存走全局 engine 的读取（业务主路径）；显式传入 engine 的调用（测试）不缓存
_cache: dict[str, bytes] = {}

# 逃生舱环境变量名
ENV_OVERRIDE = "TOOLBOX_APP_SECRET_HEX"


def _load_override() -> bytes:
    """读取并校验环境变量指定的固定密钥"""
    raw = os.environ.get(ENV_OVERRIDE, "")
    if not raw:
        return b""
    try:
        key = bytes.fromhex(raw)
    except ValueError:
        raise ValueError(f"{ENV_OVERRIDE} 必须是合法 hex 字符串")
    if len(key) != 32:
        raise ValueError(f"{ENV_OVERRIDE} 解码后必须为 32 字节（64 个 hex 字符），当前 {len(key)} 字节")
    return key


def _ensure_table(engine):
    """幂等建表（DDL checkfirst，可重复执行）"""
    from app.models.app_secret import AppSecret

    AppSecret.__table__.create(bind=engine, checkfirst=True)


def _read_row(engine, key_id: str):
    from app.models.app_secret import AppSecret

    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        row = session.query(AppSecret).filter(AppSecret.key_id == key_id).first()
        return row.secret_value if row else None
    finally:
        session.close()


def _insert_row(engine, key_id: str, value_hex: str) -> bool:
    """写入密钥行；key_id 冲突（并发竞争）时返回 False"""
    from app.models.app_secret import AppSecret

    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        session.add(AppSecret(key_id=key_id, secret_value=value_hex))
        session.commit()
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()


def get_or_create_secret(key_id: str, length: int = 32, engine=None) -> bytes:
    """
    读取（或首次生成）指定 key_id 的应用级密钥。

    key_id: 密钥标识，如 'llm_master_key' / 'openclaw_master_key'
    length: 首次生成时的字节长度（读取已有值时忽略）
    engine: 可注入独立 engine（测试用）；默认使用全局 engine（结果进程内缓存）

    返回原始字节串。设置 TOOLBOX_APP_SECRET_HEX 时直接返回其解码值。
    """
    override = _load_override()
    if override:
        return override

    # 延迟导入避免 import 环（models.base 仅依赖 config）
    from app.models.base import engine as global_engine

    eng = engine if engine is not None else global_engine
    use_cache = engine is None

    with _lock:
        if use_cache:
            cached = _cache.get(key_id)
            if cached is not None:
                return cached

        _ensure_table(eng)
        value_hex = _read_row(eng, key_id)

        if value_hex is None:
            import secrets as _secrets

            value_hex = _secrets.token_bytes(length).hex()
            if not _insert_row(eng, key_id, value_hex):
                # 并发竞争：另一个进程/线程先写入了，回读它的值
                value_hex = _read_row(eng, key_id)
                if value_hex is None:
                    raise RuntimeError(f"app_secrets 写入竞争后仍读取不到 key_id={key_id}")
            logger.info(
                "[app_secrets] 已生成应用级密钥 key_id=%s length=%sB（首次访问自动创建）",
                key_id, length,
            )
        else:
            logger.info("[app_secrets] 读取应用级密钥 key_id=%s（来自数据库）", key_id)

        key = bytes.fromhex(value_hex)
        if len(key) != length:
            raise RuntimeError(
                f"app_secrets 中 key_id={key_id} 长度为 {len(key)} 字节，与预期 {length} 字节不符；"
                f"该密钥可能被手动修改过，请核实（修改密钥会导致既有密文不可解）"
            )

        if use_cache:
            _cache[key_id] = key
        return key


def clear_secret_cache():
    """清空进程内密钥缓存（测试用；生产环境改库后应重启服务）"""
    with _lock:
        _cache.clear()
