# 接口设计规范

1. Controller层接口定义要完整：
    - 入参使用request封装传递到service层
    - service层的方法命名与controller层定义的接口的方法名称保持一致
    - 出参使用response封装由service层传递到controller层
    - 禁止在controller层做entity/domain对象与request/response的转换
    - request和response的字段都要有io.swagger.v3.oas.annotations.media.Schema注解对字段进行说明
    - 使用项目已有的Result做接口返回
    - 要加上io.swagger.v3.oas.annotations的常用注解如@Tag,@Operation
    - 所有接口入参里面的主键id使用String接收,再进行转换,避免精度丢失导致的问题
2. 接口和方法参数不允许超过两个，超过时使用request或DTO对象封装
3. Controller层路由禁止添加/api前缀
4. Controller层接口的Mapping注解value属性值不允许重复且不允许为空，必须明确指定value属性值且使用驼峰结构命名，避免使用下划线分隔符。所有接口注解必须显式指定value属性，如@GetMapping(value = "/page")、@PostMapping(value = "/create")等，禁止使用@GetMapping()或@PostMapping等空注解形式
5. 用户相关接口禁止直接传递用户id，需要后端根据token获取当前登录用户信息
6. 禁止使用/{param}格式的路径参数，避免网关路由冲突和分发错误
7. 路径参数统一使用@RequestParam而非@PathVariable，确保网关分发准确性
8. 接口路径命名应具有明确的语义，避免使用通用词汇如/get、/list等
9. 批量操作接口应使用专门的Request对象封装参数，而非直接传递List
10. 接口路径应避免层级过深，建议不超过3级路径结构
11. 更新操作应直接使用封装了ID和其他数据的Request对象，而不是单独传递ID参数。Service层方法应保持参数简洁，业务逻辑所需数据应全部包含在Request对象中
12. Controller层接口应保持简洁，避免为特定字段创建独立的更新方法（如updateStatus等），应只保留一个通用的update方法，具体的业务逻辑在Service层实现
13. Service层在执行更新操作时，应对每个字段进行空值检查，只更新非空字段，避免空字段覆盖原有值，确保数据完整性
14. Controller层应避免创建多个特定条件的查询接口，只保留一个分页查询方法，通过在请求对象中包含所有可查询字段来支持不同的查询需求
15. 分页查询接口应支持模糊查询和精确查询，通过在Service层根据字段类型和业务需求判断查询方式
16. request和response中不能使用Long类型,因为Long类型在前端传递时会丢失精度,必须使用String类型接收,在service层进行转换
