import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import Breadcrumb from '../components/Breadcrumb'
import PaperCard from '../components/PaperCard'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import { getSubject, getPapersForSubject } from '../services/subjects'

export default function PaperListPage() {
  const [searchParams] = useSearchParams()
  const subjectId = searchParams.get('subject_id')
  const examType = searchParams.get('exam_type')

  const [subject, setSubject] = useState(null)
  const [papers, setPapers] = useState([])
  const [filterType, setFilterType] = useState('all') // 'all' | 'question' | 'answer_key'
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!subjectId) return
    setLoading(true)
    setError(null)
    Promise.all([
      getSubject(subjectId),
      getPapersForSubject(subjectId, examType ? { exam_type: examType } : {}),
    ])
      .then(([subRes, papersRes]) => {
        setSubject(subRes.data)
        setPapers(papersRes.data)
      })
      .catch(err => setError(err.response?.data?.detail || 'Failed to load papers'))
      .finally(() => setLoading(false))
  }, [subjectId, examType])

  const filtered = filterType === 'all' ? papers : papers.filter(p => p.paper_type === filterType)
  const questionCount = papers.filter(p => p.paper_type === 'question').length
  const answerKeyCount = papers.filter(p => p.paper_type === 'answer_key').length

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {subject && (
        <Breadcrumb items={[
          { label: 'Home', href: '/' },
          { label: subject.class_name, href: `/class/${subject.class_id}` },
          { label: subject.name, href: `/subject/${subject.id}` },
          { label: examType || 'All Papers' },
        ]} />
      )}

      <div className="mt-6 mb-8 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900">
            {examType || 'All Papers'}
          </h1>
          {subject && (
            <p className="text-gray-500 mt-1">{subject.class_name} — {subject.name}</p>
          )}
        </div>

        {/* Filter tabs */}
        <div className="flex items-center gap-2 bg-gray-100 rounded-xl p-1 self-start sm:self-auto">
          {[
            { value: 'all', label: `All (${papers.length})` },
            { value: 'question', label: `Q Papers (${questionCount})` },
            { value: 'answer_key', label: `Answer Keys (${answerKeyCount})` },
          ].map(tab => (
            <button
              key={tab.value}
              onClick={() => setFilterType(tab.value)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                filterType === tab.value
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {loading && <LoadingSpinner text="Loading papers…" />}
      {error && <ErrorMessage message={error} />}

      {!loading && !error && (
        <>
          {filtered.length === 0 ? (
            <div className="text-center py-20 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
              <div className="text-5xl mb-4">📂</div>
              <p className="text-gray-500 font-medium">No papers found.</p>
              <p className="text-gray-400 text-sm mt-1">
                {filterType !== 'all' ? 'Try switching the filter above.' : 'Check back soon!'}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {filtered.map(p => <PaperCard key={p.id} paper={p} />)}
            </div>
          )}
        </>
      )}
    </div>
  )
}
