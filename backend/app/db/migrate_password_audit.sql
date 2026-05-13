-- 兼容已有 password_reset_logs 表的迁移脚本

DO $$
BEGIN
    -- 检查旧表是否存在
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'password_reset_logs') THEN
        -- 重命名旧表
        ALTER TABLE password_reset_logs RENAME TO password_audit_logs;

        -- 添加新列（如果不存在）
        ALTER TABLE password_audit_logs ADD COLUMN IF NOT EXISTS action_type VARCHAR(20) DEFAULT 'admin_reset';
        ALTER TABLE password_audit_logs ADD COLUMN IF NOT EXISTS success BOOLEAN DEFAULT TRUE;
        ALTER TABLE password_audit_logs ADD COLUMN IF NOT EXISTS error_message TEXT;
        ALTER TABLE password_audit_logs ADD COLUMN IF NOT EXISTS device_info TEXT;
        ALTER TABLE password_audit_logs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP;

        -- 重命名旧列以符合新语义
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'password_audit_logs' AND column_name = 'reset_by_user_id') THEN
            ALTER TABLE password_audit_logs RENAME COLUMN reset_by_user_id TO actor_user_id;
        END IF;

        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'password_audit_logs' AND column_name = 'reset_at') THEN
            ALTER TABLE password_audit_logs RENAME COLUMN reset_at TO created_at;
        END IF;

        -- 创建新索引
        CREATE INDEX IF NOT EXISTS idx_audit_user_id ON password_audit_logs(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_action_type ON password_audit_logs(action_type);
        CREATE INDEX IF NOT EXISTS idx_audit_created_at ON password_audit_logs(created_at);
        CREATE INDEX IF NOT EXISTS idx_audit_user_action ON password_audit_logs(user_id, action_type);
    ELSE
        -- 创建新表
        CREATE TABLE password_audit_logs (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            action_type VARCHAR(20) NOT NULL DEFAULT 'login',
            success BOOLEAN NOT NULL DEFAULT TRUE,
            error_message TEXT,
            ip_address INET,
            device_info TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            actor_user_id VARCHAR(36)
        );

        CREATE INDEX idx_audit_user_id ON password_audit_logs(user_id);
        CREATE INDEX idx_audit_action_type ON password_audit_logs(action_type);
        CREATE INDEX idx_audit_created_at ON password_audit_logs(created_at);
        CREATE INDEX idx_audit_user_action ON password_audit_logs(user_id, action_type);
    END IF;
END $$;
