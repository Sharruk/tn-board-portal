import { createContext, useContext, useState, useEffect } from 'react'
import { useAuth } from './AuthContext'
import { getAdminMe } from '../services/adminRoles'

const ADMIN_EMAIL = 'hungrylearner786@gmail.com'

const AdminAuthContext = createContext(null)

/**
 * Dedicated Admin Authentication Provider.
 * Mounted exclusively on /admin/* and /admin/login routes.
 * Ensures zero network overhead or delays for ordinary users and contributors on public routes.
 */
export function AdminAuthProvider({ children }) {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()
  const [adminProfile, setAdminProfile] = useState(null)
  const [adminLoading, setAdminLoading] = useState(true)

  const checkAdminStatus = async () => {
    if (!isAuthenticated || !user) {
      setAdminProfile(null)
      setAdminLoading(false)
      return
    }

    const email = (user.email || '').trim().toLowerCase()

    // Fast synchronous path: primary Super Admin
    if (email === ADMIN_EMAIL.toLowerCase()) {
      setAdminProfile({
        email: user.email,
        role: 'SUPER_ADMIN',
        is_super_admin: true,
        display_name: user.displayName || 'Hungry Learner',
        firebase_uid: user.uid,
      })
      setAdminLoading(false)
      return
    }

    // Appointed Admin or Pre-authorized Admin: verify against backend
    setAdminLoading(true)
    try {
      const res = await getAdminMe()
      setAdminProfile(res)
    } catch (err) {
      setAdminProfile(null)
    } finally {
      setAdminLoading(false)
    }
  }

  useEffect(() => {
    if (!authLoading) {
      checkAdminStatus()
    }
  }, [user, isAuthenticated, authLoading])

  const isAdmin = !!(adminProfile && (adminProfile.role === 'ADMIN' || adminProfile.role === 'SUPER_ADMIN'))
  const isSuperAdmin = !!(
    (user && (user.email || '').trim().toLowerCase() === ADMIN_EMAIL.toLowerCase()) ||
    (adminProfile && (adminProfile.is_super_admin || adminProfile.role === 'SUPER_ADMIN'))
  )

  return (
    <AdminAuthContext.Provider
      value={{
        adminProfile,
        isAdmin,
        isSuperAdmin,
        adminLoading: authLoading || adminLoading,
        refreshAdmin: checkAdminStatus,
      }}
    >
      {children}
    </AdminAuthContext.Provider>
  )
}

export function useAdminAuth() {
  const ctx = useContext(AdminAuthContext)
  if (!ctx) {
    throw new Error('useAdminAuth must be used inside AdminAuthProvider')
  }
  return ctx
}

