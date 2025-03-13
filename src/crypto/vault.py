"""
Vault management for encrypting and decrypting password entries.
"""
import json
import base64
import os
from typing import Dict, Any, Optional, List

from crypto.utils import get_vault_crypto, VaultCrypto

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
        self._master_password = None
        self._salt = None
        
        # Persistent key storage to ensure consistent decryption
        self._key_storage = {}  # Dictionary to store derived keys by salt
    
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
        self._master_password = master_password
        self._salt = salt
        
        if not master_password:
            print("Cannot unlock vault: Master password is empty")
            return False
            
        if not salt:
            print("Cannot unlock vault: Salt is empty")
            return False
        
        # Check if we already have a derived key for this salt
        cache_key = f"{salt}"
        if cache_key in self._key_storage:
            print(f"Using cached key for salt: {salt[:10]}...")
            # Use the cached key
            self._crypto._encryption_key = self._key_storage[cache_key]
            self._crypto._derived = True
            self._unlocked = True
            print(f"Vault unlocked successfully with cached key at {self._last_unlock_attempt_time}")
            return True
            
        try:
            print(f"Attempting to unlock vault with salt: {salt[:10]}...")
            # First ensure we're in a clean state
            try:
                self._crypto.clear()
                print("Cleared previous vault state")
            except Exception as clear_err:
                print(f"Non-critical error while clearing vault: {clear_err}")
                
            # Derive encryption key
            self._crypto.derive_key(master_password, salt)
            
            # Store the key in our persistent storage
            self._key_storage[cache_key] = self._crypto._encryption_key
            
            self._unlocked = True
            print(f"Vault unlocked successfully with new key at {self._last_unlock_attempt_time}")
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
        # Don't clear key storage, only mark vault as locked
        self._crypto._derived = False
        self._unlocked = False
        
        # Clear cached entries
        self._entries_cache.clear()
        
        print("Vault locked (keys retained for consistent decryption)")
    
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
            if self._unlock_params:
                print("Vault not unlocked, attempting auto-unlock")
                self.unlock(*self._unlock_params)
            else:
                raise ValueError("Vault is locked. Unlock it first.")
        
        # Add validation to ensure we have required fields
        if not entry_data.get('title'):
            print("Warning: Entry has no title, adding default")
            entry_data['title'] = "Untitled Entry"
            
        # Add validation for other required fields
        for field in ['username', 'password']:
            if field not in entry_data:
                print(f"Warning: Entry missing '{field}', adding empty value")
                entry_data[field] = ""
        
        # Encrypt the data
        encrypted = self._crypto.encrypt(entry_data)
        
        # Add the salt to the encrypted data
        if self._salt and 'salt' not in encrypted:
            encrypted['salt'] = self._salt
        
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
        # Check cache first - use the exact encrypted_json as key for consistency
        cache_key = hash(encrypted_json)
        if cache_key in self._entries_cache:
            print(f"Using cached decryption for entry hash {cache_key}")
            return self._entries_cache[cache_key]
        
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
        
        # Make sure we use the right key for this specific salt
        entry_salt = encrypted_data.get('salt', self._salt)
        if entry_salt != self._salt:
            print(f"Warning: Entry salt {entry_salt[:10]} doesn't match current vault salt {self._salt[:10]}")
            # Try to use a cached key or derive a new one for this specific salt
            if self._master_password:
                print(f"Re-deriving key with entry-specific salt")
                temp_result = self.unlock(self._master_password, entry_salt)
                if not temp_result:
                    raise ValueError(f"Failed to unlock vault with entry-specific salt")
            else:
                raise ValueError(f"Cannot decrypt entry with different salt: missing master password")
        
        # Decrypt data
        try:
            decrypted = self._crypto.decrypt(encrypted_data)
            
            # Validate decrypted data
            if not isinstance(decrypted, dict):
                raise ValueError(f"Decryption produced invalid data type: {type(decrypted)}")
                
            if 'title' not in decrypted or not decrypted['title']:
                print("Warning: Decrypted entry has no title, adding default")
                decrypted['title'] = "Untitled Entry"
            
            # Cache for future use
            self._entries_cache[cache_key] = decrypted
            
            return decrypted
        except Exception as e:
            print(f"Error decrypting entry: {str(e)}")
            import traceback
            traceback.print_exc()
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def clear_cache(self) -> None:
        """Clear the decrypted entries cache"""
        self._entries_cache.clear()
        print("Entry cache cleared")


# Singleton instance
_vault_instance = None

def get_vault() -> Vault:
    """Get the singleton vault instance"""
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = Vault()
    return _vault_instance