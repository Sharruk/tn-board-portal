import { Outlet, useLocation } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

export default function MainLayout() {
  const { pathname } = useLocation()
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Navbar />
      <main className="flex-1" key={pathname}>
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
