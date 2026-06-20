import { createBrowserRouter, Navigate } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout'
import AdminLayout from '../components/admin/AdminLayout'
import ProtectedRoute from '../components/admin/ProtectedRoute'

import HomePage from '../pages/HomePage'
import ClassPage from '../pages/ClassPage'
import SubjectPage from '../pages/SubjectPage'
import PaperListPage from '../pages/PaperListPage'
import PaperDetailPage from '../pages/PaperDetailPage'
import SearchPage from '../pages/SearchPage'
import NotFoundPage from '../pages/NotFoundPage'

import LoginPage from '../pages/admin/LoginPage'
import DashboardPage from '../pages/admin/DashboardPage'
import PapersPage from '../pages/admin/PapersPage'

const router = createBrowserRouter([
  // ── Public routes ──────────────────────────────────────
  {
    path: '/',
    element: <MainLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'class/:id', element: <ClassPage /> },
      { path: 'subject/:id', element: <SubjectPage /> },
      { path: 'papers', element: <PaperListPage /> },
      { path: 'paper/:id', element: <PaperDetailPage /> },
      { path: 'search', element: <SearchPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },

  // ── Admin login (standalone, no layout) ───────────────
  { path: '/admin/login', element: <LoginPage /> },

  // ── Protected admin routes (sidebar layout) ───────────
  {
    path: '/admin',
    element: (
      <ProtectedRoute>
        <AdminLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Navigate to="/admin/dashboard" replace /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'papers', element: <PapersPage /> },
    ],
  },
])

export default router
