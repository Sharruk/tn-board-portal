import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'

const CLASSES = [9, 10, 11, 12]

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [classesOpen, setClassesOpen] = useState(false)
  const navigate = useNavigate()

  return (
    <nav className="bg-white border-b border-gray-100 sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <span className="text-lg font-bold text-gray-900">TN Board</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-6">
            <NavLink to="/" end className={({ isActive }) => `text-sm font-medium transition-colors ${isActive ? 'text-blue-600' : 'text-gray-600 hover:text-gray-900'}`}>
              Home
            </NavLink>

            {/* Classes dropdown */}
            <div className="relative" onMouseEnter={() => setClassesOpen(true)} onMouseLeave={() => setClassesOpen(false)}>
              <button className="text-sm font-medium text-gray-600 hover:text-gray-900 flex items-center gap-1 transition-colors">
                Classes
                <svg xmlns="http://www.w3.org/2000/svg" className={`w-4 h-4 transition-transform ${classesOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {classesOpen && (
                <div className="absolute top-full left-0 w-40 pt-1 z-50">
                  <div className="bg-white rounded-xl shadow-lg border border-gray-100 py-1">
                    {CLASSES.map(c => (
                      <Link key={c} to={`/class/${c}`}
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-600 transition-colors"
                        onClick={() => setClassesOpen(false)}>
                        Class {c}
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <NavLink to="/official-notices" className={({ isActive }) => `text-sm font-medium transition-colors ${isActive ? 'text-indigo-600' : 'text-gray-600 hover:text-gray-900'}`}>
              Official Notices
            </NavLink>

            <NavLink to="/news" className={({ isActive }) => `text-sm font-medium transition-colors ${isActive ? 'text-blue-600' : 'text-gray-600 hover:text-gray-900'}`}>
              News
            </NavLink>

            <NavLink to="/search" className={({ isActive }) => `text-sm font-medium transition-colors ${isActive ? 'text-blue-600' : 'text-gray-600 hover:text-gray-900'}`}>
              Search
            </NavLink>

            <Link to="/submit-material" className="ml-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
              Submit Material
            </Link>
          </div>

          {/* Mobile burger */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="md:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {menuOpen
                ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-gray-100 bg-white px-4 py-3 space-y-1">
          <Link to="/" onClick={() => setMenuOpen(false)} className="block px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">Home</Link>
          {CLASSES.map(c => (
            <Link key={c} to={`/class/${c}`} onClick={() => setMenuOpen(false)}
              className="block px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 pl-6">
              Class {c}
            </Link>
          ))}
          <Link to="/official-notices" onClick={() => setMenuOpen(false)} className="block px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">Official Notices</Link>
          <Link to="/news" onClick={() => setMenuOpen(false)} className="block px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">News</Link>
          <Link to="/search" onClick={() => setMenuOpen(false)} className="block px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">Search</Link>
          <Link to="/submit-material" onClick={() => setMenuOpen(false)} className="block mt-2 mx-3 mb-3 px-3 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 text-center shadow-sm">
            Submit Material
          </Link>
        </div>
      )}
    </nav>
  )
}
