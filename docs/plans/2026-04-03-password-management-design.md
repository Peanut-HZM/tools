# 密码管理功能设计文档

**日期**: 2026-04-03
**状态**: 已批准

---

## 概述

为系统添加密码管理功能，包括后台管理员重置用户密码和用户自助修改密码两个场景。

---

## 功能需求

### 1. 后台管理员重置用户密码

**入口**: 后台管理 → 用户管理 → 操作列

**功能描述**:
- 管理员可以点击"重置密码"按钮为用户重置密码
- 提供两种重置模式：
  - **直接设置**: 管理员手动输入新密码
  - **随机生成**: 系统自动生成 12 位随机密码（大小写字母 + 数字 + 特殊字符）
- 重置成功后显示新密码供管理员复制
- 记录操作日志（管理员 ID、用户 ID、时间）

**UI 流程**:
```
用户列表 → 点击"重置密码" → 弹出模态框 → 选择模式 → 输入/生成密码 → 确认 → 显示新密码 → 完成
```

### 2. 用户自助修改密码

**入口** (两个):
- **快捷入口**: 右上角用户菜单 → "修改密码"选项
- **独立页面**: 后台管理左侧菜单 → "账户设置"

**功能描述**:
- 用户需要验证当前密码
- 新密码必须满足复杂度要求
- 需要二次确认新密码

**表单字段**:
- 当前密码（必填，验证）
- 新密码（必填，8-100 位，包含大小写字母 + 数字 + 特殊字符）
- 确认新密码（必填，必须与新密码一致）

### 3. 密码复杂度规则

| 规则 | 要求 |
|------|------|
| 长度 | 8-100 位 |
| 大写字母 | 必须包含至少 1 个 |
| 小写字母 | 必须包含至少 1 个 |
| 数字 | 必须包含至少 1 个 |
| 特殊字符 | 必须包含至少 1 个 (!@#$%^&* 等) |

---

## 技术设计

### 后端 API

#### 1. 管理员重置用户密码

```
POST /api/admin/users/{user_id}/reset-password
```

**请求体**:
```json
{
  "mode": "direct" | "random",
  "new_password": "string"  // mode=direct 时必填
}
```

**响应**:
```json
{
  "success": true,
  "new_password": "string",  // 返回新密码供管理员复制
  "message": "密码重置成功"
}
```

**权限**: 仅管理员可访问

#### 2. 用户修改密码

```
PUT /api/auth/password
```

**请求体**:
```json
{
  "old_password": "string",
  "new_password": "string"
}
```

**响应**:
```json
{
  "success": true,
  "message": "密码修改成功"
}
```

**权限**: 需要登录（JWT 认证）

### 数据模型

#### 新增请求模型

```python
class AdminPasswordReset(BaseModel):
    """管理员重置密码请求"""
    mode: str = Field(..., pattern="^(direct|random)$")
    new_password: Optional[str] = Field(None, min_length=8, max_length=100)

class UserPasswordChange(BaseModel):
    """用户修改密码请求"""
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
```

#### 密码验证工具函数

```python
def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    验证密码强度
    返回：(是否通过，错误信息)
    """
```

### 操作日志

记录管理员密码重置操作，可选择以下方案：

**方案 A**（推荐）: 新增 `password_reset_logs` 表
```sql
CREATE TABLE password_reset_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    reset_by_user_id VARCHAR(36) NOT NULL,
    reset_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET
);
```

**方案 B**: 仅通过日志文件记录

---

## 前端组件

### 1. 管理员重置密码模态框

```tsx
// components/Admin/PasswordResetModal.tsx
- 模式切换 Tab（直接设置 / 随机生成）
- 密码输入框（直接设置模式）
- 密码显示区域（随机生成模式）
- 复制按钮
- 确认/取消按钮
```

### 2. 用户修改密码模态框/页面

```tsx
// components/User/ChangePasswordModal.tsx
// components/User/AccountSettings.tsx
- 当前密码输入框
- 新密码输入框（带强度提示）
- 确认密码输入框
- 密码规则说明
- 提交/取消按钮
```

### 3. 用户菜单入口

```tsx
// 修改现有用户菜单组件
- 添加"修改密码"菜单项
```

---

## 错误处理

| 场景 | 错误信息 |
|------|----------|
| 旧密码错误 | "当前密码不正确" |
| 新密码与原密码相同 | "新密码不能与当前密码相同" |
| 密码复杂度不足 | "密码必须包含大小写字母、数字和特殊字符，长度 8-100 位" |
| 确认密码不一致 | "两次输入的密码不一致" |
| 用户不存在 | "用户不存在" |
| 无权限 | "无权执行此操作" |

---

## 测试计划

### 后端测试
- [ ] 密码强度验证函数单元测试
- [ ] 管理员重置密码 API 测试（直接设置模式）
- [ ] 管理员重置密码 API 测试（随机生成模式）
- [ ] 用户修改密码 API 测试
- [ ] 权限测试（普通用户无法调用管理员 API）
- [ ] 旧密码验证测试

### 前端测试
- [ ] 重置密码模态框 UI 测试
- [ ] 修改密码表单验证测试
- [ ] 密码强度实时校验测试
- [ ] 用户菜单入口测试
- [ ] 账户设置页面测试

---

## 实现优先级

1. 后端密码强度验证函数
2. 后端管理员重置密码 API
3. 后端用户修改密码 API
4. 前端管理员重置密码模态框
5. 前端用户修改密码功能（模态框 + 页面）
6. 前端用户菜单入口
7. 集成测试与验证
