import { createBrowserRouter } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout'
import HomePage from '../pages/HomePage'
import ClassPage from '../pages/ClassPage'
import SubjectPage from '../pages/SubjectPage'
import PaperListPage from '../pages/PaperListPage'
import PaperDetailPage from '../pages/PaperDetailPage'
import SearchPage from '../pages/SearchPage'
import NotFoundPage from '../pages/NotFoundPage'

const router = createBrowserRouter([
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
])

export default router
