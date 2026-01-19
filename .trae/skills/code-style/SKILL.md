---
name: code-style-rules
description: 编码产出规范（代码风格、注释、导包、DTO、ID生成）
---

# 编码产出规范（必须）

## 注释规范

- **新增/修改的业务类与对外方法必须补齐类级与方法级注释**
  - 类级注释：说明用途、主要职责
  - 方法级注释：说明用途、关键入参/返回、边界条件

## 导包规范

- **必须使用 `import`**；禁止使用全限定类名（FQN）直接引用
  - ❌ 错误示例：`com.tpehr.budget.annperbonus.domain.AnnperBonusOrgCalcResult result = ...`
  - ✅ 正确示例：先 `import com.tpehr.budget.annperbonus.domain.AnnperBonusOrgCalcResult;`，再使用 `AnnperBonusOrgCalcResult result = ...`

## DTO 字段类型规范

- **禁止在 `entity/request/response/dto` 中直接使用 `enum` 作为字段类型**
- **使用 `String/Integer` 等代码值字段 + 注释/字典映射**
- 必要时在转换层做枚举转换

## ID 生成规范

- **新增数据的 `id` 必须使用项目已存在的雪花算法生成器**
- **禁止自行引入 `UUID.randomUUID()` 作为主键策略**（除非项目已有明确约定）
