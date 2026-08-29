import { createContext, useContext, useState, useEffect } from 'react'
import { auth } from '../lib/firebase'
import { onAuthStateChanged } from 'firebase/auth'

// The single authorized admin email address.
// This is intentionally NOT a secret — it is only used for frontend UI gating.
// Backend authorization is enforced independently via Firebase token verification.
const ADMIN_EMAIL = 'hungrylearner786@gmail.com'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [session, setSession] = useState(undefined)
  const [firebaseUser, setFirebaseUser] = useState(null)

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      setFirebaseUser(user)
      if (user) {
        // We'll store a placeholder "session" for now so downstream components don't break.
        // We fetch the actual token when making API calls.
        setSession({ user })
      } else {
        setSession(null)
      }
    })

    return () => unsubscribe()
  }, [])

  const logout = async () => {
    await auth.signOut()
  }

  // isAdmin is TRUE only when:
  //   1. A Firebase user is signed in (firebaseUser != null), AND
  //   2. Their verified email exactly matches the single authorized admin address.
  //
  // This is a UI-layer guard. The backend enforces the same rule authoritatively
  // by verifying the Firebase ID token and checking the decoded email server-side.
  const isAdmin = !!(firebaseUser && firebaseUser.email === ADMIN_EMAIL)

  return (
    <AuthContext.Provider value={{
      session,
      firebaseUser,
      user: firebaseUser,
      isAuthenticated: !!firebaseUser,
      isAdmin,
      isLoading: session === undefined,
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
