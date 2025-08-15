#!/usr/bin/env python3
"""
Enhanced Demo Setup Script for Chat Application
Creates multiple demo users, friendships, chats, and sample messages
"""

import asyncio
import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import engine, Base, get_db
from app.models.user import User
from app.models.friendship import Friendship, FriendshipStatus
from app.models.chat import Chat, ChatMember, ChatType, MemberRole
from app.models.message import Message, MessageReaction, MessageType, MessageStatus

# Create all tables
Base.metadata.create_all(bind=engine)

def create_demo_users():
    """Create demo users with various profiles"""
    
    db = next(get_db())
    
    # Check if users already exist
    existing_users = db.query(User).count()
    if existing_users >= 6:
        print(f"Found {existing_users} users already in database. Skipping user creation.")
        return db.query(User).all()
    
    demo_users_data = [
        {
            "username": "demo",
            "email": "demo@example.com",
            "full_name": "Demo User",
            "password": "demo123",
            "bio": "I'm the demo user! Try out all the features with me.",
            "status_message": "Ready to chat! 💬"
        },
        {
            "username": "alice",
            "email": "alice@example.com",
            "full_name": "Alice Johnson",
            "password": "alice123",
            "bio": "Software engineer who loves coding and coffee ☕",
            "status_message": "Building amazing things with code!"
        },
        {
            "username": "bob",
            "email": "bob@example.com",
            "full_name": "Bob Smith",
            "password": "bob123",
            "bio": "Digital marketing specialist and travel enthusiast 🌍",
            "status_message": "Always exploring new places!"
        },
        {
            "username": "charlie",
            "email": "charlie@example.com",
            "full_name": "Charlie Wilson",
            "password": "charlie123",
            "bio": "Graphic designer with a passion for visual storytelling 🎨",
            "status_message": "Creating beautiful designs daily"
        },
        {
            "username": "diana",
            "email": "diana@example.com",
            "full_name": "Diana Chen",
            "password": "diana123",
            "bio": "Product manager turning ideas into reality 🚀",
            "status_message": "Innovation is my middle name"
        },
        {
            "username": "eve",
            "email": "eve@example.com",
            "full_name": "Eve Rodriguez",
            "password": "eve123",
            "bio": "Data scientist uncovering insights from numbers 📊",
            "status_message": "Data tells the best stories"
        }
    ]
    
    created_users = []
    
    for user_data in demo_users_data:
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == user_data["username"]).first()
        if existing_user:
            print(f"User {user_data['username']} already exists. Skipping.")
            created_users.append(existing_user)
            continue
        
        # Create new user
        user = User(
            username=user_data["username"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            bio=user_data["bio"],
            status_message=user_data["status_message"],
            is_online=True
        )
        user.set_password(user_data["password"])
        
        db.add(user)
        created_users.append(user)
        print(f"Created user: {user_data['username']} ({user_data['full_name']})")
    
    db.commit()
    
    # Refresh users to get IDs
    for user in created_users:
        db.refresh(user)
    
    return created_users

def create_friendships(users):
    """Create friendships between demo users"""
    
    db = next(get_db())
    
    # Check if friendships already exist
    existing_friendships = db.query(Friendship).count()
    if existing_friendships >= 8:
        print(f"Found {existing_friendships} friendships already in database. Skipping friendship creation.")
        return
    
    # Define friendship connections (requester_username, addressee_username)
    friendship_connections = [
        ("demo", "alice"),
        ("demo", "bob"),
        ("demo", "charlie"),
        ("alice", "bob"),
        ("alice", "diana"),
        ("bob", "charlie"),
        ("charlie", "eve"),
        ("diana", "eve"),
        ("alice", "eve"),
        ("bob", "diana")
    ]
    
    users_by_username = {user.username: user for user in users}
    
    for req_username, addr_username in friendship_connections:
        requester = users_by_username.get(req_username)
        addressee = users_by_username.get(addr_username)
        
        if not requester or not addressee:
            print(f"Warning: Could not find users for friendship {req_username} -> {addr_username}")
            continue
        
        # Check if friendship already exists
        existing_friendship = db.query(Friendship).filter(
            ((Friendship.requester_id == requester.id) & (Friendship.addressee_id == addressee.id)) |
            ((Friendship.requester_id == addressee.id) & (Friendship.addressee_id == requester.id))
        ).first()
        
        if existing_friendship:
            print(f"Friendship between {req_username} and {addr_username} already exists. Skipping.")
            continue
        
        # Create friendship
        friendship = Friendship(
            requester_id=requester.id,
            addressee_id=addressee.id,
            status=FriendshipStatus.ACCEPTED,
            accepted_at=datetime.now() - timedelta(days=1, hours=2)
        )
        
        db.add(friendship)
        print(f"Created friendship: {req_username} ↔ {addr_username}")
    
    db.commit()

def create_private_chats(users):
    """Create private chats between friends"""
    
    db = next(get_db())
    
    # Check if private chats already exist
    existing_private_chats = db.query(Chat).filter(Chat.chat_type == ChatType.PRIVATE).count()
    if existing_private_chats >= 5:
        print(f"Found {existing_private_chats} private chats already in database. Skipping private chat creation.")
        return
    
    users_by_username = {user.username: user for user in users}
    
    # Create private chats between some friends
    private_chat_pairs = [
        ("demo", "alice"),
        ("demo", "bob"),
        ("alice", "diana"),
        ("bob", "charlie"),
        ("charlie", "eve")
    ]
    
    for user1_name, user2_name in private_chat_pairs:
        user1 = users_by_username.get(user1_name)
        user2 = users_by_username.get(user2_name)
        
        if not user1 or not user2:
            continue
        
        # Check if private chat already exists
        existing_chat = db.query(Chat).join(ChatMember).filter(
            Chat.chat_type == ChatType.PRIVATE,
            ChatMember.user_id.in_([user1.id, user2.id])
        ).group_by(Chat.id).having(func.count(ChatMember.id) == 2).first()
        
        if existing_chat:
            print(f"Private chat between {user1_name} and {user2_name} already exists. Skipping.")
            continue
        
        # Create private chat
        chat = Chat(
            chat_type=ChatType.PRIVATE,
            created_by_id=user1.id,
            last_message_at=datetime.now() - timedelta(minutes=30)
        )
        
        db.add(chat)
        db.commit()
        db.refresh(chat)
        
        # Add both users as members
        member1 = ChatMember(
            chat_id=chat.id,
            user_id=user1.id,
            role=MemberRole.MEMBER,
            can_send_messages=True
        )
        
        member2 = ChatMember(
            chat_id=chat.id,
            user_id=user2.id,
            role=MemberRole.MEMBER,
            can_send_messages=True
        )
        
        db.add(member1)
        db.add(member2)
        
        print(f"Created private chat between {user1_name} and {user2_name}")
    
    db.commit()

def create_group_chats(users):
    """Create group chats"""
    
    db = next(get_db())
    
    # Check if group chats already exist
    existing_group_chats = db.query(Chat).filter(Chat.chat_type == ChatType.GROUP).count()
    if existing_group_chats >= 3:
        print(f"Found {existing_group_chats} group chats already in database. Skipping group chat creation.")
        return
    
    users_by_username = {user.username: user for user in users}
    
    # Group chat configurations
    group_chats_config = [
        {
            "name": "Tech Talk",
            "description": "Discussing the latest in technology",
            "owner": "demo",
            "members": ["demo", "alice", "diana", "eve"]
        },
        {
            "name": "Coffee Lovers ☕",
            "description": "For those who can't function without coffee",
            "owner": "alice",
            "members": ["alice", "demo", "bob", "charlie"]
        },
        {
            "name": "Travel Buddies 🌍",
            "description": "Share your travel experiences and tips",
            "owner": "bob",
            "members": ["bob", "charlie", "diana", "eve"]
        }
    ]
    
    for group_config in group_chats_config:
        owner = users_by_username.get(group_config["owner"])
        if not owner:
            continue
        
        # Check if group already exists
        existing_group = db.query(Chat).filter(
            Chat.name == group_config["name"],
            Chat.chat_type == ChatType.GROUP
        ).first()
        
        if existing_group:
            print(f"Group chat '{group_config['name']}' already exists. Skipping.")
            continue
        
        # Create group chat
        chat = Chat(
            name=group_config["name"],
            description=group_config["description"],
            chat_type=ChatType.GROUP,
            created_by_id=owner.id,
            last_message_at=datetime.now() - timedelta(hours=2)
        )
        
        db.add(chat)
        db.commit()
        db.refresh(chat)
        
        # Add owner
        owner_member = ChatMember(
            chat_id=chat.id,
            user_id=owner.id,
            role=MemberRole.OWNER,
            can_send_messages=True,
            can_add_members=True,
            can_edit_chat=True,
            can_delete_messages=True
        )
        db.add(owner_member)
        
        # Add other members
        for member_username in group_config["members"]:
            if member_username == group_config["owner"]:
                continue  # Skip owner, already added
                
            member_user = users_by_username.get(member_username)
            if not member_user:
                continue
            
            member = ChatMember(
                chat_id=chat.id,
                user_id=member_user.id,
                role=MemberRole.MEMBER,
                can_send_messages=True,
                can_add_members=False,
                can_edit_chat=False,
                can_delete_messages=False
            )
            db.add(member)
        
        print(f"Created group chat: {group_config['name']} with {len(group_config['members'])} members")
    
    db.commit()

def create_sample_messages():
    """Create sample messages in chats"""
    
    db = next(get_db())
    
    # Check if messages already exist
    existing_messages = db.query(Message).count()
    if existing_messages >= 20:
        print(f"Found {existing_messages} messages already in database. Skipping message creation.")
        return
    
    # Get all chats
    chats = db.query(Chat).filter(Chat.is_active == True).all()
    users = db.query(User).all()
    users_by_id = {user.id: user for user in users}
    
    # Sample messages for different types of chats
    private_messages = [
        "Hey! How's your day going?",
        "Great to connect with you here! 😊",
        "Did you see the latest updates to the app?",
        "This chat feature is really smooth!",
        "Want to grab coffee sometime?",
        "Sure! I know a great place downtown.",
        "Perfect! Looking forward to it. ☕",
    ]
    
    group_messages = [
        "Welcome everyone to the group! 🎉",
        "Thanks for creating this! Excited to be here.",
        "This is going to be a great way to stay in touch.",
        "Has anyone tried the new message reactions?",
        "Yes! They're awesome. Love the emoji picker! ❤️",
        "The reply feature is really handy too.",
        "Agreed! This beats our old chat setup by miles.",
        "Who's organizing the next meetup?",
        "I can help with that! Let's plan something fun."
    ]
    
    for chat in chats:
        # Get chat members
        chat_members = db.query(ChatMember).filter(
            ChatMember.chat_id == chat.id,
            ChatMember.is_active == True
        ).all()
        
        if len(chat_members) < 2:
            continue
        
        # Choose appropriate messages based on chat type
        messages = group_messages if chat.chat_type == ChatType.GROUP else private_messages
        
        # Create 3-5 messages per chat
        num_messages = min(len(messages), 5)
        message_texts = messages[:num_messages]
        
        for i, message_text in enumerate(message_texts):
            # Alternate between different members
            sender_member = chat_members[i % len(chat_members)]
            
            # Create message with timestamp spread over last few days
            created_time = datetime.now() - timedelta(
                days=2 - (i * 0.3),
                hours=i * 2,
                minutes=i * 15
            )
            
            message = Message(
                chat_id=chat.id,
                sender_id=sender_member.user_id,
                content=message_text,
                message_type=MessageType.TEXT,
                status=MessageStatus.DELIVERED,
                created_at=created_time
            )
            
            db.add(message)
        
        # Update chat's last message timestamp
        chat.last_message_at = datetime.now() - timedelta(minutes=10 + (len(chats) - chats.index(chat)) * 5)
        
        print(f"Created {num_messages} messages for chat: {chat.name or 'Private Chat'}")
    
    db.commit()

def create_sample_reactions():
    """Add sample reactions to some messages"""
    
    db = next(get_db())
    
    # Check if reactions already exist
    existing_reactions = db.query(MessageReaction).count()
    if existing_reactions >= 10:
        print(f"Found {existing_reactions} reactions already in database. Skipping reaction creation.")
        return
    
    # Get some messages to add reactions to
    messages = db.query(Message).limit(10).all()
    users = db.query(User).all()
    
    reaction_emojis = ["👍", "❤️", "😂", "😮", "🎉", "👏"]
    
    reactions_added = 0
    
    for message in messages:
        # Get chat members who can react
        chat_members = db.query(ChatMember).filter(
            ChatMember.chat_id == message.chat_id,
            ChatMember.user_id != message.sender_id,  # Don't react to own messages
            ChatMember.is_active == True
        ).all()
        
        if not chat_members:
            continue
        
        # Add 1-2 reactions per message randomly
        import random
        num_reactions = random.randint(0, min(2, len(chat_members)))
        
        selected_members = random.sample(chat_members, num_reactions)
        
        for member in selected_members:
            reaction_emoji = random.choice(reaction_emojis)
            
            # Check if this user already reacted to this message with this emoji
            existing_reaction = db.query(MessageReaction).filter(
                MessageReaction.message_id == message.id,
                MessageReaction.user_id == member.user_id,
                MessageReaction.reaction == reaction_emoji
            ).first()
            
            if existing_reaction:
                continue
            
            reaction = MessageReaction(
                message_id=message.id,
                user_id=member.user_id,
                reaction=reaction_emoji
            )
            
            db.add(reaction)
            reactions_added += 1
    
    db.commit()
    print(f"Created {reactions_added} message reactions")

def main():
    """Main setup function"""
    print("🚀 Starting Enhanced Demo Setup for Chat Application...")
    print("=" * 60)
    
    try:
        # Create demo users
        print("\n📝 Creating demo users...")
        users = create_demo_users()
        print(f"✅ Total users in database: {len(users)}")
        
        # Create friendships
        print("\n👥 Creating friendships...")
        create_friendships(users)
        print("✅ Friendships created successfully")
        
        # Create private chats
        print("\n💬 Creating private chats...")
        create_private_chats(users)
        print("✅ Private chats created successfully")
        
        # Create group chats
        print("\n👥 Creating group chats...")
        create_group_chats(users)
        print("✅ Group chats created successfully")
        
        # Create sample messages
        print("\n📨 Creating sample messages...")
        create_sample_messages()
        print("✅ Sample messages created successfully")
        
        # Create sample reactions
        print("\n😊 Creating sample reactions...")
        create_sample_reactions()
        print("✅ Sample reactions created successfully")
        
        print("\n" + "=" * 60)
        print("🎉 Enhanced Demo Setup Complete!")
        print("=" * 60)
        print("\n📋 Demo User Accounts:")
        print("┌─────────────────────────────────────────────────────┐")
        
        demo_accounts = [
            ("demo", "demo123", "Demo User"),
            ("alice", "alice123", "Alice Johnson"),
            ("bob", "bob123", "Bob Smith"),
            ("charlie", "charlie123", "Charlie Wilson"),
            ("diana", "diana123", "Diana Chen"),
            ("eve", "eve123", "Eve Rodriguez")
        ]
        
        for username, password, full_name in demo_accounts:
            print(f"│ Username: {username:<12} Password: {password:<10} │")
        
        print("└─────────────────────────────────────────────────────┘")
        print("\n🌟 Features Available:")
        print("• Real-time messaging with WebSocket support")
        print("• Friend requests and friend management")
        print("• Private chats between friends")
        print("• Group chats with role-based permissions")
        print("• Message reactions and replies")
        print("• User search and discovery")
        print("• User blocking and privacy controls")
        print("• Comprehensive chat management")
        
        print("\n🚀 To start the application:")
        print("1. Backend: cd backend && uvicorn main:app --reload")
        print("2. Frontend: cd client && npm run dev")
        print("3. Open: http://localhost:3000")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during setup: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
