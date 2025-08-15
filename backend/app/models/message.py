"""
Message and MessageReaction models for chat messages
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class MessageType(enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    VOICE = "voice"
    DOCUMENT = "document"
    LOCATION = "location"
    CONTACT = "contact"
    STICKER = "sticker"
    SYSTEM = "system"  # For system messages like "User joined"


class MessageStatus(enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Message content
    content = Column(Text, nullable=True)  # Text content
    message_type = Column(Enum(MessageType), default=MessageType.TEXT)
    
    # Reply functionality
    reply_to_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    
    # Forward functionality
    forwarded_from_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    forwarded_from_chat_id = Column(Integer, ForeignKey("chats.id"), nullable=True)
    
    # File attachment
    file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    
    # Message metadata
    message_metadata = Column(JSON, nullable=True)  # For storing additional data (location coords, contact info, etc.)
    
    # Message status
    status = Column(Enum(MessageStatus), default=MessageStatus.SENT)
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    edited_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    chat = relationship("Chat", foreign_keys=[chat_id], back_populates="messages")
    forwarded_from_chat = relationship("Chat", foreign_keys=[forwarded_from_chat_id])
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    file = relationship("File", backref="message")
    reactions = relationship("MessageReaction", back_populates="message", cascade="all, delete-orphan")
    
    # Self-referential relationships for replies and forwards
    reply_to = relationship("Message", foreign_keys=[reply_to_message_id], remote_side=[id], backref="replies")
    forwarded_from = relationship("Message", foreign_keys=[forwarded_from_message_id], remote_side=[id], backref="forwards")
    
    def __repr__(self):
        return f"<Message {self.id} in Chat {self.chat_id}>"


class MessageReaction(Base):
    __tablename__ = "message_reactions"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Reaction content (emoji or reaction type)
    reaction = Column(String, nullable=False)  # e.g., "👍", "❤️", "😂"
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    message = relationship("Message", back_populates="reactions")
    user = relationship("User", back_populates="message_reactions")
    
    def __repr__(self):
        return f"<Reaction {self.reaction} by {self.user_id} on {self.message_id}>"
