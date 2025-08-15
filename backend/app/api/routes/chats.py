"""
Chat management routes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.chat import Chat, ChatMember, ChatType, MemberRole
from app.models.message import Message
from app.api.routes.auth import get_current_user
from app.models.friendship import Friendship, FriendshipStatus
from sqlalchemy import or_, and_, desc, func

router = APIRouter()


# Pydantic schemas
class ChatCreate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    chat_type: ChatType = ChatType.PRIVATE
    participant_ids: List[int]


class ChatUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None


class MemberUpdate(BaseModel):
    role: Optional[MemberRole] = None
    can_send_messages: Optional[bool] = None
    can_add_members: Optional[bool] = None
    can_edit_chat: Optional[bool] = None
    can_delete_messages: Optional[bool] = None


@router.get("/")
async def get_user_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all chats for the current user"""
    
    # Get user's chat memberships
    chat_memberships = db.query(ChatMember).filter(
        ChatMember.user_id == current_user.id,
        ChatMember.is_active == True
    ).all()
    
    chats_data = []
    
    for membership in chat_memberships:
        chat = membership.chat
        if not chat or not chat.is_active:
            continue
            
        # Get last message
        last_message = db.query(Message).filter(
            Message.chat_id == chat.id,
            Message.is_deleted == False
        ).order_by(desc(Message.created_at)).first()
        
        # Get other participants for private chats
        other_participants = db.query(ChatMember).filter(
            ChatMember.chat_id == chat.id,
            ChatMember.user_id != current_user.id,
            ChatMember.is_active == True
        ).all()
        
        participants_data = []
        for participant_member in other_participants:
            if participant_member.user:
                participants_data.append({
                    "id": participant_member.user.id,
                    "username": participant_member.user.username,
                    "full_name": participant_member.user.full_name,
                    "is_online": participant_member.user.is_online,
                    "avatar_url": participant_member.user.avatar_url,
                    "role": participant_member.role
                })
        
        # For private chats, use the other participant's name
        chat_name = chat.name
        if chat.chat_type == ChatType.PRIVATE and len(participants_data) == 1:
            chat_name = participants_data[0]["full_name"]
        
        chat_data = {
            "id": chat.id,
            "name": chat_name,
            "description": chat.description,
            "chat_type": chat.chat_type,
            "avatar_url": chat.avatar_url,
            "is_pinned": membership.is_pinned,
            "is_muted": membership.is_muted,
            "unread_count": membership.unread_count,
            "last_message_at": chat.last_message_at,
            "participants": participants_data,
            "last_message": {
                "id": last_message.id,
                "content": last_message.content,
                "sender_name": last_message.sender.full_name if last_message and last_message.sender else None,
                "created_at": last_message.created_at
            } if last_message else None,
            "member_role": membership.role,
            "created_at": chat.created_at
        }
        chats_data.append(chat_data)
    
    # Sort chats by last message time or creation time
    chats_data.sort(key=lambda x: x["last_message_at"] or x["created_at"], reverse=True)
    
    return {"chats": chats_data}


