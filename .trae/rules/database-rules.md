# 数据库规范

1. 所有数据表必须包含字段id,create_time,create_by,update_time,update_by,deleted
2. 删除操作优先使用逻辑删除，添加deleted字段标识
3. 数据库字段命名使用下划线分隔，Java实体类使用驼峰命名
4. 优先使用LambdaQueryWrapper构造条件查询，避免硬编码字段名
5. 使用Lambda表达式引用实体类属性，提高代码可维护性和类型安全
6. 复杂查询条件应使用LambdaQueryWrapper的链式调用，保持代码清晰
7. 避免在查询条件中使用字符串字段名，防止字段名变更导致的运行时错误
