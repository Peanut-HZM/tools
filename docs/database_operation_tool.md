# 数据库操作工具需求文档

## 目录

1. [数据库配置管理功能](#1-数据库配置管理功能)
   - [1.1 自动配置发现](#11-自动配置发现)
   - [1.2 手动配置管理](#12-手动配置管理)
   - [1.3 配置验证与测试](#13-配置验证与测试)
2. [SQL脚本执行功能](#2-sql脚本执行功能)
   - [2.1 数据源选择机制](#21-数据源选择机制)
   - [2.2 交互式脚本编辑与执行](#22-交互式脚本编辑与执行)
   - [2.3 脚本文件加载与执行](#23-脚本文件加载与执行)
   - [2.4 脚本类型识别与处理](#24-脚本类型识别与处理)
   - [2.5 执行结果处理](#25-执行结果处理)
   - [2.6 执行历史与回放](#26-执行历史与回放)
3. [错误处理与调试支持](#3-错误处理与调试支持)
   - [3.1 详细错误报告](#31-详细错误报告)
   - [3.2 智能修复建议](#32-智能修复建议)
   - [3.3 事务管理](#33-事务管理)
   - [3.4 错误日志与追踪](#34-错误日志与追踪)
   - [3.5 调试功能](#35-调试功能)
4. [数据库结构浏览功能](#4-数据库结构浏览功能)
   - [4.1 Schema浏览](#41-schema浏览)
   - [4.2 数据导出/导入](#42-数据导出导入)
   - [4.3 数据库备份/恢复](#43-数据库备份恢复)
5. [数据库和表管理功能](#5-数据库和表管理功能)
   - [5.1 数据库管理（增删改查）](#51-数据库管理增删改查)
     - [5.1.1 数据库查询（查）](#511-数据库查询查)
     - [5.1.2 数据库创建（增）](#512-数据库创建增)
     - [5.1.3 数据库修改（改）](#513-数据库修改改)
     - [5.1.4 数据库删除（删）](#514-数据库删除删)
     - [5.1.5 数据库切换](#515-数据库切换)
   - [5.2 表管理（增删改查）](#52-表管理增删改查)
     - [5.2.1 表查询（查）](#521-表查询查)
     - [5.2.2 表创建（增）](#522-表创建增)
     - [5.2.3 表修改（改）](#523-表修改改)
     - [5.2.4 表删除（删）](#524-表删除删)
   - [5.3 交互式管理命令](#53-交互式管理命令)
   - [5.4 安全与验证](#54-安全与验证)
6. [项目集成与用户隔离](#6-项目集成与用户隔离)
   - [6.1 项目集成需求](#61-项目集成需求)
   - [6.2 前端集成](#62-前端集成)
   - [6.3 后端集成](#63-后端集成)
   - [6.4 用户隔离设计](#64-用户隔离设计)
   - [6.5 数据库设计](#65-数据库设计)
   - [6.6 API接口设计](#66-api接口设计)
7. [工具实现要求](#7-工具实现要求)
   - [7.1 项目结构](#71-项目结构)
   - [7.2 技术栈](#72-技术栈)
   - [7.3 代码结构说明](#73-代码结构说明)
   - [7.4 配置文件格式](#74-配置文件格式)
   - [7.5 测试要求](#75-测试要求)
8. [使用示例](#8-使用示例)
   - [8.1 安装与启动](#81-安装与启动)
   - [8.2 自动发现项目数据库配置](#82-自动发现项目数据库配置)
   - [8.3 手动添加数据库配置](#83-手动添加数据库配置)
   - [8.4 交互式Shell使用](#84-交互式shell使用)
   - [8.5 执行查询SQL脚本示例](#85-执行查询sql脚本示例)
   - [8.6 执行数据操作SQL脚本示例](#86-执行数据操作sql脚本示例)
   - [8.7 错误处理示例](#87-错误处理示例)
   - [8.8 数据导出示例](#88-数据导出示例)
   - [8.9 Schema浏览示例](#89-schema浏览示例)
   - [8.10 数据库和表管理示例](#810-数据库和表管理示例)
9. [非功能性需求](#9-非功能性需求)
   - [9.1 性能要求](#91-性能要求)
   - [9.2 安全性要求](#92-安全性要求)
   - [9.3 可扩展性要求](#93-可扩展性要求)
   - [9.4 可用性要求](#94-可用性要求)
   - [9.5 可靠性要求](#95-可靠性要求)
   - [9.6 维护性要求](#96-维护性要求)
10. [API说明（可选）](#10-api说明可选)
   - [10.1 Python API](#101-python-api)
   - [10.2 REST API（可选）](#102-rest-api可选)
11. [故障排除指南](#11-故障排除指南)
    - [11.1 常见问题](#111-常见问题)
    - [11.2 日志查看](#112-日志查看)
    - [11.3 配置文件修复](#113-配置文件修复)
12. [版本历史](#12-版本历史)
13. [总结](#13-总结)

---

## 1. 数据库配置管理功能

### 1.1 自动配置发现
- **自动读取当前项目配置**：能够扫描项目文件系统，自动识别并提取所有数据库连接配置
  - 支持配置文件格式：`.env`、`.env.local`、`.env.production`等环境变量文件
  - 支持Java项目配置：`application.properties`、`application.yml`、`application-*.yml`
  - 支持PHP项目配置：`database.php`、`config/database.php`、`.env`
  - 支持Node.js项目配置：`config.js`、`database.json`、`.env`
  - 支持Python项目配置：`settings.py`、`config.py`、`.env`
  - 支持Docker Compose配置：`docker-compose.yml`、`docker-compose.*.yml`
  - 支持Kubernetes配置：`configmap.yaml`、`secret.yaml`
  - 扫描深度：默认扫描项目根目录及3层子目录，可配置扫描深度
  - 配置文件缓存：对已扫描的配置文件进行缓存，避免重复扫描
- **配置去重处理**：
  - 基于连接参数（主机、端口、数据库名、用户名）识别重复配置
  - 支持模糊匹配：忽略端口号差异（使用默认端口时）
  - 去重策略：保留最完整的配置信息（优先保留包含密码的配置）
  - 提供去重报告：显示哪些配置被合并，合并原因

### 1.2 手动配置管理
- **多数据源支持**：
  - 提供命令行界面和交互式界面，允许用户手动添加、编辑和删除数据库连接配置
  - 支持数据库类型：MySQL（5.7+、8.0+）、PostgreSQL（10+）、SQLite（3.x）、Oracle（11g+、12c+）、SQL Server（2012+）、MariaDB（10.3+）、ClickHouse、MongoDB（可选）
  - **别名管理**：
    - 支持为每个数据源设置唯一别名（Alias），别名规则：字母、数字、下划线，长度2-32字符
    - 别名冲突检测：添加配置时自动检测别名是否已存在
    - 别名快速搜索：支持通过别名前缀快速定位配置
  - **环境分组**：
    - 支持对数据源进行分组管理（如：开发环境、测试环境、预发布环境、生产环境）
    - 环境标签颜色区分：不同环境使用不同颜色标识，防止误操作
    - 环境切换保护：生产环境操作需要二次确认
  - **连接参数配置**：
    - 基础参数：主机地址（host）、端口（port）、数据库名（database）、用户名（username）、密码（password）
    - 高级参数：连接超时（connect_timeout）、读取超时（read_timeout）、字符集（charset）、时区（timezone）
    - 连接池配置：最小连接数（min_pool_size）、最大连接数（max_pool_size）、连接空闲时间（idle_timeout）
    - SSL/TLS支持：支持SSL连接配置（证书路径、验证模式）
  - **持久化存储**：
    - 配置文件格式：YAML格式（`.db_tool_config.yaml`），存储在用户主目录下的`.db_tool`文件夹
    - 敏感信息加密：使用AES-256加密算法对密码等敏感字段进行加密存储
    - 配置文件版本管理：支持配置文件的版本控制和备份
    - 配置导入/导出：支持将配置导出为JSON/YAML格式，便于团队共享（密码字段需单独处理）
  - **配置模板**：
    - 提供常用数据库类型的配置模板
    - 支持自定义配置模板
    - 支持从模板快速创建新配置

### 1.3 配置验证与测试
- **连接测试**：
  - 添加/编辑配置时自动进行连接测试
  - 测试结果反馈：成功/失败状态、连接耗时、数据库版本信息
  - 批量测试：支持对所有配置进行批量连接测试
  - 定期健康检查：可配置定期自动检查配置有效性（可选功能）
- **配置验证规则**：
  - 必填字段校验：主机、端口、数据库名、用户名
  - 端口范围校验：1-65535
  - 主机格式校验：IP地址或域名格式
  - 数据库名格式校验：根据数据库类型验证命名规范

## 2. SQL脚本执行功能

### 2.1 数据源选择机制
- **交互式选择**：
  - 提供交互式列表，显示所有可用数据源（包括自动发现和手动配置的）
  - 列表展示信息：别名、主机地址、端口、数据库名、环境标签、连接状态
  - 支持键盘导航：方向键选择，Enter确认，ESC取消
  - 支持搜索过滤：输入关键字快速过滤数据源列表
- **命令行指定**：
  - 支持通过命令行参数（如 `-d <alias>` 或 `--database <alias>`）直接指定目标数据源启动
  - 支持通过环境变量指定默认数据源：`DB_TOOL_DEFAULT_DB=<alias>`
  - 参数优先级：命令行参数 > 环境变量 > 交互式选择
- **动态切换**：
  - 在交互式模式下，支持通过命令（如 `use <alias>` 或 `switch <alias>`）快速切换当前活动数据源
  - 切换时自动测试新数据源连接，失败时提示并保持原数据源
  - 支持切换历史记录：可通过 `use -` 切换到上一个数据源
- **状态提示**：
  - 在交互界面醒目位置（如Prompt前缀）显示当前连接的数据库信息
  - 显示格式：`[环境标签] 别名@主机:端口/数据库名 >`
  - 生产环境使用红色高亮提示，防止误操作
  - 支持自定义Prompt格式

### 2.2 交互式脚本编辑与执行
- **脚本输入区域**：
  - 提供多行文本输入区域，支持用户直接编写或粘贴SQL脚本
  - 支持语法高亮：根据当前数据库类型自动识别SQL关键字并高亮显示
  - 支持代码补全：自动补全表名、列名、关键字（基于当前数据库schema）
  - 支持多语句执行：自动识别SQL语句分隔符（`;`、`\G`等），支持批量执行
  - 支持注释：识别并保留SQL注释（`--`、`/* */`）
- **SQL格式化**：
  - 提供一键格式化功能（快捷键：Ctrl+Shift+F），自动调整SQL语句的缩进和换行
  - 格式化规则：关键字大写、统一缩进（2或4空格）、统一换行规则
  - 支持自定义格式化规则：缩进大小、关键字大小写、换行风格
- **语法检查**：
  - 在执行前根据当前连接的数据库类型进行静态语法分析
  - 实时提示潜在的语法错误：未闭合的引号、括号不匹配、关键字拼写错误
  - 提供错误位置定位：高亮显示错误位置，提供修复建议
  - 支持数据库特定语法检查：MySQL的`LIMIT`、PostgreSQL的`LIMIT/OFFSET`等
- **参数化查询支持**：
  - 支持变量替换：在SQL中使用 `{{变量名}}` 或 `:变量名` 占位符
  - 交互式参数输入：执行时提示用户输入参数值
  - 参数文件支持：从JSON/YAML文件读取参数值
  - 参数验证：对参数类型和格式进行验证（数字、字符串、日期等）

### 2.3 脚本文件加载与执行
- **命令行模式**：
  - 支持通过参数直接指定SQL脚本路径执行
  - 命令格式：`db-tool [选项] <数据库别名> <SQL脚本路径>`
  - 示例：`db-tool -d prod ./scripts/update_users.sql`
  - 支持批量执行：`db-tool -d prod ./scripts/*.sql`（按文件名排序执行）
  - 支持目录递归执行：`db-tool -d prod -r ./scripts/`（递归执行目录下所有SQL文件）
  - 执行选项：
    - `-f, --force`：强制执行，跳过确认提示
    - `-v, --verbose`：详细输出模式
    - `-q, --quiet`：静默模式，只输出结果
    - `--dry-run`：干运行模式，只检查语法不执行
- **交互模式**：
  - 支持通过文件选择器上传或选择本地SQL脚本
  - 支持拖拽文件到工具界面
  - 系统自动读取脚本内容并填充至脚本输入框
  - 用户可在执行前对脚本内容进行查看、二次编辑或格式化
  - 支持脚本历史记录：记录最近打开的10个脚本文件
- **脚本模板功能**：
  - 提供常用SQL模板：查询表结构、统计表记录数、备份表数据等
  - 支持自定义模板：用户可创建和保存常用SQL模板
  - 模板变量替换：模板支持变量占位符，执行时自动替换

### 2.4 脚本类型识别与处理
- **脚本类型自动识别**：
  - 查询语句（SELECT）：识别SELECT语句及其变体
  - 数据操作（DML）：INSERT、UPDATE、DELETE、MERGE
  - 数据定义（DDL）：CREATE、ALTER、DROP、TRUNCATE
  - 数据控制（DCL）：GRANT、REVOKE
  - 事务控制（TCL）：COMMIT、ROLLBACK、SAVEPOINT
  - 存储过程/函数：CALL、EXECUTE
- **执行策略**：
  - 查询语句：自动使用只读事务，支持结果缓存
  - 数据操作：自动开启事务，失败时自动回滚
  - DDL语句：根据数据库类型决定是否自动提交
  - 批量执行：支持事务批量提交，可配置批量大小

### 2.5 执行结果处理
- **查询结果展示**：
  - 表格形式展示：使用ASCII表格或Unicode表格，支持中文对齐
  - 分页显示：大数据集自动分页，默认每页20条，可配置
  - 分页控制：支持上一页、下一页、跳转到指定页、显示总数
  - 列宽自适应：根据内容自动调整列宽，超长内容截断显示（可展开查看）
  - 数据类型格式化：日期时间、数字、布尔值等按格式显示
  - 空值显示：NULL值使用特殊标记显示（如`<NULL>`）
  - 结果导出：支持导出为CSV、JSON、Excel、Markdown格式
- **数据操作结果**：
  - 精确输出受影响的行数：格式为"成功影响X条记录"
  - 显示执行时间：格式为"执行耗时：X.XXX秒"
  - 显示主键信息：INSERT操作显示生成的主键值（如果支持）
- **DDL执行结果**：
  - 输出执行状态：成功/失败
  - 显示警告信息：数据库返回的警告信息
  - 显示影响对象：创建/修改/删除的对象名称
- **执行统计信息**：
  - 执行时间统计：总耗时、网络耗时、数据库执行耗时
  - 资源使用统计：查询结果行数、数据大小、内存占用
  - 性能分析：对于慢查询（>1秒）提供性能分析建议

### 2.6 执行历史与回放
- **执行历史记录**：
  - 自动记录所有执行的SQL语句（可配置是否记录查询语句）
  - 历史记录存储：SQLite数据库存储，支持搜索和过滤
  - 历史记录信息：执行时间、数据源、执行结果、执行耗时
  - 历史记录管理：支持查看、删除、导出历史记录
- **历史回放**：
  - 支持从历史记录中选择并重新执行
  - 支持批量回放：选择多个历史记录批量执行
  - 支持历史记录导出为SQL脚本文件

## 3. 错误处理与调试支持

### 3.1 详细错误报告
- **错误信息收集**：
  - 当SQL脚本执行失败时，提供详细的错误信息
  - 错误代码：数据库返回的原始错误代码（如MySQL的1062、1451等）
  - 错误描述：人类可读的错误描述信息
  - SQL语句位置：失败的具体SQL语句在脚本中的位置（行号、列号）
  - 错误上下文：显示失败语句的前后3条语句，便于定位问题
  - 数据库约束详情：
    - 主键冲突：显示冲突的主键值和表名
    - 外键约束：显示违反的外键约束名称、关联表信息
    - 唯一约束：显示违反的唯一约束字段和值
    - 非空约束：显示违反非空约束的字段名
    - 检查约束：显示违反的检查约束条件和值
  - 执行环境信息：数据库版本、当前用户、当前数据库、执行时间

### 3.2 智能修复建议
- **错误分类与建议**：
  - **语法错误**：
    - 指出错误位置（行号、列号、字符位置）
    - 提供正确语法示例
    - 常见错误：关键字拼写、括号不匹配、引号未闭合、缺少逗号
    - 提供快速修复按钮（如果可自动修复）
  - **权限错误**：
    - 提示需要的数据库权限（SELECT、INSERT、UPDATE、DELETE、CREATE等）
    - 提供授权SQL示例
    - 检查当前用户权限并提示缺失权限
  - **约束错误**：
    - 建议检查相关表结构和数据完整性
    - 提供查询冲突数据的SQL示例
    - 提供解决建议：删除冲突数据、修改数据、调整约束
  - **连接错误**：
    - 网络连接失败：检查主机、端口、防火墙设置
    - 认证失败：检查用户名、密码、权限
    - 数据库不存在：提供创建数据库的SQL示例
  - **性能错误**：
    - 查询超时：建议添加索引、优化查询语句
    - 锁等待超时：提示可能存在的死锁或长时间事务
    - 资源不足：提示内存、连接数等资源限制

### 3.3 事务管理
- **自动事务处理**：
  - 对于数据操作脚本（INSERT、UPDATE、DELETE），自动开启事务
  - 执行成功时自动提交，失败时自动回滚
  - 支持手动事务控制：`BEGIN`、`COMMIT`、`ROLLBACK`
- **事务隔离级别**：
  - 支持设置事务隔离级别（READ UNCOMMITTED、READ COMMITTED、REPEATABLE READ、SERIALIZABLE）
  - 默认使用数据库默认隔离级别
- **保存点支持**：
  - 支持创建保存点（SAVEPOINT）
  - 支持回滚到指定保存点
  - 支持嵌套事务（如果数据库支持）

### 3.4 错误日志与追踪
- **错误日志记录**：
  - 所有错误自动记录到日志文件
  - 日志格式：时间戳、错误级别、错误代码、错误描述、SQL语句、堆栈信息
  - 日志文件管理：按日期分割日志文件，支持日志轮转
  - 敏感信息脱敏：日志中自动脱敏密码、身份证号等敏感信息
- **错误统计**：
  - 统计常见错误类型和频率
  - 提供错误趋势分析
  - 支持错误报告导出

### 3.5 调试功能
- **执行计划分析**：
  - 对于SELECT语句，自动获取并显示执行计划（EXPLAIN）
  - 分析执行计划，识别性能瓶颈
  - 提供索引使用建议
- **慢查询检测**：
  - 自动检测执行时间超过阈值的查询（默认1秒）
  - 记录慢查询日志
  - 提供慢查询优化建议
- **断点调试**（可选功能）：
  - 支持在SQL语句中设置断点
  - 支持单步执行SQL语句
  - 支持查看执行过程中的变量值

## 4. 数据库结构浏览功能

### 4.1 Schema浏览
- **数据库对象列表**：
  - 显示数据库中的所有表、视图、存储过程、函数、触发器
  - 支持按类型、名称过滤和搜索
  - 支持按创建时间、修改时间排序
- **表结构查看**：
  - 显示表的完整结构：列名、数据类型、约束、默认值、注释
  - 显示表的索引信息：索引名、索引类型、索引列、唯一性
  - 显示表的外键关系：外键名、关联表、关联列
  - 显示表的统计信息：记录数、数据大小、索引大小
- **表数据预览**：
  - 支持快速预览表的前N条数据（默认10条）
  - 支持按条件过滤预览数据
  - 支持按列排序预览数据

### 4.2 数据导出/导入
- **数据导出**：
  - 支持导出表数据为CSV、JSON、Excel、SQL INSERT语句格式
  - 支持导出表结构为SQL DDL语句
  - 支持导出整个数据库结构（Schema）
  - 支持按条件导出数据（WHERE子句）
  - 支持大数据量分块导出
- **数据导入**：
  - 支持从CSV、JSON、Excel文件导入数据
  - 支持导入SQL脚本文件
  - 支持导入前数据验证和预览
  - 支持导入冲突处理策略：跳过、更新、报错

### 4.3 数据库备份/恢复
- **数据库备份**：
  - 支持全量备份：导出整个数据库结构和数据
  - 支持增量备份：只备份变更的数据
  - 支持表级备份：备份指定表的数据和结构
  - 备份文件格式：SQL脚本、压缩文件（.gz、.zip）
  - 备份文件管理：支持备份文件列表、删除、恢复
- **数据库恢复**：
  - 支持从备份文件恢复数据库
  - 支持恢复前数据验证
  - 支持恢复策略：覆盖、追加、跳过已存在数据

## 5. 数据库和表管理功能

### 5.1 数据库管理（增删改查）

#### 5.1.1 数据库查询（查）
- **列出所有数据库**：
  - 命令：`SHOW DATABASES` 或 `\l`（PostgreSQL）或交互式命令 `list databases`
  - 显示所有可访问的数据库列表
  - 显示信息：数据库名、字符集、排序规则、创建时间、大小
  - 支持按名称、大小、创建时间排序
  - 支持搜索过滤：输入关键字快速过滤数据库列表
- **查看数据库详情**：
  - 命令：`SHOW DATABASE <database_name>` 或 `describe database <database_name>`
  - 显示数据库的详细信息：
    - 字符集和排序规则
    - 数据库大小（数据大小、索引大小、总大小）
    - 表数量、视图数量、存储过程数量
    - 创建时间和最后修改时间
    - 用户权限信息
- **查看当前数据库**：
  - 命令：`SELECT DATABASE()` 或交互式命令 `current database`
  - 显示当前连接的数据库名称

#### 5.1.2 数据库创建（增）
- **创建新数据库**：
  - 命令：`CREATE DATABASE <database_name>` 或交互式命令 `create database <database_name>`
  - 支持指定字符集：`CREATE DATABASE db_name CHARACTER SET utf8mb4`
  - 支持指定排序规则：`CREATE DATABASE db_name COLLATE utf8mb4_unicode_ci`
  - 支持指定其他选项（根据数据库类型）：
    - MySQL：字符集、排序规则、加密选项
    - PostgreSQL：编码、模板数据库、连接限制
    - SQL Server：文件组、文件路径
  - 创建前验证：检查数据库名是否已存在、名称格式是否合法
  - 创建后验证：自动测试新数据库连接
- **从模板创建数据库**：
  - 支持从现有数据库模板创建新数据库
  - 支持复制数据库结构和数据
- **交互式创建向导**：
  - 提供交互式向导，引导用户输入数据库名称和选项
  - 实时验证输入的有效性
  - 显示创建预览，确认后执行

#### 5.1.3 数据库修改（改）
- **修改数据库属性**：
  - 命令：`ALTER DATABASE <database_name>` 或交互式命令 `alter database <database_name>`
  - 支持修改字符集：`ALTER DATABASE db_name CHARACTER SET utf8mb4`
  - 支持修改排序规则：`ALTER DATABASE db_name COLLATE utf8mb4_unicode_ci`
  - 支持修改其他属性（根据数据库类型）：
    - MySQL：字符集、排序规则、加密选项
    - PostgreSQL：连接限制、所有者、表空间
    - SQL Server：文件组、文件大小限制
  - 修改前提示：显示当前值和将要修改的值，需要确认
  - 修改后验证：验证修改是否成功
- **重命名数据库**：
  - 命令：根据数据库类型使用相应的重命名语句
  - 注意：某些数据库（如MySQL）不支持直接重命名，需要导出导入
  - 提供重命名流程指导

#### 5.1.4 数据库删除（删）
- **删除数据库**：
  - 命令：`DROP DATABASE <database_name>` 或交互式命令 `drop database <database_name>`
  - 安全确认：删除前必须二次确认，显示数据库信息（表数量、数据大小等）
  - 生产环境保护：生产环境删除需要额外授权或特殊标志
  - 支持级联删除选项：`DROP DATABASE db_name CASCADE`（如果数据库支持）
  - 删除前备份提示：建议用户先备份数据库
  - 删除后验证：确认数据库已删除
- **强制删除**：
  - 支持强制删除（即使有活动连接）
  - 需要明确指定 `--force` 参数
  - 显示警告信息

#### 5.1.5 数据库切换
- **切换当前数据库**：
  - 命令：`USE <database_name>` 或 `\c <database_name>`（PostgreSQL）或交互式命令 `use <database_name>`
  - 切换后更新提示信息，显示新的当前数据库
  - 切换前验证：检查数据库是否存在、是否有访问权限
  - 切换后测试：自动测试新数据库连接

### 5.2 表管理（增删改查）

#### 5.2.1 表查询（查）
- **列出所有表**：
  - 命令：`SHOW TABLES` 或 `\dt`（PostgreSQL）或交互式命令 `show tables`、`list tables`
  - 显示当前数据库中的所有表
  - 显示信息：表名、表类型（表/视图）、记录数、数据大小、创建时间
  - 支持按名称、大小、记录数、创建时间排序
  - 支持搜索过滤：输入关键字快速过滤表列表
  - 支持显示系统表选项：可选择是否显示系统表
- **查看表结构**：
  - 命令：`DESCRIBE <table_name>` 或 `DESC <table_name>` 或 `\d <table_name>`（PostgreSQL）或交互式命令 `describe <table_name>`
  - 显示表的完整结构信息：
    - 列信息：列名、数据类型、是否允许NULL、默认值、注释
    - 主键信息：主键列名
    - 索引信息：索引名、索引类型、索引列、唯一性
    - 外键信息：外键名、关联表、关联列
    - 约束信息：唯一约束、检查约束、非空约束
    - 表选项：存储引擎（MySQL）、表空间、字符集等
- **查看表统计信息**：
  - 命令：`SHOW TABLE STATUS LIKE '<table_name>'` 或交互式命令 `table stats <table_name>`
  - 显示表的统计信息：
    - 记录数（行数）
    - 数据大小、索引大小、总大小
    - 平均行长度
    - 创建时间、更新时间
    - 自增值（如果有自增列）
- **查看表数据**：
  - 命令：`SELECT * FROM <table_name> LIMIT N` 或交互式命令 `select from <table_name>`
  - 支持指定查询条件、排序、限制条数
  - 支持分页查看

#### 5.2.2 表创建（增）
- **创建新表**：
  - 命令：`CREATE TABLE <table_name> (...)` 或交互式命令 `create table <table_name>`
  - 支持完整的表定义：
    - 列定义：列名、数据类型、约束、默认值、注释
    - 主键定义：单列主键、复合主键
    - 索引定义：普通索引、唯一索引、全文索引
    - 外键定义：外键约束、关联表、关联列
    - 表选项：存储引擎、字符集、排序规则、表注释
  - 交互式创建向导：
    - 引导用户输入表名
    - 逐步添加列定义（列名、类型、约束等）
    - 实时验证语法和约束
    - 生成CREATE TABLE语句预览
    - 确认后执行创建
  - 从模板创建表：
    - 提供常用表模板（用户表、日志表、配置表等）
    - 支持从现有表复制结构创建新表
    - 支持从SQL文件导入表结构
  - 创建前验证：
    - 检查表名是否已存在
    - 验证表名格式是否合法
    - 检查列定义是否完整
    - 验证约束是否合理
- **从查询结果创建表**：
  - 命令：`CREATE TABLE <new_table> AS SELECT ...`
  - 支持从SELECT查询结果创建新表
  - 支持只复制表结构（不复制数据）：`CREATE TABLE <new_table> LIKE <source_table>`

#### 5.2.3 表修改（改）
- **修改表结构**：
  - 命令：`ALTER TABLE <table_name> ...` 或交互式命令 `alter table <table_name>`
  - **添加列**：
    - `ALTER TABLE table_name ADD COLUMN column_name data_type [约束]`
    - 支持指定列位置：`FIRST`（第一列）或 `AFTER column_name`（指定列之后）
    - 交互式添加：引导用户输入列定义
  - **删除列**：
    - `ALTER TABLE table_name DROP COLUMN column_name`
    - 安全确认：删除前显示列信息和依赖关系，需要确认
    - 检查依赖：如果有外键或其他约束引用该列，提示警告
  - **修改列**：
    - `ALTER TABLE table_name MODIFY COLUMN column_name new_data_type`
    - 支持修改数据类型、默认值、是否允许NULL、注释
    - 类型转换检查：检查数据类型兼容性，可能丢失数据的转换需要确认
  - **重命名列**：
    - `ALTER TABLE table_name RENAME COLUMN old_name TO new_name`
    - 检查依赖：如果有索引、外键等引用该列，自动更新引用
  - **重命名表**：
    - `ALTER TABLE old_name RENAME TO new_name` 或 `RENAME TABLE old_name TO new_name`
    - 检查依赖：更新所有引用该表的外键、视图、存储过程等
  - **修改表选项**：
    - 修改存储引擎：`ALTER TABLE table_name ENGINE=InnoDB`
    - 修改字符集：`ALTER TABLE table_name CONVERT TO CHARACTER SET utf8mb4`
    - 修改表注释：`ALTER TABLE table_name COMMENT='新注释'`
- **索引管理**：
  - **添加索引**：
    - `CREATE INDEX index_name ON table_name (column_list)`
    - 支持普通索引、唯一索引、全文索引、复合索引
    - 交互式添加：引导用户选择列和索引类型
  - **删除索引**：
    - `DROP INDEX index_name ON table_name`
    - 删除前显示索引信息，需要确认
  - **修改索引**：
    - 某些数据库支持修改索引（如PostgreSQL），根据数据库类型提供相应功能
- **约束管理**：
  - **添加约束**：
    - 主键约束：`ALTER TABLE table_name ADD PRIMARY KEY (column_list)`
    - 外键约束：`ALTER TABLE table_name ADD FOREIGN KEY (column) REFERENCES ref_table(ref_column)`
    - 唯一约束：`ALTER TABLE table_name ADD UNIQUE (column_list)`
    - 检查约束：`ALTER TABLE table_name ADD CHECK (condition)`
  - **删除约束**：
    - `ALTER TABLE table_name DROP CONSTRAINT constraint_name`
    - 删除前显示约束信息，需要确认
- **批量修改**：
  - 支持在一个ALTER TABLE语句中执行多个修改操作
  - 提供修改预览，显示所有将要执行的修改
  - 支持修改回滚（如果数据库支持）

#### 5.2.4 表删除（删）
- **删除表**：
  - 命令：`DROP TABLE <table_name>` 或交互式命令 `drop table <table_name>`
  - 安全确认：
    - 删除前显示表信息（记录数、数据大小、依赖关系）
    - 必须二次确认
    - 生产环境删除需要额外授权
  - 支持级联删除：
    - `DROP TABLE table_name CASCADE`（删除表及其依赖对象）
    - 显示将被级联删除的对象列表
  - 支持批量删除：
    - `DROP TABLE table1, table2, ...`
    - 交互式选择多个表进行删除
  - 删除前备份提示：
    - 建议用户先备份表数据
    - 提供快速备份命令
  - 删除后验证：
    - 确认表已删除
    - 清理相关缓存和元数据
- **清空表数据**：
  - 命令：`TRUNCATE TABLE <table_name>` 或交互式命令 `truncate table <table_name>`
  - 与DELETE的区别说明：
    - TRUNCATE更快，但不可回滚
    - DELETE可以带WHERE条件，可以回滚
  - 安全确认：清空前显示表记录数，需要确认
  - 支持级联清空：`TRUNCATE TABLE table_name CASCADE`（如果数据库支持）

### 5.3 交互式管理命令

#### 5.3.1 数据库管理命令
```bash
# 列出所有数据库
[development] dev_mysql@localhost:3306/test_db > list databases
# 或
[development] dev_mysql@localhost:3306/test_db > show databases

# 查看数据库详情
[development] dev_mysql@localhost:3306/test_db > describe database new_db

# 创建数据库
[development] dev_mysql@localhost:3306/test_db > create database new_db charset utf8mb4

# 修改数据库
[development] dev_mysql@localhost:3306/test_db > alter database new_db charset utf8mb4 collate utf8mb4_unicode_ci

# 删除数据库
[development] dev_mysql@localhost:3306/test_db > drop database old_db
⚠️  警告：此操作将删除数据库 'old_db' 及其所有数据！
数据库信息：
  - 表数量: 15
  - 数据大小: 125.5 MB
  - 索引大小: 45.2 MB
是否确认删除？[y/N]: y
✓ 数据库 'old_db' 已删除

# 切换数据库
[development] dev_mysql@localhost:3306/test_db > use new_db
已切换到数据库: new_db
[development] dev_mysql@localhost:3306/new_db >
```

#### 5.3.2 表管理命令
```bash
# 列出所有表
[development] dev_mysql@localhost:3306/test_db > show tables
# 或
[development] dev_mysql@localhost:3306/test_db > list tables

# 查看表结构
[development] dev_mysql@localhost:3306/test_db > describe users
# 或
[development] dev_mysql@localhost:3306/test_db > desc users

# 查看表统计信息
[development] dev_mysql@localhost:3306/test_db > table stats users

# 创建表（交互式向导）
[development] dev_mysql@localhost:3306/test_db > create table products
请输入表名: products
是否使用模板？[y/N]: n
添加列 #1:
  列名: id
  数据类型: INT
  是否主键？[Y/n]: y
  是否自增？[Y/n]: y
  是否允许NULL？[y/N]: n
添加列 #2:
  列名: name
  数据类型: VARCHAR(100)
  是否允许NULL？[y/N]: n
添加列 #3:
  列名: price
  数据类型: DECIMAL(10,2)
  默认值: 0.00
  是否允许NULL？[y/N]: n
是否继续添加列？[y/N]: n

生成的SQL:
CREATE TABLE products (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  price DECIMAL(10,2) NOT NULL DEFAULT 0.00
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

是否执行？[Y/n]: y
✓ 表 'products' 创建成功

# 修改表结构
[development] dev_mysql@localhost:3306/test_db > alter table products add column description TEXT
✓ 列 'description' 已添加到表 'products'

# 删除表
[development] dev_mysql@localhost:3306/test_db > drop table old_table
⚠️  警告：此操作将删除表 'old_table' 及其所有数据！
表信息：
  - 记录数: 1,250
  - 数据大小: 2.5 MB
  - 索引大小: 0.8 MB
是否确认删除？[y/N]: y
✓ 表 'old_table' 已删除

# 清空表数据
[development] dev_mysql@localhost:3306/test_db > truncate table temp_data
⚠️  警告：此操作将清空表 'temp_data' 的所有数据（1,250 条记录）！
是否确认？[y/N]: y
✓ 表 'temp_data' 已清空
```

### 5.4 安全与验证
- **操作前验证**：
  - 所有删除操作必须二次确认
  - 显示将被影响的对象信息（记录数、大小等）
  - 生产环境操作需要额外授权标志
- **依赖关系检查**：
  - 删除数据库前检查是否有表、视图等依赖
  - 删除表前检查是否有外键、视图、存储过程等依赖
  - 显示依赖关系图，帮助用户理解影响范围
- **操作回滚**：
  - 支持事务包装，失败时自动回滚
  - 提供操作历史，支持撤销（如果可能）
- **权限检查**：
  - 执行操作前检查用户权限
  - 权限不足时提供明确的错误提示和授权建议

## 6. 项目集成与用户隔离

### 6.1 项目集成需求

#### 6.1.1 集成目标
- **嵌入到现有工具项目**：数据库操作工具需要作为工具项目的一个功能模块，集成到现有的前端（frontend）和后端（backend）架构中
- **统一用户体验**：与项目其他工具保持一致的UI/UX风格和交互模式
- **统一认证体系**：使用项目现有的用户认证系统，无需单独登录
- **统一权限管理**：遵循项目的权限管理规范

#### 6.1.2 集成架构
- **前端集成**：
  - 在项目首页添加数据库管理工具的入口卡片
  - 创建独立的工具页面组件（`DatabaseTool.tsx`）
  - 使用项目现有的路由系统（React Router）
  - 使用项目现有的UI组件库和样式系统
  - 使用项目现有的认证Context（`useAuth` hook）
- **后端集成**：
  - 创建独立的API路由模块（`database_tool.py`）
  - 使用项目现有的FastAPI框架和中间件
  - 使用项目现有的认证中间件（`get_current_user_id`）
  - 使用项目现有的数据库连接（如果适用）
  - 遵循项目现有的API设计规范

### 6.2 前端集成

#### 6.2.1 首页入口设计
- **工具卡片**：
  - 在首页工具列表中添加"数据库管理工具"卡片
  - 卡片信息：
    - 工具ID：`database-tool`
    - 工具标题：`数据库管理工具`（支持国际化）
    - 工具描述：`统一管理多个数据库连接，执行SQL脚本，浏览数据库结构`
    - 工具图标：数据库相关图标（如`Database`、`Server`等）
    - 工具分类：`开发工具`或`数据库工具`
    - 工具标签：`数据库`、`SQL`、`管理`
- **路由配置**：
  - 在`App.tsx`中添加路由：`/tools/database-tool`
  - 路由组件：`<DatabaseTool />`
  - 需要认证：是（使用项目的认证保护机制）

#### 6.2.2 工具页面组件
- **组件结构**：
  ```
  frontend/src/components/Tools/DatabaseTool/
  ├── DatabaseTool.tsx          # 主组件
  ├── DatabaseConfigPanel.tsx   # 数据库配置面板
  ├── SQLExecutor.tsx            # SQL执行器
  ├── SchemaBrowser.tsx         # Schema浏览器
  ├── TableManager.tsx          # 表管理器
  └── components/               # 子组件
      ├── ConnectionList.tsx    # 连接列表
      ├── SQLEditor.tsx         # SQL编辑器
      ├── ResultViewer.tsx      # 结果查看器
      └── HistoryPanel.tsx      # 历史记录面板
  ```
- **页面布局**：
  - 使用项目现有的Layout组件
  - 左侧边栏：数据库连接列表、快速操作
  - 主内容区：SQL编辑器、结果展示、Schema浏览
  - 右侧面板（可选）：执行历史、配置管理
- **状态管理**：
  - 使用React Hooks（useState、useEffect）管理本地状态
  - 使用Context API管理全局状态（当前连接、用户信息等）
  - 使用项目现有的API调用模式（fetch或axios）

#### 6.2.3 用户认证集成
- **认证检查**：
  - 使用`useAuth` hook获取当前用户信息
  - 未登录用户重定向到登录页面
  - 已登录用户显示用户信息（用户名、角色等）
- **权限控制**：
  - 根据用户角色显示/隐藏功能
  - 普通用户：只能管理自己的数据库配置
  - 管理员：可以查看所有用户的配置（可选功能）

#### 6.2.4 API调用
- **API客户端**：
  - 创建`databaseToolApi.ts`文件，封装所有API调用
  - 使用项目现有的API基础URL配置
  - 使用项目现有的认证token机制（Authorization header）
  - 统一的错误处理
- **API方法**：
  ```typescript
  // 数据库配置管理
  getDatabases(userId: string): Promise<DatabaseConfig[]>
  createDatabase(config: CreateDatabaseRequest): Promise<DatabaseConfig>
  updateDatabase(id: string, config: UpdateDatabaseRequest): Promise<DatabaseConfig>
  deleteDatabase(id: string): Promise<void>
  testConnection(config: TestConnectionRequest): Promise<ConnectionTestResult>
  
  // SQL执行
  executeSQL(databaseId: string, sql: string): Promise<SQLExecutionResult>
  executeSQLFile(databaseId: string, file: File): Promise<SQLExecutionResult>
  
  // Schema浏览
  getTables(databaseId: string): Promise<Table[]>
  getTableSchema(databaseId: string, tableName: string): Promise<TableSchema>
  getTableData(databaseId: string, tableName: string, params: QueryParams): Promise<TableData>
  
  // 执行历史
  getHistory(userId: string, filters?: HistoryFilters): Promise<ExecutionHistory[]>
  deleteHistory(historyId: string): Promise<void>
  ```

### 6.3 后端集成

#### 6.3.1 API路由设计
- **路由模块**：
  - 文件路径：`backend/app/routes/database_tool.py`
  - 路由前缀：`/api/database-tool`
  - 标签：`database-tool`
- **路由注册**：
  ```python
  # 在 backend/app/main.py 中注册
  from app.routes import database_tool
  app.include_router(database_tool.router, prefix="/api")
  ```

#### 6.3.2 API端点设计
- **数据库配置管理**：
  ```
  GET    /api/database-tool/databases          # 获取用户的所有数据库配置
  POST   /api/database-tool/databases          # 创建新的数据库配置
  GET    /api/database-tool/databases/{id}     # 获取指定数据库配置
  PUT    /api/database-tool/databases/{id}    # 更新数据库配置
  DELETE /api/database-tool/databases/{id}    # 删除数据库配置
  POST   /api/database-tool/databases/test    # 测试数据库连接
  POST   /api/database-tool/databases/scan    # 扫描项目配置文件（可选）
  ```
- **SQL执行**：
  ```
  POST   /api/database-tool/execute            # 执行SQL语句
  POST   /api/database-tool/execute/file       # 执行SQL文件
  POST   /api/database-tool/execute/batch      # 批量执行SQL
  ```
- **Schema浏览**：
  ```
  GET    /api/database-tool/databases/{id}/databases    # 获取数据库列表
  GET    /api/database-tool/databases/{id}/tables       # 获取表列表
  GET    /api/database-tool/databases/{id}/tables/{table}/schema  # 获取表结构
  GET    /api/database-tool/databases/{id}/tables/{table}/data      # 获取表数据
  ```
- **执行历史**：
  ```
  GET    /api/database-tool/history            # 获取执行历史
  DELETE /api/database-tool/history/{id}       # 删除历史记录
  GET    /api/database-tool/history/{id}       # 获取历史详情
  POST   /api/database-tool/history/{id}/replay # 重放历史记录
  ```

#### 6.3.3 服务层设计
- **服务模块**：
  - 文件路径：`backend/app/services/database_tool_service.py`
  - 职责：
    - 数据库配置的CRUD操作
    - SQL执行逻辑
    - 数据库连接管理
    - Schema信息获取
    - 执行历史管理
- **数据访问层**：
  - 使用SQLAlchemy ORM或直接使用数据库驱动
  - 封装数据库操作，提供统一接口
  - 处理数据库类型差异

#### 6.3.4 认证与授权
- **认证中间件**：
  - 所有API端点使用`Depends(get_current_user_id)`获取当前用户ID
  - 确保只有登录用户才能访问
- **用户隔离**：
  - 所有数据库查询自动添加`user_id`过滤条件
  - 创建操作自动关联当前用户ID
  - 更新/删除操作验证资源所有权

### 6.4 用户隔离设计

#### 6.4.1 隔离原则
- **数据隔离**：
  - 每个用户只能看到和管理自己的数据库配置
  - 每个用户只能查看自己的执行历史
  - 用户之间完全隔离，无法访问其他用户的数据
- **操作隔离**：
  - SQL执行操作记录用户ID
  - 所有操作日志关联用户ID
  - 错误日志包含用户信息（用于问题排查）

#### 6.4.2 隔离实现
- **数据库层面**：
  - 所有表包含`user_id`字段
  - 查询时自动添加`WHERE user_id = current_user_id`条件
  - 创建时自动设置`user_id = current_user_id`
  - 更新/删除时验证`user_id`匹配
- **应用层面**：
  - 服务层方法接收`user_id`参数
  - 数据访问层自动处理用户过滤
  - API层从认证中间件获取`user_id`
- **前端层面**：
  - API调用自动携带用户认证信息
  - 不显示其他用户的数据
  - 操作结果只影响当前用户的数据

#### 6.4.3 管理员功能（可选）
- **管理员权限**：
  - 管理员可以查看所有用户的数据库配置（只读）
  - 管理员可以查看所有用户的执行历史（用于审计）
  - 管理员不能修改或删除其他用户的配置
- **权限检查**：
  - 在服务层检查用户角色
  - 管理员查询时使用不同的过滤条件
  - 前端根据角色显示/隐藏功能

### 6.5 数据库设计

#### 6.5.1 数据库配置表（db_configs）
```sql
CREATE TABLE db_configs (
    id VARCHAR(64) PRIMARY KEY,                    -- 配置ID（UUID或雪花ID）
    user_id VARCHAR(64) NOT NULL,                   -- 用户ID（外键关联users表）
    alias VARCHAR(32) NOT NULL,                     -- 配置别名
    db_type VARCHAR(20) NOT NULL,                  -- 数据库类型（mysql/postgresql/sqlite等）
    host VARCHAR(255) NOT NULL,                    -- 主机地址
    port INT NOT NULL,                             -- 端口号
    database_name VARCHAR(255) NOT NULL,           -- 数据库名
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
    last_connected_at DATETIME,                   -- 最后连接时间
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_user_alias (user_id, alias),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 6.5.2 执行历史表（sql_execution_history）
```sql
CREATE TABLE sql_execution_history (
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
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_db_config_id (db_config_id),
    INDEX idx_created_at (created_at),
    INDEX idx_sql_type (sql_type),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (db_config_id) REFERENCES db_configs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 6.5.3 数据库扫描记录表（db_scan_history，可选）
```sql
CREATE TABLE db_scan_history (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    scan_path VARCHAR(500) NOT NULL,                -- 扫描路径
    configs_found INT DEFAULT 0,                    -- 发现的配置数量
    scan_result JSON,                               -- 扫描结果（JSON格式）
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 6.5.4 表结构缓存表（table_schema_cache，可选）
```sql
CREATE TABLE table_schema_cache (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    db_config_id VARCHAR(64) NOT NULL,
    table_name VARCHAR(255) NOT NULL,
    schema_data JSON NOT NULL,                      -- 表结构数据（JSON格式）
    cached_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,                   -- 缓存过期时间
    INDEX idx_user_db (user_id, db_config_id),
    INDEX idx_expires_at (expires_at),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (db_config_id) REFERENCES db_configs(id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_db_table (user_id, db_config_id, table_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 6.6 API接口设计

#### 6.6.1 请求/响应模型
- **数据库配置模型**：
  ```python
  class DatabaseConfig(BaseModel):
      id: str
      user_id: str
      alias: str
      db_type: str  # mysql, postgresql, sqlite, etc.
      host: str
      port: int
      database_name: str
      username: str
      password_encrypted: str  # 加密存储，不返回给前端
      environment: Optional[str]
      group_name: Optional[str]
      charset: Optional[str]
      connect_timeout: int = 10
      max_pool_size: int = 10
      ssl_mode: Optional[str]
      extra_config: Optional[dict]
      is_active: bool = True
      last_connected_at: Optional[datetime]
      created_at: datetime
      updated_at: datetime
  
  class CreateDatabaseRequest(BaseModel):
      alias: str
      db_type: str
      host: str
      port: int
      database_name: str
      username: str
      password: str  # 前端传入明文，后端加密存储
      environment: Optional[str] = None
      group_name: Optional[str] = None
      charset: Optional[str] = None
      connect_timeout: int = 10
      max_pool_size: int = 10
      ssl_mode: Optional[str] = None
      extra_config: Optional[dict] = None
  
  class UpdateDatabaseRequest(BaseModel):
      alias: Optional[str] = None
      host: Optional[str] = None
      port: Optional[int] = None
      database_name: Optional[str] = None
      username: Optional[str] = None
      password: Optional[str] = None  # 如果提供，则更新密码
      environment: Optional[str] = None
      group_name: Optional[str] = None
      # ... 其他可选字段
  ```
- **SQL执行模型**：
  ```python
  class SQLExecutionRequest(BaseModel):
      db_config_id: str
      sql: str
      parameters: Optional[dict] = None  # 参数化查询参数
  
  class SQLExecutionResult(BaseModel):
      execution_id: str
      status: str  # success, failed, timeout
      affected_rows: Optional[int] = None
      execution_time_ms: int
      error_message: Optional[str] = None
      result_data: Optional[list] = None  # SELECT查询结果
      result_columns: Optional[list] = None  # 列名
      total_rows: Optional[int] = None  # 总行数（分页时）
  ```
- **执行历史模型**：
  ```python
  class ExecutionHistory(BaseModel):
      id: str
      user_id: str
      db_config_id: str
      db_alias: str  # 数据库别名（用于显示）
      sql_statement: str
      sql_type: str
      execution_status: str
      affected_rows: Optional[int]
      execution_time_ms: int
      error_message: Optional[str]
      created_at: datetime
  ```

#### 6.6.2 API端点详细设计
- **获取数据库配置列表**：
  ```python
  @router.get("/database-tool/databases", response_model=List[DatabaseConfig])
  async def get_databases(
      user_id: str = Depends(get_current_user_id),
      skip: int = 0,
      limit: int = 100
  ):
      """获取当前用户的所有数据库配置"""
      return database_tool_service.get_user_databases(user_id, skip, limit)
  ```
- **创建数据库配置**：
  ```python
  @router.post("/database-tool/databases", response_model=DatabaseConfig)
  async def create_database(
      request: CreateDatabaseRequest,
      user_id: str = Depends(get_current_user_id)
  ):
      """创建新的数据库配置"""
      # 验证别名唯一性（同一用户下）
      # 加密密码
      # 测试连接
      # 保存配置
      return database_tool_service.create_database(user_id, request)
  ```
- **执行SQL**：
  ```python
  @router.post("/database-tool/execute", response_model=SQLExecutionResult)
  async def execute_sql(
      request: SQLExecutionRequest,
      user_id: str = Depends(get_current_user_id)
  ):
      """执行SQL语句"""
      # 验证数据库配置所有权
      # 执行SQL
      # 记录执行历史
      return database_tool_service.execute_sql(user_id, request)
  ```

#### 6.6.3 错误处理
- **统一错误响应**：
  ```python
  class ErrorResponse(BaseModel):
      error_code: str
      error_message: str
      detail: Optional[str] = None
  ```
- **错误码定义**：
  - `DB_CONFIG_NOT_FOUND`: 数据库配置不存在
  - `DB_CONFIG_ACCESS_DENIED`: 无权访问该数据库配置
  - `DB_CONNECTION_FAILED`: 数据库连接失败
  - `SQL_EXECUTION_FAILED`: SQL执行失败
  - `INVALID_SQL_SYNTAX`: SQL语法错误
  - `DUPLICATE_ALIAS`: 别名重复

## 7. 工具实现要求

### 7.1 项目结构
数据库操作工具集成到现有工具项目中，文件结构如下：

```
tools/
├── backend/
│   └── app/
│       ├── routes/
│       │   └── database_tool.py              # 数据库工具API路由
│       ├── services/
│       │   └── database_tool_service.py      # 数据库工具服务层
│       ├── models/
│       │   └── database_tool_models.py      # 数据库工具数据模型
│       └── utils/
│           ├── db_connection_manager.py     # 数据库连接管理
│           ├── sql_executor.py              # SQL执行器
│           ├── schema_browser.py            # Schema浏览器
│           └── db_config_parser.py          # 配置文件解析器
│
├── frontend/
│   └── src/
│       ├── components/
│       │   └── Tools/
│       │       └── DatabaseTool/            # 数据库工具组件
│       │           ├── DatabaseTool.tsx    # 主组件
│       │           ├── DatabaseConfigPanel.tsx
│       │           ├── SQLExecutor.tsx
│       │           ├── SchemaBrowser.tsx
│       │           ├── TableManager.tsx
│       │           └── components/          # 子组件
│       │               ├── ConnectionList.tsx
│       │               ├── SQLEditor.tsx
│       │               ├── ResultViewer.tsx
│       │               └── HistoryPanel.tsx
│       ├── api/
│       │   └── databaseToolApi.ts          # API客户端
│       └── types/
│           └── databaseTool.ts              # TypeScript类型定义
│
└── docs/
    └── database_operation_tool.md          # 需求文档（本文档）
```

**说明**：
- 后端代码集成到`backend/app/`目录下，遵循项目现有的目录结构
- 前端代码集成到`frontend/src/components/Tools/`目录下，与其他工具保持一致
- 数据库表结构存储在项目的主数据库中（与用户表同一数据库）
- 配置文件不再使用独立的YAML文件，而是存储在数据库中

### 7.2 技术栈
数据库操作工具集成到现有项目中，使用项目现有的技术栈：

**后端技术栈**（与项目保持一致）：
- **框架**：FastAPI（项目已使用）
- **Python版本**：Python 3.10+（与项目保持一致）
- **数据库ORM**：SQLAlchemy 2.0+（如果项目使用）或直接使用数据库驱动
- **认证**：使用项目现有的JWT认证机制
- **核心依赖库**（需要添加到`backend/requirements.txt`）：
  - `sqlalchemy>=2.0.0`：用于数据库连接和操作，支持多种数据库
  - `pandas>=1.5.0`：用于查询结果的表格化展示和数据导出（可选）
  - `sqlparse>=0.4.0`：用于SQL脚本的格式化和解析
  - `python-dotenv>=1.0.0`：用于环境变量配置文件解析
  - `pyyaml>=6.0`：用于YAML配置文件解析
  - `cryptography>=41.0.0`：用于敏感信息加密存储
- **数据库驱动**（根据支持的数据库类型添加）：
  - `pymysql>=1.0.0`：MySQL驱动
  - `psycopg2-binary>=2.9.0`：PostgreSQL驱动
  - `aiosqlite>=0.19.0`：SQLite驱动（异步）
  - `cx_Oracle>=8.3.0`：Oracle驱动（可选）

**前端技术栈**（与项目保持一致）：
- **框架**：React + TypeScript（项目已使用）
- **路由**：React Router（项目已使用）
- **状态管理**：React Hooks + Context API（项目已使用）
- **UI组件**：使用项目现有的UI组件库
- **API调用**：使用项目现有的API调用方式（fetch或axios）
- **样式**：使用项目现有的样式系统（Tailwind CSS等）

### 7.3 代码结构说明

**后端代码结构**：
- **database_tool.py**（路由层）：
  - 定义所有API端点
  - 处理HTTP请求和响应
  - 使用认证中间件获取用户ID
  - 调用服务层方法
- **database_tool_service.py**（服务层）：
  - 业务逻辑处理
  - 数据库配置的CRUD操作
  - SQL执行逻辑
  - 执行历史管理
  - 用户隔离逻辑
- **database_tool_models.py**（数据模型）：
  - Pydantic模型定义
  - 请求/响应模型
  - 数据验证
- **db_connection_manager.py**（连接管理）：
  - 数据库连接的创建、管理和复用
  - 连接池管理
  - 连接健康检查
  - 支持多种数据库类型
- **sql_executor.py**（SQL执行器）：
  - SQL脚本的执行
  - 事务管理
  - 执行结果收集和格式化
  - 错误处理
- **schema_browser.py**（Schema浏览器）：
  - 获取数据库列表
  - 获取表列表和结构
  - 获取表数据
- **db_config_parser.py**（配置解析器）：
  - 扫描项目文件系统，识别数据库配置文件
  - 解析各种格式的配置文件（.env、.properties、.yml、.php等）
  - 提取数据库连接参数

**前端代码结构**：
- **DatabaseTool.tsx**（主组件）：
  - 页面布局和状态管理
  - 协调子组件
  - 处理用户交互
- **DatabaseConfigPanel.tsx**（配置面板）：
  - 数据库配置列表
  - 添加/编辑/删除配置
  - 测试连接
- **SQLExecutor.tsx**（SQL执行器）：
  - SQL编辑器
  - 执行SQL语句
  - 显示执行结果
- **SchemaBrowser.tsx**（Schema浏览器）：
  - 显示数据库和表列表
  - 显示表结构
  - 预览表数据
- **TableManager.tsx**（表管理器）：
  - 表的增删改查操作
  - 表结构修改
- **databaseToolApi.ts**（API客户端）：
  - 封装所有API调用
  - 处理认证token
  - 统一错误处理

### 7.4 数据存储格式

**数据库配置存储**：
- 所有数据库配置存储在数据库表`db_configs`中（见6.5.1节）
- 密码使用AES-256加密后存储
- 每个用户的配置完全隔离，通过`user_id`字段关联

**API请求/响应格式**：
- **创建数据库配置请求**：
```json
{
  "alias": "dev_mysql",
  "db_type": "mysql",
  "host": "localhost",
  "port": 3306,
  "database_name": "test_db",
  "username": "root",
  "password": "plaintext_password",  // 前端传入明文，后端加密存储
  "environment": "development",
  "group_name": "开发环境",
  "charset": "utf8mb4",
  "connect_timeout": 10,
  "max_pool_size": 10
}
```

- **数据库配置响应**（不包含密码）：
```json
{
  "id": "uuid-or-snowflake-id",
  "user_id": "user-uuid",
  "alias": "dev_mysql",
  "db_type": "mysql",
  "host": "localhost",
  "port": 3306,
  "database_name": "test_db",
  "username": "root",
  "environment": "development",
  "group_name": "开发环境",
  "charset": "utf8mb4",
  "is_active": true,
  "last_connected_at": "2026-01-27T10:30:00Z",
  "created_at": "2026-01-27T10:00:00Z",
  "updated_at": "2026-01-27T10:30:00Z"
}
```

**执行历史存储**：
- 所有执行历史存储在数据库表`sql_execution_history`中（见6.5.2节）
- 查询结果（SELECT）以JSON格式存储，支持分页
- 错误信息完整记录，便于问题排查

### 7.5 测试要求
- **单元测试**：
  - 覆盖所有核心功能模块（配置解析、连接管理、SQL执行、错误处理等）
  - 测试覆盖率要求：≥80%
  - 使用pytest框架
  - Mock数据库连接，避免依赖真实数据库
- **集成测试**：
  - 使用Docker容器创建测试数据库（MySQL、PostgreSQL、SQLite）
  - 模拟真实数据库操作场景
  - 测试各种数据库类型的兼容性
  - 测试错误场景和边界情况
- **错误处理测试**：
  - 验证各种异常情况的处理（连接失败、SQL错误、权限错误等）
  - 验证错误信息的准确性和可读性
  - 验证修复建议的合理性
- **性能测试**：
  - 测试大数据量查询的性能
  - 测试连接池的性能
  - 测试配置扫描的性能

## 8. 使用示例

### 8.1 安装与启动
```bash
# 安装工具
pip install -r requirements.txt
python setup.py install

# 启动交互式Shell
db-tool

# 指定数据源启动
db-tool -d dev_mysql

# 执行SQL脚本文件
db-tool -d prod_postgres ./scripts/update_users.sql

# 批量执行SQL脚本
db-tool -d dev_mysql -r ./scripts/migrations/
```

### 8.2 自动发现项目数据库配置
```bash
$ db-tool --scan
正在扫描项目配置文件...
发现以下数据库配置：

[1] dev_mysql (MySQL)
    主机: localhost:3306
    数据库: test_db
    来源: .env
    环境: development

[2] prod_postgres (PostgreSQL)
    主机: prod-db.example.com:5432
    数据库: production
    来源: config/database.yml
    环境: production

是否将这些配置添加到工具中？[Y/n]: Y
配置已保存到 ~/.db_tool/.db_tool_config.yaml
```

### 8.3 手动添加数据库配置
```bash
# 交互式添加
$ db-tool --add-config
请输入数据库别名: dev_mysql
请选择数据库类型 [mysql/postgresql/sqlite/oracle]: mysql
请输入主机地址: localhost
请输入端口 [3306]: 
请输入数据库名: test_db
请输入用户名: root
请输入密码: ********
请选择环境 [dev/test/prod]: dev
正在测试连接...
✓ 连接成功！数据库版本: MySQL 8.0.33
配置已保存。

# 命令行添加
$ db-tool --add-config \
  --alias prod_postgres \
  --type postgresql \
  --host prod-db.example.com \
  --port 5432 \
  --database production \
  --username app_user \
  --password "your_password" \
  --env prod
```

### 8.4 交互式Shell使用
```bash
$ db-tool
[development] dev_mysql@localhost:3306/test_db > 

# 切换数据源
[development] dev_mysql@localhost:3306/test_db > use prod_postgres
已切换到: [production] prod_postgres@prod-db.example.com:5432/production

# 执行查询SQL
[production] prod_postgres@prod-db.example.com:5432/production > SELECT id, name, email FROM users LIMIT 5;

┌────┬──────────────┬─────────────────────┐
│ id │ name         │ email               │
├────┼──────────────┼─────────────────────┤
│  1 │ 张三         │ zhangsan@example.com│
│  2 │ 李四         │ lisi@example.com    │
│  3 │ 王五         │ wangwu@example.com  │
│  4 │ 赵六         │ zhaoliu@example.com │
│  5 │ 钱七         │ qianqi@example.com  │
└────┴──────────────┴─────────────────────┘
5 rows in set (0.023 sec)

# 格式化SQL
[production] prod_postgres@prod-db.example.com:5432/production > format
请输入SQL语句（输入END结束）:
> SELECT id,name,email FROM users WHERE status='active' ORDER BY created_at DESC;
> END

格式化后的SQL:
SELECT id,
       name,
       email
FROM users
WHERE status = 'active'
ORDER BY created_at DESC;

# 执行数据操作
[production] prod_postgres@prod-db.example.com:5432/production > UPDATE users SET status='inactive' WHERE id=100;
✓ 成功影响 1 条记录
执行耗时：0.045秒

# 查看执行历史
[production] prod_postgres@prod-db.example.com:5432/production > history
┌────┬─────────────────────┬──────────────────────────┬──────────┬────────┐
│ #  │ 时间                │ SQL语句                  │ 结果     │ 耗时   │
├────┼─────────────────────┼──────────────────────────┼──────────┼────────┤
│  1 │ 2026-01-27 10:23:15 │ SELECT * FROM users...   │ 成功(5)  │ 0.023s │
│  2 │ 2026-01-27 10:24:30 │ UPDATE users SET...      │ 成功(1)  │ 0.045s │
└────┴─────────────────────┴──────────────────────────┴──────────┴────────┘

# 退出
[production] prod_postgres@prod-db.example.com:5432/production > exit
```

### 8.5 执行查询SQL脚本示例
```bash
$ db-tool -d dev_mysql ./scripts/query_users.sql

执行SQL脚本: ./scripts/query_users.sql
数据源: [development] dev_mysql@localhost:3306/test_db

查询结果:
┌────┬──────────────┬─────────────────────┬──────────┐
│ id │ name         │ email               │ status   │
├────┼──────────────┼─────────────────────┼──────────┤
│  1 │ 张三         │ zhangsan@example.com│ active   │
│  2 │ 李四         │ lisi@example.com    │ active   │
│  3 │ 王五         │ wangwu@example.com  │ inactive │
└────┴──────────────┴─────────────────────┴──────────┘
共 3 条记录

执行耗时：0.015秒
```

### 8.6 执行数据操作SQL脚本示例
```bash
$ db-tool -d dev_mysql ./scripts/update_status.sql

执行SQL脚本: ./scripts/update_status.sql
数据源: [development] dev_mysql@localhost:3306/test_db

开始执行事务...
执行语句 1/2: UPDATE users SET status='active' WHERE id IN (1,2,3);
✓ 成功影响 3 条记录

执行语句 2/2: INSERT INTO user_logs (user_id, action, created_at) VALUES (1, 'status_updated', NOW());
✓ 成功影响 1 条记录

事务提交成功！
总执行耗时：0.078秒
```

### 8.7 错误处理示例
```bash
$ db-tool -d dev_mysql
[development] dev_mysql@localhost:3306/test_db > INSERT INTO users (id, name) VALUES (1, '测试');

❌ 执行失败！

错误代码: 1062
错误描述: Duplicate entry '1' for key 'PRIMARY'

失败位置: 
  INSERT INTO users (id, name) VALUES (1, '测试');
                      ^
                      |
                  主键冲突

修复建议:
1. 检查主键值是否已存在:
   SELECT * FROM users WHERE id = 1;

2. 如果记录已存在，使用UPDATE语句:
   UPDATE users SET name = '测试' WHERE id = 1;

3. 如果需要插入新记录，使用不冲突的主键值:
   INSERT INTO users (id, name) VALUES (2, '测试');

4. 或者使用INSERT IGNORE或ON DUPLICATE KEY UPDATE:
   INSERT INTO users (id, name) VALUES (1, '测试')
   ON DUPLICATE KEY UPDATE name = '测试';

事务已回滚，数据未受影响。
```

### 8.8 数据导出示例
```bash
# 导出表数据为CSV
$ db-tool -d dev_mysql --export users --format csv --output ./exports/users.csv
正在导出 users 表数据...
✓ 成功导出 1000 条记录到 ./exports/users.csv

# 导出查询结果为JSON
$ db-tool -d dev_mysql --query "SELECT * FROM users WHERE status='active'" --format json --output ./exports/active_users.json
正在执行查询...
✓ 成功导出 500 条记录到 ./exports/active_users.json

# 导出表结构为SQL
$ db-tool -d dev_mysql --export-schema users --output ./exports/users_schema.sql
正在导出 users 表结构...
✓ 表结构已导出到 ./exports/users_schema.sql
```

### 8.9 Schema浏览示例
```bash
$ db-tool -d dev_mysql
[development] dev_mysql@localhost:3306/test_db > show tables;

┌─────────────────┬──────────┬──────────────┐
│ 表名            │ 记录数   │ 数据大小     │
├─────────────────┼──────────┼──────────────┤
│ users           │ 1,000    │ 256 KB       │
│ orders          │ 5,000    │ 1.2 MB       │
│ products        │ 500      │ 128 KB       │
└─────────────────┴──────────┴──────────────┘

[development] dev_mysql@localhost:3306/test_db > describe users;

表结构: users
┌─────────────┬──────────────┬──────┬─────┬──────────┬─────────────────┐
│ 列名        │ 数据类型     │ 空值 │ 键  │ 默认值   │ 注释            │
├─────────────┼──────────────┼─────┼─────┼──────────┼─────────────────┤
│ id          │ INT          │ NO   │ PRI │ NULL     │ 用户ID          │
│ name        │ VARCHAR(100) │ NO   │     │ NULL     │ 用户名          │
│ email       │ VARCHAR(255) │ NO   │ UNI │ NULL     │ 邮箱            │
│ status      │ VARCHAR(20)  │ YES  │     │ 'active' │ 状态            │
│ created_at  │ DATETIME     │ NO   │     │ NOW()    │ 创建时间        │
└─────────────┴──────────────┴──────┴─────┴──────────┴─────────────────┘

索引:
- PRIMARY KEY (id)
- UNIQUE KEY (email)
- KEY idx_status (status)
```

### 8.10 数据库和表管理示例
```bash
$ db-tool -d dev_mysql
[development] dev_mysql@localhost:3306/test_db > 

# 列出所有数据库
[development] dev_mysql@localhost:3306/test_db > list databases
┌──────────────┬──────────────┬──────────────────┬──────────────┐
│ 数据库名     │ 字符集       │ 排序规则         │ 大小         │
├──────────────┼──────────────┼──────────────────┼──────────────┤
│ information_schema │ utf8mb4 │ utf8mb4_0900_ai_ci │ 系统数据库 │
│ mysql        │ utf8mb4      │ utf8mb4_0900_ai_ci │ 系统数据库 │
│ test_db      │ utf8mb4      │ utf8mb4_unicode_ci  │ 125.5 MB    │
│ new_db       │ utf8mb4      │ utf8mb4_unicode_ci  │ 2.3 MB     │
└──────────────┴──────────────┴──────────────────┴──────────────┘

# 创建新数据库
[development] dev_mysql@localhost:3306/test_db > create database demo_db charset utf8mb4 collate utf8mb4_unicode_ci
✓ 数据库 'demo_db' 创建成功

# 切换数据库
[development] dev_mysql@localhost:3306/test_db > use demo_db
已切换到数据库: demo_db
[development] dev_mysql@localhost:3306/demo_db > 

# 列出所有表
[development] dev_mysql@localhost:3306/demo_db > show tables
当前数据库 'demo_db' 中没有表

# 创建表（使用交互式向导）
[development] dev_mysql@localhost:3306/demo_db > create table users
请输入表名: users
是否使用模板？[y/N]: y
请选择模板:
  1. 用户表（id, username, email, password, created_at）
  2. 日志表（id, action, user_id, created_at）
  3. 配置表（id, key, value, description）
  4. 自定义
请选择 [1-4]: 1

生成的SQL:
CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  email VARCHAR(100) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

是否执行？[Y/n]: y
✓ 表 'users' 创建成功

# 查看表结构
[development] dev_mysql@localhost:3306/demo_db > describe users
表结构: users
┌─────────────┬──────────────┬──────┬─────┬──────────────┬─────────────────┐
│ 列名        │ 数据类型     │ 空值 │ 键  │ 默认值       │ 注释            │
├─────────────┼──────────────┼─────┼─────┼──────────────┼─────────────────┤
│ id          │ INT          │ NO   │ PRI │ NULL         │ 自增主键        │
│ username    │ VARCHAR(50)  │ NO   │ UNI │ NULL         │ 用户名          │
│ email       │ VARCHAR(100) │ NO   │ UNI │ NULL         │ 邮箱            │
│ password    │ VARCHAR(255) │ NO   │     │ NULL         │ 密码            │
│ created_at  │ DATETIME     │ NO   │     │ CURRENT_TIME │ 创建时间        │
└─────────────┴──────────────┴──────┴─────┴──────────────┴─────────────────┘

索引:
- PRIMARY KEY (id)
- UNIQUE KEY (username)
- UNIQUE KEY (email)

# 修改表结构 - 添加列
[development] dev_mysql@localhost:3306/demo_db > alter table users add column status VARCHAR(20) DEFAULT 'active' AFTER email
✓ 列 'status' 已添加到表 'users'

# 修改表结构 - 添加索引
[development] dev_mysql@localhost:3306/demo_db > alter table users add index idx_status (status)
✓ 索引 'idx_status' 已添加到表 'users'

# 查看表统计信息
[development] dev_mysql@localhost:3306/demo_db > table stats users
表统计信息: users
  - 记录数: 0
  - 数据大小: 16 KB
  - 索引大小: 16 KB
  - 总大小: 32 KB
  - 存储引擎: InnoDB
  - 字符集: utf8mb4
  - 排序规则: utf8mb4_unicode_ci

# 删除表（带确认）
[development] dev_mysql@localhost:3306/demo_db > drop table temp_table
⚠️  警告：此操作将删除表 'temp_table' 及其所有数据！
表信息：
  - 记录数: 1,250
  - 数据大小: 2.5 MB
  - 索引大小: 0.8 MB
是否确认删除？[y/N]: y
✓ 表 'temp_table' 已删除

# 删除数据库（带确认）
[development] dev_mysql@localhost:3306/demo_db > drop database old_db
⚠️  警告：此操作将删除数据库 'old_db' 及其所有数据！
数据库信息：
  - 表数量: 15
  - 数据大小: 125.5 MB
  - 索引大小: 45.2 MB
是否确认删除？[y/N]: n
操作已取消
```

## 9. 非功能性需求

### 9.1 性能要求
- **查询性能**：
  - 查询结果展示支持大数据集的分页处理（默认每页20条，可配置）
  - 支持流式处理，避免一次性加载所有数据到内存
  - 查询结果缓存：相同查询在短时间内（5分钟）直接返回缓存结果
- **连接性能**：
  - 连接池管理：复用数据库连接，减少连接建立开销
  - 连接超时设置：默认10秒，可配置
  - 支持连接健康检查，自动移除失效连接
- **配置扫描性能**：
  - 配置文件扫描支持并行处理
  - 扫描结果缓存，避免重复扫描
  - 支持增量扫描，只扫描变更的配置文件
- **响应时间要求**：
  - 简单查询（<1000行）：响应时间 < 1秒
  - 复杂查询（<10000行）：响应时间 < 5秒
  - 配置扫描：< 10秒（100个配置文件以内）

### 9.2 安全性要求
- **敏感信息保护**：
  - 数据库密码等敏感信息使用AES-256加密存储
  - 密码不在日志中明文输出，使用`***`替代
  - 支持从环境变量读取密码，避免配置文件存储
  - 配置文件权限控制：仅用户可读写（600权限）
- **连接安全**：
  - 支持SSL/TLS加密连接
  - 支持证书验证
  - 生产环境连接需要二次确认
- **SQL注入防护**：
  - 参数化查询支持，避免SQL注入
  - SQL语句执行前进行基本的安全检查
- **访问控制**：
  - 支持基于角色的访问控制（可选功能）
  - 生产环境操作需要额外授权

### 9.3 可扩展性要求
- **数据库类型扩展**：
  - 支持通过插件方式添加新的数据库类型支持
  - 插件接口标准化，便于第三方开发
  - 支持数据库驱动动态加载
- **功能扩展**：
  - 模块化设计，支持功能插件
  - 支持自定义命令和脚本
  - 支持自定义结果格式化器
- **配置扩展**：
  - 配置文件支持自定义字段
  - 支持配置模板和预设

### 9.4 可用性要求
- **用户体验**：
  - 提供清晰、友好的命令行界面
  - 错误信息清晰易懂，提供修复建议
  - 支持命令自动补全（Tab键）
  - 支持命令历史记录（上下箭头键）
- **跨平台支持**：
  - 支持Windows、macOS、Linux操作系统
  - 统一的行为和界面体验
- **国际化支持**：
  - 支持中英文界面切换
  - 错误信息支持多语言
- **文档完整性**：
  - 提供完整的用户手册
  - 提供API文档（如果提供API）
  - 提供配置示例和最佳实践
  - 提供故障排除指南和常见问题解答

### 9.5 可靠性要求
- **错误恢复**：
  - 连接失败时自动重试（最多3次）
  - 事务失败时自动回滚
  - 配置文件损坏时自动备份恢复
- **数据一致性**：
  - 所有数据操作支持事务
  - 支持事务隔离级别设置
  - 确保配置文件的原子性更新
- **日志记录**：
  - 所有关键操作记录日志
  - 日志文件自动轮转，避免文件过大
  - 支持日志级别配置（DEBUG、INFO、WARNING、ERROR）
- **监控与告警**（可选）：
  - 支持操作监控和统计
  - 支持异常告警（如连接失败、执行超时）

### 9.6 维护性要求
- **代码质量**：
  - 代码遵循PEP 8规范
  - 完整的代码注释和文档字符串
  - 模块化设计，职责清晰
- **测试覆盖**：
  - 单元测试覆盖率 ≥ 80%
  - 集成测试覆盖主要功能场景
  - 持续集成（CI）支持
- **版本管理**：
  - 使用语义化版本号（Semantic Versioning）
  - 提供变更日志（CHANGELOG）
  - 支持版本回退

## 10. API说明（可选）

### 10.1 Python API
如果工具提供Python API供其他程序调用，需要提供以下接口：

```python
from db_tool import DatabaseTool, DatabaseConfig

# 创建配置
config = DatabaseConfig(
    alias="dev_mysql",
    type="mysql",
    host="localhost",
    port=3306,
    database="test_db",
    username="root",
    password="password"
)

# 创建工具实例
tool = DatabaseTool(config)

# 执行查询
results = tool.execute_query("SELECT * FROM users LIMIT 10")
print(results.to_dataframe())

# 执行更新
affected_rows = tool.execute_update("UPDATE users SET status='active' WHERE id=1")
print(f"影响 {affected_rows} 条记录")

# 获取表结构
schema = tool.get_table_schema("users")
print(schema)
```

### 10.2 REST API（可选）
如果提供Web界面，需要提供REST API：

- `GET /api/databases` - 获取所有数据库配置
- `POST /api/databases` - 添加数据库配置
- `GET /api/databases/{alias}/tables` - 获取表列表
- `POST /api/databases/{alias}/execute` - 执行SQL语句
- `GET /api/databases/{alias}/history` - 获取执行历史

## 11. 故障排除指南

### 11.1 常见问题
- **连接失败**：
  - 检查主机、端口、用户名、密码是否正确
  - 检查网络连接和防火墙设置
  - 检查数据库服务是否运行
  - 检查用户权限是否足够

- **配置扫描失败**：
  - 检查项目目录权限
  - 检查配置文件格式是否正确
  - 检查是否有足够的磁盘空间

- **SQL执行失败**：
  - 检查SQL语法是否正确
  - 检查数据库权限
  - 检查表结构是否匹配
  - 查看详细错误信息和建议

- **性能问题**：
  - 检查查询是否使用了索引
  - 检查数据量是否过大
  - 考虑使用分页查询
  - 检查连接池配置

### 11.2 日志查看
```bash
# 查看日志文件
tail -f ~/.db_tool/logs/db_tool.log

# 查看错误日志
grep ERROR ~/.db_tool/logs/db_tool.log

# 查看特定时间段的日志
grep "2026-01-27 10:" ~/.db_tool/logs/db_tool.log
```

### 11.3 配置文件修复
```bash
# 备份配置文件
cp ~/.db_tool/.db_tool_config.yaml ~/.db_tool/.db_tool_config.yaml.bak

# 验证配置文件格式
db-tool --validate-config

# 重置配置文件（谨慎使用）
db-tool --reset-config
```

## 12. 版本历史

### v1.0.0（初始版本）
- 数据库配置自动发现和手动管理
- 多数据源支持（MySQL、PostgreSQL、SQLite、Oracle等）
- 交互式SQL执行
- SQL脚本文件执行
- 查询结果表格化展示
- 错误处理和修复建议
- 数据导出功能（CSV、JSON、Excel）
- Schema浏览功能
- 执行历史记录

## 13. 总结

本文档详细描述了数据库操作工具的功能需求、技术实现要求、使用示例和非功能性需求。该工具旨在为开发人员提供一个统一、高效、安全的数据库操作平台，支持多种数据库类型，提供友好的交互界面和强大的功能。

### 核心特性
1. **智能配置管理**：自动发现项目中的数据库配置，支持多数据源管理和环境分组
2. **灵活的SQL执行**：支持交互式执行和脚本文件执行，提供语法检查和格式化功能
3. **完善的错误处理**：详细的错误报告和智能修复建议，确保数据安全
4. **丰富的功能扩展**：Schema浏览、数据导出/导入、备份/恢复等功能
5. **优秀的用户体验**：清晰的界面、友好的提示、完善的文档

### 技术亮点
- 模块化设计，易于扩展和维护
- 支持多种数据库类型，统一的操作接口
- 安全的敏感信息处理，加密存储密码
- 高性能的连接池管理和查询结果处理
- 完善的测试覆盖和错误处理机制

### 适用场景
- 开发环境数据库操作和调试
- 测试环境数据准备和验证
- 生产环境数据查询和监控（需谨慎使用）
- 数据库迁移和脚本执行
- 数据导出和分析

### 后续规划（可选）
- Web界面支持
- 可视化查询构建器
- 数据库性能监控和分析
- 数据对比和同步功能
- 团队协作和权限管理
- 更多数据库类型支持（MongoDB、Redis等）
