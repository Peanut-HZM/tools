-- 用户表 (如果不存在则创建，用于解决依赖问题)
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 数据库配置表
CREATE TABLE IF NOT EXISTS db_configs (
    id VARCHAR(64) PRIMARY KEY,                    -- 配置ID（UUID或雪花ID）
    user_id VARCHAR(64) NOT NULL,                   -- 用户ID（外键关联users表）
    alias VARCHAR(32) NOT NULL,                     -- 配置别名
    db_type VARCHAR(20) NOT NULL,                  -- 数据库类型（mysql/postgresql/sqlite等）
    host VARCHAR(255) NOT NULL,                    -- 主机地址
    port INT NOT NULL,                             -- 端口号
    database_name VARCHAR(255),                    -- 数据库名 (可选)
    username VARCHAR(100) NOT NULL,                -- 用户名
    password_encrypted TEXT NOT NULL,               -- 加密后的密码
    environment VARCHAR(20),                       -- 环境标签（dev/test/prod）
    group_name VARCHAR(50),                        -- 分组名称
    charset VARCHAR(50),                           -- 字符集
    connect_timeout INT DEFAULT 10,               -- 连接超时（秒）
    max_pool_size INT DEFAULT 10,                  -- 最大连接池大小
    ssl_mode VARCHAR(20),                          -- SSL模式
    ssl_cert_path TEXT,                            -- SSL证书路径
    extra_config JSON,                             -- 额外配置（JSON格式）
    is_active BOOLEAN DEFAULT TRUE,                -- 是否激活
    last_connected_at TIMESTAMP,                   -- 最后连接时间
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_db_configs_user_id ON db_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_db_configs_user_alias ON db_configs(user_id, alias);

-- 执行历史表
CREATE TABLE IF NOT EXISTS sql_execution_history (
    id VARCHAR(64) PRIMARY KEY,                    -- 历史记录ID
    user_id VARCHAR(64) NOT NULL,                   -- 用户ID
    db_config_id VARCHAR(64) NOT NULL,             -- 数据库配置ID
    sql_statement TEXT NOT NULL,                    -- SQL语句
    sql_type VARCHAR(20),                           -- SQL类型（SELECT/INSERT/UPDATE/DELETE/DDL等）
    execution_status VARCHAR(20) NOT NULL,          -- 执行状态（success/failed/timeout）
    affected_rows INT,                              -- 受影响行数
    execution_time_ms INT,                          -- 执行耗时（毫秒）
    error_message TEXT,                             -- 错误信息（如果失败）
    result_data JSON,                               -- 结果数据（JSON格式，用于SELECT查询）
    result_size INT,                                -- 结果大小（字节）
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (db_config_id) REFERENCES db_configs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_history_user_id ON sql_execution_history(user_id);
CREATE INDEX IF NOT EXISTS idx_history_db_config_id ON sql_execution_history(db_config_id);
CREATE INDEX IF NOT EXISTS idx_history_created_at ON sql_execution_history(created_at);
CREATE INDEX IF NOT EXISTS idx_history_sql_type ON sql_execution_history(sql_type);

-- 数据库扫描记录表
CREATE TABLE IF NOT EXISTS db_scan_history (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    scan_path VARCHAR(500) NOT NULL,                -- 扫描路径
    configs_found INT DEFAULT 0,                    -- 发现的配置数量
    scan_result JSON,                               -- 扫描结果（JSON格式）
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scan_user_id ON db_scan_history(user_id);

-- 表结构缓存表
CREATE TABLE IF NOT EXISTS table_schema_cache (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    db_config_id VARCHAR(64) NOT NULL,
    table_name VARCHAR(255) NOT NULL,
    schema_data JSON NOT NULL,                      -- 表结构数据（JSON格式）
    cached_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL                   -- 缓存过期时间
);

CREATE INDEX IF NOT EXISTS idx_cache_user_db ON table_schema_cache(user_id, db_config_id);
CREATE INDEX IF NOT EXISTS idx_cache_expires_at ON table_schema_cache(expires_at);
-- Redis配置表
CREATE TABLE IF NOT EXISTS redis_configs (
    id VARCHAR(64) PRIMARY KEY,                    -- 配置ID
    user_id VARCHAR(64) NOT NULL,                   -- 用户ID
    alias VARCHAR(32) NOT NULL,                     -- 配置别名
    host VARCHAR(255) NOT NULL,                    -- 主机地址
    port INT NOT NULL DEFAULT 6379,                -- 端口号
    username VARCHAR(100),                         -- 用户名
    password_encrypted TEXT,                        -- 加密后的密码
    db INT DEFAULT 0,                              -- 数据库索引
    group_name VARCHAR(50),                        -- 分组名称
    is_active BOOLEAN DEFAULT TRUE,                -- 是否激活
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_redis_configs_user_id ON redis_configs(user_id);

-- SSH配置表
CREATE TABLE IF NOT EXISTS ssh_configs (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    alias VARCHAR(64) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INT NOT NULL DEFAULT 22,
    username VARCHAR(128) NOT NULL,
    password_encrypted TEXT,
    private_key_encrypted TEXT,
    passphrase_encrypted TEXT,
    group_name VARCHAR(64),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ssh_configs_user_id ON ssh_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_ssh_configs_user_alias ON ssh_configs(user_id, alias);

-- 用户显示偏好表
CREATE TABLE IF NOT EXISTS user_display_preferences (
    user_id VARCHAR(64) PRIMARY KEY,
    visible_connections JSON,                        -- null=全部显示, ["id1","id2"]=仅显示这些
    visible_databases JSON,                          -- {"config_id": ["db1", "db2"]} 每个连接可见的数据库
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_display_prefs_user_id ON user_display_preferences(user_id);
