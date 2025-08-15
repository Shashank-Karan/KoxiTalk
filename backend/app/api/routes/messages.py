"""
Message management routes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.chat import Chat, ChatMember
from app.models.message import Message, MessageReaction, MessageType, MessageStatus
from app.api.routes.auth import get_current_user
from sqlalchemy import desc, and_

router = APIRouter()


# Pydantic schemas for request/response
class MessageCreate(BaseModel):
    content: str
    chat_id: int
    message_type: MessageType = MessageType.TEXT
    reply_to_message_id: Optional[int] = None
    file_id: Optional[int] = None


class MessageUpdate(BaseModel):
    content: str


class ReactionCreate(BaseModel):
    reaction: str


@router.get("/")
async def get_messages(
    chat_id: int,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages for a specific chat"""
    
    # Check if user is member of the chat
    chat_member = db.query(ChatMember).filter(
        ChatMember.chat_id == chat_id,
        ChatMember.user_id == current_user.id,
        ChatMember.is_active == True
    ).first()
    
    if not chat_member:
        raise HTTPException(status_code=403, detail="You are not a member of this chat")
    
    # Get messages with reactions
    messages = db.query(Message).filter(
        Message.chat_id == chat_id,
        Message.is_deleted == False
    ).order_by(desc(Message.created_at)).offset(offset).limit(limit).all()
    
    # Load reactions for each message
    messages_with_reactions = []
    for message in messages:
        reactions = db.query(MessageReaction).filter(
            MessageReaction.message_id == message.id
        ).all()
        
        message_dict = {
            "id": message.id,
            "content": message.content,
            "sender_id": message.sender_id,
            "sender_name": message.sender.full_name if message.sender else "Unknown",
            "message_type": message.message_type,
            "reply_to_message_id": message.reply_to_message_id,
            "is_edited": message.is_edited,
            "created_at": message.created_at,
            "updated_at": message.updated_at,
            "reactions": [
                {
                    "id": r.id,
                    "reaction": r.reaction,
                    "user_id": r.user_id,
                    "user_name": r.user.full_name if r.user else "Unknown"
                } for r in reactions
            ]
        }
        messages_with_reactions.append(message_dict)
    
    # Return messages in chronological order (oldest first for display)
    messages_with_reactions.reverse()
    
    # Return just the messages array for frontend compatibility
    return messages_with_reactions


@router.post("/")
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a new message"""
    
    # Check if user is member of the chat
    chat_member = db.query(ChatMember).filter(
        ChatMember.chat_id == message_data.chat_id,
        ChatMember.user_id == current_user.id,
        ChatMember.is_active == True,
        ChatMember.can_send_messages == True
    ).first()
    
    if not chat_member:
        raise HTTPException(status_code=403, detail="You cannot send messages to this chat")
    
    # Validate reply_to_message if provided
    if message_data.reply_to_message_id:
        reply_message = db.query(Message).filter(
            Message.id == message_data.reply_to_message_id,
            Message.chat_id == message_data.chat_id,
            Message.is_deleted == False
        ).first()
        
        if not reply_message:
            raise HTTPException(status_code=404, detail="Reply message not found")
    
    # Create message
    new_message = Message(
        chat_id=message_data.chat_id,
        sender_id=current_user.id,
        content=message_data.content,
        message_type=message_data.message_type,
        reply_to_message_id=message_data.reply_to_message_id,
        file_id=message_data.file_id,
        status=MessageStatus.SENT
    )
    
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    # Update chat's last message timestamp
    chat = db.query(Chat).filter(Chat.id == message_data.chat_id).first()
    if chat:
        chat.last_message_at = new_message.created_at
        db.commit()
    
    return {
        "id": new_message.id,
        "content": new_message.content,
        "sender_id": new_message.sender_id,
        "sender_name": current_user.full_name,
        "message_type": new_message.message_type,
        "reply_to_message_id": new_message.reply_to_message_id,
        "created_at": new_message.created_at,
        "message": "Message sent successfully"
    }


@router.put("/{message_id}")
async def edit_message(
    message_id: int,
    message_update: MessageUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Edit a message"""
    
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.sender_id == current_user.id,
        Message.is_deleted == False
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found or you don't have permission to edit it")
    
    # Update message
    message.content = message_update.content
    message.is_edited = True
    message.edited_at = db.execute("SELECT NOW()").scalar()
    
    db.commit()
    db.refresh(message)
    
    return {"message": "Message updated successfully"}


