"""
Pydantic schemas for authentication and user management
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""
    email: str
    username: str = Field(..., min_length=3, max_length=30)
    full_name: str = Field(..., min_length=2, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=3, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str  # Can be email or username
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None
    phone_number: Optional[str] = None
    show_last_seen: Optional[bool] = None
    show_read_receipts: Optional[bool] = None
    allow_groups: Optional[bool] = None


class UserResponse(BaseModel):
    """Schema for user response (excludes sensitive data)"""
    id: int
    email: str
    username: str
    full_name: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_online: bool
    last_seen: Optional[datetime] = None
    show_last_seen: bool
    show_read_receipts: bool
    allow_groups: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserPublic(BaseModel):
    """Schema for public user information (limited data)"""
    id: int
    username: str
    full_name: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    is_online: bool
    last_seen: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TokenData(BaseModel):
    """Schema for token data"""
    user_id: int


class Token(BaseModel):
    """Schema for authentication tokens"""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str


class PasswordReset(BaseModel):
    """Schema for password reset"""
    token: str
    new_password: str = Field(..., min_length=3, max_length=100)


class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str
    new_password: str = Field(..., min_length=3, max_length=100)
