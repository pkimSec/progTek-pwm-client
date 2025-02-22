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

class RegisterRequest(BaseModel):
    email: str
    password: str
    invite_code: str

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

class APIError(Exception):
    def __init__(self, message: str, status_code: int):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)