-- 为 4 张凭据配置表添加 storage_location 列（幂等，可重复执行）
-- 用法：psql "$DATABASE_URL" -f backend/scripts/migrate_storage_location.sql
--
-- 语义：storage_location ∈ {LOCAL, SERVER}
--   LOCAL  = 存本机 SQLite（~/.toolbox/toolbox.db）
--   SERVER = 存本服务器 PostgreSQL
-- 现有行统一标记为 SERVER，保持历史行为不变。
--
-- 注意：PostgreSQL 支持 ADD COLUMN IF NOT EXISTS（9.6+）；
--       SQLite 不支持，故应用层加列走 app/storage/ddl.py 的探测式写法。

ALTER TABLE db_configs
    ADD COLUMN IF NOT EXISTS storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER';

ALTER TABLE redis_configs
    ADD COLUMN IF NOT EXISTS storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER';

ALTER TABLE ssh_configs
    ADD COLUMN IF NOT EXISTS storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER';

ALTER TABLE k8s_connections
    ADD COLUMN IF NOT EXISTS storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER';

-- 校验：以下查询期望返回 0（非 0 说明存在异常归属行，需人工核查）
SELECT COUNT(*) AS unexpected_rows FROM db_configs WHERE storage_location <> 'SERVER';
