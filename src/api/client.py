import aiohttp
import json
import asyncio
import weakref
from typing import Optional, Dict, Any, Union, ClassVar
from datetime import datetime, timedelta
from urllib.parse import urljoin
from typing import List, Dict, Any, Optional

from .endpoints import APIEndpoints
from api.models import User
from .models import (
    LoginRequest, LoginResponse, RegisterRequest,
    PasswordEntry, EntryVersion, APIError
)

# Global session tracker
_active_sessions = set()

class APIClient:
    """Asynchronous API client for password manager server"""
    
    # Class variable for session cache
    _instance_cache: ClassVar[Dict[str, 'APIClient']] = {}
    
    def __init__(self, base_url: str):
        """Initialize API client with base URL"""
        self.endpoints = APIEndpoints(base_url)
        self.session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None
        self._session_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._rate_limit_remaining: int = 20
        self._rate_limit_reset: Optional[datetime] = None   
        self._master_password: Optional[str] = None  # Store master password for vault operations
        self._user_email: Optional[str] = None  # Store user email for reconnection
        self._is_closing = False  # Flag to prevent multiple close attempts
        
        # Cache this instance by base_url for reuse
        APIClient._instance_cache[base_url] = self
        
        print(f"Created new APIClient for {base_url}")

    @classmethod
    def get_instance(cls, base_url: str) -> 'APIClient':
        """Get existing client instance or create a new one"""
        if base_url in cls._instance_cache:
            return cls._instance_cache[base_url]
        return cls(base_url)
    
    @classmethod
    def clear_all_instances(cls):
        """Clear all cached instances"""
        print(f"Clearing {len(cls._instance_cache)} APIClient instances")
        cls._instance_cache.clear()

    async def ensure_session(self):
        """Ensure its a valid session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            # Track the session
            _active_sessions.add(weakref.ref(self.session, lambda _: _active_sessions.discard(_)))
            print(f"Created new session, total active: {len(_active_sessions)}")

    @property
    def is_authenticated(self) -> bool:
        """Check if client has valid access token"""
        return bool(self._access_token) and (
            self._token_expires_at is None or 
            self._token_expires_at > datetime.now()
        )
    
    def set_master_password(self, password: str) -> None:
        """Set master password for vault operations"""
        self._master_password = password

    async def __aenter__(self):
        """Context manager entry - create session"""
        await self.create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup session"""
        await self.close()

    async def create_session(self):
        """Create new aiohttp session"""
        print("Creating new aiohttp session")
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=10)  # 10 seconds timeout
            self.session = aiohttp.ClientSession(timeout=timeout)
            # Track the session
            _active_sessions.add(weakref.ref(self.session, lambda _: _active_sessions.discard(_)))
            print(f"Created new session, total active: {len(_active_sessions)}")
            print("Session created successfully")

    async def close(self):
        """Close the session"""
        if self._is_closing:
            print("Close already in progress, skipping")
            return
            
        self._is_closing = True
        print(f"Closing API client session for {self.endpoints.base_url}")
        
        if self.session and not self.session.closed:
            try:
                print(f"Closing session {id(self.session)}")
                await self.session.close()
                print("Session closed successfully")
            except Exception as e:
                print(f"Error closing session: {str(e)}")
            finally:
                self.session = None
                
        self._is_closing = False
                
    def _get_headers(self, include_auth: bool = True) -> Dict[str, str]:
        """Get request headers including auth token if available"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if include_auth and self._access_token:
            headers['Authorization'] = f'Bearer {self._access_token}'
        
        # Add session token if available
        if self._session_token:
            headers['X-Session-ID'] = self._session_token
            
        return headers

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Any:
        """Handle API response and potential errors"""
        print(f"Handling response with status: {response.status}")
        
        # Update rate limit info
        self._rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 20))
        reset_time = response.headers.get('X-RateLimit-Reset')
        if reset_time:
            self._rate_limit_reset = datetime.fromtimestamp(int(reset_time))

        try:
            data = await response.json()
            print(f"Response data: {data}")
        except json.JSONDecodeError:
            data = await response.text()
            print(f"Raw response text: {data}")

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
        include_auth: bool = True,
        retry_auth: bool = True
    ) -> Any:
        """Make HTTP request to API with optional token refresh"""
        await self.ensure_session()

        try:
            headers = self._get_headers(include_auth)
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                headers=headers,
                ssl=False  # Disable SSL verification for local development
            ) as response:
                # Update rate limit info
                self._rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 20))
                reset_time = response.headers.get('X-RateLimit-Reset')
                if reset_time:
                    self._rate_limit_reset = datetime.fromtimestamp(int(reset_time))

                # Check for 401 Unauthorized - token might be expired
                if response.status == 401 and retry_auth and self._master_password and self._user_email:
                    print("Token expired. Attempting to reauthenticate...")
                    
                    # Try to reauthenticate and retry the request
                    try:
                        # Relogin with stored credentials
                        await self.login(self._user_email, self._master_password)
                        
                        # Retry the request with new token
                        return await self._request(method, url, data, include_auth, False)
                    except Exception as e:
                        print(f"Reauthentication failed: {str(e)}")
                        # Let the original 401 error propagate

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
                
        except aiohttp.ClientError as e:
            raise APIError(
                message=f"Network error: {str(e)}",
                status_code=0
            )

    async def login(self, email: str, password: str) -> LoginResponse:
        """Log in user and get access token"""
        data = LoginRequest(email=email, password=password).model_dump()
        response = await self._request('POST', self.endpoints.login, data, include_auth=False)
        self._access_token = response['access_token']
        
        # Store session token if provided
        if 'session_token' in response:
            self._session_token = response['session_token']
        
        # Set token expiration (1 hour from now - matches server config)
        self._token_expires_at = datetime.now() + timedelta(hours=1)
        
        # Store credentials for potential auto-reconnect
        self._user_email = email
        self._master_password = password
        
        return LoginResponse(**response)

    async def logout(self):
        """Log out user and clear session"""
        print(f"Logging out session {id(self) if self else 'None'}")
        if self.session and not self.session.closed:
            try:
                await self._request('POST', self.endpoints.logout)
                print("Logout API request completed")
            except Exception as e:
                print(f"Error during logout request: {str(e)}")
            finally:
                self._access_token = None
                self._session_token = None
                self._token_expires_at = None
                self._master_password = None
                self._user_email = None
                await self.close()
                print("Logout cleanup complete")
        else:
            print("No active session to logout")

    async def register(self, email: str, password: str, invite_code: str):
        """Register new user"""
        data = RegisterRequest(
            email=email,
            password=password,
            invite_code=invite_code
        ).model_dump()
        return await self._request('POST', self.endpoints.register, data, include_auth=False)

    async def list_users(self) -> List[Dict[str, Any]]:
        """Get list of all users (admin only)"""
        response = await self._request('GET', self.endpoints.users)
        return response['users']

    async def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get user details by ID (admin only)"""
        return await self._request('GET', self.endpoints.user(user_id))

    async def update_user_status(self, user_id: int, is_active: bool) -> Dict[str, str]:
        """Enable or disable a user account (admin only)"""
        data = {'is_active': is_active}
        return await self._request('PATCH', self.endpoints.user(user_id), data)

    async def update_user_role(self, user_id: int, role: str) -> Dict[str, str]:
        """Update user role (admin only)"""
        data = {'role': role}
        return await self._request('PATCH', self.endpoints.user(user_id), data)

    async def delete_user(self, user_id: int) -> Dict[str, str]:
        """Delete a user (admin only)"""
        return await self._request('DELETE', self.endpoints.user(user_id))

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