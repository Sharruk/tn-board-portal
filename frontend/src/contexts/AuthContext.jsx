import { createContext, useContext, useState, useEffect } from 'react'
import { auth } from '../lib/firebase'
import { onAuthStateChanged } from 'firebase/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [session, setSession] = useState(undefined)
  const [firebaseUser, setFirebaseUser] = useState(null)

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      setFirebaseUser(user)
      if (user) {
        // We'll store a placeholder "session" for now so downstream components don't break
        // We will fetch the actual token when making API calls.
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

  return (
    <AuthContext.Provider value={{
      session,
      firebaseUser,
      isAuthenticated: !!firebaseUser,
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
