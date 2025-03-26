from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    role: str
    user_id: int
    session_token: Optional[str] = None

class RegisterRequest(BaseModel):
    """Request model for user registration"""
    email: str
    password: str
    invite_code: str
    
    class Config:
        # Allow extra fields in case server API changes
        extra = "ignore"
        
    def model_dump(self) -> dict:
        """
        Convert model to dictionary compatible with API request.
        This is helpful for backward compatibility with older Pydantic versions.
        """
        if hasattr(super(), "model_dump"):
            # For Pydantic v2+
            return super().model_dump()
        elif hasattr(super(), "dict"):
            # For Pydantic v1
            return super().dict()
        else:
            # Manual fallback
            return {
                "email": self.email,
                "password": self.password,
                "invite_code": self.invite_code
            }

class VaultSetupRequest(BaseModel):
    master_password: str

class EncryptedEntry(BaseModel):
    iv: str  # base64 encoded
    ciphertext: str  # base64 encoded
    salt: str  # base64 encoded

class EntryData(BaseModel):
    title: str
    username: str
    password: str
    url: Optional[str] = None
    notes: Optional[str] = None
    category: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class PasswordEntry(BaseModel):
    id: int
    encrypted_data: str
    created_at: datetime
    updated_at: datetime

class EntryVersion(BaseModel):
    id: int
    encrypted_data: str
    created_at: datetime

class User(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: Optional[str] = None

class APIError(Exception):
    def __init__(self, message: str, status_code: int):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)