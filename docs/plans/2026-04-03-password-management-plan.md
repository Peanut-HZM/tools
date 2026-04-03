# 密码管理功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现完整的密码管理功能，包括后台管理员重置用户密码和用户自助修改密码

**Architecture:** 
- 后端：在 auth_service.py 中添加密码验证和重置方法，在 admin.py 和 auth.py 中添加对应 API
- 前端：在 UserManagement 组件添加重置密码模态框，在用户菜单添加修改密码入口，创建账户设置页面
- 数据库：创建 password_reset_logs 表记录管理员密码重置操作

**Tech Stack:** Python 3.12, FastAPI, React 18, TypeScript, PostgreSQL

---

## 任务列表

### Task 1: 创建密码重置日志数据库表

**Files:**
- Create: `backend/app/models/password_log_models.py`
- Modify: `backend/app/config/database.py` (创建表迁移)

**Step 1: 创建 SQLAlchemy 模型**

```python
# backend/app/models/password_log_models.py
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import INET
from datetime import datetime
from app.models.base import Base

class PasswordResetLog(Base):
    __tablename__ = "password_reset_logs"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    reset_by_user_id = Column(String(36), nullable=False)
    reset_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(INET)
```

**Step 2: 创建迁移脚本**

```python
# backend/alembic/versions/xxxx_add_password_reset_logs.py
def upgrade():
    op.execute("""
        CREATE TABLE password_reset_logs (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            reset_by_user_id VARCHAR(36) NOT NULL,
            reset_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address INET
        );
        CREATE INDEX idx_password_reset_logs_user_id ON password_reset_logs(user_id);
    """)

def downgrade():
    op.drop_table("password_reset_logs")
```

**Step 3: 运行迁移**

```bash
cd backend
alembic upgrade head
```

Expected: Table created successfully

---

### Task 2: 实现密码强度验证工具函数

**Files:**
- Create: `backend/app/utils/password_utils.py`

**Step 1: 创建密码验证工具函数**

```python
# backend/app/utils/password_utils.py
import re
import string
import random
from typing import Tuple


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    验证密码强度
    
    规则:
    - 长度 8-100 位
    - 至少包含 1 个大写字母
    - 至少包含 1 个小写字母
    - 至少包含 1 个数字
    - 至少包含 1 个特殊字符
    
    返回：(是否通过，错误信息)
    """
    if not password:
        return False, "密码不能为空"
    
    if len(password) < 8 or len(password) > 100:
        return False, "密码长度必须在 8-100 位之间"
    
    if not re.search(r'[A-Z]', password):
        return False, "密码必须包含至少 1 个大写字母"
    
    if not re.search(r'[a-z]', password):
        return False, "密码必须包含至少 1 个小写字母"
    
    if not re.search(r'\d', password):
        return False, "密码必须包含至少 1 个数字"
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?`~]', password):
        return False, "密码必须包含至少 1 个特殊字符"
    
    return True, ""


def generate_random_password(length: int = 12) -> str:
    """
    生成随机密码
    
    规则:
    - 默认 12 位
    - 必须包含大小写字母、数字、特殊字符
    """
    if length < 8:
        length = 8
    
    # 确保每种字符至少有一个
    password = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice('!@#$%^&*()_+-='),
    ]
    
    # 随机填充剩余位数
    all_chars = string.ascii_letters + string.digits + '!@#$%^&*()_+-='
    password.extend(random.choice(all_chars) for _ in range(length - 4))
    
    # 打乱顺序
    random.shuffle(password)
    
    return ''.join(password)
```

**Step 2: 创建单元测试**

```python
# backend/tests/utils/test_password_utils.py
from app.utils.password_utils import validate_password_strength, generate_random_password


def test_validate_password_strength_valid():
    """测试有效密码"""
    is_valid, message = validate_password_strength("Test123!@#")
    assert is_valid
    assert message == ""


