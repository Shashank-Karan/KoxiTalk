#!/usr/bin/env python3
"""
Debug script to test login functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

def debug_login():
    settings = get_settings()
    print(f"🔍 Testing login with database: {settings.database_url}")
    
    # Create engine and session
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Import the User model
        from app.models.user import User
        
        # Check if demo user exists
        demo_user = session.query(User).filter(User.username == "demo").first()
        
        if demo_user:
            print(f"✅ Demo user found:")
            print(f"   ID: {demo_user.id}")
            print(f"   Username: {demo_user.username}")
            print(f"   Email: {demo_user.email}")
            print(f"   Full Name: {demo_user.full_name}")
            print(f"   Is Active: {demo_user.is_active}")
            
            # Test password verification
            if demo_user.verify_password("demo123"):
                print("✅ Password verification successful!")
            else:
                print("❌ Password verification failed!")
                
        else:
            print("❌ Demo user not found!")
            
            # List all users
            all_users = session.query(User).all()
            print(f"📋 Found {len(all_users)} users in database:")
            for user in all_users:
                print(f"   - {user.username} ({user.email})")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    debug_login()
