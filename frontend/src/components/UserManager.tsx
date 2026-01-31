/**
 * UserManager Component
 * 
 * Manages user selection and authentication.
 * Features:
 * - User login/registration
 * - Switch between existing users
 * - Create new user profiles
 * - Persist user selection in localStorage
 * - Trigger register reload on user change
 * 
 * @component
 * @param {Object} props - Component props
 * @param {Function} props.onUserChange - Callback when user is changed or selected
 * @returns {JSX.Element} User management interface
 */

import { useState, useEffect } from 'react'

interface UserManagerProps {
  onUserChange: (username: string) => void
}

export default function UserManager({ onUserChange }: UserManagerProps) {
  const [username, setUsername] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [existingUsers, setExistingUsers] = useState<string[]>([])
  const [showNewUserForm, setShowNewUserForm] = useState(false)
  const [newUsername, setNewUsername] = useState('')

  useEffect(() => {
    const savedUsername = localStorage.getItem('phonox_username')
    console.log('UserManager: Initializing, saved username:', savedUsername)
    console.log('UserManager: Mobile detection - isMobile:', /Mobi|Android/i.test(navigator.userAgent))
    console.log('UserManager: LocalStorage available:', typeof(Storage) !== "undefined")
    
    // Load existing users from API
    loadExistingUsers()
    if (savedUsername) {
      console.log('UserManager: Setting username and triggering onUserChange for:', savedUsername)
      setUsername(savedUsername)
      onUserChange(savedUsername)
    } else {
      console.log('UserManager: No saved username, showing modal')
      setShowModal(true)
    }
  }, [])

  const loadExistingUsers = async () => {
    try {
      const API_BASE = window.location.hostname === 'localhost' 
        ? 'http://localhost:8000' 
        : `http://${window.location.hostname}:8000`
      console.log('UserManager: API_BASE:', API_BASE)
      const url = `${API_BASE}/api/register/users?_t=${Date.now()}` // Cache busting
      console.log('UserManager: Fetching from:', url)
      const response = await fetch(url, { 
        cache: 'no-cache',
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      })
      if (response.ok) {
        const users = await response.json()
        setExistingUsers(users)
        console.log('UserManager: Loaded existing users:', users)
      } else {
        console.error('UserManager: API response not ok:', response.status, response.statusText)
      }
    } catch (error) {
      console.error('UserManager: Failed to load existing users:', error)
    }
  }

  const handleSave = () => {
    if (username.trim()) {
      localStorage.setItem('phonox_username', username.trim())
      onUserChange(username.trim())
      setShowModal(false)
      loadExistingUsers() // Refresh user list
    }
  }

  const handleUserSwitch = (selectedUser: string) => {
    console.log('UserManager: Switching to user:', selectedUser)
    setUsername(selectedUser)
    localStorage.setItem('phonox_username', selectedUser)
    // Force service worker to update cache when switching users
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistrations().then(function(registrations) {
        for (let registration of registrations) {
          registration.update()
        }
      })
    }
    // Trigger user change callback to reload register
    onUserChange(selectedUser)
  }

  const handleNewUser = () => {
    setShowNewUserForm(true)
  }

  const handleCreateNewUser = () => {
    if (newUsername.trim()) {
      const trimmedName = newUsername.trim()
      setUsername(trimmedName)
      localStorage.setItem('phonox_username', trimmedName)
      onUserChange(trimmedName)
      setNewUsername('')
      setShowNewUserForm(false)
      loadExistingUsers() // Refresh user list
    }
  }

  const handleCancelNewUser = () => {
    setNewUsername('')
    setShowNewUserForm(false)
  }

  const handleLogout = () => {
    localStorage.removeItem('phonox_username')
    setUsername('')
    setShowModal(true)
    onUserChange('')
    loadExistingUsers() // Refresh user list
  }

  // Detect if user is on mobile device
  const isMobile = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent)

  if (showModal) {
    
    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        background: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999
      }}>
        <div style={{
          background: 'linear-gradient(135deg, #1a1a2e 0%, #0f0f1e 50%, #16213e 100%)',
          border: '1px solid rgba(102, 126, 234, 0.3)',
          padding: isMobile ? '1.5rem 1rem' : '2rem',
          borderRadius: '16px',
          minWidth: isMobile ? '90vw' : '400px',
          maxWidth: isMobile ? '90vw' : '500px',
          maxHeight: isMobile ? '90vh' : 'auto',
          overflow: 'auto',
          textAlign: 'center',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.5)'
        }}>
          <h2 style={{ 
            margin: '0 0 1.5rem 0',
            color: '#e0e7ff',
            fontSize: isMobile ? '1.3rem' : '1.8rem',
            fontWeight: 700,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text'
          }}>
            🎵 Phonox
          </h2>
          
          {/* Show existing users first - mobile-friendly */}
          {existingUsers.length > 0 && (
            <div>
              <p style={{ 
                margin: '0 0 1rem 0', 
                color: 'rgba(255, 255, 255, 0.7)',
                fontSize: isMobile ? '0.95rem' : '1rem'
              }}>
                Select your name:
              </p>
              <div style={{
                display: 'grid',
                gridTemplateColumns: isMobile ? 'repeat(auto-fit, minmax(100px, 1fr))' : 'repeat(auto-fit, minmax(120px, 1fr))',
                gap: isMobile ? '8px' : '10px',
                margin: '0 0 1.5rem 0'
              }}>
                {existingUsers.map(user => (
                  <button
                    key={user}
                    onClick={() => {
                      setUsername(user)
                      handleUserSwitch(user)
                      setShowModal(false)
                    }}
                    style={{
                      background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                      color: 'white',
                      border: 'none',
                      padding: isMobile ? '0.75rem' : '1rem',
                      borderRadius: '10px',
                      fontSize: isMobile ? '0.85rem' : '1rem',
                      cursor: 'pointer',
                      minHeight: isMobile ? '48px' : '60px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'all 0.2s',
                      fontWeight: 600,
                      boxShadow: '0 4px 12px rgba(16, 185, 129, 0.2)'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateY(-2px)'
                      e.currentTarget.style.boxShadow = '0 6px 16px rgba(16, 185, 129, 0.3)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)'
                      e.currentTarget.style.boxShadow = '0 4px 12px rgba(16, 185, 129, 0.2)'
                    }}
                  >
                    👤 {user}
                  </button>
                ))}
              </div>
              
              <div style={{ 
                borderTop: '1px solid rgba(255, 255, 255, 0.1)', 
                paddingTop: '1rem',
                margin: '1rem 0'
              }}>
                <p style={{ 
                  margin: '0 0 1rem 0', 
                  color: 'rgba(255, 255, 255, 0.7)',
                  fontSize: isMobile ? '0.85rem' : '0.9rem'
                }}>
                  Or create a new user:
                </p>
              </div>
            </div>
          )}
          
          {/* Input for new user */}
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder={existingUsers.length > 0 ? "New username" : "Your name"}
            style={{
              width: '100%',
              padding: isMobile ? '0.75rem' : '0.75rem',
              border: '1px solid rgba(102, 126, 234, 0.3)',
              borderRadius: '10px',
              marginBottom: '1rem',
              fontSize: isMobile ? '1rem' : '1rem',
              boxSizing: 'border-box',
              background: 'rgba(255, 255, 255, 0.05)',
              color: '#e0e7ff',
              transition: 'all 0.2s'
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = 'rgba(102, 126, 234, 0.6)'
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = 'rgba(102, 126, 234, 0.3)'
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
            }}
            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
            autoFocus={existingUsers.length === 0}
          />
          <button
            onClick={handleSave}
            disabled={!username.trim()}
            style={{
              background: username.trim() ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 'rgba(255, 255, 255, 0.1)',
              color: 'white',
              border: username.trim() ? 'none' : '1px solid rgba(255, 255, 255, 0.2)',
              padding: isMobile ? '0.85rem 1.25rem' : '0.85rem 2rem',
              borderRadius: '10px',
              fontSize: isMobile ? '0.95rem' : '1rem',
              cursor: username.trim() ? 'pointer' : 'not-allowed',
              minHeight: isMobile ? '48px' : '50px',
              width: isMobile ? '100%' : 'auto',
              fontWeight: 600,
              transition: 'all 0.2s',
              boxShadow: username.trim() ? '0 4px 16px rgba(102, 126, 234, 0.3)' : 'none'
            }}
            onMouseEnter={(e) => {
              if (username.trim()) {
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.4)'
              }
            }}
            onMouseLeave={(e) => {
              if (username.trim()) {
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = '0 4px 16px rgba(102, 126, 234, 0.3)'
              }
            }}
          >
            {existingUsers.length > 0 ? 'Create New User' : 'Continue'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
      <span style={{ color: 'rgba(255, 255, 255, 0.9)', fontSize: '0.9rem' }}>
        👤 {username}
      </span>
      
      {/* Always visible user list for mobile */}
      {existingUsers.length > 0 && (
        <div style={{ display: 'flex', gap: isMobile ? '4px' : '5px', flexWrap: 'wrap' }}>
          {existingUsers.map(user => (
            <button
              key={user}
              onClick={() => handleUserSwitch(user)}
              style={{
                background: user === username ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 'rgba(255, 255, 255, 0.05)',
                border: user === username ? 'none' : '1px solid rgba(102, 126, 234, 0.3)',
                color: user === username ? 'white' : 'rgba(255, 255, 255, 0.8)',
                padding: isMobile ? '6px 8px' : '6px 10px',
                borderRadius: '10px',
                fontSize: isMobile ? '0.75rem' : '0.8rem',
                cursor: 'pointer',
                transition: 'all 0.2s',
                fontWeight: user === username ? 600 : 500,
                boxShadow: user === username ? '0 2px 8px rgba(102, 126, 234, 0.3)' : 'none'
              }}
              onMouseEnter={(e) => {
                if (user !== username) {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                  e.currentTarget.style.borderColor = 'rgba(102, 126, 234, 0.5)'
                }
              }}
              onMouseLeave={(e) => {
                if (user !== username) {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                  e.currentTarget.style.borderColor = 'rgba(102, 126, 234, 0.3)'
                }
              }}
            >
              {user}
            </button>
          ))}
        </div>
      )}
      
      {/* Always visible Add User button */}
      <button
        onClick={handleNewUser}
        style={{
          background: 'rgba(102, 126, 234, 0.2)',
          border: '1px solid rgba(102, 126, 234, 0.5)',
          color: 'rgba(102, 126, 234, 1)',
          padding: isMobile ? '6px 8px' : '6px 10px',
          borderRadius: '10px',
          fontSize: isMobile ? '0.65rem' : '0.7rem',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '32px',
          minWidth: 'auto',
          whiteSpace: 'nowrap',
          transition: 'all 0.2s'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'rgba(102, 126, 234, 0.3)'
          e.currentTarget.style.borderColor = 'rgba(102, 126, 234, 0.8)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'rgba(102, 126, 234, 0.2)'
          e.currentTarget.style.borderColor = 'rgba(102, 126, 234, 0.5)'
        }}
      >
        + New
      </button>

      {showNewUserForm && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: 'rgba(0,0,0,0.8)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999
        }}>
          <div style={{
            background: 'white',
            padding: '2rem',
            borderRadius: '8px',
            minWidth: '300px',
            textAlign: 'center'
          }}>
            <h3 style={{ margin: '0 0 1rem 0' }}>Add New User</h3>
            <input
              type="text"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              placeholder="Enter username"
              style={{
                width: '100%',
                padding: '0.5rem',
                border: '1px solid #ddd',
                borderRadius: '4px',
                marginBottom: '1rem',
                fontSize: '1rem'
              }}
              onKeyDown={(e) => e.key === 'Enter' && handleCreateNewUser()}
              autoFocus
            />
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
              <button
                onClick={handleCreateNewUser}
                disabled={!newUsername.trim()}
                style={{
                  background: newUsername.trim() ? '#4CAF50' : '#ccc',
                  color: 'white',
                  border: 'none',
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  fontSize: '1rem',
                  cursor: newUsername.trim() ? 'pointer' : 'not-allowed'
                }}
              >
                Add User
              </button>
              <button
                onClick={handleCancelNewUser}
                style={{
                  background: '#f44336',
                  color: 'white',
                  border: 'none',
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  fontSize: '1rem',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}