def test_validate_password_strength_too_short():
    """测试密码过短"""
    is_valid, message = validate_password_strength("Test1!")
    assert not is_valid
    assert "8-100" in message


def test_validate_password_strength_no_uppercase():
    """测试缺少大写字母"""
    is_valid, message = validate_password_strength("test123!@#")
    assert not is_valid
    assert "大写字母" in message


def test_validate_password_strength_no_lowercase():
    """测试缺少小写字母"""
    is_valid, message = validate_password_strength("TEST123!@#")
    assert not is_valid
    assert "小写字母" in message


def test_validate_password_strength_no_digit():
    """测试缺少数字"""
    is_valid, message = validate_password_strength("Testabc!@#")
    assert not is_valid
    assert "数字" in message


def test_validate_password_strength_no_special():
    """测试缺少特殊字符"""
    is_valid, message = validate_password_strength("Test12345")
    assert not is_valid
    assert "特殊字符" in message


def test_generate_random_password_length():
    """测试随机密码长度"""
    password = generate_random_password()
    assert len(password) == 12
    
    password = generate_random_password(16)
    assert len(password) == 16


def test_generate_random_password_strength():
    """测试随机密码强度"""
    password = generate_random_password()
    is_valid, _ = validate_password_strength(password)
    assert is_valid
```

**Step 3: 运行测试**

```bash
cd backend
pytest tests/utils/test_password_utils.py -v
```

Expected: All tests pass

---

### Task 3: 添加密码管理数据模型

**Files:**
- Modify: `backend/app/models/auth_models.py`

**Step 1: 添加请求模型**

```python
# backend/app/models/auth_models.py - 在文件末尾添加

class AdminPasswordReset(BaseModel):
    """管理员重置密码请求"""
    mode: str = Field(..., pattern="^(direct|random)$", description="重置模式：direct=直接设置，random=随机生成")
    new_password: Optional[str] = Field(None, min_length=8, max_length=100, description="新密码（mode=direct 时必填）")


class AdminPasswordResetResponse(BaseModel):
    """管理员重置密码响应"""
    success: bool
    new_password: str
    message: str


class UserPasswordChange(BaseModel):
    """用户修改密码请求"""
    old_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, max_length=100, description="新密码")


class UserPasswordChangeResponse(BaseModel):
    """用户修改密码响应"""
    success: bool
    message: str
