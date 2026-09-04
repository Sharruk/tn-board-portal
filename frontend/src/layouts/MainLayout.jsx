import { useEffect } from 'react'
import { Outlet, useLocation, ScrollRestoration } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { trackPageView } from '../services/analytics'

export default function MainLayout() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
    trackPageView(pathname)
  }, [pathname])

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <ScrollRestoration />
      <Navbar />
      <main className="flex-1" key={pathname}>
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
