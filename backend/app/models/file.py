"""
File model for handling media uploads and attachments
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class FileType(enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    VOICE = "voice"
    DOCUMENT = "document"
    STICKER = "sticker"


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    
    # File information
    original_name = Column(String, nullable=False)
    file_name = Column(String, nullable=False)  # Generated filename on server
    file_path = Column(String, nullable=False)  # Relative path to file
    file_url = Column(String, nullable=True)  # Public URL if using cloud storage
    
    # File properties
    file_type = Column(Enum(FileType), nullable=False)
    mime_type = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)  # Size in bytes
    
    # Media-specific properties (for images/videos)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True)  # For audio/video in seconds
    
    # Thumbnail for videos/images
    thumbnail_path = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    
    # Upload information
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Status
    is_processed = Column(Boolean, default=True)  # For videos that need processing
    is_public = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    uploader = relationship("User", back_populates="uploaded_files")
    
    def __repr__(self):
        return f"<File {self.id}: {self.original_name}>"
    
    @property
    def file_size_mb(self) -> float:
        """Return file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def is_image(self) -> bool:
        """Check if file is an image"""
        return self.file_type == FileType.IMAGE
    
    @property
    def is_video(self) -> bool:
        """Check if file is a video"""
        return self.file_type == FileType.VIDEO
    
    @property
    def is_audio(self) -> bool:
        """Check if file is audio"""
        return self.file_type in [FileType.AUDIO, FileType.VOICE]
