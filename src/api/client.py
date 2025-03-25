import aiohttp
import json
import asyncio
import weakref
from typing import Optional, Dict, Any, Union, ClassVar
from datetime import datetime, timedelta
from urllib.parse import urljoin
from typing import List, Dict, Any, Optional
from utils.async_utils import async_callback

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
    
    def __new__(cls, base_url: str):
        """
        Override __new__ to implement the singleton pattern per base_url.
        This ensures that only one instance is created per base URL.
        """
        # Normalize the base URL to avoid duplicates due to trailing slashes
        base_url = base_url.rstrip('/')
        
        # Check if an instance already exists for this base URL
        if base_url in cls._instance_cache:
            print(f"Returning existing APIClient instance for {base_url}")
            return cls._instance_cache[base_url]
        
        # Create a new instance if none exists
        instance = super().__new__(cls)
        cls._instance_cache[base_url] = instance
        
        # Store base_url in the instance for use in __init__
        instance._base_url = base_url
        
        return instance

    def __init__(self, base_url: str):
        """Initialize API client with base URL"""
        # Normalize the base URL
        base_url = base_url.rstrip('/')
        
        # Check if this instance has already been initialized
        if hasattr(self, 'initialized') and self.initialized and hasattr(self, '_base_url') and self._base_url == base_url:
            return

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
        self._auth_retry_count = 0

        # Mark as initialized
        self.initialized = True

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
        print(f"Ensuring session for {self.endpoints.base_url}")
        
        # Check if we already have this exact session in _active_sessions
        if hasattr(self, 'session') and self.session:
            for session_ref in list(_active_sessions):
                session = session_ref()
                if session is self.session:
                    if not session.closed:
                        print("Session already exists in active sessions and is open")
                        return
                    else:
                        print("Session exists in active sessions but is closed")
                        # Will create a new one below
                        break
        
        # Only create a new session if we don't have one or the existing one is closed
        if self.session is None or self.session.closed:
            print("Session is None or closed, creating new session")
            try:
                # If we already have a session, make sure to close it first
                if self.session is not None and not self.session.closed:
                    try:
                        print(f"Closing existing session before creating a new one")
                        await self.session.close()
                    except Exception as e:
                        print(f"Error closing existing session: {str(e)}")
                
                # Now create a fresh session
                timeout = aiohttp.ClientTimeout(total=30)
                self.session = aiohttp.ClientSession(timeout=timeout)
            
                # Track the session
                _active_sessions.add(weakref.ref(self.session, lambda _: _active_sessions.discard(_)))
                print(f"Created new session, total active: {len(_active_sessions)}")
            except Exception as e:
                print(f"Error creating session: {str(e)}")
                import traceback
                traceback.print_exc()
                raise
        else:
            print("Using existing session")

    @property
    def is_authenticated(self) -> bool:
        """Check if client has valid access token"""
        return bool(self._access_token) and (
            self._token_expires_at is None or 
            self._token_expires_at > datetime.now()
        )
    
    def set_master_password(self, password: str) -> None:
        """
        Set master password for vault operations.
        Also initializes vault if salt is available.
        
        Args:
            password: User's master password
        """
        self._master_password = password
        
        # If we already have a salt, try to unlock the vault
        if hasattr(self, 'user_session') and self.user_session and self.user_session.vault_salt:
            from crypto.vault import get_vault
            vault = get_vault()
            vault.unlock(password, self.user_session.vault_salt)

    async def list_invite_codes(self) -> List[Dict[str, Any]]:
        """List all invite codes (admin only)"""
        try:
            response = await self._request('GET', self.endpoints.invites)
            return response['invite_codes']
        except Exception as e:
            print(f"Error listing invite codes: {str(e)}")
            # Return empty list if endpoint not yet implemented
            return []

    async def deactivate_invite_code(self, invite_code: str) -> Dict[str, str]:
        """Deactivate an invite code (admin only)"""
        try:
            return await self._request(
                'DELETE', 
                self.endpoints.invite_code(invite_code)
            )
        except Exception as e:
            print(f"Error deactivating invite code: {str(e)}")
            raise e

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
                import traceback
                traceback.print_exc()
            finally:
                self.session = None
            
        self._is_closing = False

    def sync_close(self):
        """Synchronous version of close method for cleanup operations"""
        print(f"Synchronous close of API client for {self.endpoints.base_url}")
        if self.session and not self.session.closed:
            try:
                # Create an event loop if needed
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Run close operation
                loop.run_until_complete(self.close())
                print("Session closed successfully (sync)")
            except Exception as e:
                print(f"Error in sync_close: {str(e)}")
                import traceback
                traceback.print_exc()
                
    def _get_headers(self, include_auth: bool = True) -> Dict[str, str]:
        """Get request headers including auth token if available"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if include_auth and self._access_token:
            headers['Authorization'] = f'Bearer {self._access_token}'
        
        # Add session token if available - ensure this runs for ALL requests
        if hasattr(self, '_session_token') and self._session_token:
            headers['X-API-Session-Token'] = self._session_token
        
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
        print(f"=== API Request: {method} {url} ===")
        await self.ensure_session()

        try:
            print(f"Preparing headers, auth included: {include_auth}")
            headers = self._get_headers(include_auth)
            print(f"Headers: {headers}")
            if data:
                print(f"Request data: {data}")
            
            print(f"Sending request to: {url}")
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                headers=headers,
                ssl=False  # Disable SSL verification for local development
            ) as response:
                print(f"Response status: {response.status}")
                
                # Update rate limit info
                self._rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 20))
                reset_time = response.headers.get('X-RateLimit-Reset')
                if reset_time:
                    self._rate_limit_reset = datetime.fromtimestamp(int(reset_time))

                # Check for 401 Unauthorized - token might be expired
                if response.status == 401 and retry_auth and self._master_password and self._user_email:
                    # Increment retry counter to prevent infinite loops
                    self._auth_retry_count += 1
                    
                    # Only retry up to 3 times to prevent infinite loops
                    if self._auth_retry_count > 3:
                        print(f"Authentication retry limit exceeded ({self._auth_retry_count}), giving up")
                        self._auth_retry_count = 0  # Reset for future requests
                        
                        # Read the response for error details
                        try:
                            error_data = await response.json()
                            error_msg = error_data.get('message', 'Authentication failed')
                        except:
                            error_msg = "Authentication failed"
                            
                        raise APIError(
                            message=f"Authentication failed after multiple retries. The server may have restarted with new credentials: {error_msg}",
                            status_code=401
                        )
                    
                    print(f"Token expired. Attempting to reauthenticate... (retry #{self._auth_retry_count})")
                    
                    # Try to reauthenticate and retry the request
                    try:
                        # Relogin with stored credentials
                        login_response = await self.login(self._user_email, self._master_password)
                        
                        # Important: Update session token from login response
                        if hasattr(login_response, 'session_token') and login_response.session_token:
                            self._session_token = login_response.session_token
                            print(f"Updated session token after reauthentication: {self._session_token}")
                        
                        # Reset retry counter on success
                        self._auth_retry_count = 0
                        
                        # Retry the request with new token
                        return await self._request(method, url, data, include_auth, False)
                    except Exception as e:
                        print(f"Reauthentication failed: {str(e)}")
                        # Let the original 401 error propagate but with more detail
                        raise APIError(
                            message=f"Failed to reauthenticate: {str(e)}. The server may have restarted.",
                            status_code=401
                        )

                try:
                    print("Reading response content")
                    try:
                        data = await response.json()
                        print(f"JSON response: {data}")
                    except json.JSONDecodeError:
                        data = await response.text()
                        print(f"Text response: {data}")

                    if not response.ok:
                        print(f"Error response - Status: {response.status}, Message: {data}")
                        raise APIError(
                            message=data.get('message', 'Unknown error'),
                            status_code=response.status
                        )

                    # Reset retry counter on success
                    self._auth_retry_count = 0
                    return data
                except Exception as e:
                    print(f"Error processing response: {str(e)}")
                    raise
                
        except aiohttp.ClientError as e:
            print(f"Network error: {str(e)}")
            raise APIError(
                message=f"Network error: {str(e)}",
                status_code=0
            )
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

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

    async def list_categories(self) -> List[Dict[str, Any]]:
        """Get all categories for the current user"""
        try:
            print(f"Fetching categories from: {self.endpoints.categories}")
            response = await self._request('GET', self.endpoints.categories)
            print(f"Category response: {response}")
            if isinstance(response, dict) and 'categories' in response:
                return response['categories']
            else:
                print(f"Unexpected response format: {response}")
                return []
        except Exception as e:
            print(f"Error listing categories: {str(e)}")
            # Return empty list on error to avoid UI breaking
            return []


    async def create_category(self, name: str, parent_id: Optional[int] = None) -> Dict[str, Any]:
        """Create a new category"""
        data = {
            'name': name
        }
        if parent_id is not None:
            data['parent_id'] = parent_id
        
        try:
            print(f"Creating category: {name}")
            response = await self._request('POST', self.endpoints.categories, data)
            print(f"Create category response: {response}")
            if isinstance(response, dict) and 'category' in response:
                return response['category']
            else:
                print(f"Unexpected response format: {response}")
                return {'id': None, 'name': name}
        except Exception as e:
            print(f"Error creating category: {str(e)}")
            raise

    async def get_category(self, category_id: int) -> Dict[str, Any]:
        """Get a specific category"""
        return await self._request('GET', self.endpoints.category(category_id))

    async def update_category(self, category_id: int, name: Optional[str] = None, parent_id: Optional[int] = None) -> Dict[str, Any]:
        """Update a category"""
        data = {}
        if name is not None:
            data['name'] = name
        if parent_id is not None:
            data['parent_id'] = parent_id
        
        response = await self._request('PUT', self.endpoints.category(category_id), data)
        return response['category']

    async def delete_category(self, category_id: int) -> Dict[str, str]:
        """Delete a category"""
        return await self._request('DELETE', self.endpoints.category(category_id))

    async def logout(self):
        """
        Log out user and clear session.
        Also locks the vault and clears sensitive data.
        """
        print(f"Logging out session {id(self) if self else 'None'}")
        if self.session and not self.session.closed:
            try:
                await self._request('POST', self.endpoints.logout)
                print("Logout API request completed")
            except Exception as e:
                print(f"Error during logout request: {str(e)}")
            finally:
                # Lock vault and clear sensitive data
                from crypto.vault import get_vault
                vault = get_vault()
                vault.lock()
                
                # Clear session data
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
        """
        Register new user with invite code
    
        Parameters:
        email (str): User's email address
        password (str): User's password
        invite_code (str): Invite code provided by admin
    
        Returns:
        dict: Registration response data
    
        Raises:
        APIError: If registration fails
        """
        data = {
            "email": email,
            "password": password,
            "invite_code": invite_code
        }
    
        try:
            await self.ensure_session()
        
            # Debug logging
            print(f"Sending registration request to: {self.endpoints.register}")
            print(f"Registration data: {data}")
        
            # Make the API request
            response = await self._request(
                'POST', 
                self.endpoints.register, 
                data, 
                include_auth=False,  # No auth needed for registration
                retry_auth=False     # Don't retry auth for registration
            )
        
            print(f"Registration response: {response}")
            return response
        
        except aiohttp.ClientError as e:
            error_msg = f"Network error during registration: {str(e)}"
            print(error_msg)
            raise APIError(message=error_msg, status_code=0)
        except Exception as e:
            error_msg = f"Error during registration: {str(e)}"
            print(error_msg)
            raise

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

    async def change_password(self, current_password: str, new_password: str) -> Dict[str, Any]:
        """
        Change user's password and re-encrypt vault entries
        
        Args:
            current_password (str): Current password
            new_password (str): New password
                
        Returns:
            Dict[str, Any]: Response containing new vault salt
        """
        print(f"Changing password for user")
        
        # Import needed modules at the top to avoid UnboundLocalError
        from crypto.vault import get_vault
        
        data = {
            'current_password': current_password,
            'new_password': new_password
        }
        
        try:
            # First get all current entries
            entries = await self.list_entries()
            decrypted_entries = []
            
            # Decrypt entries with current password and salt
            vault = get_vault()
            if vault.is_unlocked():
                for entry in entries:
                    try:
                        decrypted_data = vault.decrypt_entry(entry.encrypted_data)
                        decrypted_entries.append((entry.id, decrypted_data))
                    except Exception as e:
                        print(f"Warning: Could not decrypt entry {entry.id}: {e}")
            
            # Now change the password
            response = await self._request('PUT', self.endpoints.change_password, data)
            
            # Update master password after successful change
            if 'new_salt' in response:
                print(f"Password changed successfully, updating local data with new salt")
                self._master_password = new_password
                
                # Try to unlock vault with new credentials
                # Note: get_vault is already imported at the top
                vault = get_vault()
                # First lock the vault to ensure clean state
                try:
                    vault.lock()
                    print("Locked vault before re-initializing with new credentials")
                except Exception as e:
                    print(f"Non-critical error while locking vault: {e}")
                    
                # Now unlock with new credentials
                new_salt = response['new_salt']
                if vault.unlock(new_password, new_salt):
                    print("Vault unlocked with new password")
                    
                    # Re-encrypt entries with new password and salt
                    if decrypted_entries:
                        print(f"Re-encrypting {len(decrypted_entries)} entries with new password")
                        for entry_id, decrypted_data in decrypted_entries:
                            try:
                                # Encrypt with new key
                                encrypted_data = vault.encrypt_entry(decrypted_data)
                                # Update entry
                                await self.update_entry(entry_id, encrypted_data)
                                print(f"Successfully re-encrypted entry {entry_id}")
                            except Exception as e:
                                print(f"Error re-encrypting entry {entry_id}: {e}")
                else:
                    print("WARNING: Failed to unlock vault with new password")
                
                # Update user_session if exists
                if hasattr(self, 'user_session') and self.user_session:
                    self.user_session.master_password = new_password
                    self.user_session.set_vault_salt(new_salt)
                    print("Updated user session with new credentials")
            
            return response
            
        except Exception as e:
            print(f"Error changing password: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Create a descriptive error message
            if hasattr(e, 'message'):
                error_message = e.message
            else:
                error_message = str(e)
                
            if "401" in error_message:
                raise Exception("Current password is incorrect") from e
            else:
                raise Exception(f"Failed to change password: {error_message}") from e

    async def delete_user(self, user_id: int) -> Dict[str, str]:
        """Delete a user (admin only)"""
        return await self._request('DELETE', self.endpoints.user(user_id))

    async def create_invite(self) -> str:
        """Create invite code (admin only)"""
        response = await self._request('POST', self.endpoints.create_invite)
        return response['invite_code']

    async def setup_vault(self, master_password: str):
        """
        Initialize user's vault with master password.
        
        Args:
            master_password: User's master password for vault encryption
        """
        data = {'master_password': master_password}
        response = await self._request('POST', self.endpoints.vault_setup, data)
        
        # Initialize vault with master password and salt
        from crypto.vault import get_vault
        salt = response.get('salt') or await self.get_vault_salt()
        
        # Unlock vault with master password and salt
        vault = get_vault()
        vault.unlock(master_password, salt)
        
        # Store master password for future vault unlocking
        if hasattr(self, '_master_password'):
            self._master_password = master_password
        
        return response

    async def get_vault_salt(self):
        """
        Get vault salt for key derivation.
        Fetches salt from server and caches it for future use.
        """
        try:
            # Make sure we have a valid session before proceeding
            await self.ensure_session()
            
            # Make the API request
            print("Requesting vault salt from server")
            response = await self._request('GET', self.endpoints.vault_salt)
            
            # Extract salt from response
            salt = response.get('salt')
            if not salt:
                print("Warning: Server returned empty salt")
                return None
                
            print(f"Retrieved vault salt from server: {salt[:10]}...")
            
            # Store salt for later use if we have a user session
            if hasattr(self, 'user_session') and self.user_session and hasattr(self.user_session, 'set_vault_salt'):
                self.user_session.set_vault_salt(salt)
                print("Stored salt in user session")
            else:
                print("Warning: Cannot store salt in user session")
            
            # Try to unlock vault if we have a master password
            if hasattr(self, '_master_password') and self._master_password:
                from crypto.vault import get_vault
                vault = get_vault()
                if vault.unlock(self._master_password, salt):
                    print("Vault unlocked successfully after getting salt")
                else:
                    print("Failed to unlock vault after getting salt")
            
            return salt
        except Exception as e:
            print(f"Error getting vault salt: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    async def create_entry(self, entry_data: Dict[str, Any]) -> PasswordEntry:
        """
        Create new password entry.
        
        Args:
            entry_data: Dictionary with entry fields (will be encrypted)
        
        Returns:
            PasswordEntry object
        """
        # Check if entry_data is already encrypted
        if isinstance(entry_data, str):
            # Already encrypted
            encrypted_data = entry_data
        else:
            # Need to encrypt using vault
            from crypto.vault import get_vault
            vault = get_vault()
            if not vault.is_unlocked():
                # Try to unlock with master password and salt
                if hasattr(self, '_master_password') and hasattr(self.user_session, 'vault_salt'):
                    vault.unlock(self._master_password, self.user_session.vault_salt)
                else:
                    raise ValueError("Vault is locked and cannot encrypt data")
            
            # Encrypt the entry data
            encrypted_data = vault.encrypt_entry(entry_data)
        
        # Send to server
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

    async def update_entry(self, entry_id: int, entry_data: Union[str, Dict[str, Any]]) -> Dict[str, Union[str, int]]:
        """
        Update password entry.
        
        Args:
            entry_id: ID of the entry to update
            entry_data: Dictionary with entry fields or encrypted JSON string
        
        Returns:
            Response from server
        """
        # Check if entry_data is already encrypted
        if isinstance(entry_data, str):
            # Already encrypted
            encrypted_data = entry_data
        else:
            # Need to encrypt using vault
            from crypto.vault import get_vault
            vault = get_vault()
            if not vault.is_unlocked():
                # Try to unlock with master password and salt
                if hasattr(self, '_master_password') and hasattr(self, 'user_session') and hasattr(self.user_session, 'vault_salt'):
                    vault.unlock(self._master_password, self.user_session.vault_salt)
                else:
                    raise ValueError("Vault is locked and cannot encrypt data")
            
            # Log entry data for debugging
            print(f"Entry data before encryption: {entry_data}")
            
            # Ensure title is included
            if 'title' not in entry_data or not entry_data['title']:
                raise ValueError("Title is required")
            
            # Encrypt the entry data
            encrypted_data = vault.encrypt_entry(entry_data)

        # Send to server
        data = {'encrypted_data': encrypted_data}
        print(f"Sending update for entry {entry_id} with data: {encrypted_data[:30]}...")
        response = await self._request('PUT', self.endpoints.vault_entry(entry_id), data)
        print(f"Update response: {response}")
        return response

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