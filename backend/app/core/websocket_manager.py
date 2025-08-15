"""
WebSocket Manager for real-time communication
Handles connections, messaging, typing indicators, and online status
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import asyncio
from datetime import datetime
import logging

from app.core.database import get_redis
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ConnectionManager:
    """Manages WebSocket connections for users"""
    
    def __init__(self):
        # Active connections: user_id -> List[WebSocket]
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # User rooms: chat_id -> Set[user_id]
        self.chat_rooms: Dict[int, Set[int]] = {}
        # Typing indicators: chat_id -> Set[user_id]
        self.typing_users: Dict[int, Set[int]] = {}
        self.redis = get_redis()
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Connect a user's WebSocket"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        
        self.active_connections[user_id].append(websocket)
        
        # Update user online status
        await self.set_user_online(user_id, True)
        
        # Notify user's contacts that they're online
        await self.broadcast_user_status(user_id, "online")
        
        logger.info(f"User {user_id} connected via WebSocket")
    
    async def disconnect(self, user_id: int, websocket: WebSocket = None):
        """Disconnect a user's WebSocket"""
        if user_id in self.active_connections:
            if websocket:
                self.active_connections[user_id].remove(websocket)
            
            # If no more connections, set user offline
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                await self.set_user_online(user_id, False)
                await self.broadcast_user_status(user_id, "offline")
        
        # Remove from all chat rooms
        for chat_id in list(self.chat_rooms.keys()):
            if user_id in self.chat_rooms[chat_id]:
                self.chat_rooms[chat_id].remove(user_id)
                if not self.chat_rooms[chat_id]:
                    del self.chat_rooms[chat_id]
        
        # Remove from typing indicators
        for chat_id in list(self.typing_users.keys()):
            if user_id in self.typing_users[chat_id]:
                self.typing_users[chat_id].remove(user_id)
                await self.broadcast_typing_status(chat_id, user_id, False)
        
        logger.info(f"User {user_id} disconnected")
    
    async def join_chat_room(self, user_id: int, chat_id: int):
        """Add user to a chat room"""
        if chat_id not in self.chat_rooms:
            self.chat_rooms[chat_id] = set()
        
        self.chat_rooms[chat_id].add(user_id)
        logger.info(f"User {user_id} joined chat room {chat_id}")
    
    async def leave_chat_room(self, user_id: int, chat_id: int):
        """Remove user from a chat room"""
        if chat_id in self.chat_rooms and user_id in self.chat_rooms[chat_id]:
            self.chat_rooms[chat_id].remove(user_id)
            
            # Stop typing if user was typing
            if chat_id in self.typing_users and user_id in self.typing_users[chat_id]:
                await self.set_typing_status(chat_id, user_id, False)
    
    async def send_personal_message(self, user_id: int, message: dict):
        """Send a message to a specific user"""
        if user_id in self.active_connections:
            message_data = json.dumps(message)
            disconnected_connections = []
            
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message_data)
                except Exception:
                    disconnected_connections.append(connection)
            
            # Remove disconnected connections
            for connection in disconnected_connections:
                self.active_connections[user_id].remove(connection)
    
    async def broadcast_to_chat(self, chat_id: int, message: dict, exclude_user_id: int = None):
        """Broadcast a message to all users in a chat room"""
        if chat_id not in self.chat_rooms:
            return
        
        message_data = json.dumps(message)
        
        for user_id in self.chat_rooms[chat_id]:
            if exclude_user_id and user_id == exclude_user_id:
                continue
            
            await self.send_personal_message(user_id, message)
    
    async def set_typing_status(self, chat_id: int, user_id: int, is_typing: bool):
        """Update typing status for a user in a chat"""
        if chat_id not in self.typing_users:
            self.typing_users[chat_id] = set()
        
        if is_typing:
            self.typing_users[chat_id].add(user_id)
        else:
            self.typing_users[chat_id].discard(user_id)
        
        # Broadcast typing status to other users in the chat
        await self.broadcast_typing_status(chat_id, user_id, is_typing)
    
    async def broadcast_typing_status(self, chat_id: int, user_id: int, is_typing: bool):
        """Broadcast typing status to all users in a chat"""
        message = {
            "type": "typing",
            "chat_id": chat_id,
            "user_id": user_id,
            "is_typing": is_typing,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_chat(chat_id, message, exclude_user_id=user_id)
    
    async def set_user_online(self, user_id: int, is_online: bool):
        """Update user's online status in Redis (if available)"""
        if self.redis is None:
            return  # Skip if Redis is not available
            
        try:
            if is_online:
                self.redis.hset("user_status", user_id, "online")
                self.redis.hset("user_last_seen", user_id, datetime.utcnow().isoformat())
            else:
                self.redis.hset("user_status", user_id, "offline")
                self.redis.hset("user_last_seen", user_id, datetime.utcnow().isoformat())
        except Exception as e:
            logger.warning(f"Redis operation failed: {e}")
    
    async def broadcast_user_status(self, user_id: int, status: str):
        """Broadcast user status change to their contacts"""
        # This would typically query the database to get user's contacts
        # and then send status updates to them
        message = {
            "type": "user_status",
            "user_id": user_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # For now, we'll broadcast to all connected users
        # In production, this should be optimized to only send to contacts
        for connected_user_id in self.active_connections.keys():
            if connected_user_id != user_id:
                await self.send_personal_message(connected_user_id, message)


class WebSocketManager:
    """Main WebSocket manager class"""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Connect a user"""
        await self.connection_manager.connect(websocket, user_id)
    
    async def disconnect(self, user_id: int, websocket: WebSocket = None):
        """Disconnect a user"""
        await self.connection_manager.disconnect(user_id, websocket)
    
    async def handle_message(self, user_id: int, data: dict):
        """Handle incoming WebSocket messages"""
        message_type = data.get("type")
        
        if message_type == "join_chat":
            chat_id = data.get("chat_id")
            if chat_id:
                await self.connection_manager.join_chat_room(user_id, chat_id)
        
        elif message_type == "leave_chat":
            chat_id = data.get("chat_id")
            if chat_id:
                await self.connection_manager.leave_chat_room(user_id, chat_id)
        
        elif message_type == "typing":
            chat_id = data.get("chat_id")
            is_typing = data.get("is_typing", False)
            if chat_id is not None:
                await self.connection_manager.set_typing_status(chat_id, user_id, is_typing)
        
        elif message_type == "message":
            # Handle new message
            chat_id = data.get("chat_id")
            content = data.get("content")
            if chat_id and content:
                # This would typically save the message to database
                # and then broadcast to chat members
                message = {
                    "type": "new_message",
                    "chat_id": chat_id,
                    "sender_id": user_id,
                    "content": content,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await self.connection_manager.broadcast_to_chat(chat_id, message)
        
        elif message_type == "message_read":
            # Handle message read receipt
            message_id = data.get("message_id")
            chat_id = data.get("chat_id")
            if message_id and chat_id:
                read_receipt = {
                    "type": "message_read",
                    "message_id": message_id,
                    "chat_id": chat_id,
                    "reader_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await self.connection_manager.broadcast_to_chat(chat_id, read_receipt, exclude_user_id=user_id)
    
    async def broadcast_new_message(self, chat_id: int, message_data: dict):
        """Broadcast a new message to chat members"""
        await self.connection_manager.broadcast_to_chat(chat_id, {
            "type": "new_message",
            **message_data
        })
    
    async def broadcast_message_status(self, chat_id: int, message_id: int, status: str, user_id: int = None):
        """Broadcast message status change"""
        await self.connection_manager.broadcast_to_chat(chat_id, {
            "type": "message_status",
            "message_id": message_id,
            "status": status,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        })
