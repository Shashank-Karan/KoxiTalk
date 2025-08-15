#!/usr/bin/env python3
"""
Simple WebSocket test client
"""

import asyncio
import websockets
import json
import sys

async def test_websocket():
    uri = "ws://localhost:8000/ws/1"  # Connect as user ID 1 (demo user)
    
    try:
        print(f"🔗 Connecting to WebSocket: {uri}")
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected successfully!")
            
            # Send a test message
            test_message = {
                "type": "message",
                "content": "Hello WebSocket!",
                "chat_id": 1
            }
            
            print(f"📤 Sending test message: {test_message}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            print("⏳ Waiting for response...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Received response: {response}")
                
                # Try to parse the response
                try:
                    parsed_response = json.loads(response)
                    print(f"✅ Parsed response: {parsed_response}")
                except json.JSONDecodeError:
                    print(f"ℹ️  Plain text response: {response}")
                    
            except asyncio.TimeoutError:
                print("⏰ No response received within 5 seconds")
            
            # Send a typing indicator
            typing_message = {
                "type": "typing",
                "chat_id": 1,
                "is_typing": True
            }
            
            print(f"📤 Sending typing indicator: {typing_message}")
            await websocket.send(json.dumps(typing_message))
            
            # Wait a bit more
            await asyncio.sleep(2)
            
            print("🎉 WebSocket test completed successfully!")
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ WebSocket connection closed: {e}")
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Starting WebSocket functionality test...")
    try:
        asyncio.run(test_websocket())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
