#!/usr/bin/env python3
"""
Script to create multiple demo users for testing chat functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

def create_demo_users():
    settings = get_settings()
    print(f"🔧 Creating demo users in database: {settings.database_url}")
    
    # Create engine and session
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    demo_users = [
        {
            "username": "alice",
            "email": "alice@example.com",
            "full_name": "Alice Johnson",
            "bio": "Software developer who loves to chat!",
            "password": "alice123"
        },
        {
            "username": "bob",
            "email": "bob@example.com",
            "full_name": "Bob Smith",
            "bio": "Tech enthusiast and coffee lover ☕",
            "password": "bob123"
        },
        {
            "username": "charlie",
            "email": "charlie@example.com", 
            "full_name": "Charlie Brown",
            "bio": "Designer by day, gamer by night 🎮",
            "password": "charlie123"
        },
        {
            "username": "diana",
            "email": "diana@example.com",
            "full_name": "Diana Prince",
            "bio": "Product manager with a passion for UX 💫",
            "password": "diana123"
        },
        {
            "username": "eve",
            "email": "eve@example.com",
            "full_name": "Eve Wilson",
            "bio": "Data scientist exploring the world of AI 🤖",
            "password": "eve123"
        }
    ]
    
    try:
        from app.models.user import User
        
        created_users = []
        
        for user_data in demo_users:
            # Check if user already exists
            existing_user = session.query(User).filter(
                (User.username == user_data["username"]) | 
                (User.email == user_data["email"])
            ).first()
            
            if existing_user:
                print(f"⚠️  User {user_data['username']} already exists, skipping...")
                continue
            
            # Create new user
            new_user = User(
                username=user_data["username"],
                email=user_data["email"],
                full_name=user_data["full_name"],
                bio=user_data["bio"],
                is_active=True
            )
            new_user.set_password(user_data["password"])
            
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            
            created_users.append(new_user)
            print(f"✅ Created user: {new_user.username} ({new_user.email})")
        
        print(f"\n🎉 Successfully created {len(created_users)} new demo users!")
        
        # List all users
        all_users = session.query(User).all()
        print(f"\n📋 All users in database ({len(all_users)} total):")
        for user in all_users:
            print(f"  - {user.username} ({user.full_name}) - {user.email}")
        
        print(f"\n🔑 Demo login credentials:")
        print(f"  - demo / demo123")
        for user_data in demo_users:
            if user_data["username"] not in [u.username for u in session.query(User).filter(User.username == user_data["username"])]:
                continue
            print(f"  - {user_data['username']} / {user_data['password']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    create_demo_users()
