"""
Main FastAPI application for the Real-Time Chat Application
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from pathlib import Path
import json
import asyncio
from typing import Dict, List

from app.core.config import get_settings
from app.core.database import engine, Base
from app.api.routes import auth, users, chats, messages, files

# Import models to ensure they're registered with SQLAlchemy
from app.models import user, chat, message, file, friendship

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize settings
settings = get_settings()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.chat_rooms: Dict[int, List[int]] = {}  # chat_id -> [user_ids]
    
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"User {user_id} connected")
    
    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        # Remove from all chat rooms
        for chat_id in list(self.chat_rooms.keys()):
            if user_id in self.chat_rooms[chat_id]:
                self.chat_rooms[chat_id].remove(user_id)
        print(f"User {user_id} disconnected")
    
    async def join_chat(self, user_id: int, chat_id: int):
        if chat_id not in self.chat_rooms:
            self.chat_rooms[chat_id] = []
        if user_id not in self.chat_rooms[chat_id]:
            self.chat_rooms[chat_id].append(user_id)
        print(f"User {user_id} joined chat {chat_id}")
    
    async def send_message_to_chat(self, chat_id: int, message: dict, sender_id: int):
        if chat_id in self.chat_rooms:
            for user_id in self.chat_rooms[chat_id]:
                if user_id != sender_id and user_id in self.active_connections:
                    try:
                        await self.active_connections[user_id].send_text(json.dumps({
                            "type": "message",
                            "data": message
                        }))
                    except Exception as e:
                        print(f"Failed to send message to user {user_id}: {e}")

manager = ConnectionManager()

# Initialize FastAPI app
app = FastAPI(
    title="Real-Time Chat API",
    description="A comprehensive chat application API with real-time features",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for media uploads
Path("uploads").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include API routes
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(chats.router, prefix="/api/chats", tags=["Chats"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(files.router, prefix="/api/files", tags=["Files"])

# WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                message_type = message_data.get("type")
                
                if message_type == "join_chat":
                    chat_id = message_data["chat_id"]
                    await manager.join_chat(user_id, chat_id)
                    await websocket.send_text(json.dumps({
                        "type": "join_success",
                        "chat_id": chat_id
                    }))
                
                elif message_type == "send_message":
                    chat_id = message_data["chat_id"]
                    content = message_data["content"]
                    reply_to_message_id = message_data.get("reply_to_message_id")
                    
                    # Import database dependencies
                    from app.core.database import get_db
                    from app.models.user import User
                    from app.models.chat import ChatMember
                    from app.models.message import Message, MessageType, MessageStatus
                    from datetime import datetime
                    
                    # Get database session
                    db = next(get_db())
                    
                    try:
                        # Get user from database
                        db_user = db.query(User).filter(User.id == user_id).first()
                        if not db_user:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": "User not found"
                            }))
                            continue
                        
                        # Check if user is member of the chat
                        chat_member = db.query(ChatMember).filter(
                            ChatMember.chat_id == chat_id,
                            ChatMember.user_id == user_id,
                            ChatMember.is_active == True,
                            ChatMember.can_send_messages == True
                        ).first()
                        
                        if not chat_member:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": "You cannot send messages to this chat"
                            }))
                            continue
                        
                        # Create and save message to database
                        new_message = Message(
                            chat_id=chat_id,
                            sender_id=user_id,
                            content=content,
                            message_type=MessageType.TEXT,
                            reply_to_message_id=reply_to_message_id,
                            status=MessageStatus.SENT
                        )
                        
                        db.add(new_message)
                        db.commit()
                        db.refresh(new_message)
                        
                        # Update chat's last message timestamp
                        from app.models.chat import Chat
                        chat = db.query(Chat).filter(Chat.id == chat_id).first()
                        if chat:
                            chat.last_message_at = new_message.created_at
                            db.commit()
                        
                        # Create message object for broadcasting
                        message = {
                            "id": new_message.id,
                            "content": new_message.content,
                            "sender_id": new_message.sender_id,
                            "sender_name": db_user.full_name,
                            "timestamp": new_message.created_at.isoformat(),
                            "chat_id": chat_id,
                            "message_type": new_message.message_type.value,
                            "reply_to_message_id": new_message.reply_to_message_id,
                            "created_at": new_message.created_at.isoformat()
                        }
                        
                        # Send to other users in the chat
                        await manager.send_message_to_chat(chat_id, message, user_id)
                        
                        # Send confirmation back to sender
                        await websocket.send_text(json.dumps({
                            "type": "message_sent",
                            "data": message
                        }))
                        
                    except Exception as e:
                        print(f"Error saving message to database: {e}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "Failed to save message"
                        }))
                    finally:
                        db.close()
                    
                elif message_type == "typing":
                    chat_id = message_data["chat_id"]
                    is_typing = message_data["is_typing"]
                    
                    # Broadcast typing status to chat room
                    typing_data = {
                        "type": "typing",
                        "user_id": user_id,
                        "is_typing": is_typing
                    }
                    
                    # Send to other users in chat
                    if chat_id in manager.chat_rooms:
                        for other_user_id in manager.chat_rooms[chat_id]:
                            if other_user_id != user_id and other_user_id in manager.active_connections:
                                try:
                                    await manager.active_connections[other_user_id].send_text(json.dumps(typing_data))
                                except Exception as e:
                                    print(f"Failed to send typing status: {e}")
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except Exception as e:
                print(f"Error handling WebSocket message: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Failed to process message"
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(user_id)

@app.get("/")
async def root():
    return {"message": "Real-Time Chat API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
