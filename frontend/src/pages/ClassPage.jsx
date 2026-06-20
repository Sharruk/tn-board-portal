import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import Breadcrumb from '../components/Breadcrumb'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import { getSubjectsForClass } from '../services/classes'

const SUBJECT_ICONS = {
  tamil: '🔤', english: '📖', maths: '📐', science: '🔬', social: '🌍',
  physics: '⚡', chemistry: '🧪', biology: '🌿', cs: '💻', ca: '🖥️',
  acc: '📊', comm: '🏪', eco: '📈',
}

export default function ClassPage() {
  const { id } = useParams()
  const [subjects, setSubjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getSubjectsForClass(id)
      .then(res => setSubjects(res.data))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load subjects'))
      .finally(() => setLoading(false))
  }, [id])

  const className = `Class ${id}`

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <Breadcrumb items={[{ label: 'Home', href: '/' }, { label: className }]} />

      <div className="mt-6 mb-10">
        <h1 className="text-3xl font-extrabold text-gray-900">{className} — Subjects</h1>
        <p className="text-gray-500 mt-2">Choose a subject to browse question papers and answer keys</p>
      </div>

      {loading && <LoadingSpinner text="Loading subjects…" />}
      {error && <ErrorMessage message={error} />}

      {!loading && !error && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {subjects.map(subject => (
              <Link
                key={subject.id}
                to={`/subject/${subject.id}`}
                className="group card p-5 flex items-center gap-4 hover:border-blue-200"
              >
                <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center text-xl shrink-0 group-hover:bg-blue-100 transition-colors">
                  {SUBJECT_ICONS[subject.slug] || '📄'}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-800 group-hover:text-blue-700 transition-colors">{subject.name}</h3>
                  <p className="text-sm text-gray-400 mt-0.5">
                    {subject.paper_count > 0
                      ? `${subject.paper_count} paper${subject.paper_count !== 1 ? 's' : ''} available`
                      : 'Coming soon'}
                    {subject.is_practical && <span className="ml-2 badge bg-green-100 text-green-700">Practical</span>}
                  </p>
                </div>
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-gray-300 group-hover:text-blue-500 transition-colors shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            ))}
          </div>

          {subjects.length === 0 && (
            <div className="text-center py-16 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
              <p className="text-gray-400">No subjects found for this class.</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
