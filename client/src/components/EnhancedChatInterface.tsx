'use client'

import React, { useState, useEffect, useRef } from 'react'
import io, { Socket } from 'socket.io-client'
import { 
  Send, MessageCircle, Users, Settings, LogOut, Search, UserPlus, 
  UserCheck, UserX, MoreVertical, Phone, Video, Paperclip, 
  Smile, ThumbsUp, Heart, Laugh, Angry, Sad, ArrowLeft, Menu, RefreshCw
} from 'lucide-react'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

interface Message {
  id: number
  content: string
  sender_id: number
  sender_name: string
  timestamp: string
  type: 'sent' | 'received'
  message_type: 'text' | 'image' | 'video' | 'audio' | 'voice' | 'document'
  reply_to_message_id?: number
  reactions?: MessageReaction[]
}

interface MessageReaction {
  id: number
  reaction: string
  user_id: number
  user_name: string
}

interface User {
  id: number
  username: string
  full_name: string
  email?: string
  is_online: boolean
  avatar_url?: string
  status_message?: string
  last_seen?: string
}

interface Friend {
  user: User
  friendship_id: number
  friends_since: string
}

interface FriendRequest {
  friendship_id: number
  user: User
  sent_at: string
}

interface Chat {
  id: number
  name?: string
  chat_type: 'private' | 'group'
  participants: User[]
  last_message?: Message
  unread_count: number
  is_pinned: boolean
}

interface EnhancedChatInterfaceProps {
  user: User
  onLogout: () => void
}

