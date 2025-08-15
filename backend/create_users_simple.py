#!/usr/bin/env python3
"""
Simple script to create demo users for testing the chat application
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import get_settings
from app.models.user import User

def create_users():
    """Create demo users for testing"""
    
    settings = get_settings()
    
    # Create engine and session
    engine = create_engine(settings.database_url)
    
    # Create all tables
    from app.core.database import Base
    Base.metadata.create_all(bind=engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        users_to_create = [
            {
                "email": "demo@example.com",
                "username": "demo",
                "full_name": "Demo User",
                "bio": "Demo user for testing",
                "password": "demo123"
            },
            {
                "email": "alice@example.com",
                "username": "alice",
                "full_name": "Alice Johnson",
                "bio": "Love chatting!",
                "password": "alice123"
            },
            {
                "email": "bob@example.com",
                "username": "bob",
                "full_name": "Bob Smith",
                "bio": "Developer",
                "password": "bob123"
            }
        ]
        
        created_count = 0
        
        for user_data in users_to_create:
            # Check if user exists
            existing_user = session.query(User).filter(User.username == user_data["username"]).first()
            
            if existing_user:
                print(f"✅ User '{user_data['username']}' already exists")
                continue
            
            # Create new user
            user = User(
                email=user_data["email"],
                username=user_data["username"],
                full_name=user_data["full_name"],
                bio=user_data["bio"]
            )
            user.set_password(user_data["password"])
            
            session.add(user)
            created_count += 1
            print(f"🎉 Created user: {user_data['username']}")
        
        # Commit changes
        session.commit()
        
        print(f"\n✅ Setup complete! Created {created_count} new users.")
        print("\n🔗 Test the application:")
        print("   Frontend: http://localhost:3000")
        print("   Backend: http://127.0.0.1:8000")
        print("   API Docs: http://127.0.0.1:8000/docs")
        
        print("\n👤 Login credentials:")
        for user_data in users_to_create:
            print(f"   {user_data['username']} / {user_data['password']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Creating demo users...")
    create_users()
