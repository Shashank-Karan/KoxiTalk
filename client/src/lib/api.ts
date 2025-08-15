import axios from 'axios'

// API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

// Create axios instance with default config
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    // Only add token if we're on the client side
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle errors and token refresh
api.interceptors.response.use(
  (response) => {
    return response
  },
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      // Try to refresh the token
      if (typeof window !== 'undefined') {
        const refreshToken = localStorage.getItem('refresh_token')
        if (refreshToken) {
          try {
            const response = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
              refresh_token: refreshToken
            })
            
            const { access_token, refresh_token: newRefreshToken } = response.data
            localStorage.setItem('access_token', access_token)
            localStorage.setItem('refresh_token', newRefreshToken)
            
            // Retry the original request with new token
            originalRequest.headers.Authorization = `Bearer ${access_token}`
            return api(originalRequest)
          } catch (refreshError) {
            // Refresh failed, clear tokens and redirect to login
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
            window.location.reload() // Force page reload to show login
            return Promise.reject(refreshError)
          }
        } else {
          // No refresh token, clear any existing access token
          localStorage.removeItem('access_token')
          window.location.reload()
        }
      }
    }
    return Promise.reject(error)
  }
)

// API functions
export const apiClient = {
  // Health check
  health: () => api.get('/health'),

  // Auth
  login: (credentials: { username: string; password: string }) => {
    const params = new URLSearchParams()
    params.append('username', credentials.username)
    params.append('password', credentials.password)
    return api.post('/api/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
  
  register: (userData: {
    email: string
    username: string
    full_name: string
    password: string
  }) => api.post('/api/auth/register', userData),

  // Users
  getCurrentUser: () => api.get('/api/auth/me'),
  updateUser: (userData: any) => api.put('/api/users/me', userData),
  getUserById: (userId: number) => api.get(`/api/users/${userId}`),
  searchUsers: (query: string) => api.get(`/api/users/search?q=${query}`),

  // Friend Management
  sendFriendRequest: (userId: number) => api.post(`/api/users/friends/request/${userId}`),
  respondToFriendRequest: (friendshipId: number, action: 'accept' | 'decline') => 
    api.put(`/api/users/friends/request/${friendshipId}/${action}`),
  getFriends: () => api.get('/api/users/friends'),
  getPendingFriendRequests: () => api.get('/api/users/friends/requests/pending'),
  removeFriend: (friendshipId: number) => api.delete(`/api/users/friends/${friendshipId}`),

  // User Blocking
  blockUser: (userId: number) => api.post(`/api/users/block/${userId}`),
  unblockUser: (userId: number) => api.delete(`/api/users/block/${userId}`),
  getBlockedUsers: () => api.get('/api/users/blocked'),

  // Chats
  getChats: () => api.get('/api/chats/'),
  createChat: (chatData: any) => api.post('/api/chats/', chatData),
  getChatById: (chatId: number) => api.get(`/api/chats/${chatId}`),
  updateChat: (chatId: number, chatData: any) => api.put(`/api/chats/${chatId}`, chatData),
  deleteChat: (chatId: number) => api.delete(`/api/chats/${chatId}`),
  
  // Chat Members
  addChatMember: (chatId: number, userId: number) => api.post(`/api/chats/${chatId}/members`, { user_id: userId }),
  removeChatMember: (chatId: number, userId: number) => api.delete(`/api/chats/${chatId}/members/${userId}`),
  updateMemberRole: (chatId: number, userId: number, role: string) => 
    api.put(`/api/chats/${chatId}/members/${userId}`, { role }),

  // Messages
  getMessages: (chatId: number, limit?: number, offset?: number) => 
    api.get(`/api/messages/?chat_id=${chatId}${limit ? `&limit=${limit}` : ''}${offset ? `&offset=${offset}` : ''}`),
  sendMessage: (messageData: any) => api.post('/api/messages/', messageData),
  editMessage: (messageId: number, content: string) => api.put(`/api/messages/${messageId}`, { content }),
  deleteMessage: (messageId: number) => api.delete(`/api/messages/${messageId}`),
  
  // Message Reactions
  addReaction: (messageId: number, reaction: string) => api.post(`/api/messages/${messageId}/reactions`, { reaction }),
  removeReaction: (messageId: number, reactionId: number) => api.delete(`/api/messages/${messageId}/reactions/${reactionId}`),
  
  // Files
  uploadFile: (file: File, chatId?: number) => {
    const formData = new FormData()
    formData.append('file', file)
    if (chatId) formData.append('chat_id', chatId.toString())
    return api.post('/api/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  getFile: (fileId: number) => api.get(`/api/files/${fileId}`),
  deleteFile: (fileId: number) => api.delete(`/api/files/${fileId}`)
}

export default apiClient
