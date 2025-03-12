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
        self._last_unlock_attempt_time = None
        self._unlock_params = None  # Store the last params used to unlock
    
    def unlock(self, master_password: str, salt: str) -> bool:
        """
        Unlock the vault with master password and salt.
        
        Args:
            master_password: User's master password
            salt: Base64 encoded salt from server
        
        Returns:
            True if successful, False otherwise
        """
        import time
        self._last_unlock_attempt_time = time.time()
        
        # Save unlock parameters for potential retry
        self._unlock_params = (master_password, salt)
        
        if not master_password:
            print("Cannot unlock vault: Master password is empty")
            return False
            
        if not salt:
            print("Cannot unlock vault: Salt is empty")
            return False
            
        try:
            print(f"Attempting to unlock vault with salt: {salt[:10]}...")
            # First ensure we're in a clean state
            try:
                self._crypto.clear()
                self._entries_cache.clear()
                self._unlocked = False
                print("Cleared previous vault state")
            except Exception as clear_err:
                print(f"Non-critical error while clearing vault: {clear_err}")
                
            # Derive encryption key
            self._crypto.derive_key(master_password, salt)
            self._unlocked = True
            print(f"Vault unlocked successfully at {self._last_unlock_attempt_time}")
            return True
        except Exception as e:
            print(f"Error unlocking vault: {e}")
            import traceback
            traceback.print_exc()
            self._unlocked = False
            return False

    def retry_unlock(self) -> bool:
        """Retry unlocking the vault with the last parameters"""
        if not self._unlock_params:
            print("No previous unlock parameters found")
            return False
            
        print("Retrying vault unlock with previous parameters")
        return self.unlock(*self._unlock_params)
    
    def lock(self) -> None:
        """
        Lock the vault, clearing all sensitive data from memory.
        """
        # Clear crypto keys
        self._crypto.clear()
        
        # Clear cached entries
        self._entries_cache.clear()
        
        self._unlocked = False
        print("Vault locked")
    
    def is_unlocked(self) -> bool:
        """Check if vault is unlocked"""
        crypto_has_key = self._crypto.has_key()
        result = self._unlocked and crypto_has_key
        
        if not result:
            print(f"Vault is locked: _unlocked={self._unlocked}, crypto_has_key={crypto_has_key}")
            if self._last_unlock_attempt_time:
                import time
                print(f"Last unlock attempt was {time.time() - self._last_unlock_attempt_time:.2f} seconds ago")
                
            # If we have unlock params and the vault should be unlocked but isn't,
            # retry unlocking automatically
            if self._unlock_params and self._unlocked and not crypto_has_key:
                print("Auto-retrying vault unlock")
                return self.retry_unlock()
        
        return result
    
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
            # Try unlocking one more time if we have parameters
            if self._unlock_params and self.retry_unlock():
                print("Successfully unlocked vault on retry during decrypt")
            else:
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