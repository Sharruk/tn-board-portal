import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="bg-gray-900 text-gray-400 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <span className="text-white font-bold">TN Board Platform</span>
            </div>
            <p className="text-sm leading-relaxed">
              Free question papers and answer keys for Tamil Nadu State Board students — Class 9 to 12.
            </p>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-3 text-sm">Classes</h4>
            <div className="space-y-2">
              {[9, 10, 11, 12].map(c => (
                <Link key={c} to={`/class/${c}`} className="block text-sm hover:text-white transition-colors">Class {c}</Link>
              ))}
            </div>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-3 text-sm">Quick Links</h4>
            <div className="space-y-2">
              <Link to="/" className="block text-sm hover:text-white transition-colors">Home</Link>
              <Link to="/search" className="block text-sm hover:text-white transition-colors">Search Papers</Link>
            </div>
          </div>
        </div>
        <div className="border-t border-gray-800 pt-6 text-center text-xs text-gray-600">
          © {new Date().getFullYear()} TN State Board Learning Platform. For educational purposes only.
        </div>
      </div>
    </footer>
  )
}
