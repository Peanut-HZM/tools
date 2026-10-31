/**
 * 存储位置相关类型
 */

/** 配置存储位置：local=本机 SQLite / server=服务器 PostgreSQL */
export type StorageLocation = 'local' | 'server';

/** 存储状态 */
export interface StorageStatus {
  /** 远程服务器是否可用 */
  server_available: boolean;
  /** 不可用原因（可直接展示给用户） */
  server_reason: string;
  /** 本地 SQLite 文件路径 */
  local_path: string;
}

/** 单条迁移结果 */
export interface MigrateResult {
  success: boolean;
  storage_location: StorageLocation;
  message: string;
}

/** 批量迁移结果 */
export interface MigrateAllResult {
  success: boolean;
  migrated: number;
  failed: number;
  errors: Array<{ config_id: string; message: string }>;
}

/** 工具标识（与后端 TOOL_TABLES 对应） */
export type StorageTool = 'database' | 'k8s' | 'ssh' | 'redis';
