from cryptography.fernet import Fernet
from app.config.config import settings
import base64
import logging

logger = logging.getLogger(__name__)

class EncryptionUtils:
    _cipher_suite = None

    @classmethod
    def _get_cipher_suite(cls):
        if cls._cipher_suite is None:
            key = settings.DB_ENCRYPTION_KEY
            # Fernet key must be 32 url-safe base64-encoded bytes
            # If the key provided is not in this format, we might need to adjust or hash it
            try:
                cls._cipher_suite = Fernet(key)
            except ValueError:
                # If key is invalid (e.g. not 32 bytes base64), try to derive a valid key
                # This is a fallback for development convenience
                import hashlib
                m = hashlib.sha256()
                m.update(key.encode('utf-8'))
                # Get 32 bytes and base64 encode it
                derived_key = base64.urlsafe_b64encode(m.digest())
                cls._cipher_suite = Fernet(derived_key)
                
        return cls._cipher_suite

    @classmethod
    def encrypt(cls, plain_text: str) -> str:
        """Encrypts a string"""
        if not plain_text:
            return ""
        try:
            cipher_suite = cls._get_cipher_suite()
            encrypted_text = cipher_suite.encrypt(plain_text.encode('utf-8'))
            return encrypted_text.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    @classmethod
    def decrypt(cls, encrypted_text: str) -> str:
        """Decrypts a string"""
        if not encrypted_text:
            return ""
        try:
            cipher_suite = cls._get_cipher_suite()
            decrypted_text = cipher_suite.decrypt(encrypted_text.encode('utf-8'))
            return decrypted_text.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
