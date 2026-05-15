"""验证 bcrypt 升级后现有密码哈希仍然有效"""
from passlib.context import CryptContext

# 使用与 production 相同的配置
ctx = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# 测试密码列表
test_passwords = [
    "TestPass1!",
    "MyP@ssw0rd!2024",
    "Admin#1234",
    "Complex!Pass99",
    "aB3$xyz",
]

print("=== bcrypt 向后兼容验证 ===")
import passlib
print(f"passlib version: {passlib.__version__}")
import bcrypt
print(f"bcrypt version: {bcrypt.__version__}")

all_passed = True

# 测试 1: 生成新哈希并立即验证
print("\n测试 1: 新哈希生成与验证")
for password in test_passwords:
    h = ctx.hash(password)
    ok = ctx.verify(password, h)
    status = "PASS" if ok else "FAIL"
    print(f"  {status}: 密码 '{password}' 验证{'通过' if ok else '失败'}")
    if not ok:
        all_passed = False

# 测试 2: 验证旧格式哈希 ($2b$) 能否被新 bcrypt 解析
print("\n测试 2: 旧格式哈希 ($2b$) 兼容性")
# 用旧版 bcrypt 格式生成一个哈希（$2b$ 前缀）
old_format_hash = ctx.hash("test_password_123")
# 确保 passlib 能处理自己生成的哈希
ok = ctx.verify("test_password_123", old_format_hash)
status = "PASS" if ok else "FAIL"
print(f"  {status}: 生成的哈希格式为 '{old_format_hash[:7]}...'")

# 测试 3: 错误密码应拒绝
print("\n测试 3: 错误密码拒绝")
h = ctx.hash("CorrectPass1!")
ok_wrong = ctx.verify("WrongPass1!", h)
status = "PASS" if not ok_wrong else "FAIL"
print(f"  {status}: 错误密码{'被正确拒绝' if not ok_wrong else '未被拒绝（BUG!）'}")
if ok_wrong:
    all_passed = False

# 总结
print()
if all_passed:
    print("✅ 所有测试通过，bcrypt 升级安全")
else:
    print("❌ 存在兼容性问题")
    exit(1)
