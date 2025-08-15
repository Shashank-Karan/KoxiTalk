'use client'

import { useState, useEffect } from 'react'
import { Toaster } from 'react-hot-toast'
import EnhancedChatInterface from '@/components/EnhancedChatInterface'
import Login from '@/components/Login'
import LoadingSpinner from '@/components/LoadingSpinner'

export default function Home() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isClient, setIsClient] = useState(false)

  useEffect(() => {
    // Set client-side flag to prevent hydration mismatch
    setIsClient(true)
  }, [])

  useEffect(() => {
    // Check if user is already logged in and validate token
    const validateToken = async () => {
      // Only run on client side to avoid hydration mismatch
      if (!isClient) {
        return
      }
      
      const token = localStorage.getItem('access_token')
      if (token) {
        try {
          const { api } = await import('@/lib/api')
          const response = await api.get('/api/auth/me')
          setUser(response.data)
        } catch (error) {
          console.error('Token validation failed:', error)
          // Clear invalid tokens
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
        }
      }
      setLoading(false)
    }
    
    if (isClient) {
      validateToken()
    }
  }, [isClient])

  const handleLogin = (userData: any) => {
    setUser(userData)
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
  }

  // Don't render anything until client-side hydration is complete
  if (!isClient) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" text="Initializing..." />
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" text="Loading..." />
      </div>
    )
  }

  return (
    <>
      <Toaster position="top-right" />
      <main className="min-h-screen bg-gray-100">
        {user ? (
          <EnhancedChatInterface user={user} onLogout={handleLogout} />
        ) : (
          <Login onLogin={handleLogin} />
        )}
      </main>
    </>
  )
}
