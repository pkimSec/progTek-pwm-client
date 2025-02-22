from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

@dataclass
class APIEndpoints:
    """API endpoint configuration"""
    def __init__(self, base_url: str):
        """Initialize with base URL"""
        self.base_url = base_url.rstrip('/')
        
    def _url(self, path: str) -> str:
        """Construct full URL from path"""
        return urljoin(f"{self.base_url}/", path.lstrip('/'))

    @property
    def login(self) -> str:
        return self._url('/api/login')

    @property
    def logout(self) -> str:
        return self._url('/api/logout')

    @property
    def register(self) -> str:
        return self._url('/api/register')

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
    def vault_entries(self) -> str:
        return self._url('/api/vault/entries')

    def vault_entry(self, entry_id: int) -> str:
        return self._url(f'/api/vault/entries/{entry_id}')

    def entry_versions(self, entry_id: int) -> str:
        return self._url(f'/api/vault/entries/{entry_id}/versions')

    def entry_version(self, entry_id: int, version_id: int) -> str:
        return self._url(f'/api/vault/entries/{entry_id}/versions/{version_id}')