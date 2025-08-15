"""
User model for authentication and user management
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from passlib.context import CryptContext

from app.core.database import Base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Profile information
    bio = Column(Text, nullable=True)
    avatar_url = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    status_message = Column(String, nullable=True, default="Hey there! I'm using this chat app.")
    
    # Status and settings
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, nullable=True)
    
    # Privacy settings
    show_last_seen = Column(Boolean, default=True)
    show_read_receipts = Column(Boolean, default=True)
    allow_groups = Column(Boolean, default=True)
    allow_friend_requests = Column(Boolean, default=True)
    discoverable_by_username = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    chat_memberships = relationship("ChatMember", back_populates="user")
    uploaded_files = relationship("File", back_populates="uploader")
    message_reactions = relationship("MessageReaction", back_populates="user")
    sent_friend_requests = relationship("Friendship", foreign_keys="Friendship.requester_id", back_populates="requester")
    received_friend_requests = relationship("Friendship", foreign_keys="Friendship.addressee_id", back_populates="addressee")
    blocked_users = relationship("UserBlock", foreign_keys="UserBlock.blocker_id", back_populates="blocker")
    blocked_by_users = relationship("UserBlock", foreign_keys="UserBlock.blocked_id", back_populates="blocked_user")
    
    def set_password(self, password: str):
        """Hash and set user password"""
        self.hashed_password = pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(password, self.hashed_password)
    
    def __repr__(self):
        return f"<User {self.username}>"
