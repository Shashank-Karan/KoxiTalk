#!/usr/bin/env python3
"""
Debug script to check registered routes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_routes():
    try:
        from app.main import app
        print("✅ FastAPI app imported successfully")
        
        print("\n📋 Registered routes:")
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                print(f"  {route.methods} {route.path}")
        
        # Test specific auth routes
        print("\n🔍 Looking for auth routes...")
        auth_routes = [route for route in app.routes if hasattr(route, 'path') and '/auth/' in route.path]
        if auth_routes:
            print("✅ Auth routes found:")
            for route in auth_routes:
                print(f"  {route.methods} {route.path}")
        else:
            print("❌ No auth routes found!")
            
        # Check if routers are included
        print(f"\n📊 Total routes: {len(app.routes)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_routes()
