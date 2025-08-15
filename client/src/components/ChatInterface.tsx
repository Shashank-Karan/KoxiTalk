'use client'

import React, { useState, useEffect, useRef } from 'react'
import io, { Socket } from 'socket.io-client'
import { Send, MessageCircle, Users, Settings, LogOut } from 'lucide-react'

interface Message {
  id: number
  content: string
  sender_id: number
  sender_name: string
  timestamp: string
  type: 'sent' | 'received'
}

interface User {
  id: number
  username: string
  full_name: string
  is_online: boolean
}

interface ChatInterfaceProps {
  user: any
  onLogout: () => void
}

export default function ChatInterface({ user: propUser, onLogout }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [user, setUser] = useState<User | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Use the user prop
  useEffect(() => {
    if (propUser) {
      setUser({
        ...propUser,
        is_online: true
      })
      setIsAuthenticated(true)
    }
  }, [propUser])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const addMessage = (content: string, type: 'sent' | 'received' = 'sent') => {
    const newMsg: Message = {
      id: Date.now(),
      content,
      sender_id: user?.id || 1,
      sender_name: user?.full_name || 'You',
      timestamp: new Date().toISOString(),
      type
    }
    setMessages(prev => [...prev, newMsg])
  }

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newMessage.trim()) return

    // Add message to local state
    addMessage(newMessage, 'sent')
    setNewMessage('')

    // TODO: Send to backend API
    // For now, simulate a response
    setTimeout(() => {
      addMessage(`Echo: ${newMessage}`, 'received')
    }, 1000)
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  }

  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <MessageCircle className="mx-auto mb-4 h-12 w-12 text-blue-500" />
          <h1 className="text-2xl font-bold mb-2">Real-Time Chat Application</h1>
          <p className="text-gray-600">Connecting...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-white">
      {/* Sidebar */}
      <div className="w-1/4 bg-gray-50 border-r border-gray-200 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Chats</h2>
            <Settings className="h-5 w-5 text-gray-500 cursor-pointer hover:text-gray-700" />
          </div>
        </div>

        {/* User info */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center text-white font-semibold">
                {user?.full_name.charAt(0)}
              </div>
              <div>
                <p className="font-medium">{user?.full_name}</p>
                <p className="text-sm text-gray-500">@{user?.username}</p>
              </div>
            </div>
            <button
              onClick={onLogout}
              className="p-1.5 text-gray-500 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Chat list */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-4">
            <div className="bg-white rounded-lg p-3 border border-gray-200 cursor-pointer hover:bg-gray-50">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white text-sm">
                  D
                </div>
                <div>
                  <p className="font-medium">Demo Chat</p>
                  <p className="text-sm text-gray-500">Click to start chatting</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Chat header */}
        <div className="p-4 border-b border-gray-200 bg-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center text-white font-semibold">
                D
              </div>
              <div>
                <p className="font-semibold">Demo Chat</p>
                <p className="text-sm text-gray-500">
                  {isConnected ? (
                    <span className="text-green-500">• Online</span>
                  ) : (
                    <span className="text-gray-400">• Offline</span>
                  )}
                </p>
              </div>
            </div>
            <Users className="h-5 w-5 text-gray-500 cursor-pointer hover:text-gray-700" />
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-8">
              <MessageCircle className="mx-auto mb-2 h-12 w-12 text-gray-300" />
              <p>No messages yet. Start the conversation!</p>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.type === 'sent' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                    message.type === 'sent'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-200 text-gray-800'
                  }`}
                >
                  <p className="text-sm">{message.content}</p>
                  <p
                    className={`text-xs mt-1 ${
                      message.type === 'sent' ? 'text-blue-100' : 'text-gray-500'
                    }`}
                  >
                    {formatTime(message.timestamp)}
                  </p>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Message input */}
        <div className="p-4 border-t border-gray-200 bg-white">
          <form onSubmit={handleSendMessage} className="flex space-x-2">
            <input
              type="text"
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              placeholder="Type a message..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              type="submit"
              disabled={!newMessage.trim()}
              className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
