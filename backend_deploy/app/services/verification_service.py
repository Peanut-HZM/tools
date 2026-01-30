"""
Verification Service - Handles verification code generation and validation
"""
import random
import string
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# In-memory storage for verification codes
# Structure: { "target": { "code": "123456", "exp": datetime } }
verification_store: Dict[str, Dict] = {}

class VerificationService:
    """Service for handling verification codes"""
    
    def __init__(self):
        pass
    
    def send_code(self, target: str, type: str) -> str:
        """
        Send verification code to target (email or phone)
        
        Args:
            target: Email address or phone number
            type: 'email' or 'phone'
            
        Returns:
            The generated code (for testing/mocking purposes)
        """
        code = self._generate_code(type)
        
        # Store code with expiration (e.g., 5 minutes)
        verification_store[target] = {
            "code": code,
            "exp": datetime.utcnow() + timedelta(minutes=5)
        }
        
        # Mock sending
        if type == 'phone':
            logger.info(f"Sending SMS to {target}: {code}")
            # In real implementation, call SMS provider API here
        else:
            logger.info(f"Sending Email to {target}: {code}")
            # In real implementation, call Email provider API here
            
        return code
    
    def verify_code(self, target: str, code: str) -> bool:
        """
        Verify the code for the target
        
        Args:
            target: Email address or phone number
            code: The code provided by user
            
        Returns:
            True if valid, False otherwise
        """
        if not target or not code:
            return False
            
        record = verification_store.get(target)
        if not record:
            return False
            
        if datetime.utcnow() > record["exp"]:
            # Code expired
            del verification_store[target]
            return False
            
        if record["code"] != code:
            return False
            
        # Code valid, consume it
        del verification_store[target]
        return True
        
    def _generate_code(self, type: str) -> str:
        """Generate a verification code"""
        if type == 'phone':
            # Mock phone code as requested
            return "202601"
        else:
            # Generate 6-digit random code for email
            return "".join(random.choices(string.digits, k=6))

# Singleton instance
verification_service = VerificationService()
