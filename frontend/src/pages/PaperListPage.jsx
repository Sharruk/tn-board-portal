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
  const category = searchParams.get('category')

  const title = category || examType || 'All Papers'
  const subTypes = examType ? examType.split(',').map(s => s.trim()).filter(Boolean) : []
  const hasMultipleSubTypes = subTypes.length > 1

  const [subject, setSubject] = useState(null)
  const [papers, setPapers] = useState([])
  const [selectedSubType, setSelectedSubType] = useState('all')
  const [filterType, setFilterType] = useState('all') // 'all' | 'question' | 'answer_key'
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!subjectId) return
    setLoading(true)
    setError(null)
    setSelectedSubType('all')
    Promise.all([
      getSubject(subjectId),
      getPapersForSubject(subjectId, examType ? { exam_type: examType } : {}),
    ])
      .then(([subRes, papersRes]) => {
        setSubject(subRes.data)
        setPapers(papersRes.data)
      })
      .catch(err => setError(err.message || 'Failed to load papers'))
      .finally(() => setLoading(false))
  }, [subjectId, examType])

  const subTypeFiltered = selectedSubType === 'all'
    ? papers
    : papers.filter(p => p.exam_type === selectedSubType)

  const filtered = filterType === 'all'
    ? subTypeFiltered
    : subTypeFiltered.filter(p => p.paper_type === filterType)

  const questionCount = subTypeFiltered.filter(p => p.paper_type === 'question').length
  const answerKeyCount = subTypeFiltered.filter(p => p.paper_type === 'answer_key').length

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {subject && (
        <Breadcrumb items={[
          { label: 'Home', href: '/' },
          { label: subject.class_name, href: `/class/${subject.class_id}` },
          { label: subject.name, href: `/subject/${subject.id}` },
          { label: title },
        ]} />
      )}

      <div className="mt-6 mb-8">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-extrabold text-gray-900">
              {title}
            </h1>
            {subject && (
              <p className="text-gray-500 mt-1">{subject.class_name} — {subject.name}</p>
            )}
          </div>

          {/* Filter tabs */}
          <div className="flex items-center gap-2 bg-gray-100 rounded-xl p-1 self-start sm:self-auto">
            {[
              { value: 'all', label: `All (${subTypeFiltered.length})` },
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

        {/* Sub-type filter pills (e.g. Unit Test 1, Unit Test 2, Unit Test 3) */}
        {hasMultipleSubTypes && (
          <div className="flex flex-wrap items-center gap-2 mt-4 pt-4 border-t border-gray-100">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider mr-1">Exam:</span>
            <button
              onClick={() => setSelectedSubType('all')}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                selectedSubType === 'all'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              All ({papers.length})
            </button>
            {subTypes.map(st => {
              const count = papers.filter(p => p.exam_type === st).length
              return (
                <button
                  key={st}
                  onClick={() => setSelectedSubType(st)}
                  className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                    selectedSubType === st
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {st} ({count})
                </button>
              )
            })}
          </div>
        )}
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
