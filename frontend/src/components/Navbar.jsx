import { useState, useRef, useEffect } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { signInWithGoogle } from '../lib/firebase'
import UserAvatar from './common/UserAvatar'
import { getUnreadConversationCount } from '../services/conversations'

const CLASSES = [9, 10, 11, 12]

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const [classesOpen, setClassesOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [unreadMsgCount, setUnreadMsgCount] = useState(0)
  const userMenuRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (isAuthenticated) {
      getUnreadConversationCount()
        .then(res => setUnreadMsgCount(res.unread_count || 0))
        .catch(() => setUnreadMsgCount(0))
    } else {
      setUnreadMsgCount(0)
    }
  }, [isAuthenticated])

  useEffect(() => {
    function handleClickOutside(e) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleLogout = async () => {
    setUserMenuOpen(false)
    setMenuOpen(false)
    try {
      await logout()
      navigate('/')
    } catch (err) {
      console.error('Logout error:', err)
    }
  }

  return (
    <nav className="bg-white border-b border-gray-100 sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-xs">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <span className="text-lg font-bold text-gray-900 tracking-tight">TN Board</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden lg:flex items-center gap-5">
            <NavLink to="/" end className={({ isActive }) => `text-sm font-medium transition-colors ${isActive ? 'text-blue-600 font-semibold' : 'text-gray-600 hover:text-gray-900'}`}>
              Home
            </NavLink>

            {/* Classes dropdown */}
            <div className="relative" onMouseEnter={() => setClassesOpen(true)} onMouseLeave={() => setClassesOpen(false)}>
              <button className="text-sm font-medium text-gray-600 hover:text-gray-900 flex items-center gap-1 transition-colors">
                Classes
                <svg xmlns="http://www.w3.org/2000/svg" className={`w-4 h-4 transition-transform ${classesOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {classesOpen && (
                <div className="absolute top-full left-0 w-40 pt-1 z-50">
                  <div className="bg-white rounded-2xl shadow-lg border border-gray-100 py-1.5 overflow-hidden">
                    {CLASSES.map(c => (
                      <Link key={c} to={`/class/${c}`}
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-600 transition-colors"
                        onClick={() => setClassesOpen(false)}>
                        Class {c}
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <NavLink to="/official-notices" className={({ isActive }) => `text-sm font-medium transition-colors ${isActive ? 'text-indigo-600 font-semibold' : 'text-gray-600 hover:text-gray-900'}`}>
              Official Notices
            </NavLink>

            <NavLink to="/news" className={({ isActive }) => `text-sm font-medium transition-colors ${isActive ? 'text-blue-600 font-semibold' : 'text-gray-600 hover:text-gray-900'}`}>
              News
            </NavLink>

            <NavLink to="/leaderboard" className={({ isActive }) => `text-sm font-medium transition-colors ${isActive ? 'text-blue-600 font-semibold' : 'text-gray-600 hover:text-gray-900'}`}>
              Leaderboard
            </NavLink>

            <NavLink to="/community" className={({ isActive }) => `text-sm font-medium transition-colors ${isActive ? 'text-blue-600 font-semibold' : 'text-gray-600 hover:text-gray-900'}`}>
              Community
            </NavLink>

            <NavLink to="/search" className={({ isActive }) => `text-sm font-medium transition-colors ${isActive ? 'text-blue-600 font-semibold' : 'text-gray-600 hover:text-gray-900'}`}>
              Search
            </NavLink>

            <Link to="/submit-material" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl text-xs font-bold transition-colors shadow-xs">
              Submit Material
            </Link>

            {/* Auth section */}
            {isAuthenticated ? (
              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center gap-2 p-1 rounded-full hover:bg-gray-100 transition border border-transparent hover:border-gray-200 relative"
                  aria-label="User menu"
                >
                  <UserAvatar user={user} size="sm" className="border border-gray-200" />
                  {unreadMsgCount > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-red-500 text-white rounded-full text-[9px] font-bold flex items-center justify-center border-2 border-white">
                      {unreadMsgCount > 9 ? '9+' : unreadMsgCount}
                    </span>
                  )}
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5 text-gray-500 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {/* User Dropdown */}
                {userMenuOpen && (
                  <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-2xl shadow-xl border border-gray-100 py-2 z-50 animate-fade-in">
                    <div className="px-4 py-2 border-b border-gray-100 flex items-center gap-3">
                      <UserAvatar user={user} size="sm" />
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-gray-900 truncate">{user?.displayName || 'Contributor'}</p>
                        <p className="text-[11px] text-gray-500 truncate">{user?.email}</p>
                      </div>
                    </div>
                    <Link
                      to="/profile"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center gap-2.5 px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-blue-50 hover:text-blue-600 transition"
                    >
                      <span>👤</span> Profile &amp; Account
                    </Link>
                    <Link
                      to="/my-contributions"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center gap-2.5 px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-blue-50 hover:text-blue-600 transition"
                    >
                      <span>📂</span> My Contributions
                    </Link>
                    <Link
                      to="/messages"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center justify-between px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-blue-50 hover:text-blue-600 transition"
                    >
                      <div className="flex items-center gap-2.5">
                        <span>💬</span> Messages &amp; Support
                      </div>
                      {unreadMsgCount > 0 && (
                        <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.2 rounded-full">
                          {unreadMsgCount}
                        </span>
                      )}
                    </Link>
                    <Link
                      to="/submit-material"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center gap-2.5 px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-blue-50 hover:text-blue-600 transition"
                    >
                      <span>📤</span> Submit Material
                    </Link>
                    <div className="border-t border-gray-100 mt-1 pt-1">
                      <button
                        onClick={handleLogout}
                        className="w-full text-left flex items-center gap-2.5 px-4 py-2 text-xs font-bold text-red-600 hover:bg-red-50 transition"
                      >
                        <span>🚪</span> Log out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={signInWithGoogle}
                className="inline-flex items-center gap-2 bg-white hover:bg-gray-50 border border-gray-200 text-gray-700 text-xs font-bold px-3.5 py-2 rounded-xl transition shadow-2xs"
              >
                <span>🔐</span> Login
              </button>
            )}

          </div>

          {/* Mobile burger */}
          <div className="flex items-center gap-2 lg:hidden">
            {isAuthenticated && (
              <Link to="/profile" className="p-1 relative">
                <UserAvatar user={user} size="sm" />
                {unreadMsgCount > 0 && (
                  <span className="absolute 0 top-0 right-0 w-3 h-3 bg-red-500 rounded-full border-2 border-white" />
                )}
              </Link>
            )}
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="p-2 rounded-xl text-gray-600 hover:bg-gray-100 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {menuOpen
                  ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
              </svg>
            </button>
          </div>

        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="lg:hidden border-t border-gray-100 bg-white px-4 py-3 space-y-1 animate-fade-in shadow-xl">
          {isAuthenticated && (
            <div className="p-3 bg-blue-50/70 rounded-2xl border border-blue-100 flex items-center justify-between mb-2">
              <div className="truncate">
                <p className="text-xs font-bold text-gray-900 truncate">{user?.displayName || 'Contributor'}</p>
                <p className="text-[11px] text-gray-500 truncate">{user?.email}</p>
              </div>
              <Link
                to="/profile"
                onClick={() => setMenuOpen(false)}
                className="text-xs font-bold text-blue-600 hover:underline shrink-0"
              >
                View Profile →
              </Link>
            </div>
          )}

          <Link to="/" onClick={() => setMenuOpen(false)} className="block px-3 py-2 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50">Home</Link>
          {CLASSES.map(c => (
            <Link key={c} to={`/class/${c}`} onClick={() => setMenuOpen(false)}
              className="block px-3 py-2 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 pl-6">
              Class {c}
            </Link>
          ))}
          <Link to="/official-notices" onClick={() => setMenuOpen(false)} className="block px-3 py-2 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50">Official Notices</Link>
          <Link to="/news" onClick={() => setMenuOpen(false)} className="block px-3 py-2 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50">News</Link>
          <Link to="/leaderboard" onClick={() => setMenuOpen(false)} className="block px-3 py-2 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50">Leaderboard</Link>
          <Link to="/community" onClick={() => setMenuOpen(false)} className="block px-3 py-2 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50">Community</Link>
          <Link to="/search" onClick={() => setMenuOpen(false)} className="block px-3 py-2 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50">Search</Link>

          {isAuthenticated ? (
            <>
              <Link to="/my-contributions" onClick={() => setMenuOpen(false)} className="block px-3 py-2 rounded-xl text-sm font-medium text-blue-600 hover:bg-blue-50">
                📂 My Contributions
              </Link>
              <Link to="/messages" onClick={() => setMenuOpen(false)} className="flex items-center justify-between px-3 py-2 rounded-xl text-sm font-medium text-indigo-600 hover:bg-indigo-50">
                <span>💬 Messages &amp; Support</span>
                {unreadMsgCount > 0 && (
                  <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                    {unreadMsgCount}
                  </span>
                )}
              </Link>
              <Link to="/profile" onClick={() => setMenuOpen(false)} className="block px-3 py-2 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50">
                👤 Profile Settings
              </Link>
              <button
                onClick={handleLogout}
                className="w-full text-left block px-3 py-2 rounded-xl text-sm font-bold text-red-600 hover:bg-red-50"
              >
                🚪 Log out
              </button>
            </>
          ) : (
            <button
              onClick={() => {
                setMenuOpen(false)
                signInWithGoogle()
              }}
              className="w-full text-left block px-3 py-2 rounded-xl text-sm font-bold text-blue-600 hover:bg-blue-50"
            >
              🔐 Sign in with Google
            </button>
          )}

          <Link to="/submit-material" onClick={() => setMenuOpen(false)} className="block mt-2 mx-1 mb-2 px-3 py-2.5 rounded-xl text-sm font-bold bg-blue-600 text-white hover:bg-blue-700 text-center shadow-xs">
            Submit Material
          </Link>
        </div>
      )}
    </nav>
  )
}