```

---

### Task 4: 实现密码管理服务方法

**Files:**
- Modify: `backend/app/services/auth_service.py`

**Step 1: 导入密码工具**

```python
# backend/app/services/auth_service.py - 在文件开头添加
from app.utils.password_utils import validate_password_strength, generate_random_password
import uuid
```

**Step 2: 添加管理员重置密码方法**

```python
# backend/app/services/auth_service.py - 添加方法

    def admin_reset_password(self, user_id: str, mode: str, new_password: Optional[str], 
                             reset_by_user_id: str, ip_address: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        管理员重置用户密码
        
        Args:
            user_id: 目标用户 ID
            mode: "direct" 或 "random"
            new_password: 新密码（mode=direct 时必填）
            reset_by_user_id: 执行重置的管理员用户 ID
            ip_address: 请求 IP 地址
            
        Returns:
            (success, message, actual_password)
            - success: 是否成功
            - message: 错误信息（成功时为空）
            - actual_password: 实际设置的新密码
        """
        # 验证密码强度
        if mode == "direct":
            if not new_password:
                return False, "新密码不能为空", ""
            is_valid, error_msg = validate_password_strength(new_password)
            if not is_valid:
                return False, error_msg, ""
            actual_password = new_password
        else:  # mode == "random"
            actual_password = generate_random_password(12)
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 检查用户是否存在
                cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                if not cursor.fetchone():
                    return False, "用户不存在", ""
                
                # 更新密码
                hashed_password = self._hash_password(actual_password)
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE user_id = %s",
                    (hashed_password, user_id)
                )
                
                # 记录日志
                cursor.execute(
                    """INSERT INTO password_reset_logs (id, user_id, reset_by_user_id, ip_address)
                       VALUES (%s, %s, %s, %s)""",
                    (str(uuid.uuid4()), user_id, reset_by_user_id, ip_address)
                )
                
                conn.commit()
                return True, "", actual_password
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error resetting password: {e}")
            return False, f"重置失败：{str(e)}", ""
        finally:
            conn.close()
```

**Step 3: 添加用户修改密码方法**

```python
# backend/app/services/auth_service.py - 添加方法

    def change_password(self, user_id: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        用户修改密码
        
        Args:
            user_id: 用户 ID
            old_password: 当前密码
            new_password: 新密码
            
        Returns:
            (success, message)
        """
        # 验证新密码强度
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            return False, error_msg
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 获取用户
                cursor.execute(
                    "SELECT password_hash FROM users WHERE user_id = %s",
                    (user_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return False, "用户不存在"
                
                # 验证旧密码
                if not self._verify_password(old_password, row['password_hash']):
                    return False, "当前密码不正确"
                
                # 检查新旧密码是否相同
                if self._verify_password(new_password, row['password_hash']):
                    return False, "新密码不能与当前密码相同"
                
                # 更新密码
                hashed_password = self._hash_password(new_password)
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE user_id = %s",
                    (hashed_password, user_id)
                )
                
                conn.commit()
                return True, "密码修改成功"
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error changing password: {e}")
            return False, f"修改失败：{str(e)}"
        finally:
            conn.close()
```

**Step 4: 创建服务层测试**

```python
# backend/tests/services/test_auth_service_password.py
import pytest
from app.services.auth_service import get_auth_service


class TestPasswordReset:
    """测试管理员重置密码"""
    
    def test_admin_reset_password_direct_mode(self, admin_user, db_connection):
        """测试直接设置模式"""
        service = get_auth_service()
        success, message, password = service.admin_reset_password(
            user_id=admin_user.user_id,
            mode="direct",
            new_password="NewTest123!@#",
            reset_by_user_id="test-admin-id",
            ip_address="127.0.0.1"
        )
        assert success
        assert password == "NewTest123!@#"
    
    def test_admin_reset_password_random_mode(self, admin_user, db_connection):
        """测试随机生成模式"""
        service = get_auth_service()
        success, message, password = service.admin_reset_password(
            user_id=admin_user.user_id,
            mode="random",
            new_password=None,
            reset_by_user_id="test-admin-id",
            ip_address="127.0.0.1"
        )
        assert success
        assert len(password) == 12
        # 验证密码强度
        from app.utils.password_utils import validate_password_strength
        is_valid, _ = validate_password_strength(password)
        assert is_valid
    
    def test_admin_reset_password_invalid(self, admin_user, db_connection):
        """测试无效密码"""
        service = get_auth_service()
        success, message, password = service.admin_reset_password(
            user_id=admin_user.user_id,
            mode="direct",
            new_password="weak",  # 太短
            reset_by_user_id="test-admin-id",
            ip_address="127.0.0.1"
        )
        assert not success
        assert "8-100" in message


class TestPasswordChange:
    """测试用户修改密码"""
    
    def test_change_password_success(self, test_user, db_connection):
        """测试成功修改密码"""
        service = get_auth_service()
        success, message = service.change_password(
            user_id=test_user.user_id,
            old_password="Test123!@#",  # 初始密码
            new_password="NewTest456!@#"
        )
        assert success
        assert "成功" in message
    
    def test_change_password_wrong_old(self, test_user, db_connection):
        """测试旧密码错误"""
        service = get_auth_service()
        success, message = service.change_password(
            user_id=test_user.user_id,
            old_password="WrongPassword123!",
            new_password="NewTest456!@#"
        )
        assert not success
        assert "不正确" in message
    
    def test_change_password_same_as_old(self, test_user, db_connection):
        """测试新旧密码相同"""
        service = get_auth_service()
        success, message = service.change_password(
            user_id=test_user.user_id,
            old_password="Test123!@#",
            new_password="Test123!@#"
        )
        assert not success
        assert "不能与当前密码相同" in message
    
    def test_change_password_weak_new(self, test_user, db_connection):
        """测试新密码强度不足"""
        service = get_auth_service()
        success, message = service.change_password(
            user_id=test_user.user_id,
            old_password="Test123!@#",
            new_password="weak"
        )
        assert not success
        assert "8-100" in message or "必须包含" in message
```

**Step 5: 运行测试**

```bash
cd backend
pytest tests/services/test_auth_service_password.py -v
```

Expected: All tests pass

---

### Task 5: 实现管理员重置密码 API

**Files:**
- Modify: `backend/app/routes/admin.py`

**Step 1: 添加导入**

```python
# backend/app/routes/admin.py - 添加导入
from app.models.auth_models import AdminPasswordReset, AdminPasswordResetResponse
```

**Step 2: 添加 API 端点**

```python
# backend/app/routes/admin.py - 添加路由

@router.post("/users/{user_id}/reset-password", response_model=AdminPasswordResetResponse)
async def admin_reset_password(
    user_id: str,
    request: AdminPasswordReset,
    current_user: UserResponse = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service),
    request_obj: Request = None
):
    """
    管理员重置用户密码
    
    - **mode**: 重置模式 (direct=直接设置，random=随机生成)
    - **new_password**: 新密码（mode=direct 时必填）
    """
    # 获取 IP 地址
    ip_address = None
    if request_obj:
        ip_address = request_obj.client.host if request_obj.client else None
    
    success, message, new_password = auth_service.admin_reset_password(
        user_id=user_id,
        mode=request.mode,
        new_password=request.new_password,
        reset_by_user_id=current_user.user_id,
        ip_address=ip_address
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "success": True,
        "new_password": new_password,
        "message": "密码重置成功"
    }
```

---

### Task 6: 实现用户修改密码 API

**Files:**
- Modify: `backend/app/routes/auth.py`

**Step 1: 添加导入**

```python
# backend/app/routes/auth.py - 添加导入
from app.models.auth_models import UserPasswordChange, UserPasswordChangeResponse
```

**Step 2: 添加 API 端点**

```python
# backend/app/routes/auth.py - 添加路由

@router.put("/password", response_model=UserPasswordChangeResponse)
async def change_password(
    request: UserPasswordChange,
    current_user_id: str = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    用户修改密码
    
    - **old_password**: 当前密码
    - **new_password**: 新密码
    """
    success, message = auth_service.change_password(
        user_id=current_user_id,
        old_password=request.old_password,
        new_password=request.new_password
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "success": True,
        "message": message
    }
```

---

### Task 7: 创建管理员重置密码模态框组件

**Files:**
- Create: `frontend/src/components/Admin/PasswordResetModal.tsx`

**Step 1: 创建组件**

```tsx
// frontend/src/components/Admin/PasswordResetModal.tsx
import { useState } from 'react';
import { resetUserPassword } from '../../api/adminApi';
import { useToast } from '../../hooks/useToast';

interface PasswordResetModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId: string;
  username: string;
  onSuccess?: () => void;
}

type ResetMode = 'direct' | 'random';

export default function PasswordResetModal({
  isOpen,
  onClose,
  userId,
  username,
  onSuccess,
}: PasswordResetModalProps) {
  const [mode, setMode] = useState<ResetMode>('direct');
  const [newPassword, setNewPassword] = useState('');
  const [generatedPassword, setGeneratedPassword] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { success, error } = useToast();

  const handleReset = async () => {
    if (mode === 'direct' && !newPassword.trim()) {
      error('请输入新密码');
      return;
    }

    setLoading(true);
    try {
      const result = await resetUserPassword(userId, mode, mode === 'direct' ? newPassword : undefined);
      setGeneratedPassword(result.new_password);
      success('密码重置成功');
      onSuccess?.();
    } catch (e) {
      error(e instanceof Error ? e.message : '密码重置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (generatedPassword) {
      navigator.clipboard.writeText(generatedPassword);
      success('密码已复制到剪贴板');
    }
  };

  const handleClose = () => {
    setGeneratedPassword(null);
    setNewPassword('');
    setMode('direct');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 p-6 rounded-lg w-full max-w-md border border-slate-700">
        {!generatedPassword ? (
          <>
            <h3 className="text-xl font-bold text-white mb-4">
              重置密码 - {username}
            </h3>

            {/* 模式切换 */}
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setMode('direct')}
                className={`flex-1 px-4 py-2 rounded text-sm transition-colors ${
                  mode === 'direct'
                    ? 'bg-cyan-500 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                直接设置
              </button>
              <button
                onClick={() => setMode('random')}
                className={`flex-1 px-4 py-2 rounded text-sm transition-colors ${
                  mode === 'random'
                    ? 'bg-cyan-500 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                随机生成
              </button>
            </div>

            {/* 密码输入 */}
            {mode === 'direct' && (
              <div className="mb-4">
                <label className="block text-slate-300 mb-2 text-sm">新密码</label>
                <input
                  type="text"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="输入新密码（8-100 位，包含大小写字母 + 数字 + 特殊字符）"
                  className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:border-cyan-500 outline-none"
                />
                <p className="text-xs text-slate-500 mt-1">
                  密码必须包含：大写字母、小写字母、数字、特殊字符
                </p>
              </div>
            )}

            {mode === 'random' && (
              <div className="mb-4 p-4 bg-slate-700/50 rounded text-sm text-slate-300">
                <i className="fa-solid fa-info-circle mr-2"></i>
                系统将自动生成一个 12 位的随机密码，包含大小写字母、数字和特殊字符。
              </div>
            )}

            <div className="flex justify-end gap-3">
              <button
                onClick={handleClose}
                className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleReset}
                disabled={loading}
                className={`px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded transition-colors ${
                  loading ? 'opacity-50 cursor-not-allowed' : ''
                }`}
              >
                {loading ? (
                  <>
                    <i className="fas fa-spinner fa-spin mr-2"></i>
                    处理中...
                  </>
                ) : (
                  '确认重置'
                )}
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="w-16 h-16 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <i className="fa-solid fa-check text-2xl"></i>
            </div>
            <h3 className="text-xl font-bold text-white mb-2 text-center">密码重置成功</h3>
            <p className="text-slate-400 mb-4 text-center">
              请复制下方生成的新密码并发送给用户
            </p>

            <div className="bg-slate-900 p-4 rounded mb-4 select-all font-mono text-cyan-400 text-lg break-all border border-slate-700">
              {generatedPassword}
            </div>

            <div className="flex gap-3 mb-4">
              <button
                onClick={handleCopy}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors"
              >
                <i className="fa-solid fa-copy mr-2"></i>
                复制密码
              </button>
            </div>

            <button
              onClick={handleClose}
              className="w-full px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded transition-colors"
            >
              完成
            </button>
          </>
        )}
      </div>
    </div>
  );
}
```

---

### Task 8: 添加管理员重置密码 API 客户端

**Files:**
- Modify: `frontend/src/api/adminApi.ts`

**Step 1: 添加类型和函数**

```typescript
// frontend/src/api/adminApi.ts - 添加

export interface PasswordResetResponse {
  success: boolean;
  new_password: string;
  message: string;
}

export async function resetUserPassword(
  userId: string,
  mode: 'direct' | 'random',
  newPassword?: string
): Promise<PasswordResetResponse> {
  const response = await fetch(`${API_BASE_URL}/users/${userId}/reset-password`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders() as Record<string, string>,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      mode,
      new_password: newPassword
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '密码重置失败');
  }
  return response.json();
}
```

---

### Task 9: 在用户管理页面集成重置密码功能

**Files:**
- Modify: `frontend/src/components/Admin/UserManagement.tsx`

**Step 1: 导入模态框组件**

```tsx
// frontend/src/components/Admin/UserManagement.tsx - 添加导入
import PasswordResetModal from './PasswordResetModal';
```

**Step 2: 添加状态**

```tsx
// frontend/src/components/Admin/UserManagement.tsx - 添加状态
const [resetModalOpen, setResetModalOpen] = useState(false);
const [selectedUserForReset, setSelectedUserForReset] = useState<{ id: string; username: string } | null>(null);
```

**Step 3: 添加处理函数**

```tsx
// frontend/src/components/Admin/UserManagement.tsx - 添加函数
const handleOpenResetModal = (userId: string, username: string) => {
  setSelectedUserForReset({ id: userId, username });
  setResetModalOpen(true);
};
```

**Step 4: 在表格操作列添加按钮**

```tsx
// frontend/src/components/Admin/UserManagement.tsx - 修改操作列
<td className="px-6 py-4">
  {!batchMode && (
    <div className="flex gap-2">
      <button
        onClick={() => handleOpenResetModal(user.user_id, user.username)}
        className="text-orange-400 hover:text-orange-300 transition-colors text-sm"
        title="重置密码"
      >
        <i className="fa-solid fa-key"></i>
      </button>
      <button
        onClick={() => handleDelete(user.user_id)}
        className="text-red-400 hover:text-red-300 transition-colors text-sm"
      >
        删除
      </button>
    </div>
  )}
  {batchMode && (
    <span className="text-slate-500 text-xs">批量操作中...</span>
  )}
</td>
```

**Step 5: 在组件末尾添加模态框**

```tsx
// frontend/src/components/Admin/UserManagement.tsx - 在组件末尾添加
{/* Password Reset Modal */}
{selectedUserForReset && (
  <PasswordResetModal
    isOpen={resetModalOpen}
    onClose={() => {
      setResetModalOpen(false);
      setSelectedUserForReset(null);
    }}
    userId={selectedUserForReset.id}
    username={selectedUserForReset.username}
    onSuccess={() => {
      fetchUsers();
    }}
  />
)}
```

---

### Task 10: 创建用户修改密码组件

**Files:**
- Create: `frontend/src/components/User/ChangePasswordModal.tsx`
- Create: `frontend/src/components/User/AccountSettings.tsx`

**Step 1: 创建修改密码模态框**

```tsx
// frontend/src/components/User/ChangePasswordModal.tsx
import { useState } from 'react';
import { changePassword } from '../../api/authApi';
import { useToast } from '../../hooks/useToast';

interface ChangePasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export default function ChangePasswordModal({
  isOpen,
  onClose,
  onSuccess,
}: ChangePasswordModalProps) {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { success, error } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      error('两次输入的新密码不一致');
      return;
    }

    if (newPassword === oldPassword) {
      error('新密码不能与当前密码相同');
      return;
    }

    setLoading(true);
    try {
      await changePassword(oldPassword, newPassword);
      success('密码修改成功，请重新登录');
      onSuccess?.();
      // 退出登录，要求重新登录
      localStorage.removeItem('auth_token');
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    } catch (e) {
      error(e instanceof Error ? e.message : '密码修改失败');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setOldPassword('');
    setNewPassword('');
    setConfirmPassword('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 p-6 rounded-lg w-full max-w-md border border-slate-700">
        <h3 className="text-xl font-bold text-white mb-4">修改密码</h3>
        
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-slate-300 mb-2 text-sm">当前密码</label>
            <input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              required
              className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:border-cyan-500 outline-none"
            />
          </div>

          <div className="mb-4">
            <label className="block text-slate-300 mb-2 text-sm">新密码</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              placeholder="8-100 位，包含大小写字母 + 数字 + 特殊字符"
              className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:border-cyan-500 outline-none"
            />
          </div>

          <div className="mb-4">
            <label className="block text-slate-300 mb-2 text-sm">确认新密码</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:border-cyan-500 outline-none"
            />
          </div>

          <div className="mb-4 p-3 bg-slate-700/50 rounded text-xs text-slate-400">
            <i className="fa-solid fa-circle-info mr-2"></i>
            密码要求：
            <ul className="mt-1 space-y-1">
              <li>• 长度 8-100 位</li>
              <li>• 至少包含 1 个大写字母</li>
              <li>• 至少包含 1 个小写字母</li>
              <li>• 至少包含 1 个数字</li>
              <li>• 至少包含 1 个特殊字符 (!@#$%^&* 等)</li>
            </ul>
          </div>

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className={`px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded transition-colors ${
                loading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {loading ? (
                <>
                  <i className="fas fa-spinner fa-spin mr-2"></i>
                  处理中...
                </>
              ) : (
                '确认修改'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

---

### Task 11: 创建账户设置页面

**Files:**
- Create: `frontend/src/components/User/AccountSettings.tsx`

**Step 1: 创建账户设置页面组件**

```tsx
// frontend/src/components/User/AccountSettings.tsx
import { useState } from 'react';
import { changePassword, UserResponse } from '../../api/authApi';
import { useToast } from '../../hooks/useToast';

export default function AccountSettings() {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { success, error } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      error('两次输入的新密码不一致');
      return;
    }

    if (newPassword === oldPassword) {
      error('新密码不能与当前密码相同');
      return;
    }

    setLoading(true);
    try {
      await changePassword(oldPassword, newPassword);
      success('密码修改成功，请重新登录');
      // 清空表单
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      // 退出登录
      localStorage.removeItem('auth_token');
      setTimeout(() => {
        window.location.href = '/login';
      }, 1500);
    } catch (e) {
      error(e instanceof Error ? e.message : '密码修改失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold text-white mb-6">账户设置</h2>

      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-xl font-semibold text-white mb-4">
          <i className="fa-solid fa-lock mr-2"></i>
          修改密码
        </h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-slate-300 mb-2 text-sm">当前密码</label>
            <input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              required
              className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:border-cyan-500 outline-none"
            />
          </div>

          <div>
            <label className="block text-slate-300 mb-2 text-sm">新密码</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              placeholder="8-100 位，包含大小写字母 + 数字 + 特殊字符"
              className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:border-cyan-500 outline-none"
            />
          </div>

          <div>
            <label className="block text-slate-300 mb-2 text-sm">确认新密码</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:border-cyan-500 outline-none"
            />
          </div>

          <div className="p-4 bg-slate-700/50 rounded text-sm text-slate-400">
            <i className="fa-solid fa-circle-info mr-2"></i>
            <strong>密码要求：</strong>
            <ul className="mt-2 space-y-1">
              <li>• 长度 8-100 位</li>
              <li>• 至少包含 1 个大写字母 (A-Z)</li>
              <li>• 至少包含 1 个小写字母 (a-z)</li>
              <li>• 至少包含 1 个数字 (0-9)</li>
              <li>• 至少包含 1 个特殊字符 (!@#$%^&* 等)</li>
            </ul>
          </div>

          <div className="flex justify-end pt-4">
            <button
              type="submit"
              disabled={loading}
              className={`px-6 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg transition-colors ${
                loading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {loading ? (
                <>
                  <i className="fas fa-spinner fa-spin mr-2"></i>
                  处理中...
                </>
              ) : (
                <>
                  <i className="fa-solid fa-check mr-2"></i>
                  确认修改
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

---

### Task 12: 添加用户修改密码 API 客户端

**Files:**
- Modify: `frontend/src/api/authApi.ts`

**Step 1: 添加函数**

```typescript
// frontend/src/api/authApi.ts - 添加

export async function changePassword(oldPassword: string, newPassword: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE_URL}/password`, {
    method: 'PUT',
    headers: {
      ...getAuthHeaders() as Record<string, string>,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      old_password: oldPassword,
      new_password: newPassword
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '密码修改失败');
  }
  return response.json();
}
```

---

### Task 13: 在用户菜单添加修改密码入口

**Files:**
- Modify: 找到并修改用户菜单组件（通常在 Header 或 Layout 组件中）

**Step 1: 找到用户菜单组件位置**

```bash
# 搜索用户菜单相关组件
grep -r "退出\|logout\|user.*menu" frontend/src/components --include="*.tsx" | head -10
```

**Step 2: 添加修改密码菜单项和模态框**

```tsx
// 在用户菜单组件中（需要找到实际文件）
import ChangePasswordModal from './User/ChangePasswordModal';

// 添加状态
const [changePasswordModalOpen, setChangePasswordModalOpen] = useState(false);

// 在用户菜单下拉列表中添加菜单项
<button
  onClick={() => setChangePasswordModalOpen(true)}
  className="w-full text-left px-4 py-2 text-slate-300 hover:text-white hover:bg-slate-700 rounded transition-colors"
>
  <i className="fa-solid fa-key mr-2"></i>
  修改密码
</button>

{/* 添加模态框 */}
<ChangePasswordModal
  isOpen={changePasswordModalOpen}
  onClose={() => setChangePasswordModalOpen(false)}
  onSuccess={() => {
    // 清除用户状态
    onLogout?.();
  }}
/>
```

---

### Task 14: 在后台管理添加账户设置路由

**Files:**
- Modify: `frontend/src/App.tsx`

**Step 1: 导入账户设置组件**

```tsx
// frontend/src/App.tsx - 添加导入
import AccountSettings from './components/User/AccountSettings';
```

**Step 2: 添加路由**

```tsx
// frontend/src/App.tsx - 在 admin 路由下添加
<Route path="account-settings" element={<AccountSettings />} />
```

**Step 3: 在左侧菜单添加链接**

找到后台管理的侧边栏菜单组件，添加：

```tsx
<Link to="/admin/account-settings" className="...">
  <i className="fa-solid fa-user-gear"></i>
  账户设置
</Link>
```

---

### Task 15: 浏览器验证

**Step 1: 启动后端服务**

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 19092
```

Expected: Backend running on http://localhost:19092

**Step 2: 启动前端服务**

```bash
cd frontend
npm run dev
```

Expected: Frontend running on http://localhost:5178

**Step 3: 使用浏览器验证功能**

```bash
# 使用 agent-browser skill
agent-browser open http://localhost:5178/admin/users
```

**验证清单:**
- [ ] 用户列表页面正常显示
- [ ] 操作列显示钥匙图标（重置密码按钮）
- [ ] 点击重置密码按钮弹出模态框
- [ ] 模态框显示"直接设置"和"随机生成"两个 Tab
- [ ] 直接设置模式可以输入密码
- [ ] 随机生成模式显示说明文字
- [ ] 重置成功后显示新密码
- [ ] 复制按钮可以复制密码到剪贴板
- [ ] 右上角用户菜单显示"修改密码"选项
- [ ] 点击修改密码弹出模态框
- [ ] 修改密码表单验证正常
- [ ] 账户设置页面可以访问
- [ ] 浏览器 Console 无错误

---

## 测试命令

### 后端测试
```bash
cd backend
pytest tests/utils/test_password_utils.py -v
pytest tests/services/test_auth_service_password.py -v
```

### 前端测试
```bash
cd frontend
npm run test
```

### 浏览器验证
```bash
agent-browser open http://localhost:5178/login
```

---

## 提交规范

每个任务完成后单独提交：

```bash
git add <files>
git commit -m "feat: <功能描述>"
```

例如：
- `feat: add password strength validation utils`
- `feat: add admin password reset API`
- `feat: add user password change API`
- `feat: add password reset modal component`
- `feat: add change password modal component`
- `feat: add account settings page`
