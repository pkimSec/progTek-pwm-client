from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

@dataclass
class APIEndpoints:
    """API endpoint configuration"""
    def __init__(self, base_url: str):
        """Initialize with base URL"""
        # Ensure the base URL has the correct format with trailing slash
        self.base_url = base_url.rstrip('/')
        
        # Validate base URL format
        if not self.base_url.startswith(('http://', 'https://')):
            if self.base_url.startswith(('localhost', '127.0.0.1')):
                self.base_url = 'http://' + self.base_url
            else:
                raise ValueError("Base URL must start with http:// or https://")
        
        print(f"Initialized API endpoints with base URL: {self.base_url}")
        
    def _url(self, path: str) -> str:
        """Construct full URL from path"""
        # Always ensure path starts with / for proper joining
        normalized_path = '/' + path.lstrip('/')
        return urljoin(f"{self.base_url}/", normalized_path.lstrip('/'))

    @property
    def login(self) -> str:
        return self._url('/api/login')

    @property
    def logout(self) -> str:
        return self._url('/api/logout')

    @property
    def register(self) -> str:
        # Ensure this matches the server endpoint exactly
        return self._url('/api/register')

    @property
    def users(self) -> str:
        return self._url('/api/users')

    def user(self, user_id: int) -> str:
        return self._url(f'/api/users/{user_id}')

    @property
    def create_invite(self) -> str:
        return self._url('/api/invite')

    @property
    def vault_setup(self) -> str:
        return self._url('/api/vault/setup')

    @property
    def vault_salt(self) -> str:
        return self._url('/api/vault/salt')

    @property
    def invites(self) -> str:
        return self._url('/api/invites')

    def invite_code(self, code: str) -> str:
        return self._url(f'/api/invites/{code}')

    @property
    def vault_entries(self) -> str:
        return self._url('/api/vault/entries')

    def vault_entry(self, entry_id: int) -> str:
        return self._url(f'/api/vault/entries/{entry_id}')

    def entry_versions(self, entry_id: int) -> str:
        return self._url(f'/api/vault/entries/{entry_id}/versions')

    def entry_version(self, entry_id: int, version_id: int) -> str:
        return self._url(f'/api/vault/entries/{entry_id}/versions/{version_id}')