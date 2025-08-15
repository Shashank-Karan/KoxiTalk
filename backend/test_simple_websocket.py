#!/usr/bin/env python3
"""
Simple WebSocket test client for test endpoint
"""

import asyncio
import websockets
import sys

async def test_simple_websocket():
    uri = "ws://localhost:8000/test-ws"
    
    try:
        print(f"🔗 Connecting to WebSocket: {uri}")
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected successfully!")
            
            # Wait for welcome message
            welcome = await websocket.recv()
            print(f"📥 Welcome message: {welcome}")
            
            # Send a test message
            test_message = "Hello WebSocket!"
            print(f"📤 Sending: {test_message}")
            await websocket.send(test_message)
            
            # Wait for echo
            response = await websocket.recv()
            print(f"📥 Received: {response}")
            
            # Send another message
            test_message2 = "This is working great!"
            print(f"📤 Sending: {test_message2}")
            await websocket.send(test_message2)
            
            # Wait for echo
            response2 = await websocket.recv()
            print(f"📥 Received: {response2}")
            
            print("🎉 Simple WebSocket test completed successfully!")
            
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Starting simple WebSocket test...")
    try:
        asyncio.run(test_simple_websocket())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
