#!/usr/bin/env python3
"""
Simple script to create demo users using raw SQLAlchemy
"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from passlib.context import CryptContext

# Configuration
DATABASE_URL = "sqlite:///./chatapp.db"

Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SimpleUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Profile information
    bio = Column(Text, nullable=True)
    avatar_url = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    
    # Status and settings
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, nullable=True)
    
    # Privacy settings
    show_last_seen = Column(Boolean, default=True)
    show_read_receipts = Column(Boolean, default=True)
    allow_groups = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def set_password(self, password: str):
        """Hash and set user password"""
        self.hashed_password = pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(password, self.hashed_password)

def create_demo_users():
    """Create demo users"""
    
    # Create engine and tables
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        users_data = [
            {
                "email": "demo@example.com",
                "username": "demo",
                "full_name": "Demo User",
                "bio": "Demo user for testing the chat app!",
                "password": "demo123"
            },
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
                "bio": "Developer and tech enthusiast",
                "password": "bob123"
            }
        ]
        
        created_count = 0
        
        for user_data in users_data:
            # Check if user exists
            existing_user = session.query(SimpleUser).filter(SimpleUser.username == user_data["username"]).first()
            
            if existing_user:
                print(f"✅ User '{user_data['username']}' already exists")
                continue
            
            # Create user
            user = SimpleUser(
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
        
        print(f"\n✅ Demo users setup complete! Created {created_count} new users.")
        print("\n🔗 Access your application:")
        print("   💻 Frontend: http://localhost:3000")
        print("   🚀 Backend API: http://127.0.0.1:8000")
        print("   📖 API Docs: http://127.0.0.1:8000/docs")
        
        print("\n👤 Login credentials:")
        for user_data in users_data:
            print(f"   Username: {user_data['username']:8} | Password: {user_data['password']}")
        
        print("\n🎯 Next steps:")
        print("   1. Open http://localhost:3000 in your browser")
        print("   2. Try logging in with any of the credentials above")
        print("   3. Start chatting!")
        
    except Exception as e:
        print(f"❌ Error creating users: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Setting up demo users for the chat application...")
    create_demo_users()
