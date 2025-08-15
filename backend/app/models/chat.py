"""
Chat and ChatMember models for managing conversations
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class ChatType(enum.Enum):
    PRIVATE = "private"
    GROUP = "group"
    CHANNEL = "channel"


class MemberRole(enum.Enum):
    MEMBER = "member"
    ADMIN = "admin"
    OWNER = "owner"


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)  # Null for private chats
    description = Column(Text, nullable=True)
    chat_type = Column(Enum(ChatType), nullable=False, default=ChatType.PRIVATE)
    
    # Group/Channel settings
    avatar_url = Column(String, nullable=True)
    is_public = Column(Boolean, default=False)
    invite_link = Column(String, nullable=True, unique=True)
    max_members = Column(Integer, default=1000)
    
    # Privacy settings
    allow_invite_link = Column(Boolean, default=True)
    allow_messages_from_non_members = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    
    # Creator information
    created_by_id = Column(Integer, ForeignKey("users.id"))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by_id])
    members = relationship("ChatMember", back_populates="chat", cascade="all, delete-orphan")
    messages = relationship("Message", foreign_keys="Message.chat_id", back_populates="chat", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Chat {self.id}: {self.name or 'Private'}>"


class ChatMember(Base):
    __tablename__ = "chat_members"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Member settings
    role = Column(Enum(MemberRole), default=MemberRole.MEMBER)
    nickname = Column(String, nullable=True)  # Custom name in this chat
    
    # Permissions
    can_send_messages = Column(Boolean, default=True)
    can_add_members = Column(Boolean, default=False)
    can_edit_chat = Column(Boolean, default=False)
    can_delete_messages = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_muted = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)
    
    # Message tracking
    last_read_message_id = Column(Integer, nullable=True)
    unread_count = Column(Integer, default=0)
    
    # Timestamps
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    left_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    chat = relationship("Chat", back_populates="members")
    user = relationship("User", back_populates="chat_memberships")
    
    def __repr__(self):
        return f"<ChatMember {self.user_id} in {self.chat_id}>"
