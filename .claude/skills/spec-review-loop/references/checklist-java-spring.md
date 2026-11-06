# 审查检查清单 · Java / Spring 栈插件

本文件为 spec-review-loop 的技术栈插件，仅在项目识别为 Java/Spring 时加载，覆盖维度 1、2。

---

## 维度 1：项目规范符合性

### 1.1 CLAUDE.md / AGENTS.md 规范遵守

| 检查项 | 检查方法 | 常见问题 | 修复建议 |
|--------|----------|----------|----------|
| Controller 无业务逻辑 | 检查 Controller 方法体是否包含 if/for/计算逻辑 | Controller 中直接做数据转换、条件判断 | 将逻辑移至 Service 层 |
| request/response 封装 | 检查 Controller 入参是否使用 Request 对象 | 直接传 entity 或基本类型参数 | 创建 Request/Response DTO |
| String 接收 Long | 检查 Request/Response 中主键字段类型 | 使用 Long 类型接收主键 | 改为 String 类型，Service 层转换 |
| 路径命名驼峰 | 检查 @GetMapping/@PostMapping 的 value 属性 | 使用下划线分隔或为空 | 改为驼峰命名，显式指定 value |
| LambdaQueryWrapper | 检查 Mapper 调用是否使用 Lambda 链式 | 使用字符串字段名构造条件 | 改为 Lambda 表达式引用 |
| 避免循环中 DB 操作 | 检查 for/while 循环内是否有 Mapper 调用 | 循环内逐条 insert/update | 改为批量操作 |
| 类级+方法级注释 | 检查类和方法是否有中文注释 | 缺少 @author 或方法说明 | 补充注释 |
| 日志中文 | 检查 log.info/error 的消息文本 | 日志使用英文描述 | 改为中文描述 |
| import 导包 | 检查代码中是否有全限定名称引用 | 如 `com.xxx.SomeClass` 直接使用 | 添加 import 语句 |
| @Schema 注解 | 检查 Request/Response 字段是否有 @Schema | 字段缺少 API 文档注解 | 补充 @Schema 注解 |
| 枚举不作为字段类型 | 检查 entity/request/response 中是否有枚举字段 | 使用枚举类作为 DTO 字段 | 改为 String/Integer |

### 1.2 接口设计规范

| 检查项 | 检查方法 | 常见问题 | 修复建议 |
|--------|----------|----------|----------|
| Mapping 注解显式 value | 检查 @GetMapping/@PostMapping 是否指定 value | 使用空注解 @GetMapping() | 显式指定 value 属性 |
| 禁止 @PathVariable | 检查是否使用 @PathVariable | 路径参数使用 /{id} 格式 | 改为 @RequestParam |
| Result 返回类型 | 检查 Controller 返回类型是否为 Result | 直接返回业务对象 | 包裹为 Result |
| @Tag/@Operation 注解 | 检查 Controller 和方法是否有 Swagger 注解 | 缺少 API 分组和操作说明 | 补充注解 |

---

## 维度 2：现有功能安全性

### 2.1 业务逻辑影响

| 检查项 | 检查方法 | 常见问题 | 修复建议 |
|--------|----------|----------|----------|
| 新增代码影响现有流程 | 对比修改前后的方法调用链 | 新增条件分支改变原有执行路径 | 确保新增逻辑仅在新增条件下触发 |
| 接口路径冲突 | 搜索同模块 Controller 的 Mapping 注解值 | 新接口路径与已有接口重复 | 修改路径或合并接口 |
| 公共方法签名变更 | 检查修改方法的参数列表和返回类型 | 增加参数或修改返回类型 | 保持向后兼容，新增重载方法 |
| Bean 注入冲突 | 检查同类型 Bean 是否有多个实现 | 新增同类型 Bean 导致注入歧义 | 使用 @Qualifier 或 @Primary |
| Mapper XML 影响 | 检查修改的 SQL 片段是否被其他方法引用 | 修改共用 SQL 片段影响其他调用方 | 新增独立 SQL 片段 |
| N+1 查询 | 检查循环内是否有单条查询调用 | 循环内调用 getById | 改为批量查询 |

### 2.2 配置影响

| 检查项 | 检查方法 | 常见问题 | 修复建议 |
|--------|----------|----------|----------|
| 新增配置影响其他模块 | 检查新增配置项的作用范围 | 全局配置影响所有模块 | 缩小配置作用范围 |
| 循环中调用远程接口 | 检查 for/while 内是否有 feign/http 调用 | 循环内逐条调用远程服务 | 改为批量接口或并行调用 |
