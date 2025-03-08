"""
Vault management for encrypting and decrypting password entries.
"""
import json
import base64
from typing import Dict, Any, Optional, List

from .utils import get_vault_crypto, VaultCrypto

class Vault:
    """
    Manages the user's password vault.
    Handles encryption/decryption of entries and vault locking.
    """
    def __init__(self):
        """Initialize vault"""
        # Get crypto instance
        self._crypto = get_vault_crypto()
        self._unlocked = False
        self._entries_cache = {}  # Cache for decrypted entries
    
    def unlock(self, master_password: str, salt: str) -> bool:
        """
        Unlock the vault with master password and salt.
        
        Args:
            master_password: User's master password
            salt: Base64 encoded salt from server
        
        Returns:
            True if successful, False otherwise
        """
        if not master_password:
            print("Cannot unlock vault: Master password is empty")
            return False
            
        if not salt:
            print("Cannot unlock vault: Salt is empty")
            return False
            
        try:
            print(f"Attempting to unlock vault with salt: {salt[:10]}...")
            # Derive encryption key
            self._crypto.derive_key(master_password, salt)
            self._unlocked = True
            print("Vault unlocked successfully")
            return True
        except Exception as e:
            print(f"Error unlocking vault: {e}")
            import traceback
            traceback.print_exc()
            self._unlocked = False
            return False
    
    def lock(self) -> None:
        """
        Lock the vault, clearing all sensitive data from memory.
        """
        # Clear crypto keys
        self._crypto.clear()
        
        # Clear cached entries
        self._entries_cache.clear()
        
        self._unlocked = False
    
    def is_unlocked(self) -> bool:
        """Check if vault is unlocked"""
        return self._unlocked and self._crypto.has_key()
    
    def encrypt_entry(self, entry_data: Dict[str, Any]) -> str:
        """
        Encrypt an entry for storage.
        
        Args:
            entry_data: Dictionary with entry fields
            
        Returns:
            JSON string with encrypted data
        """
        if not self.is_unlocked():
            raise ValueError("Vault is locked. Unlock it first.")
        
        # Encrypt the data
        encrypted = self._crypto.encrypt(entry_data)
        
        # Convert to JSON string
        return json.dumps(encrypted)
    
    def decrypt_entry(self, encrypted_json: str) -> Dict[str, Any]:
        """
        Decrypt an entry.
        
        Args:
            encrypted_json: JSON string with encrypted data
            
        Returns:
            Decrypted entry as dictionary
        """
        if not self.is_unlocked():
            raise ValueError("Vault is locked. Unlock it first.")
        
        # Parse JSON
        try:
            encrypted_data = json.loads(encrypted_json)
        except json.JSONDecodeError:
            raise ValueError("Invalid encrypted data format")
        
        # Check if already cached
        entry_id = id(encrypted_json)
        if entry_id in self._entries_cache:
            return self._entries_cache[entry_id]
        
        # Decrypt data
        decrypted = self._crypto.decrypt(encrypted_data)
        
        # Cache for future use
        self._entries_cache[entry_id] = decrypted
        
        return decrypted
    
    def clear_cache(self) -> None:
        """Clear the decrypted entries cache"""
        self._entries_cache.clear()


# Singleton instance
_vault_instance = None

def get_vault() -> Vault:
    """Get the singleton vault instance"""
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = Vault()
    return _vault_instance