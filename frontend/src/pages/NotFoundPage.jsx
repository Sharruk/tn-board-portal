import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center px-4 text-center">
      <div className="text-8xl font-extrabold text-blue-600 mb-4">404</div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Page Not Found</h1>
      <p className="text-gray-500 mb-8 max-w-sm">
        The page you are looking for doesn't exist or has been moved.
      </p>
      <div className="flex flex-col sm:flex-row gap-3">
        <Link to="/" className="btn-primary">Go to Homepage</Link>
        <Link to="/search" className="btn-secondary">Search Papers</Link>
      </div>
    </div>
  )
}
