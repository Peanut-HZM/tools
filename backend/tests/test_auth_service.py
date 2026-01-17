"""
Unit tests for authentication service
"""
import pytest
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.auth_service import AuthService


class TestAuthService:
    """Tests for AuthService"""

    @pytest.fixture
    def auth_service(self):
        """Create AuthService instance for testing"""
        return AuthService()

    def test_password_hashing(self, auth_service):
        """Test password hashing and verification"""
        password = "test_password_123"
        hashed = auth_service.hash_password(password)
        
        # Hashed password should be different from original
        assert hashed != password
        
        # Verification should work
        assert auth_service.verify_password(password, hashed) == True
        
        # Wrong password should fail
        assert auth_service.verify_password("wrong_password", hashed) == False

    def test_password_hashing_different_results(self, auth_service):
        """Test that same password produces different hashes (salt)"""
        password = "test_password"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)
        
        # Different hashes due to salt
        assert hash1 != hash2
        
        # Both should verify correctly
        assert auth_service.verify_password(password, hash1) == True
        assert auth_service.verify_password(password, hash2) == True

    def test_token_generation(self, auth_service):
        """Test JWT token generation"""
        user_id = "test-user-123"
        username = "testuser"
        
        token = auth_service.create_token(user_id, username)
        
        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Token should have three parts (header.payload.signature)
        parts = token.split(".")
        assert len(parts) == 3

    def test_token_verification(self, auth_service):
        """Test JWT token verification"""
        user_id = "test-user-123"
        username = "testuser"
        
        token = auth_service.create_token(user_id, username)
        payload = auth_service.verify_token(token)
        
        # Payload should contain user info
        assert payload is not None
        assert payload.get("user_id") == user_id
        assert payload.get("username") == username

    def test_invalid_token_verification(self, auth_service):
        """Test invalid token verification"""
        invalid_token = "invalid.token.here"
        payload = auth_service.verify_token(invalid_token)
        
        # Should return None for invalid token
        assert payload is None

    def test_empty_token_verification(self, auth_service):
        """Test empty token verification"""
        payload = auth_service.verify_token("")
        assert payload is None
        
        payload = auth_service.verify_token(None)
        assert payload is None


class TestUserValidation:
    """Tests for user input validation"""

    @pytest.fixture
    def auth_service(self):
        return AuthService()

    def test_validate_username_valid(self, auth_service):
        """Test valid username validation"""
        assert auth_service.validate_username("testuser") == True
        assert auth_service.validate_username("user123") == True
        assert auth_service.validate_username("test_user") == True

    def test_validate_username_invalid(self, auth_service):
        """Test invalid username validation"""
        # Too short
        assert auth_service.validate_username("ab") == False
        # Too long
        assert auth_service.validate_username("a" * 51) == False
        # Empty
        assert auth_service.validate_username("") == False

    def test_validate_email_valid(self, auth_service):
        """Test valid email validation"""
        assert auth_service.validate_email("test@example.com") == True
        assert auth_service.validate_email("user.name@domain.org") == True

    def test_validate_email_invalid(self, auth_service):
        """Test invalid email validation"""
        assert auth_service.validate_email("invalid-email") == False
        assert auth_service.validate_email("@domain.com") == False
        assert auth_service.validate_email("user@") == False

    def test_validate_password_valid(self, auth_service):
        """Test valid password validation"""
        assert auth_service.validate_password("password123") == True
        assert auth_service.validate_password("SecurePass!@#") == True

    def test_validate_password_invalid(self, auth_service):
        """Test invalid password validation"""
        # Too short
        assert auth_service.validate_password("short") == False
        # Empty
        assert auth_service.validate_password("") == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
