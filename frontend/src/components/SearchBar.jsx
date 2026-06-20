import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function SearchBar({ placeholder = 'Search question papers…', initialValue = '', size = 'md' }) {
  const [query, setQuery] = useState(initialValue)
  const navigate = useNavigate()

  const handleSubmit = (e) => {
    e.preventDefault()
    const trimmed = query.trim()
    if (trimmed) navigate(`/search?q=${encodeURIComponent(trimmed)}`)
  }

  const inputClass = size === 'lg'
    ? 'flex-1 px-5 py-4 text-gray-800 text-base outline-none bg-transparent placeholder-gray-400'
    : 'flex-1 px-4 py-2.5 text-gray-800 text-sm outline-none bg-transparent placeholder-gray-400'

  const btnClass = size === 'lg'
    ? 'px-6 py-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-base transition-colors'
    : 'px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm transition-colors'

  return (
    <form onSubmit={handleSubmit} className="flex rounded-xl overflow-hidden shadow-lg bg-white w-full max-w-2xl mx-auto">
      <span className="pl-4 flex items-center text-gray-400">
        <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z" />
        </svg>
      </span>
      <input
        type="text"
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder={placeholder}
        className={inputClass}
      />
      <button type="submit" className={btnClass}>Search</button>
    </form>
  )
}
