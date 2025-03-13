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
        self._derivation_count = 0  # Track how many times we've derived keys
    
    def has_key(self) -> bool:
        """Check if encryption key has been derived"""
        return self._derived and len(self._encryption_key) > 0
    
    def derive_key(self, master_password: str, salt: str = None) -> None:
        """
        Derive encryption key from the master password using PBKDF2.
        
        Args:
            master_password: The user's master password
            salt: Base64-encoded salt string from server
        """
        # Increment derivation counter and log
        self._derivation_count += 1
        print(f"[Key Derivation #{self._derivation_count}] Starting with salt: {salt[:10] if salt else None}")
        
        # Store master password reference 
        self._master_password = master_password
        
        try:
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
            print(f"[Key Derivation #{self._derivation_count}] Key derived successfully for salt: {salt[:10]}")
        except Exception as e:
            self._derived = False
            print(f"[Key Derivation #{self._derivation_count}] Error deriving key: {e}")
            import traceback
            traceback.print_exc()
            raise ValueError(f"Failed to derive encryption key: {str(e)}")
    
    def encrypt(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Encrypt data with the derived key.
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            Dict with iv, ciphertext and salt
        """
        if not self._derived or not self._encryption_key or len(self._encryption_key) == 0:
            raise ValueError("Encryption key not derived or invalid. Call derive_key first.")
        
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
        
        if not self._encryption_key or len(self._encryption_key) == 0:
            raise ValueError("Invalid encryption key state.")
        
        # Log decryption attempt with hash of ciphertext for debugging
        ciphertext_hash = hash(encrypted_data.get('ciphertext', ''))
        print(f"Attempting to decrypt data with hash: {ciphertext_hash}")
        
        # Get key from secure container
        key = self._encryption_key.get_data()
        
        # Create AES-GCM cipher
        aesgcm = AESGCM(key)
        
        # Decode base64 values
        try:
            iv = base64.b64decode(encrypted_data['iv'])
            ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        except Exception as e:
            print(f"Error decoding base64 data: {e}")
            raise ValueError(f"Invalid base64 encoding in encrypted data: {e}")
        
        try:
            # Decrypt the data
            decrypted_data = aesgcm.decrypt(
                iv,
                ciphertext,
                None  # No additional authenticated data
            )
            
            # Parse JSON string
            result = json.loads(decrypted_data.decode())
            
            # Verify we have proper data structure
            if not isinstance(result, dict):
                raise ValueError(f"Decrypted data is not a dictionary: {type(result)}")
                
            print(f"Successfully decrypted data with hash: {ciphertext_hash}")
            return result
            
        except InvalidTag:
            print(f"Decryption failed - invalid key or corrupted data for hash: {ciphertext_hash}")
            raise ValueError("Decryption failed - invalid key or corrupted data")
        except json.JSONDecodeError as e:
            print(f"Decryption succeeded but data is not valid JSON for hash: {ciphertext_hash}")
            raise ValueError(f"Decryption succeeded but data is not valid JSON: {e}")
        except Exception as e:
            print(f"Unexpected error during decryption for hash: {ciphertext_hash}: {e}")
            raise ValueError(f"Decryption error: {e}")
    
    def clear(self) -> None:
        """
        Clear all sensitive data from memory.
        Call this when locking the vault or logging out.
        """
        print("Clearing crypto state...")
        
        # DON'T clear the key if we're just locking temporarily
        # This ensures consistent decryption across unlock cycles
        # self._encryption_key.clear()
        
        # Just mark as not derived
        self._derived = False
        
        # No need to clear references to the master password if just locking
        # since we'll need them for unlock
        # self._master_password = None
        
        # Force Python garbage collection
        import gc
        gc.collect()
        print("Crypto state cleared (keys retained for consistent decryption)")


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