@router.post("/")
async def create_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chat (private or group)"""
    
    # Validate participants exist
    participants = db.query(User).filter(User.id.in_(chat_data.participant_ids)).all()
    if len(participants) != len(chat_data.participant_ids):
        raise HTTPException(status_code=404, detail="One or more participants not found")
    
    # For private chats, ensure only 1 other participant
    if chat_data.chat_type == ChatType.PRIVATE:
        if len(chat_data.participant_ids) != 1:
            raise HTTPException(status_code=400, detail="Private chats must have exactly 1 other participant")
        
        # Check if private chat already exists between these users
        existing_private_chat = db.query(Chat).join(ChatMember).filter(
            Chat.chat_type == ChatType.PRIVATE,
            ChatMember.user_id.in_([current_user.id, chat_data.participant_ids[0]])
        ).group_by(Chat.id).having(func.count(ChatMember.id) == 2).first()
        
        if existing_private_chat:
            raise HTTPException(status_code=400, detail="Private chat already exists with this user")
        
        # Check if users are friends (for private chats)
        friendship = db.query(Friendship).filter(
            or_(
                and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == chat_data.participant_ids[0]),
                and_(Friendship.requester_id == chat_data.participant_ids[0], Friendship.addressee_id == current_user.id)
            ),
            Friendship.status == FriendshipStatus.ACCEPTED
        ).first()
        
        if not friendship:
            raise HTTPException(status_code=400, detail="Can only create private chats with friends")
    
    # Create chat
    new_chat = Chat(
        name=chat_data.name,
        description=chat_data.description,
        chat_type=chat_data.chat_type,
        created_by_id=current_user.id
    )
    
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    
    # Add creator as owner/admin
    creator_member = ChatMember(
        chat_id=new_chat.id,
        user_id=current_user.id,
        role=MemberRole.OWNER if chat_data.chat_type == ChatType.GROUP else MemberRole.MEMBER,
        can_send_messages=True,
        can_add_members=chat_data.chat_type == ChatType.GROUP,
        can_edit_chat=chat_data.chat_type == ChatType.GROUP,
        can_delete_messages=chat_data.chat_type == ChatType.GROUP
    )
    
    db.add(creator_member)
    
    # Add other participants
    for participant_id in chat_data.participant_ids:
        member = ChatMember(
            chat_id=new_chat.id,
            user_id=participant_id,
            role=MemberRole.MEMBER,
            can_send_messages=True,
            can_add_members=False,
            can_edit_chat=False,
            can_delete_messages=False
        )
        db.add(member)
    
    db.commit()
    
    return {
        "id": new_chat.id,
        "name": new_chat.name,
        "chat_type": new_chat.chat_type,
        "message": "Chat created successfully"
    }


@router.get("/{chat_id}")
async def get_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed chat information"""
    
    # Check if user is member of the chat
    chat_member = db.query(ChatMember).filter(
        ChatMember.chat_id == chat_id,
        ChatMember.user_id == current_user.id,
        ChatMember.is_active == True
    ).first()
    
    if not chat_member:
        raise HTTPException(status_code=403, detail="You are not a member of this chat")
    
    chat = chat_member.chat
    if not chat or not chat.is_active:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Get all members
    members = db.query(ChatMember).filter(
        ChatMember.chat_id == chat_id,
        ChatMember.is_active == True
    ).all()
    
    members_data = []
    for member in members:
        if member.user:
            members_data.append({
                "id": member.user.id,
                "username": member.user.username,
                "full_name": member.user.full_name,
                "is_online": member.user.is_online,
                "avatar_url": member.user.avatar_url,
                "role": member.role,
                "joined_at": member.joined_at,
                "can_send_messages": member.can_send_messages,
                "can_add_members": member.can_add_members,
                "can_edit_chat": member.can_edit_chat,
                "can_delete_messages": member.can_delete_messages
            })
    
    return {
        "id": chat.id,
        "name": chat.name,
        "description": chat.description,
        "chat_type": chat.chat_type,
        "avatar_url": chat.avatar_url,
        "is_public": chat.is_public,
        "invite_link": chat.invite_link,
        "members": members_data,
        "created_by_id": chat.created_by_id,
        "created_at": chat.created_at,
        "member_role": chat_member.role
    }


