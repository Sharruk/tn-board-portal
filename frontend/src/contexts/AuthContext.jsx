import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { auth } from '../lib/firebase'
import { onAuthStateChanged } from 'firebase/auth'
import { getMyProfile } from '../services/profile'

// The single authorized super admin email address.
// This is intentionally NOT a secret — it is used for immediate frontend UI gating.
// Backend authorization is enforced independently via Firebase token verification.
const ADMIN_EMAIL = 'hungrylearner786@gmail.com'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [session, setSession] = useState(undefined)
  const [firebaseUser, setFirebaseUser] = useState(null)
  const [profile, setProfile] = useState(null)
  const [isProfileLoading, setIsProfileLoading] = useState(false)

  const fetchProfile = useCallback(async (user) => {
    if (!user) {
      setProfile(null)
      return
    }
    try {
      setIsProfileLoading(true)
      const data = await getMyProfile()
      setProfile(data)
    } catch (err) {
      console.warn('Failed to load user profile in AuthContext:', err)
    } finally {
      setIsProfileLoading(false)
    }
  }, [])

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      setFirebaseUser(user)
      if (user) {
        setSession({ user })
        fetchProfile(user)
      } else {
        setSession(null)
        setProfile(null)
      }
    })

    return () => unsubscribe()
  }, [fetchProfile])

  const logout = async () => {
    await auth.signOut()
    setProfile(null)
  }

  // Authoritative role derivations
  const isSuperAdmin = !!(firebaseUser && (firebaseUser.email === ADMIN_EMAIL || profile?.role === 'SUPER_ADMIN'))
  const isAdmin = isSuperAdmin || (profile?.role === 'ADMIN')
  const isVerifiedTeacher = isSuperAdmin || (isAdmin && !!(profile?.is_verified_teacher))
  const canGovernAdmins = isVerifiedTeacher
  const isContributor = isSuperAdmin || isAdmin || (profile?.role === 'CONTRIBUTOR') || ((profile?.stats?.published_count || 0) > 0)
  const role = isSuperAdmin ? 'SUPER_ADMIN' : (profile?.role || (isAdmin ? 'ADMIN' : (isContributor ? 'CONTRIBUTOR' : 'USER')))

  return (
    <AuthContext.Provider value={{
      session,
      firebaseUser,
      user: firebaseUser,
      profile,
      role,
      isAuthenticated: !!firebaseUser,
      isAdmin,
      isSuperAdmin,
      isVerifiedTeacher,
      canGovernAdmins,
      isContributor,
      refreshProfile: () => fetchProfile(firebaseUser),
      isLoading: session === undefined,
      isProfileLoading,
      logout,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
