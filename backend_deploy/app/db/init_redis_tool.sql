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
