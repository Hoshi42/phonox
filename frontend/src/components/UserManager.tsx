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

  if (showModal) {
    return (
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
          maxWidth: '90vw',
          textAlign: 'center'
        }}>
          <h2 style={{ margin: '0 0 1rem 0' }}>Welcome to Phonox</h2>
          
          {/* Show existing users first - mobile-friendly */}
          {existingUsers.length > 0 && (
            <div>
              <p style={{ margin: '0 0 1rem 0', color: '#666' }}>
                Select your name:
              </p>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                gap: '10px',
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
                      background: '#4CAF50',
                      color: 'white',
                      border: 'none',
                      padding: '1rem',
                      borderRadius: '8px',
                      fontSize: '1rem',
                      cursor: 'pointer',
                      minHeight: '60px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'background-color 0.2s'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#45a049'}
                    onMouseLeave={(e) => e.currentTarget.style.background = '#4CAF50'}
                  >
                    👤 {user}
                  </button>
                ))}
              </div>
              
              <div style={{ 
                borderTop: '1px solid #eee', 
                paddingTop: '1rem',
                margin: '1rem 0'
              }}>
                <p style={{ margin: '0 0 1rem 0', color: '#666', fontSize: '0.9rem' }}>
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
              padding: '0.75rem',
              border: '1px solid #ddd',
              borderRadius: '4px',
              marginBottom: '1rem',
              fontSize: '1rem',
              boxSizing: 'border-box'
            }}
            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
            autoFocus={existingUsers.length === 0}
          />
          <button
            onClick={handleSave}
            disabled={!username.trim()}
            style={{
              background: username.trim() ? '#2196F3' : '#ccc',
              color: 'white',
              border: 'none',
              padding: '0.75rem 1.5rem',
              borderRadius: '4px',
              fontSize: '1rem',
              cursor: username.trim() ? 'pointer' : 'not-allowed',
              minHeight: '48px'
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
        <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
          {existingUsers.map(user => (
            <button
              key={user}
              onClick={() => handleUserSwitch(user)}
              style={{
                background: user === username ? 'rgba(76, 175, 80, 0.8)' : 'rgba(255, 255, 255, 0.1)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                color: 'rgba(255, 255, 255, 0.9)',
                padding: '6px 10px',
                borderRadius: '4px',
                fontSize: '0.8rem',
                cursor: 'pointer',
                minWidth: '44px', // Mobile touch target
                minHeight: '44px'
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
          background: 'rgba(76, 175, 80, 0.2)',
          border: '1px solid rgba(76, 175, 80, 0.5)',
          color: 'rgba(76, 175, 80, 1)',
          padding: '6px 10px',
          borderRadius: '4px',
          fontSize: '0.8rem',
          cursor: 'pointer',
          minWidth: '44px',
          minHeight: '44px'
        }}
      >
        ➕ Add
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