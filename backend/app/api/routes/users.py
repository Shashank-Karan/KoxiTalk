"""
User management routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.models.friendship import Friendship, FriendshipStatus, UserBlock
from app.api.routes.auth import get_current_user
from app.schemas.auth import UserResponse, UserUpdate
from sqlalchemy import or_, and_, func

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    
    # Update user fields
    for field, value in user_update.dict(exclude_unset=True).items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.get("/search")
async def search_users(
    q: str,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search users by username or full name"""
    
    users = db.query(User).filter(
        (User.username.ilike(f"%{q}%")) | (User.full_name.ilike(f"%{q}%")),
        User.id != current_user.id,
        User.is_active == True
    ).limit(limit).all()
    
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user information by ID"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


# Friend Management Routes

@router.post("/friends/request/{user_id}")
async def send_friend_request(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a friend request to another user"""
    
    # Check if user exists
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot send friend request to yourself")
    
    # Check if friendship already exists
    existing_friendship = db.query(Friendship).filter(
        or_(
            and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == user_id),
            and_(Friendship.requester_id == user_id, Friendship.addressee_id == current_user.id)
        )
    ).first()
    
    if existing_friendship:
        raise HTTPException(status_code=400, detail="Friendship already exists")
    
    # Check if user is blocked
    is_blocked = db.query(UserBlock).filter(
        or_(
            and_(UserBlock.blocker_id == current_user.id, UserBlock.blocked_id == user_id),
            and_(UserBlock.blocker_id == user_id, UserBlock.blocked_id == current_user.id)
        ),
        UserBlock.is_active == True
    ).first()
    
    if is_blocked:
        raise HTTPException(status_code=400, detail="Cannot send friend request to blocked user")
    
    # Create friendship request
    friendship = Friendship(
        requester_id=current_user.id,
        addressee_id=user_id,
        status=FriendshipStatus.PENDING
    )
    
    db.add(friendship)
    db.commit()
    db.refresh(friendship)
    
    return {"message": "Friend request sent successfully", "friendship_id": friendship.id}


@router.put("/friends/request/{friendship_id}/{action}")
async def respond_to_friend_request(
    friendship_id: int,
    action: str,  # 'accept' or 'decline'
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept or decline a friend request"""
    
    if action not in ['accept', 'decline']:
        raise HTTPException(status_code=400, detail="Action must be 'accept' or 'decline'")
    
    friendship = db.query(Friendship).filter(
        Friendship.id == friendship_id,
        Friendship.addressee_id == current_user.id,
        Friendship.status == FriendshipStatus.PENDING
    ).first()
    
    if not friendship:
        raise HTTPException(status_code=404, detail="Friend request not found")
    
    friendship.status = FriendshipStatus.ACCEPTED if action == 'accept' else FriendshipStatus.DECLINED
    if action == 'accept':
        friendship.accepted_at = func.now()
    
    db.commit()
    
    return {"message": f"Friend request {action}ed successfully"}


@router.get("/friends")
async def get_friends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of friends"""
    
    friends = db.query(Friendship).filter(
        or_(
            and_(Friendship.requester_id == current_user.id, Friendship.status == FriendshipStatus.ACCEPTED),
            and_(Friendship.addressee_id == current_user.id, Friendship.status == FriendshipStatus.ACCEPTED)
        )
    ).all()
    
    friend_users = []
    for friendship in friends:
        friend_id = friendship.addressee_id if friendship.requester_id == current_user.id else friendship.requester_id
        friend_user = db.query(User).filter(User.id == friend_id).first()
        if friend_user:
            friend_users.append({
                "user": friend_user,
                "friendship_id": friendship.id,
                "friends_since": friendship.accepted_at
            })
    
    return friend_users


@router.get("/friends/requests/pending")
async def get_pending_friend_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get pending friend requests (both sent and received)"""
    
    sent_requests = db.query(Friendship).filter(
        Friendship.requester_id == current_user.id,
        Friendship.status == FriendshipStatus.PENDING
    ).all()
    
    received_requests = db.query(Friendship).filter(
        Friendship.addressee_id == current_user.id,
        Friendship.status == FriendshipStatus.PENDING
    ).all()
    
    result = {
        "sent": [],
        "received": []
    }
    
    for request in sent_requests:
        user = db.query(User).filter(User.id == request.addressee_id).first()
        if user:
            result["sent"].append({
                "friendship_id": request.id,
                "user": user,
                "sent_at": request.created_at
            })
    
    for request in received_requests:
        user = db.query(User).filter(User.id == request.requester_id).first()
        if user:
            result["received"].append({
                "friendship_id": request.id,
                "user": user,
                "sent_at": request.created_at
            })
    
    return result


@router.delete("/friends/{friendship_id}")
async def remove_friend(
    friendship_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a friend"""
    
    friendship = db.query(Friendship).filter(
        Friendship.id == friendship_id,
        or_(
            Friendship.requester_id == current_user.id,
            Friendship.addressee_id == current_user.id
        ),
        Friendship.status == FriendshipStatus.ACCEPTED
    ).first()
    
    if not friendship:
        raise HTTPException(status_code=404, detail="Friendship not found")
    
    db.delete(friendship)
    db.commit()
    
    return {"message": "Friend removed successfully"}


# User Blocking Routes

@router.post("/block/{user_id}")
async def block_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Block another user"""
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")
    
    # Check if user exists
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already blocked
    existing_block = db.query(UserBlock).filter(
        UserBlock.blocker_id == current_user.id,
        UserBlock.blocked_id == user_id,
        UserBlock.is_active == True
    ).first()
    
    if existing_block:
        raise HTTPException(status_code=400, detail="User is already blocked")
    
    # Create block
    user_block = UserBlock(
        blocker_id=current_user.id,
        blocked_id=user_id
    )
    
    db.add(user_block)
    
    # Remove friendship if exists
    friendship = db.query(Friendship).filter(
        or_(
            and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == user_id),
            and_(Friendship.requester_id == user_id, Friendship.addressee_id == current_user.id)
        )
    ).first()
    
    if friendship:
        db.delete(friendship)
    
    db.commit()
    
    return {"message": "User blocked successfully"}


@router.delete("/block/{user_id}")
async def unblock_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unblock a user"""
    
    user_block = db.query(UserBlock).filter(
        UserBlock.blocker_id == current_user.id,
        UserBlock.blocked_id == user_id,
        UserBlock.is_active == True
    ).first()
    
    if not user_block:
        raise HTTPException(status_code=404, detail="Block not found")
    
    user_block.is_active = False
    db.commit()
    
    return {"message": "User unblocked successfully"}


@router.get("/blocked")
async def get_blocked_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of blocked users"""
    
    blocks = db.query(UserBlock).filter(
        UserBlock.blocker_id == current_user.id,
        UserBlock.is_active == True
    ).all()
    
    blocked_users = []
    for block in blocks:
        user = db.query(User).filter(User.id == block.blocked_id).first()
        if user:
            blocked_users.append({
                "user": user,
                "blocked_at": block.created_at
            })
    
    return blocked_users
