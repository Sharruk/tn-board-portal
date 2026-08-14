import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { signInWithGoogle } from '../../lib/firebase'

/**
 * Admin Login Page
 *
 * Authentication flow:
 *   1. If already loading Firebase auth state → show nothing (prevent flicker).
 *   2. If already authorized as admin (isAdmin) → redirect to dashboard.
 *   3. If Firebase user is signed in but NOT the admin → show Access Denied screen
 *      with a sign-out option (so the correct account can be chosen).
 *   4. Otherwise → show Google Sign-In button.
 *
 * The Google sign-in call uses prompt: 'select_account' (set in firebase.js)
 * so that a cached non-admin Google session never silently passes through.
 *
 * After sign-in, authorization is evaluated by comparing the Firebase user's
 * email to the single allowed admin email in AuthContext. If the email does
 * not match, the user lands in state 3 (Access Denied), never the dashboard.
 */
export default function LoginPage() {
  const { isAdmin, isAuthenticated, isLoading, firebaseUser, logout } = useAuth()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // ── Redirect authorized admin to dashboard ──────────────────────────────
  useEffect(() => {
    if (!isLoading && isAdmin) {
      navigate('/admin/dashboard', { replace: true })
    }
  }, [isAdmin, isLoading, navigate])

  // Don't render anything while Firebase resolves the initial auth state
  if (isLoading) return null

  // ── Handlers ─────────────────────────────────────────────────────────────

  const handleGoogleSignIn = async () => {
    setLoading(true)
    setError(null)
    try {
      const { user, error: signInError } = await signInWithGoogle()
      if (signInError) {
        // User cancelled the popup or another transient sign-in error
        if (
          signInError.code === 'auth/popup-closed-by-user' ||
          signInError.code === 'auth/cancelled-popup-request'
        ) {
          // Not an error to show — user closed the chooser
          return
        }
        throw signInError
      }
      // If user signed in but is NOT the admin, AuthContext will set isAdmin=false
      // and the useEffect above will NOT redirect. The component re-renders into
      // the "Access Denied" state below automatically.
      if (!user) {
        setError('Sign-in did not return a user. Please try again.')
      }
    } catch (err) {
      setError(err.message || 'Sign-in failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleSignOut = async () => {
    setError(null)
    await logout()
  }

  // ── Access Denied state: signed in but NOT the admin ─────────────────────
  if (isAuthenticated && !isAdmin) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <div className="w-14 h-14 bg-red-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-white">Access Denied</h1>
            <p className="text-gray-400 text-sm mt-1">TN Board Learning Platform</p>
          </div>

          <div className="bg-white rounded-2xl shadow-2xl p-8">
            <div className="text-center mb-6">
              <p className="text-sm font-semibold text-red-600 mb-2">Unauthorized Account</p>
              <p className="text-sm text-gray-600">
                The signed-in Google account is not authorized to access the admin panel.
              </p>
              <div className="mt-3 px-3 py-2 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500 break-all font-mono">
                  {firebaseUser?.email}
                </p>
              </div>
            </div>

            <p className="text-xs text-gray-500 text-center mb-5">
              Sign out and sign in with the authorized admin account to continue.
            </p>

            <button
              type="button"
              id="sign-out-btn"
              onClick={handleSignOut}
              className="w-full flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-xl text-sm transition-colors shadow-sm"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              Sign Out &amp; Try Another Account
            </button>
          </div>

          <p className="text-center text-gray-500 text-xs mt-6">
            TN State Board Learning Platform — Admin Only
          </p>
        </div>
      </div>
    )
  }

  // ── Default state: not authenticated → show Google Sign-In ───────────────
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white">Admin Login</h1>
          <p className="text-gray-400 text-sm mt-1">TN Board Learning Platform</p>
        </div>

        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <p className="text-sm text-gray-600 text-center mb-6">
            Sign in with your authorised Google account to access the admin dashboard.
          </p>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex items-center gap-2 mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <button
            type="button"
            id="google-signin-btn"
            onClick={handleGoogleSignIn}
            disabled={loading}
            className="w-full flex items-center justify-center gap-3 bg-white hover:bg-gray-50 disabled:opacity-60 disabled:cursor-not-allowed border border-gray-300 text-gray-800 font-semibold py-3 rounded-xl text-sm transition-colors shadow-sm"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-gray-300 border-t-gray-700 rounded-full animate-spin" />
                Signing in…
              </>
            ) : (
              <>
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                </svg>
                Sign in with Google
              </>
            )}
          </button>
        </div>

        <p className="text-center text-gray-500 text-xs mt-6">
          TN State Board Learning Platform — Admin Only
        </p>
      </div>
    </div>
  )
}
