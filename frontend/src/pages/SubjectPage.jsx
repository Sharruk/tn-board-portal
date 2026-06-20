import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import Breadcrumb from '../components/Breadcrumb'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import { getSubject, getPapersForSubject } from '../services/subjects'
import { getExamTypes } from '../services/papers'

const EXAM_CATEGORY_GROUPS = [
  { label: 'Unit Tests', types: ['Unit Test 1', 'Unit Test 2', 'Unit Test 3'], icon: '📝' },
  { label: 'Quarterly Exam', types: ['Quarterly Exam'], icon: '📅' },
  { label: 'Half Yearly Exam', types: ['Half Yearly Exam'], icon: '📆' },
  { label: 'Annual / Public Exam', types: ['Annual Exam', 'Public Exam', 'Model Exam'], icon: '🎯' },
  { label: 'Practical Exam', types: ['Practical Exam'], icon: '🔬', practicalOnly: true },
]

export default function SubjectPage() {
  const { id } = useParams()
  const [subject, setSubject] = useState(null)
  const [papers, setPapers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    Promise.all([getSubject(id), getPapersForSubject(id)])
      .then(([subRes, papersRes]) => {
        setSubject(subRes.data)
        setPapers(papersRes.data)
      })
      .catch(err => setError(err.response?.data?.detail || 'Failed to load subject'))
      .finally(() => setLoading(false))
  }, [id])

  const getCountForTypes = (types) =>
    papers.filter(p => types.includes(p.exam_type)).length

  const groups = subject
    ? EXAM_CATEGORY_GROUPS.filter(g => !g.practicalOnly || subject.is_practical)
    : []

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {subject && (
        <Breadcrumb items={[
          { label: 'Home', href: '/' },
          { label: subject.class_name, href: `/class/${subject.class_id}` },
          { label: subject.name },
        ]} />
      )}

      {loading && <LoadingSpinner text="Loading subject…" />}
      {error && <ErrorMessage message={error} />}

      {!loading && !error && subject && (
        <>
          <div className="mt-6 mb-10">
            <h1 className="text-3xl font-extrabold text-gray-900">{subject.name}</h1>
            <p className="text-gray-500 mt-2">
              {subject.class_name} — Select an exam category to view papers
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {groups.map(group => {
              const count = getCountForTypes(group.types)
              const hasFiles = count > 0

              return (
                <div key={group.label}>
                  {hasFiles ? (
                    <Link
                      to={`/papers?subject_id=${subject.id}&exam_type=${encodeURIComponent(group.types[0])}`}
                      className="group card p-5 flex items-start gap-4 hover:border-blue-200 h-full"
                    >
                      <div className="w-11 h-11 bg-blue-50 rounded-xl flex items-center justify-center text-xl shrink-0 group-hover:bg-blue-100 transition-colors">
                        {group.icon}
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-800 group-hover:text-blue-700 transition-colors">{group.label}</h3>
                        <p className="text-sm text-blue-600 font-medium mt-1">{count} paper{count !== 1 ? 's' : ''} available</p>
                        {group.types.length > 1 && (
                          <p className="text-xs text-gray-400 mt-1">{group.types.join(', ')}</p>
                        )}
                      </div>
                      <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-gray-300 group-hover:text-blue-500 transition-colors mt-1 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </Link>
                  ) : (
                    <div className="card p-5 flex items-start gap-4 opacity-60 cursor-default h-full bg-gray-50">
                      <div className="w-11 h-11 bg-gray-100 rounded-xl flex items-center justify-center text-xl shrink-0 grayscale">
                        {group.icon}
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-500">{group.label}</h3>
                        <span className="text-xs bg-gray-200 text-gray-500 px-2 py-0.5 rounded-full mt-1 inline-block">Coming soon</span>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
