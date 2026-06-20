import { Link } from 'react-router-dom'

export default function Breadcrumb({ items }) {
  return (
    <nav className="flex items-center gap-1.5 text-sm text-gray-500 flex-wrap">
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-1.5">
          {i > 0 && <span className="text-gray-300">/</span>}
          {i < items.length - 1 ? (
            <Link to={item.href} className="hover:text-blue-600 transition-colors">
              {item.label}
            </Link>
          ) : (
            <span className="text-gray-800 font-medium">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  )
}
