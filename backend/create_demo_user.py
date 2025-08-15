#!/usr/bin/env python3
"""
Script to create a demo user for testing the chat application
"""

import asyncio
from sqlalchemy.orm import sessionmaker
from app.core.database import engine, Base
from app.models.user import User

# Create database tables if they don't exist
Base.metadata.create_all(bind=engine)

# Create session
Session = sessionmaker(bind=engine)
session = Session()

def create_demo_user():
    """Create a demo user for testing"""
    
    # Check if demo user already exists
    existing_user = session.query(User).filter(User.username == "demo").first()
    if existing_user:
        print("✅ Demo user already exists!")
        print(f"   Username: {existing_user.username}")
        print(f"   Email: {existing_user.email}")
        print(f"   Full Name: {existing_user.full_name}")
        return existing_user
    
    # Create demo user
    demo_user = User(
        email="demo@example.com",
        username="demo", 
        full_name="Demo User",
        bio="I'm a demo user for testing the chat application!"
    )
    
    # Set password
    demo_user.set_password("demo123")
    
    # Add to database
    session.add(demo_user)
    session.commit()
    session.refresh(demo_user)
    
    print("🎉 Demo user created successfully!")
    print(f"   Username: {demo_user.username}")
    print(f"   Email: {demo_user.email}")
    print(f"   Full Name: {demo_user.full_name}")
    print(f"   Password: demo123")
    
    return demo_user

def create_additional_users():
    """Create additional users for testing chat functionality"""
    
    users_data = [
        {
            "email": "alice@example.com",
            "username": "alice",
            "full_name": "Alice Johnson",
            "bio": "Love chatting with friends!",
            "password": "alice123"
        },
        {
            "email": "bob@example.com", 
            "username": "bob",
            "full_name": "Bob Smith",
            "bio": "Developer and chat enthusiast",
            "password": "bob123"
        }
    ]
    
    created_users = []
    
    for user_data in users_data:
        # Check if user exists
        existing_user = session.query(User).filter(User.username == user_data["username"]).first()
        if existing_user:
            print(f"✅ User {user_data['username']} already exists!")
            created_users.append(existing_user)
            continue
        
        # Create user
        user = User(
            email=user_data["email"],
            username=user_data["username"],
            full_name=user_data["full_name"],
            bio=user_data["bio"]
        )
        user.set_password(user_data["password"])
        
        session.add(user)
        created_users.append(user)
        print(f"🎉 Created user: {user_data['username']}")
    
    session.commit()
    return created_users

if __name__ == "__main__":
    try:
        print("🚀 Setting up demo users for the chat application...")
        
        # Create demo user
        demo_user = create_demo_user()
        
        # Create additional users
        additional_users = create_additional_users()
        
        print("\n" + "="*50)
        print("✅ Setup complete! You can now test the application.")
        print("\n🔗 Access the application:")
        print("   Frontend: http://localhost:3000")
        print("   Backend API: http://127.0.0.1:8000")
        print("   API Docs: http://127.0.0.1:8000/docs")
        
        print("\n👤 Demo login credentials:")
        print("   Username: demo")
        print("   Password: demo123")
        
        print("\n👥 Other test users:")
        print("   alice / alice123")
        print("   bob / bob123")
        
    except Exception as e:
        print(f"❌ Error setting up demo users: {e}")
    finally:
        session.close()
