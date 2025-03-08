"""
Cryptographic utility functions for the password manager client.
Includes PBKDF2 key derivation and secure memory handling.
"""
import os
import base64
import ctypes
import json
import platform
from typing import Optional, Tuple, Dict, Any, Union

# Import cryptography libraries
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

class SecureBytes:
    """
    A secure container for sensitive data like encryption keys.
    Protects memory and clears it when no longer needed.
    """
    def __init__(self, data: bytes = None):
        """Initialize with optional data"""
        self._size = len(data) if data else 0
        self._buffer = None
        
        if data:
            self.set_data(data)
    
    def set_data(self, data: bytes) -> None:
        """Set the secure data"""
        if self._buffer:
            self.clear()
            
        self._size = len(data)
        self._buffer = ctypes.create_string_buffer(data)
    
    def get_data(self) -> bytes:
        """Get a copy of the secure data"""
        if not self._buffer:
            return b''
        
        return ctypes.string_at(self._buffer, self._size)
    
    def clear(self) -> None:
        """Securely clear the data from memory"""
        if self._buffer:
            # Overwrite with zeros
            ctypes.memset(self._buffer, 0, self._size)
            self._buffer = None
            self._size = 0
    
    def __del__(self):
        """Destructor ensures data is cleared when object is garbage collected"""
        self.clear()
    
    def __len__(self) -> int:
        """Return the size of the data"""
        return self._size


class VaultCrypto:
    """
    Cryptographic operations for the vault.
    Handles key derivation, encryption, and decryption.
    """
    # Constants
    SALT_LENGTH = 16  # 128 bits
    KEY_LENGTH = 32   # 256 bits for AES-256
    ITERATIONS = 100_000  # PBKDF2 iterations
    
    def __init__(self):
        """Initialize with empty key"""
        self._encryption_key = SecureBytes()
        self._master_password = None
        self._salt = None
        self._derived = False
    
    def has_key(self) -> bool:
        """Check if encryption key has been derived"""
        return self._derived
    
    def derive_key(self, master_password: str, salt: str) -> None:
        """
        Derive encryption key from master password and server-provided salt.
        
        Args:
            master_password: The user's master password
            salt: Base64-encoded salt from server
        """
        # Clear previous key if any
        self._encryption_key.clear()
        
        # Store master password reference 
        self._master_password = master_password
        
        # Decode salt
        salt_bytes = base64.b64decode(salt)
        self._salt = salt
        
        # Create PBKDF2 key derivation function
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=salt_bytes,
            iterations=self.ITERATIONS
        )
        
        # Derive key
        key = kdf.derive(master_password.encode())
        
        # Store key securely
        self._encryption_key.set_data(key)
        self._derived = True
        print(f"Key derived successfully using PBKDF2 with {self.ITERATIONS} iterations")
    
    def encrypt(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Encrypt data with the derived key.
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            Dict with iv, ciphertext and salt
        """
        if not self._derived:
            raise ValueError("Encryption key not derived. Call derive_key first.")
        
        # Get key from secure container
        key = self._encryption_key.get_data()
        
        # Create AES-GCM cipher
        aesgcm = AESGCM(key)
        
        # Generate random nonce/IV (12 bytes for AES-GCM)
        iv = os.urandom(12)
        
        # Convert data to JSON string
        data_str = json.dumps(data)
        
        # Encrypt the data
        ciphertext = aesgcm.encrypt(
            iv,
            data_str.encode(),
            None  # No additional authenticated data
        )
        
        # Return encrypted data with IV and salt
        return {
            'iv': base64.b64encode(iv).decode('utf-8'),
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
            'salt': self._salt  # Include salt for decryption later
        }
    
    def decrypt(self, encrypted_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Decrypt data with the derived key.
        
        Args:
            encrypted_data: Dictionary with iv, ciphertext and salt
            
        Returns:
            Decrypted data as dictionary
        """
        if not self._derived:
            raise ValueError("Encryption key not derived. Call derive_key first.")
        
        # Get key from secure container
        key = self._encryption_key.get_data()
        
        # Create AES-GCM cipher
        aesgcm = AESGCM(key)
        
        # Decode base64 values
        iv = base64.b64decode(encrypted_data['iv'])
        ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        
        try:
            # Decrypt the data
            decrypted_data = aesgcm.decrypt(
                iv,
                ciphertext,
                None  # No additional authenticated data
            )
            
            # Parse JSON string
            return json.loads(decrypted_data.decode())
            
        except InvalidTag:
            raise ValueError("Decryption failed - invalid key or corrupted data")
        except json.JSONDecodeError:
            raise ValueError("Decryption succeeded but data is not valid JSON")
    
    def clear(self) -> None:
        """
        Clear all sensitive data from memory.
        Call this when locking the vault or logging out.
        """
        self._encryption_key.clear()
        self._derived = False
        
        # To be extra secure, also clear references to the master password
        self._master_password = None
        
        # Force Python garbage collection
        import gc
        gc.collect()


# Singleton instance for global access
_vault_crypto_instance = None

def get_vault_crypto() -> VaultCrypto:
    """
    Get the singleton VaultCrypto instance.
    Creates it if it doesn't exist yet.
    """
    global _vault_crypto_instance
    if _vault_crypto_instance is None:
        _vault_crypto_instance = VaultCrypto()
    return _vault_crypto_instance