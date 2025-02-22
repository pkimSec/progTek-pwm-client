import aiohttp
import json
import asyncio
from typing import Optional, Dict, Any, Union
from datetime import datetime
from urllib.parse import urljoin

from .endpoints import APIEndpoints
from .models import (
    LoginRequest, LoginResponse, RegisterRequest,
    PasswordEntry, EntryVersion, APIError
)

class APIClient:
    """Asynchronous API client for password manager server"""
    
    def __init__(self, base_url: str):
        """Initialize API client with base URL"""
        self.endpoints = APIEndpoints(base_url)
        self.session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None
        self._rate_limit_remaining: int = 20
        self._rate_limit_reset: Optional[datetime] = None

    @property
    def is_authenticated(self) -> bool:
        """Check if client has valid access token"""
        return bool(self._access_token)

    async def __aenter__(self):
        """Context manager entry - create session"""
        await self.create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup session"""
        await self.close()

    async def create_session(self):
        """Create new aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    def _get_headers(self, include_auth: bool = True) -> Dict[str, str]:
        """Get request headers including auth token if available"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if include_auth and self._access_token:
            headers['Authorization'] = f'Bearer {self._access_token}'
            
        return headers

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Any:
        """Handle API response and potential errors"""
        # Update rate limit info
        self._rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 20))
        reset_time = response.headers.get('X-RateLimit-Reset')
        if reset_time:
            self._rate_limit_reset = datetime.fromtimestamp(int(reset_time))

        try:
            data = await response.json()
        except json.JSONDecodeError:
            data = await response.text()

        if not response.ok:
            raise APIError(
                message=data.get('message', 'Unknown error'),
                status_code=response.status
            )

        return data

    async def _request(
        self,
        method: str,
        url: str,
        data: Optional[Dict] = None,
        include_auth: bool = True
    ) -> Any:
        """Make HTTP request to API"""
        if self.session is None or self.session.closed:
            await self.create_session()

        async with self.session.request(
            method=method,
            url=url,
            json=data,
            headers=self._get_headers(include_auth)
        ) as response:
            return await self._handle_response(response)

    async def login(self, email: str, password: str) -> LoginResponse:
        """Log in user and get access token"""
        data = LoginRequest(email=email, password=password).model_dump()
        response = await self._request('POST', self.endpoints.login, data, include_auth=False)
        self._access_token = response['access_token']
        return LoginResponse(**response)

    async def logout(self):
        """Log out user and clear session"""
        try:
            await self._request('POST', self.endpoints.logout)
        finally:
            self._access_token = None

    async def register(self, email: str, password: str, invite_code: str):
        """Register new user"""
        data = RegisterRequest(
            email=email,
            password=password,
            invite_code=invite_code
        ).model_dump()
        return await self._request('POST', self.endpoints.register, data, include_auth=False)

    async def create_invite(self) -> str:
        """Create invite code (admin only)"""
        response = await self._request('POST', self.endpoints.create_invite)
        return response['invite_code']

    async def setup_vault(self, master_password: str):
        """Initialize user's vault"""
        data = {'master_password': master_password}
        return await self._request('POST', self.endpoints.vault_setup, data)

    async def get_vault_salt(self) -> str:
        """Get vault salt for key derivation"""
        response = await self._request('GET', self.endpoints.vault_salt)
        return response['salt']

    async def create_entry(self, encrypted_data: str) -> PasswordEntry:
        """Create new password entry"""
        data = {'encrypted_data': encrypted_data}
        response = await self._request('POST', self.endpoints.vault_entries, data)
        return PasswordEntry(**response)

    async def list_entries(self) -> list[PasswordEntry]:
        """Get all password entries"""
        response = await self._request('GET', self.endpoints.vault_entries)
        return [PasswordEntry(**entry) for entry in response['entries']]

    async def get_entry(self, entry_id: int) -> PasswordEntry:
        """Get specific password entry"""
        response = await self._request('GET', self.endpoints.vault_entry(entry_id))
        return PasswordEntry(**response)

    async def update_entry(self, entry_id: int, encrypted_data: str) -> Dict[str, Union[str, int]]:
        """Update password entry"""
        data = {'encrypted_data': encrypted_data}
        return await self._request('PUT', self.endpoints.vault_entry(entry_id), data)

    async def delete_entry(self, entry_id: int):
        """Delete password entry"""
        return await self._request('DELETE', self.endpoints.vault_entry(entry_id))

    async def list_entry_versions(self, entry_id: int) -> list[EntryVersion]:
        """Get versions of a password entry"""
        response = await self._request('GET', self.endpoints.entry_versions(entry_id))
        return [EntryVersion(**version) for version in response['versions']]

    async def get_entry_version(self, entry_id: int, version_id: int) -> EntryVersion:
        """Get specific version of a password entry"""
        response = await self._request(
            'GET',
            self.endpoints.entry_version(entry_id, version_id)
        )
        return EntryVersion(**response)