"""
Crypto package for the password manager client.
Provides cryptographic operations for vault management.
"""

from .utils import get_vault_crypto, SecureBytes
from .vault import get_vault, Vault

__all__ = ['get_vault_crypto', 'get_vault', 'Vault', 'SecureBytes']