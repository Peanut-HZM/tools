export enum DatabaseType {
  MYSQL = "mysql",
  POSTGRESQL = "postgresql",
  SQLITE = "sqlite",
  ORACLE = "oracle",
  SQLSERVER = "sqlserver",
  MARIADB = "mariadb"
}

export enum Environment {
  DEV = "dev",
  TEST = "test",
  PROD = "prod"
}

export interface DatabaseConfig {
  id: string;
  user_id: string;
  alias: string;
  db_type: DatabaseType;
  host: string;
  port: number;
  database_name?: string;
  username: string;
  environment?: Environment;
  group_name?: string;
  charset?: string;
  connect_timeout?: number;
  max_pool_size?: number;
  ssl_mode?: string;
  ssl_cert_path?: string;
  extra_config?: Record<string, any>;
  is_active: boolean;
  last_connected_at?: string;
  created_at: string;
  updated_at: string;
  password?: string;
}

export interface CreateDatabaseRequest {
  alias: string;
  db_type: DatabaseType;
  host: string;
  port: number;
  database_name?: string;
  username: string;
  password: string;
  environment?: Environment;
  group_name?: string;
  charset?: string;
  connect_timeout?: number;
  max_pool_size?: number;
  ssl_mode?: string;
  ssl_cert_path?: string;
  extra_config?: Record<string, any>;
  is_active?: boolean;
}

export interface UpdateDatabaseRequest {
  alias?: string;
  host?: string;
  port?: number;
  database_name?: string;
  username?: string;
  password?: string;
  environment?: Environment;
  group_name?: string;
  charset?: string;
  connect_timeout?: number;
  max_pool_size?: number;
  ssl_mode?: string;
  ssl_cert_path?: string;
  extra_config?: Record<string, any>;
  is_active?: boolean;
}

export interface TestConnectionRequest {
  db_type: DatabaseType;
  host: string;
  port: number;
  database_name?: string;
  username: string;
  password: string;
  ssl_mode?: string;
  ssl_cert_path?: string;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  elapsed_ms?: number;
  version?: string;
}

export interface SQLExecutionRequest {
  db_config_id: string;
  sql: string;
  params?: Record<string, any>;
  database_name?: string;
  page?: number;
  page_size?: number;
}

export interface SQLExecutionResult {
  success: boolean;
  sql_type?: string;
  affected_rows?: number;
  execution_time_ms: number;
  error_message?: string;
  result_data?: Record<string, any>[];
  columns?: string[];
}

export interface ExecutionHistory {
  id: string;
  user_id: string;
  db_config_id: string;
  sql_statement: string;
  sql_type?: string;
  execution_status: string;
  affected_rows?: number;
  execution_time_ms?: number;
  error_message?: string;
  created_at: string;
  db_alias?: string;
}

export interface TableSchema {
  table_name: string;
  comment?: string;
  columns: any[];
  primary_key?: string[];
  indexes?: any[];
  foreign_keys?: any[];
}

export interface ColumnDefinition {
    name: string;
    type: string;
    length?: string;
    nullable: boolean;
    default_value?: string;
    comment?: string;
    primary_key: boolean;
    auto_increment: boolean;
}

export interface TableModificationRequest {
    database_name: string;
    table_name: string;
    new_table_name?: string;
    columns: ColumnDefinition[];
    comment?: string;
}

export interface TableItem {
    name: string;
    comment?: string | null;
}

export interface DatabaseStructure {
    tables: TableItem[];
    views: TableItem[];
}
