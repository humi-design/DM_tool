"""Secret Management Service.

This module provides secure encryption and decryption of sensitive data
using the MASTER_ENCRYPTION_KEY. All secrets stored in the database
are encrypted using this service.

Usage:
    secret_manager = SecretManager()
    encrypted = secret_manager.encrypt("sensitive_value")
    decrypted = secret_manager.decrypt(encrypted)
"""

import os
import base64
import hashlib
import secrets
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class SecretManager:
    """Service for encrypting and decrypting sensitive data."""
    
    _instance = None
    _fernet = None
    _encryption_key = None
    
    def __new__(cls):
        """Singleton pattern for SecretManager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the secret manager."""
        if self._fernet is None:
            self._initialize_encryption()
    
    def _initialize_encryption(self) -> None:
        """Initialize encryption with MASTER_ENCRYPTION_KEY."""
        master_key = os.environ.get('MASTER_ENCRYPTION_KEY')
        
        if not master_key:
            # Generate a key for development/testing only
            logger.warning(
                "MASTER_ENCRYPTION_KEY not set. "
                "Using temporary key. DO NOT use in production!"
            )
            # Use a deterministic key for development
            master_key = "development-only-key-do-not-use-in-production"
        
        # Derive a proper Fernet key from the master key
        self._encryption_key = self._derive_key(master_key)
        self._fernet = Fernet(self._encryption_key)
    
    def _derive_key(self, master_key: str) -> bytes:
        """Derive a Fernet-compatible key from the master key.
        
        Args:
            master_key: The master encryption key from environment
            
        Returns:
            A 32-byte URL-safe base64-encoded key
        """
        # Use PBKDF2 to derive a key from the master key
        salt = b'ai_social_os_salt_v1'  # Static salt for consistency
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return key
    
    def encrypt(self, value: str) -> str:
        """Encrypt a string value.
        
        Args:
            value: The plain text value to encrypt
            
        Returns:
            Base64-encoded encrypted value
        """
        if not value:
            return value
        
        try:
            encrypted = self._fernet.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt value: {e}")
    
    def decrypt(self, encrypted_value: str) -> str:
        """Decrypt an encrypted value.
        
        Args:
            encrypted_value: Base64-encoded encrypted value
            
        Returns:
            The decrypted plain text value
        """
        if not encrypted_value:
            return encrypted_value
        
        try:
            decoded = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted = self._fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt value: {e}")
    
    def encrypt_dict(self, data: Dict[str, Any], keys_to_encrypt: list = None) -> Dict[str, Any]:
        """Encrypt specific keys in a dictionary.
        
        Args:
            data: Dictionary containing data
            keys_to_encrypt: List of keys to encrypt (if None, encrypt all string values)
            
        Returns:
            Dictionary with specified keys encrypted
        """
        result = data.copy()
        
        for key, value in data.items():
            if keys_to_encrypt and key not in keys_to_encrypt:
                continue
            
            if isinstance(value, str) and value:
                result[key] = self.encrypt(value)
            elif isinstance(value, dict):
                result[key] = self.encrypt_dict(value, keys_to_encrypt)
        
        return result
    
    def decrypt_dict(self, data: Dict[str, Any], keys_to_decrypt: list = None) -> Dict[str, Any]:
        """Decrypt specific keys in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data
            keys_to_decrypt: List of keys to decrypt
            
        Returns:
            Dictionary with specified keys decrypted
        """
        result = data.copy()
        
        for key, value in data.items():
            if keys_to_decrypt and key not in keys_to_decrypt:
                continue
            
            if isinstance(value, str) and value and not value.startswith('gAAAAA'):
                # Already decrypted (doesn't have Fernet prefix)
                continue
            
            if isinstance(value, str) and value:
                try:
                    result[key] = self.decrypt(value)
                except DecryptionError:
                    # Value might not be encrypted
                    pass
            elif isinstance(value, dict):
                result[key] = self.decrypt_dict(value, keys_to_decrypt)
        
        return result
    
    def mask(self, value: str, show_chars: int = 4) -> str:
        """Mask a value, showing only the last few characters.
        
        Args:
            value: The value to mask
            show_chars: Number of characters to show at the end
            
        Returns:
            Masked string (e.g., "************1234")
        """
        if not value:
            return ""
        
        if len(value) <= show_chars:
            return "*" * len(value)
        
        return "*" * (len(value) - show_chars) + value[-show_chars:]
    
    def generate_key(self, length: int = 32) -> str:
        """Generate a random key.
        
        Args:
            length: Length of the key in bytes
            
        Returns:
            A URL-safe base64-encoded random key
        """
        return base64.urlsafe_b64encode(secrets.token_bytes(length)).decode()
    
    @classmethod
    def is_encrypted(cls, value: str) -> bool:
        """Check if a value is encrypted (has Fernet prefix).
        
        Args:
            value: The value to check
            
        Returns:
            True if the value appears to be encrypted
        """
        if not value:
            return False
        return value.startswith('gAAAAA')
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Used for testing."""
        cls._instance = None
        cls._fernet = None
        cls._encryption_key = None


class EncryptionError(Exception):
    """Exception raised when encryption fails."""
    pass


class DecryptionError(Exception):
    """Exception raised when decryption fails."""
    pass


# Convenience functions
def encrypt(value: str) -> str:
    """Encrypt a value using the global SecretManager."""
    return SecretManager().encrypt(value)


def decrypt(value: str) -> str:
    """Decrypt a value using the global SecretManager."""
    return SecretManager().decrypt(value)


def mask(value: str, show_chars: int = 4) -> str:
    """Mask a value using the global SecretManager."""
    return SecretManager().mask(value, show_chars)


# Integration with database models
def encrypt_credentials(model, credential_fields: list, save: bool = True):
    """Encrypt credential fields on a database model.
    
    Args:
        model: SQLAlchemy model instance
        credential_fields: List of field names that contain credentials
        save: Whether to save the model after encryption
    """
    secret_manager = SecretManager()
    
    for field in credential_fields:
        value = getattr(model, field, None)
        if value and not SecretManager.is_encrypted(value):
            setattr(model, field, secret_manager.encrypt(value))
    
    if save:
        from app import db
        db.session.commit()


def decrypt_credentials(model, credential_fields: list):
    """Decrypt credential fields on a database model.
    
    Args:
        model: SQLAlchemy model instance
        credential_fields: List of field names that contain encrypted credentials
    """
    secret_manager = SecretManager()
    
    for field in credential_fields:
        value = getattr(model, field, None)
        if value and SecretManager.is_encrypted(value):
            try:
                setattr(model, field, secret_manager.decrypt(value))
            except DecryptionError:
                logger.warning(f"Failed to decrypt field {field} on {model.__class__.__name__}")


def get_credential_value(model, field: str, decrypt: bool = True) -> Optional[str]:
    """Get a credential value, optionally decrypted.
    
    Args:
        model: SQLAlchemy model instance
        field: Field name containing the credential
        decrypt: Whether to decrypt the value
        
    Returns:
        The credential value (decrypted if requested)
    """
    value = getattr(model, field, None)
    
    if not value:
        return None
    
    if decrypt and SecretManager.is_encrypted(value):
        try:
            return SecretManager().decrypt(value)
        except DecryptionError:
            logger.warning(f"Failed to decrypt field {field}")
            return None
    
    return value


# System initialization
def initialize_system_secrets():
    """Initialize system secrets if they don't exist.
    
    This function should be called during application startup
    to ensure required system secrets are set.
    """
    secret_manager = SecretManager()
    
    # Generate SECRET_KEY if not set
    if not os.environ.get('SECRET_KEY'):
        secret_key = secret_manager.generate_key()
        os.environ['SECRET_KEY'] = secret_key
        logger.info("Generated SECRET_KEY")
    
    # Generate JWT_SECRET if not set
    if not os.environ.get('JWT_SECRET'):
        jwt_secret = secret_manager.generate_key()
        os.environ['JWT_SECRET'] = jwt_secret
        logger.info("Generated JWT_SECRET")
    
    # Ensure MASTER_ENCRYPTION_KEY exists
    if not os.environ.get('MASTER_ENCRYPTION_KEY'):
        # In production, this should fail - MASTER_ENCRYPTION_KEY must be set
        logger.warning(
            "MASTER_ENCRYPTION_KEY not set. "
            "Application may not be secure in production!"
        )


if __name__ == "__main__":
    # Test the secret manager
    sm = SecretManager()
    
    test_value = "my-secret-api-key-12345"
    encrypted = sm.encrypt(test_value)
    decrypted = sm.decrypt(encrypted)
    
    print(f"Original: {test_value}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
    print(f"Masked: {sm.mask(test_value)}")
    print(f"Is Encrypted: {SecretManager.is_encrypted(encrypted)}")
