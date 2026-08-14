import { Navigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

/**
 * ProtectedRoute — guards all /admin/* routes.
 *
 * Access is granted ONLY when the currently signed-in Firebase user's email
 * matches the single authorized admin email (evaluated via AuthContext.isAdmin).
 *
 * Authentication alone (isAuthenticated) is NOT sufficient.
 * An account that has signed in with Google but whose email does not match
 * the admin email is treated as unauthorized and redirected to /admin/login.
 */
export default function ProtectedRoute({ children }) {
  const { isAdmin, isLoading } = useAuth()
  if (isLoading) return null
  if (!isAdmin) return <Navigate to="/admin/login" replace />
  return children
}