@router.put("/{chat_id}")
async def update_chat(
    chat_id: int,
    chat_update: ChatUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update chat details (group chats only)"""
    
    # Check if user can edit the chat
    chat_member = db.query(ChatMember).filter(
        ChatMember.chat_id == chat_id,
        ChatMember.user_id == current_user.id,
        ChatMember.is_active == True,
        ChatMember.can_edit_chat == True
    ).first()
    
    if not chat_member:
        raise HTTPException(status_code=403, detail="You don't have permission to edit this chat")
    
    chat = chat_member.chat
    if not chat or not chat.is_active:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if chat.chat_type == ChatType.PRIVATE:
        raise HTTPException(status_code=400, detail="Cannot edit private chats")
    
    # Update chat fields
    if chat_update.name is not None:
        chat.name = chat_update.name
    if chat_update.description is not None:
        chat.description = chat_update.description
    if chat_update.avatar_url is not None:
        chat.avatar_url = chat_update.avatar_url
    
    db.commit()
    db.refresh(chat)
    
    return {"message": "Chat updated successfully"}


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a chat (owner only)"""
    
    # Check if user is owner of the chat
    chat_member = db.query(ChatMember).filter(
        ChatMember.chat_id == chat_id,
        ChatMember.user_id == current_user.id,
        ChatMember.is_active == True,
        ChatMember.role == MemberRole.OWNER
    ).first()
    
    if not chat_member:
        raise HTTPException(status_code=403, detail="Only the chat owner can delete the chat")
    
    chat = chat_member.chat
    if not chat or not chat.is_active:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Soft delete
    chat.is_active = False
    db.commit()
    
    return {"message": "Chat deleted successfully"}


# Chat Member Management

@router.post("/{chat_id}/members")
async def add_chat_member(
    chat_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a member to the chat"""
    
    # Check if current user can add members
    chat_member = db.query(ChatMember).filter(
        ChatMember.chat_id == chat_id,
        ChatMember.user_id == current_user.id,
        ChatMember.is_active == True,
        ChatMember.can_add_members == True
    ).first()
    
    if not chat_member:
        raise HTTPException(status_code=403, detail="You don't have permission to add members to this chat")
    
    chat = chat_member.chat
    if not chat or not chat.is_active:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if chat.chat_type == ChatType.PRIVATE:
        raise HTTPException(status_code=400, detail="Cannot add members to private chats")
    
    # Check if user exists
    new_user = db.query(User).filter(User.id == user_id).first()
    if not new_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is already a member
    existing_member = db.query(ChatMember).filter(
        ChatMember.chat_id == chat_id,
        ChatMember.user_id == user_id,
        ChatMember.is_active == True
    ).first()
    
    if existing_member:
        raise HTTPException(status_code=400, detail="User is already a member of this chat")
    
    # Add new member
    new_member = ChatMember(
        chat_id=chat_id,
        user_id=user_id,
        role=MemberRole.MEMBER,
        can_send_messages=True
    )
    
    db.add(new_member)
    db.commit()
    
    return {"message": "Member added successfully"}


@router.delete("/{chat_id}/members/{user_id}")
async def remove_chat_member(
    chat_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a member from the chat"""
    
    # Check permissions - owner/admin can remove others, anyone can leave
    can_remove = False
    
    if user_id == current_user.id:
        # User wants to leave the chat
        can_remove = True
    else:
        # Check if current user can remove members (admin/owner)
        current_member = db.query(ChatMember).filter(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == current_user.id,
            ChatMember.is_active == True,
            ChatMember.role.in_([MemberRole.ADMIN, MemberRole.OWNER])
        ).first()
        can_remove = bool(current_member)
    
    if not can_remove:
        raise HTTPException(status_code=403, detail="You don't have permission to remove this member")
    
    # Find the member to remove
    member_to_remove = db.query(ChatMember).filter(
        ChatMember.chat_id == chat_id,
        ChatMember.user_id == user_id,
        ChatMember.is_active == True
    ).first()
    
    if not member_to_remove:
        raise HTTPException(status_code=404, detail="Member not found in this chat")
    
    # Cannot remove owner
    if member_to_remove.role == MemberRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot remove chat owner")
    
    # Remove member
    member_to_remove.is_active = False
    member_to_remove.left_at = func.now()
    
    db.commit()
    
    return {"message": "Member removed successfully"}


@router.put("/{chat_id}/members/{user_id}")
async def update_member_role(
    chat_id: int,
    user_id: int,
    member_update: MemberUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update member role and permissions"""
    
    # Check if current user is owner or admin
    current_member = db.query(ChatMember).filter(
        ChatMember.chat_id == chat_id,
        ChatMember.user_id == current_user.id,
        ChatMember.is_active == True,
        ChatMember.role.in_([MemberRole.ADMIN, MemberRole.OWNER])
    ).first()
    
    if not current_member:
        raise HTTPException(status_code=403, detail="You don't have permission to update member roles")
    
    # Find the member to update
    member_to_update = db.query(ChatMember).filter(
        ChatMember.chat_id == chat_id,
        ChatMember.user_id == user_id,
        ChatMember.is_active == True
    ).first()
    
    if not member_to_update:
        raise HTTPException(status_code=404, detail="Member not found in this chat")
    
    # Cannot modify owner role (except by owner themselves)
    if member_to_update.role == MemberRole.OWNER and current_user.id != user_id:
        raise HTTPException(status_code=400, detail="Cannot modify owner permissions")
    
    # Update member properties
    if member_update.role is not None and current_member.role == MemberRole.OWNER:
        member_to_update.role = member_update.role
    if member_update.can_send_messages is not None:
        member_to_update.can_send_messages = member_update.can_send_messages
    if member_update.can_add_members is not None:
        member_to_update.can_add_members = member_update.can_add_members
    if member_update.can_edit_chat is not None:
        member_to_update.can_edit_chat = member_update.can_edit_chat
    if member_update.can_delete_messages is not None:
        member_to_update.can_delete_messages = member_update.can_delete_messages
    
    db.commit()
    
    return {"message": "Member updated successfully"}
