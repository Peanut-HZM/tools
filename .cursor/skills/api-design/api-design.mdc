---
name: api-design-rules
description: 接口设计规范（路由、参数、命名、对象流转）
---

# 接口设计规范（Controller / Service 必须遵守）

## 接口定义与对象流转

- **入参**：Controller 入参必须使用 `Request`/DTO 封装后传递到 Service
  - 禁止将一堆原始参数散落在方法签名里
- **出参**：Service 返回 `Response` 对象，Controller 仅负责返回项目已有的 `Result`（或项目统一返回体）
- **命名一致**：Service 方法命名必须与 Controller 的接口方法名称保持一致（便于追踪与搜索）
- **禁止在 Controller 转换对象**：Controller 层禁止做 `entity/domain` 与 `request/response` 的转换
  - 转换应在 Service（或项目既有的转换/Assembler 层）完成

## 方法签名与参数数量

- **参数不超过 2 个**：Controller/Service 的业务方法参数不允许超过 2 个
  - 超过时必须封装到 `Request`/DTO
  - 允许的例外：框架必需参数（例如 `HttpServletRequest/HttpServletResponse`、文件上传 `MultipartFile`）不计入业务参数数量，但仍应尽量封装业务字段

## 路由与注解（强制校验点）

- **禁止 `/api` 前缀**：Controller 层路由禁止添加 `/api` 前缀
- **Mapping 必须显式指定 value**：所有 `@GetMapping/@PostMapping/@PutMapping/@DeleteMapping/...` 必须明确指定 `value`，禁止空注解
- **Mapping value 不允许为空/重复**：同一个 Controller（以及同模块范围内）必须保证 `value` 语义清晰且不重复
- **路径命名**：路径必须语义明确，避免通用词（如 `/get`、`/list`）；层级建议不超过 3 级
- **禁止 PathVariable**：禁止使用 `/{param}` 形式的路径参数，避免网关路由冲突
  - 路径参数统一使用 `@RequestParam`（或放入 `Request` 的 body）而非 `@PathVariable`
- **批量操作**：批量接口必须使用专门 `Request` 封装参数，禁止直接接收 `List` 作为入参
- **更新操作入参**：更新必须使用包含 `ID + 其他业务字段` 的 `Request`，禁止只传一个 `id` 再额外散落其他参数
- **用户相关接口**：禁止直接传 `userId`；后端必须从 token/上下文获取当前登录用户信息
