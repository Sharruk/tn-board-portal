import { createBrowserRouter, Navigate } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout'
import AdminLayout from '../components/admin/AdminLayout'
import ProtectedRoute from '../components/admin/ProtectedRoute'

import HomePage from '../pages/HomePage'
import ClassPage from '../pages/ClassPage'
import SubjectPage from '../pages/SubjectPage'
import PaperListPage from '../pages/PaperListPage'
import PaperDetailPage from '../pages/PaperDetailPage'
import OfficialNoticesPage from '../pages/OfficialNoticesPage'
import NoticeDetailPage from '../pages/NoticeDetailPage'
import NewsPage from '../pages/NewsPage'
import NewsDetailPage from '../pages/NewsDetailPage'
import SearchPage from '../pages/SearchPage'
import NotFoundPage from '../pages/NotFoundPage'
import SubmitMaterialPage from '../pages/SubmitMaterialPage'

import LoginPage from '../pages/admin/LoginPage'
import DashboardPage from '../pages/admin/DashboardPage'
import PapersPage from '../pages/admin/PapersPage'
import AdminOfficialNoticesPage from '../pages/admin/OfficialNoticesPage'
import AdminNewsPage from '../pages/admin/NewsPage'
import ContentStatusPage from '../pages/admin/ContentStatusPage'
import SubmissionsPage from '../pages/admin/SubmissionsPage'

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
      { path: 'official-notices', element: <OfficialNoticesPage /> },
      { path: 'notice/:id', element: <NoticeDetailPage /> },
      { path: 'news', element: <NewsPage /> },
      { path: 'news/:slug', element: <NewsDetailPage /> },
      { path: 'search', element: <SearchPage /> },
      { path: 'submit-material', element: <SubmitMaterialPage /> },
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
      { path: 'official-notices', element: <AdminOfficialNoticesPage /> },
      { path: 'news', element: <AdminNewsPage /> },
      { path: 'content-status', element: <ContentStatusPage /> },
      { path: 'submissions', element: <SubmissionsPage /> },
    ],
  },
])

export default router
