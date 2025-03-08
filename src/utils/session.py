from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import os
from pathlib import Path

class UserSession:
    """Manages user session data and authentication tokens"""
    
    def __init__(self, user_id: int, role: str, access_token: str, 
                 session_token: Optional[str] = None, master_password: Optional[str] = None,
                 email: Optional[str] = None):
        """Initialize user session"""
        self.user_id = user_id
        self.role = role
        self.access_token = access_token
        self.session_token = session_token
        self._master_password = master_password  # Store master password temporarily
        self._user_email = email  # Store email for display
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.is_active = True
        self.vault_salt = None  # Store salt for vault unlocking
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role == 'admin'
    
    @property
    def session_age(self) -> timedelta:
        """Get session age"""
        return datetime.now() - self.created_at
    
    @property
    def master_password(self) -> Optional[str]:
        """Get master password (for vault unlocking only)"""
        return self._master_password
    
    @master_password.setter
    def master_password(self, value: str):
        """Set master password"""
        self._master_password = value
        
        # When setting a new master password, also try to unlock the vault
        if value and self.vault_salt:
            try:
                from crypto.vault import get_vault
                vault = get_vault()
                vault.unlock(value, self.vault_salt)
            except Exception as e:
                print(f"Error unlocking vault with new master password: {e}")
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
    
    def set_vault_salt(self, salt: str):
        """Set vault salt"""
        self.vault_salt = salt
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary (for storage)"""
        return {
            'user_id': self.user_id,
            'role': self.role,
            'access_token': self.access_token,
            'session_token': self.session_token,
            'user_email': self._user_email,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'is_active': self.is_active,
            'vault_salt': self.vault_salt  # Store salt for reuse
            # Note: master_password is intentionally not saved to disk for security
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], master_password: Optional[str] = None) -> 'UserSession':
        """Create session from dictionary (for loading)"""
        session = cls(
            user_id=data['user_id'],
            role=data['role'],
            access_token=data['access_token'],
            session_token=data.get('session_token'),
            master_password=master_password,
            email=data.get('user_email')
        )
        session.created_at = datetime.fromisoformat(data['created_at'])
        session.last_activity = datetime.fromisoformat(data['last_activity'])
        session.is_active = data['is_active']
        session.vault_salt = data.get('vault_salt')  # Get saved vault salt
        return session
    
    def save(self, config_dir: Path) -> None:
        """Save session to file"""
        session_file = config_dir / 'session.json'
        
        # Create config directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert to dictionary (master password not included)
        session_data = self.to_dict()
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=4)
    
    @classmethod
    def load(cls, config_dir: Path, master_password: Optional[str] = None) -> Optional['UserSession']:
        """Load session from file"""
        session_file = config_dir / 'session.json'
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            return cls.from_dict(session_data, master_password)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error loading session: {str(e)}")
            return None
    
    @staticmethod
    def clear(config_dir: Path) -> None:
        """Clear session data"""
        session_file = config_dir / 'session.json'
        
        if session_file.exists():
            os.remove(session_file)
            
    def clear_sensitive_data(self):
        """Clear sensitive data from memory"""
        # Clear master password
        self._master_password = None