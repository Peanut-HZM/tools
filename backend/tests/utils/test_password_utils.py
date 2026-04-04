"""
密码工具函数测试
"""
from app.utils.password_utils import validate_password_strength, generate_random_password


class TestValidatePasswordStrength:
    """测试密码强度验证"""

    def test_valid_password(self):
        """测试有效密码"""
        is_valid, message = validate_password_strength("Test123!@#")
        assert is_valid
        assert message == ""

    def test_empty_password(self):
        """测试空密码"""
        is_valid, message = validate_password_strength("")
        assert not is_valid
        assert "不能为空" in message

    def test_too_short_password(self):
        """测试密码过短"""
        is_valid, message = validate_password_strength("Test1!")
        assert not is_valid
        assert "8-100" in message

    def test_too_long_password(self):
        """测试密码过长"""
        is_valid, message = validate_password_strength("A" * 101 + "1!")
        assert not is_valid
        assert "8-100" in message

    def test_no_uppercase(self):
        """测试缺少大写字母"""
        is_valid, message = validate_password_strength("test123!@#")
        assert not is_valid
        assert "大写字母" in message

    def test_no_lowercase(self):
        """测试缺少小写字母"""
        is_valid, message = validate_password_strength("TEST123!@#")
        assert not is_valid
        assert "小写字母" in message

    def test_no_digit(self):
        """测试缺少数字"""
        is_valid, message = validate_password_strength("Testabc!@#")
        assert not is_valid
        assert "数字" in message

    def test_no_special_char(self):
        """测试缺少特殊字符"""
        is_valid, message = validate_password_strength("Test12345")
        assert not is_valid
        assert "特殊字符" in message


class TestGenerateRandomPassword:
    """测试随机密码生成"""

    def test_default_length(self):
        """测试默认长度"""
        password = generate_random_password()
        assert len(password) == 12

    def test_custom_length(self):
        """测试自定义长度"""
        password = generate_random_password(16)
        assert len(password) == 16

    def test_min_length(self):
        """测试最小长度"""
        password = generate_random_password(8)
        assert len(password) == 8

    def test_password_strength(self):
        """测试生成的密码强度"""
        for _ in range(10):  # 测试 10 次
            password = generate_random_password()
            is_valid, _ = validate_password_strength(password)
            assert is_valid, f"Generated weak password: {password}"