export default function EnhancedChatInterface({ user: propUser, onLogout }: EnhancedChatInterfaceProps) {
  const [user, setUser] = useState<User>(propUser)
  const [currentChat, setCurrentChat] = useState<Chat | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [socket, setSocket] = useState<Socket | null>(null)
  const [activeTab, setActiveTab] = useState<'chats' | 'friends' | 'discover'>('chats')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<User[]>([])
  const [friends, setFriends] = useState<Friend[]>([])
  const [pendingRequests, setPendingRequests] = useState<{sent: FriendRequest[], received: FriendRequest[]}>({sent: [], received: []})
  const [chats, setChats] = useState<Chat[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const [replyToMessage, setReplyToMessage] = useState<Message | null>(null)
  const [showEmojiPicker, setShowEmojiPicker] = useState(false)
  const [showSidebar, setShowSidebar] = useState(true)
  const [lastMessageTime, setLastMessageTime] = useState(Date.now())
  const [unreadCounts, setUnreadCounts] = useState<{[chatId: number]: number}>({})
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const notificationSoundRef = useRef<HTMLAudioElement | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Initialize WebSocket connection
  useEffect(() => {
    if (user && typeof window !== 'undefined') {
      // Get WebSocket URL from environment or use default
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://127.0.0.1:8000'
      const ws = new WebSocket(`${wsUrl}/ws/${user.id}`)
      
      ws.onopen = () => {
        console.log('Connected to WebSocket')
        setSocket(ws as any) // Type assertion for compatibility
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.type === 'message') {
            const message = data.data
            const formattedMessage = {
              id: message.id,
              content: message.content,
              sender_id: message.sender_id,
              sender_name: message.sender_name || message.sender?.full_name || 'Unknown',
              timestamp: message.timestamp || message.created_at || new Date().toISOString(),
              type: message.sender_id === user.id ? 'sent' : 'received' as 'sent' | 'received',
              message_type: message.message_type || 'text',
              reply_to_message_id: message.reply_to_message_id,
              reactions: message.reactions || []
            }
            
            // Add message to current chat messages if it's the active chat
            if (currentChat && message.chat_id === currentChat.id) {
              setMessages(prev => {
                // Avoid duplicates by checking if message already exists
                const exists = prev.some(msg => msg.id === formattedMessage.id)
                if (exists) return prev
                return [...prev, formattedMessage]
              })
            }
            
            // Update chat list with new message and move to top
            setChats(prevChats => {
              const updatedChats = prevChats.map(chat => {
                if (chat.id === message.chat_id) {
                  return {
                    ...chat,
                    last_message: formattedMessage,
                    unread_count: currentChat?.id === chat.id ? 0 : (chat.unread_count || 0) + 1
                  }
                }
                return chat
              })
              
              // Sort chats by last message time (most recent first)
              return updatedChats.sort((a, b) => {
                const aTime = a.last_message?.timestamp || ''
                const bTime = b.last_message?.timestamp || ''
                return bTime.localeCompare(aTime)
              })
            })
            
            // Show notification for new messages (only if not in current chat or window not focused)
            if (formattedMessage.type === 'received' && (!currentChat || message.chat_id !== currentChat.id || !document.hasFocus())) {
              // Find the chat name for the notification
              const messageChat = chats.find(c => c.id === message.chat_id)
              const chatName = messageChat?.name || 'Private Chat'
              
              // Show toast notification
              toast(
                `${formattedMessage.sender_name}: ${formattedMessage.content}`,
                {
                  icon: '💬',
                  duration: 4000,
                  style: {
                    background: '#f3f4f6',
                    color: '#1f2937',
                    border: '1px solid #d1d5db',
                  },
                  position: 'top-right'
                }
              )
              
              // Play notification sound
              if (notificationSoundRef.current) {
                notificationSoundRef.current.play().catch(e => console.log('Could not play sound:', e))
              }
              
              // Browser notification (if permission granted)
              if (Notification.permission === 'granted') {
                new Notification(`New message from ${formattedMessage.sender_name}`, {
                  body: formattedMessage.content,
                  icon: '/favicon.ico',
                  tag: `chat-${message.chat_id}`
                })
              }
            }
            
            setLastMessageTime(Date.now())
          } else if (data.type === 'typing') {
            setIsTyping(data.is_typing)
          } else if (data.type === 'join_success') {
            console.log(`Joined chat ${data.chat_id}`)
          } else if (data.type === 'error') {
            console.error('WebSocket error:', data.message)
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.onclose = (event) => {
        console.log('WebSocket connection closed:', event.code, event.reason)
        setSocket(null)
        
        // Attempt to reconnect after a delay if not manually closed
        if (event.code !== 1000) {
          setTimeout(() => {
            if (user && typeof window !== 'undefined') {
              console.log('Attempting to reconnect WebSocket...')
              // The useEffect will handle reconnection when socket changes
            }
          }, 3000)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        // Don't show error toast for WebSocket issues as they're often temporary
      }

      return () => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.close(1000, 'Component unmounting') // Normal closure
        }
      }
    }
  }, [user])

  // Initialize notifications and audio
  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Request notification permission
      if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission().then(permission => {
          console.log('Notification permission:', permission)
        })
      }
      
      // Create notification sound
      try {
        // Create a simple notification sound using Web Audio API
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
        const oscillator = audioContext.createOscillator()
        const gainNode = audioContext.createGain()
        
        const playNotificationSound = () => {
          try {
            const osc = audioContext.createOscillator()
            const gain = audioContext.createGain()
            
            osc.connect(gain)
            gain.connect(audioContext.destination)
            
            osc.frequency.setValueAtTime(800, audioContext.currentTime)
            gain.gain.setValueAtTime(0.1, audioContext.currentTime)
            gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3)
            
            osc.start(audioContext.currentTime)
            osc.stop(audioContext.currentTime + 0.3)
          } catch (e) {
            console.log('Could not play notification sound:', e)
          }
        }
        
        // Store the play function
        notificationSoundRef.current = { play: playNotificationSound } as any
      } catch (e) {
        console.log('Could not initialize audio:', e)
      }
    }
  }, [])

  // Load initial data
  useEffect(() => {
    // Only load data if user is authenticated and component is mounted
    if (user && typeof window !== 'undefined') {
      loadFriends()
      loadPendingRequests()
      loadChats()
    }
  }, [user])

  const loadFriends = async () => {
    try {
      console.log('Loading friends...')
      const response = await api.get('/api/users/friends')
      const friendsData = Array.isArray(response.data) ? response.data : []
      console.log('Friends loaded:', friendsData.length, 'friends')
      setFriends(friendsData)
    } catch (error) {
      console.error('Failed to load friends:', error)
      setFriends([]) // Set empty array on error
    }
  }

  const loadPendingRequests = async () => {
    try {
      const response = await api.get('/api/users/friends/requests/pending')
      // Ensure pendingRequests has the correct structure
      const requestsData = response.data || { sent: [], received: [] }
      setPendingRequests({
        sent: Array.isArray(requestsData.sent) ? requestsData.sent : [],
        received: Array.isArray(requestsData.received) ? requestsData.received : []
      })
    } catch (error) {
      console.error('Failed to load friend requests:', error)
      setPendingRequests({ sent: [], received: [] }) // Set empty arrays on error
    }
  }

  const loadChats = async () => {
    try {
      const response = await api.get('/api/chats/')
      // Backend returns { chats: [...] }
      const chatsData = response.data?.chats || []
      const formattedChats = Array.isArray(chatsData) ? chatsData.map(chat => ({
        id: chat.id,
        name: chat.name,
        chat_type: chat.chat_type,
        participants: chat.participants || [],
        last_message: chat.last_message,
        unread_count: chat.unread_count || 0,
        is_pinned: chat.is_pinned || false
      })) : []
      
      // Sort chats by most recent activity (last message timestamp)
      const sortedChats = formattedChats.sort((a, b) => {
        // Pinned chats always come first
        if (a.is_pinned && !b.is_pinned) return -1
        if (!a.is_pinned && b.is_pinned) return 1
        
        // Then sort by last message timestamp (most recent first)
        const aTime = a.last_message?.timestamp || ''
        const bTime = b.last_message?.timestamp || ''
        
        // If no timestamps, sort by chat ID (newer chats first)
        if (!aTime && !bTime) return b.id - a.id
        if (!aTime) return 1
        if (!bTime) return -1
        
        return bTime.localeCompare(aTime)
      })
      
      setChats(sortedChats)
      console.log('Loaded and sorted', sortedChats.length, 'chats')
    } catch (error) {
      console.error('Failed to load chats:', error)
      setChats([]) // Set empty array on error
    }
  }

  const searchUsers = async (query: string) => {
    if (query.length < 2) {
      setSearchResults([])
      return
    }
    
    try {
      const response = await api.get(`/api/users/search?q=${encodeURIComponent(query)}`)
      const searchData = Array.isArray(response.data) ? response.data : []
      setSearchResults(searchData)
    } catch (error) {
      console.error('Failed to search users:', error)
      setSearchResults([]) // Set empty array on error
    }
  }

  const sendFriendRequest = async (userId: number) => {
    try {
      await api.post(`/api/users/friends/request/${userId}`)
      toast.success('Friend request sent!')
      loadPendingRequests()
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to send friend request'
      if (errorMessage.includes('already exists') || errorMessage.includes('Friendship already exists')) {
        toast.success('You are already connected with this user!')
        // Refresh data to show current status
        await Promise.all([loadFriends(), loadPendingRequests(), loadChats()])
        
        // Find the user's name from search results and auto-open/create chat
        const existingUser = searchResults.find(user => user.id === userId)
        if (existingUser) {
          console.log('Auto-opening chat with existing friend:', existingUser.full_name)
          // Wait a bit for data to load, then create/open chat
          setTimeout(async () => {
            await createChatWithNewFriend(userId, existingUser.full_name)
          }, 800)
        }
      } else {
        toast.error(errorMessage)
      }
    }
  }

  const respondToFriendRequest = async (friendshipId: number, action: 'accept' | 'decline') => {
    try {
      console.log(`${action}ing friend request ${friendshipId}...`)
      
      // Get the user info from the request before accepting
      const requestToAccept = pendingRequests.received.find(req => req.friendship_id === friendshipId)
      
      await api.put(`/api/users/friends/request/${friendshipId}/${action}`)
      toast.success(`Friend request ${action}ed!`)
      
      // Reload pending requests immediately
      await loadPendingRequests()
      
      if (action === 'accept' && requestToAccept) {
        // Wait a bit for backend to process, then reload friends and chats
        setTimeout(async () => {
          console.log('Reloading friends and chats after friend acceptance...')
          await Promise.all([
            loadFriends(),
            loadChats() // Also reload chats in case there are existing chats
          ])
          
          // Auto-create and open chat with the newly accepted friend
          console.log('Auto-creating chat with newly accepted friend:', requestToAccept.user.full_name)
          await createChatWithNewFriend(requestToAccept.user.id, requestToAccept.user.full_name)
        }, 1000)
      }
    } catch (error: any) {
      console.error(`Failed to ${action} friend request:`, error)
      toast.error(error.response?.data?.detail || `Failed to ${action} friend request`)
    }
  }

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newMessage.trim() || !currentChat || !socket) return

    const messageData = {
      content: newMessage,
      chat_id: currentChat.id,
      reply_to_message_id: replyToMessage?.id,
      sender_name: user.full_name,
      timestamp: new Date().toISOString()
    }

    // Add message to local state immediately for better UX
    const localMessage: Message = {
      id: Date.now(), // temporary ID
      content: newMessage,
      sender_id: user.id,
      sender_name: user.full_name,
      timestamp: new Date().toISOString(),
      type: 'sent',
      message_type: 'text',
      reply_to_message_id: replyToMessage?.id
    }
    setMessages(prev => [...prev, localMessage])

    // Send via WebSocket
    if (socket && (socket as any).readyState === WebSocket.OPEN) {
      (socket as any).send(JSON.stringify({
        type: 'send_message',
        ...messageData
      }))
    }
    setNewMessage('')
    setReplyToMessage(null)
  }

  const loadMessagesForChat = async (chatId: number) => {
    try {
      const response = await api.get(`/api/messages/?chat_id=${chatId}&limit=50`)
      const messagesData = Array.isArray(response.data) ? response.data : []
      const formattedMessages = messagesData.map(msg => ({
        id: msg.id,
        content: msg.content,
        sender_id: msg.sender_id,
        sender_name: msg.sender?.full_name || msg.sender_name || 'Unknown',
        timestamp: msg.created_at || msg.timestamp,
        type: msg.sender_id === user.id ? 'sent' : 'received',
        message_type: msg.message_type || 'text',
        reply_to_message_id: msg.reply_to_message_id,
        reactions: msg.reactions || []
      }))
      setMessages(formattedMessages)
    } catch (error) {
      console.error('Failed to load messages:', error)
      setMessages([]) // Set empty array on error
    }
  }

  const createChatWithFriend = async (friendUserId: number) => {
    try {
      const response = await api.post('/api/chats/', {
        chat_type: 'private',
        participant_ids: [friendUserId]
      })
      toast.success('Chat created successfully!')
      await loadChats() // Reload chats to show the new one
      setActiveTab('chats') // Switch to chats tab
      
      // Auto-select the newly created chat
      const newChatId = response.data?.id
      if (newChatId) {
        setTimeout(() => {
          const newChat = chats.find(chat => chat.id === newChatId)
          if (newChat) {
            setCurrentChat(newChat)
            loadMessagesForChat(newChatId)
          }
        }, 500)
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to create chat'
      if (errorMessage.includes('already exists')) {
        // Try to find existing chat and open it
        toast.success('Opening existing chat with this friend')
        await loadChats()
        setActiveTab('chats')
      } else {
        toast.error(errorMessage)
      }
    }
  }

  const createChatWithNewFriend = async (friendUserId: number, friendName: string) => {
    try {
      console.log('Creating chat with newly accepted friend:', friendName)
      const response = await api.post('/api/chats/', {
        chat_type: 'private',
        participant_ids: [friendUserId]
      })
      
      console.log('Chat creation response:', response.data)
      toast.success(`Chat started with ${friendName}! 💬`)
      
      // Reload chats to get the latest chat data
      await loadChats()
      
      // Switch to chats tab
      setActiveTab('chats')
      
      // Auto-select and open the newly created chat
      const newChatId = response.data?.id
      if (newChatId) {
        // Wait a bit for the chats to load, then select the new chat
        setTimeout(async () => {
          // Reload chats again to make sure we have the latest data
          await loadChats()
          
          setTimeout(() => {
            // Find the chat in the updated chats list
            setChats(currentChats => {
              const newChat = currentChats.find(chat => chat.id === newChatId)
              if (newChat) {
                console.log('Opening chat with:', friendName)
                setCurrentChat(newChat)
                loadMessagesForChat(newChatId)
                
                // On mobile, hide sidebar to show the chat
                if (window.innerWidth < 1024) {
                  setShowSidebar(false)
                }
                
                // Join the WebSocket room for this chat
                if (socket && (socket as any).readyState === WebSocket.OPEN) {
                  (socket as any).send(JSON.stringify({
                    type: 'join_chat',
                    chat_id: newChatId
                  }))
                }
              } else {
                console.warn('Could not find newly created chat in chats list')
              }
              return currentChats
            })
          }, 300)
        }, 800)
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to create chat'
      console.error('Error creating chat with new friend:', error)
      
      if (errorMessage.includes('already exists')) {
        // Try to find and open existing chat
        console.log('Chat already exists, trying to open it...')
        toast.success(`Opening existing chat with ${friendName}! 💬`)
        
        await loadChats()
        setActiveTab('chats')
        
        // Try to find the existing chat with this friend
        setTimeout(async () => {
          await loadChats()
          setTimeout(() => {
            setChats(currentChats => {
              // Find chat that includes this friend
              const existingChat = currentChats.find(chat => 
                chat.participants.some(p => p.id === friendUserId)
              )
              
              if (existingChat) {
                console.log('Found existing chat, opening it')
                setCurrentChat(existingChat)
                loadMessagesForChat(existingChat.id)
                
                // On mobile, hide sidebar to show the chat
                if (window.innerWidth < 1024) {
                  setShowSidebar(false)
                }
                
                // Join the WebSocket room for this chat
                if (socket && (socket as any).readyState === WebSocket.OPEN) {
                  (socket as any).send(JSON.stringify({
                    type: 'join_chat',
                    chat_id: existingChat.id
                  }))
                }
              }
              return currentChats
            })
          }, 300)
        }, 500)
      } else {
        toast.error(`Failed to start chat with ${friendName}: ${errorMessage}`)
      }
    }
  }

  const addReaction = async (messageId: number, reaction: string) => {
    try {
      await api.post(`/api/messages/${messageId}/reactions`, { reaction })
      // Refresh messages or update state
    } catch (error) {
      console.error('Failed to add reaction:', error)
    }
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  }

  const getAvatarDisplay = (user: User) => {
    if (user.avatar_url) {
      return <img src={user.avatar_url} alt={user.full_name} className="w-full h-full object-cover" />
    }
    return user.full_name.charAt(0).toUpperCase()
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const renderSidebar = () => (
    <div className={`${showSidebar && currentChat ? 'hidden' : 'flex'} lg:flex w-full lg:w-1/3 bg-gray-50 border-r border-gray-200 flex-col`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-semibold">Chat App</h1>
          <div className="flex items-center space-x-2">
            <Settings className="h-5 w-5 text-gray-500 cursor-pointer hover:text-gray-700" />
            <button
              onClick={onLogout}
              className="p-1.5 text-gray-500 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* User info */}
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center text-white font-semibold">
            {getAvatarDisplay(user)}
          </div>
          <div className="flex-1">
            <p className="font-medium">{user.full_name}</p>
            <p className="text-sm text-gray-500">@{user.username}</p>
          </div>
          <div className="w-3 h-3 bg-green-400 rounded-full"></div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        {(['chats', 'friends', 'discover'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 p-3 text-sm font-medium capitalize ${
              activeTab === tab 
                ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50' 
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'chats' && (
          <div className="p-4 space-y-2">
            {chats.length === 0 ? (
              <div className="text-center text-gray-500 mt-8">
                <MessageCircle className="mx-auto mb-2 h-12 w-12 text-gray-300" />
                <p>No chats yet</p>
                <p className="text-xs">Add friends to start chatting!</p>
              </div>
            ) : (
              chats.map(chat => (
                <div
                  key={chat.id}
                  onClick={() => {
                    setCurrentChat(chat)
                    setMessages([]) // Clear messages when switching chats
                    loadMessagesForChat(chat.id) // Load messages for this chat
                    if (socket && (socket as any).readyState === WebSocket.OPEN) {
                      (socket as any).send(JSON.stringify({
                        type: 'join_chat',
                        chat_id: chat.id
                      }))
                    }
                    // On mobile, hide sidebar when chat is selected
                    if (window.innerWidth < 1024) {
                      setShowSidebar(false)
                    }
                  }}
                  className={`p-3 rounded-lg cursor-pointer transition-colors ${
                    currentChat?.id === chat.id ? 'bg-blue-100 border border-blue-200' : 'hover:bg-gray-100'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center text-white font-semibold">
                      {chat.name ? chat.name.charAt(0) : 'P'}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium">{chat.name || 'Private Chat'}</p>
                      <p className="text-sm text-gray-500 truncate">
                        {chat.last_message?.content || 'No messages yet'}
                      </p>
                    </div>
                    {chat.unread_count > 0 && (
                      <div className="w-5 h-5 bg-blue-500 text-white text-xs rounded-full flex items-center justify-center">
                        {chat.unread_count}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'friends' && (
          <div className="p-4">
            {/* Pending requests */}
            {pendingRequests.received.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Friend Requests</h3>
                <div className="space-y-2">
                  {pendingRequests.received.map(request => (
                    <div key={request.friendship_id} className="p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 bg-gray-500 rounded-full flex items-center justify-center text-white text-sm">
                          {getAvatarDisplay(request.user)}
                        </div>
                        <div className="flex-1">
                          <p className="font-medium text-sm">{request.user.full_name}</p>
                          <p className="text-xs text-gray-500">@{request.user.username}</p>
                        </div>
                        <div className="flex space-x-1">
                          <button
                            onClick={() => respondToFriendRequest(request.friendship_id, 'accept')}
                            className="p-1 bg-green-500 text-white rounded hover:bg-green-600"
                          >
                            <UserCheck className="h-3 w-3" />
                          </button>
                          <button
                            onClick={() => respondToFriendRequest(request.friendship_id, 'decline')}
                            className="p-1 bg-red-500 text-white rounded hover:bg-red-600"
                          >
                            <UserX className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Friends list */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-gray-700">Friends ({friends.length})</h3>
                <button
                  onClick={async () => {
                    console.log('Manual refresh triggered')
                    await Promise.all([loadFriends(), loadChats()])
                    toast.success('Data refreshed!')
                  }}
                  className="p-1 text-gray-500 hover:text-blue-500 transition-colors"
                  title="Refresh data"
                >
                  <RefreshCw className="h-4 w-4" />
                </button>
              </div>
              <div className="space-y-2">
                {friends.map(friend => (
                  <div key={friend.friendship_id} className="p-3 bg-white rounded-lg border hover:bg-gray-50">
                    <div className="flex items-center space-x-3">
                      <div className="relative">
                        <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center text-white font-semibold">
                          {getAvatarDisplay(friend.user)}
                        </div>
                        {friend.user.is_online && (
                          <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-400 rounded-full border-2 border-white"></div>
                        )}
                      </div>
                      <div className="flex-1">
                        <p className="font-medium">{friend.user.full_name}</p>
                        <p className="text-sm text-gray-500">
                          {friend.user.is_online ? 'Online' : 'Offline'}
                        </p>
                      </div>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => createChatWithFriend(friend.user.id)}
                          className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-xs"
                          title="Start Chat"
                        >
                          <MessageCircle className="h-4 w-4" />
                        </button>
                        <button className="p-1 text-gray-400 hover:text-gray-600">
                          <MoreVertical className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'discover' && (
          <div className="p-4">
            <div className="mb-4">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search users..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value)
                    searchUsers(e.target.value)
                  }}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="space-y-2">
              {searchResults.map(searchUser => (
                <div key={searchUser.id} className="p-3 bg-white rounded-lg border hover:bg-gray-50">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-purple-500 rounded-full flex items-center justify-center text-white font-semibold">
                      {getAvatarDisplay(searchUser)}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium">{searchUser.full_name}</p>
                      <p className="text-sm text-gray-500">@{searchUser.username}</p>
                    </div>
                    <button
                      onClick={() => sendFriendRequest(searchUser.id)}
                      className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                      title="Send Friend Request"
                    >
                      <UserPlus className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )

  const renderChatArea = () => {
    if (!currentChat) {
      return (
        <div className={`${currentChat || !showSidebar ? 'flex' : 'hidden lg:flex'} flex-1 flex-col items-center justify-center bg-gray-100`}>
          <div className="text-center px-4">
            <MessageCircle className="mx-auto mb-4 h-16 w-16 text-gray-300" />
            <h2 className="text-xl font-semibold text-gray-600 mb-2">Welcome to Chat App</h2>
            <p className="text-gray-500">Select a chat to start messaging</p>
            <button 
              onClick={() => setShowSidebar(true)}
              className="lg:hidden mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
            >
              View Chats
            </button>
          </div>
        </div>
      )
    }

    return (
      <div className="flex-1 flex flex-col bg-white">
        {/* Chat header */}
        <div className="p-4 border-b border-gray-200 bg-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {/* Back button for mobile */}
              <button 
                onClick={() => {
                  setCurrentChat(null)
                  setShowSidebar(true)
                }}
                className="lg:hidden p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                <ArrowLeft className="h-5 w-5" />
              </button>
              
              <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center text-white font-semibold">
                {currentChat.name ? currentChat.name.charAt(0) : 'P'}
              </div>
              <div>
                <p className="font-semibold">{currentChat.name || 'Private Chat'}</p>
                <p className="text-sm text-gray-500">
                  {isTyping ? 'Typing...' : `${currentChat.participants.length} members`}
                </p>
              </div>
            </div>
            <div className="flex space-x-2">
              <button className="hidden sm:block p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
                <Phone className="h-5 w-5" />
              </button>
              <button className="hidden sm:block p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
                <Video className="h-5 w-5" />
              </button>
              <button className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
                <MoreVertical className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Reply banner */}
        {replyToMessage && (
          <div className="p-3 bg-blue-50 border-b border-blue-200 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-1 h-8 bg-blue-500 rounded"></div>
              <div>
                <p className="text-sm font-medium">Replying to {replyToMessage.sender_name}</p>
                <p className="text-sm text-gray-600 truncate">{replyToMessage.content}</p>
              </div>
            </div>
            <button
              onClick={() => setReplyToMessage(null)}
              className="p-1 text-gray-500 hover:text-gray-700"
            >
              ✕
            </button>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-8">
              <MessageCircle className="mx-auto mb-2 h-12 w-12 text-gray-300" />
              <p>No messages yet. Start the conversation!</p>
            </div>
          ) : (
            messages.map((message) => (
              <div key={message.id} className="space-y-1">
                {message.reply_to_message_id && (
                  <div className="ml-12 p-2 bg-gray-100 rounded border-l-4 border-gray-300 text-sm">
                    <p className="font-medium text-gray-600">Replying to previous message</p>
                  </div>
                )}
                <div
                  className={`flex ${message.type === 'sent' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className="flex items-end space-x-2 max-w-sm sm:max-w-md lg:max-w-lg">
                    {message.type === 'received' && (
                      <div className="w-8 h-8 bg-gray-500 rounded-full flex items-center justify-center text-white text-xs">
                        {message.sender_name.charAt(0)}
                      </div>
                    )}
                    <div
                      className={`group relative px-4 py-2 rounded-lg ${
                        message.type === 'sent'
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-200 text-gray-800'
                      }`}
                    >
                      <p className="text-sm">{message.content}</p>
                      <div className="flex items-center justify-between mt-1">
                        <p
                          className={`text-xs ${
                            message.type === 'sent' ? 'text-blue-100' : 'text-gray-500'
                          }`}
                        >
                          {formatTime(message.timestamp)}
                        </p>
                        {/* Reactions */}
                        {message.reactions && message.reactions.length > 0 && (
                          <div className="flex space-x-1 ml-2">
                            {message.reactions.map(reaction => (
                              <span key={reaction.id} className="text-sm">
                                {reaction.reaction}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      
                      {/* Reaction options (appear on hover) */}
                      <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-white border rounded-lg shadow-lg p-1 opacity-0 group-hover:opacity-100 transition-opacity flex space-x-1">
                        {['👍', '❤️', '😂', '😮', '😢', '😡'].map(emoji => (
                          <button
                            key={emoji}
                            onClick={() => addReaction(message.id, emoji)}
                            className="p-1 hover:bg-gray-100 rounded"
                          >
                            {emoji}
                          </button>
                        ))}
                        <button
                          onClick={() => setReplyToMessage(message)}
                          className="p-1 hover:bg-gray-100 rounded text-xs text-gray-600"
                        >
                          Reply
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Message input */}
        <div className="p-4 border-t border-gray-200 bg-white">
          <form onSubmit={sendMessage} className="flex items-end space-x-2">
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              multiple
              onChange={(e) => {
                // Handle file upload
                console.log('Files selected:', e.target.files)
              }}
            />
            
            <div className="flex-1 relative">
              <input
                type="text"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder="Type a message..."
                className="w-full px-4 py-3 pr-20 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex items-center space-x-1">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="p-1 text-gray-500 hover:text-gray-700 rounded"
                >
                  <Paperclip className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setShowEmojiPicker(!showEmojiPicker)}
                  className="p-1 text-gray-500 hover:text-gray-700 rounded"
                >
                  <Smile className="h-4 w-4" />
                </button>
              </div>
            </div>
            
            <button
              type="submit"
              disabled={!newMessage.trim()}
              className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex bg-gray-100">
      {renderSidebar()}
      {renderChatArea()}
    </div>
  )
}