@router.delete("/{message_id}")
async def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a message"""
    
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.is_deleted == False
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check permissions - user can delete their own message or if they're admin
    can_delete = False
    
    if message.sender_id == current_user.id:
        can_delete = True
    else:
        # Check if user is admin/owner of the chat
        chat_member = db.query(ChatMember).filter(
            ChatMember.chat_id == message.chat_id,
            ChatMember.user_id == current_user.id,
            ChatMember.can_delete_messages == True
        ).first()
        can_delete = bool(chat_member)
    
    if not can_delete:
        raise HTTPException(status_code=403, detail="You don't have permission to delete this message")
    
    # Soft delete
    message.is_deleted = True
    message.deleted_at = db.execute("SELECT NOW()").scalar()
    
    db.commit()
    
    return {"message": "Message deleted successfully"}


# Message Reactions

@router.post("/{message_id}/reactions")
async def add_reaction(
    message_id: int,
    reaction_data: ReactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a reaction to a message"""
    
    # Check if message exists and user has access
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.is_deleted == False
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check if user is member of the chat
    chat_member = db.query(ChatMember).filter(
        ChatMember.chat_id == message.chat_id,
        ChatMember.user_id == current_user.id,
        ChatMember.is_active == True
    ).first()
    
    if not chat_member:
        raise HTTPException(status_code=403, detail="You don't have access to this chat")
    
    # Check if user already reacted with this emoji
    existing_reaction = db.query(MessageReaction).filter(
        MessageReaction.message_id == message_id,
        MessageReaction.user_id == current_user.id,
        MessageReaction.reaction == reaction_data.reaction
    ).first()
    
    if existing_reaction:
        # Remove existing reaction (toggle)
        db.delete(existing_reaction)
        db.commit()
        return {"message": "Reaction removed"}
    
    # Add new reaction
    new_reaction = MessageReaction(
        message_id=message_id,
        user_id=current_user.id,
        reaction=reaction_data.reaction
    )
    
    db.add(new_reaction)
    db.commit()
    db.refresh(new_reaction)
    
    return {
        "id": new_reaction.id,
        "reaction": new_reaction.reaction,
        "message": "Reaction added successfully"
    }


@router.delete("/{message_id}/reactions/{reaction_id}")
async def remove_reaction(
    message_id: int,
    reaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a specific reaction from a message"""
    
    reaction = db.query(MessageReaction).filter(
        MessageReaction.id == reaction_id,
        MessageReaction.message_id == message_id,
        MessageReaction.user_id == current_user.id
    ).first()
    
    if not reaction:
        raise HTTPException(status_code=404, detail="Reaction not found or you don't have permission to remove it")
    
    db.delete(reaction)
    db.commit()
    
    return {"message": "Reaction removed successfully"}


@router.get("/{message_id}/reactions")
async def get_message_reactions(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all reactions for a message"""
    
    # Check if message exists and user has access
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.is_deleted == False
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check if user is member of the chat
    chat_member = db.query(ChatMember).filter(
        ChatMember.chat_id == message.chat_id,
        ChatMember.user_id == current_user.id,
        ChatMember.is_active == True
    ).first()
    
    if not chat_member:
        raise HTTPException(status_code=403, detail="You don't have access to this chat")
    
    reactions = db.query(MessageReaction).filter(
        MessageReaction.message_id == message_id
    ).all()
    
    return {
        "reactions": [
            {
                "id": r.id,
                "reaction": r.reaction,
                "user_id": r.user_id,
                "user_name": r.user.full_name if r.user else "Unknown",
                "created_at": r.created_at
            } for r in reactions
        ]
    }
