#!/usr/bin/env python3
"""
Main FastAPI application entry point
"""

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import get_settings
from app.core.database import init_db
from app.core.websocket_manager import WebSocketManager

# Import route modules
from app.api.routes import auth, users, chats, messages, files

settings = get_settings()

app = FastAPI(
    title="ChatApp API",
    description="Real-time chat application API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(",") if settings.allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(chats.router, prefix="/api/v1/chats", tags=["chats"])
app.include_router(messages.router, prefix="/api/v1/messages", tags=["messages"])
app.include_router(files.router, prefix="/api/v1/files", tags=["files"])

# Initialize WebSocket manager
websocket_manager = WebSocketManager()

@app.on_event("startup")
async def startup_event():
    """Initialize database and other startup tasks"""
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "ChatApp API is running", "docs": "/docs"}

# Test WebSocket endpoint (no authentication)
@app.websocket("/test-ws")
async def test_websocket_endpoint(websocket: WebSocket):
    """Simple test WebSocket endpoint"""
    await websocket.accept()
    try:
        await websocket.send_text("WebSocket connection established!")
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except Exception as e:
        print(f"Test WebSocket error: {e}")

# WebSocket endpoint for real-time messaging
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for real-time communication"""
    await websocket_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                # Parse JSON message and handle it
                import json
                message_data = json.loads(data)
                await websocket_manager.handle_message(user_id, message_data)
            except json.JSONDecodeError:
                # Handle plain text messages
                message = {
                    "type": "message",
                    "content": data,
                    "sender_id": user_id,
                    "timestamp": f"{__import__('datetime').datetime.utcnow().isoformat()}"
                }
                # Echo back to sender for now
                await websocket_manager.connection_manager.send_personal_message(user_id, message)
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")
    finally:
        await websocket_manager.disconnect(user_id)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
