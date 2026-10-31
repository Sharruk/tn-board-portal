import { Navigate } from 'react-router-dom'
import { useAdminAuth } from '../../contexts/AdminAuthContext'

/**
 * ProtectedRoute — guards all /admin/* routes.
 *
 * Access is granted ONLY when the currently signed-in user has verified
 * administrative privileges (SUPER_ADMIN or ADMIN), evaluated server-side
 * via AdminAuthContext.
 */
export default function ProtectedRoute({ children }) {
  const { isAdmin, adminLoading } = useAdminAuth()
  if (adminLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
      </div>
    )
  }
  if (!isAdmin) return <Navigate to="/admin/login" replace />
  return children
}
