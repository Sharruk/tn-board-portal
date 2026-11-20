import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import Breadcrumb from '../components/Breadcrumb'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import StudyMaterialCard from '../components/StudyMaterialCard'
import { getSubject, getPapersForSubject } from '../services/subjects'
import { getMaterialsBySubject } from '../services/studyMaterials'
import { getMaterialCategories } from '../services/materialCategories'

const EXAM_CATEGORY_GROUPS = [
  { label: 'Monthly Test',           types: ['Monthly Test'],                                         icon: '🗓️' },
  { label: 'First Mid Term Test',    types: ['First Mid Term Test'],                                  icon: '📝' },
  { label: 'Unit Tests',             types: ['Unit Test 1', 'Unit Test 2', 'Unit Test 3'],             icon: '📝' },
  { label: 'Quarterly Exam',         types: ['Quarterly Exam'],                                       icon: '📅' },
  { label: 'Second Mid Term Test',   types: ['Second Mid Term Test'],                                  icon: '📝' },
  { label: 'Half Yearly Exam',       types: ['Half Yearly Exam'],                                     icon: '📆' },
  { label: 'Annual / Public Exam',   types: ['Annual Exam', 'Public Exam', 'Model Exam'],              icon: '🎯' },
  { label: 'Practical Exam',         types: ['Practical Exam'],                                       icon: '🔬', practicalOnly: true },
]

export default function SubjectPage() {
  const { id } = useParams()
  const [subject, setSubject] = useState(null)
  const [papers, setPapers] = useState([])
  const [materials, setMaterials] = useState([])
  const [categories, setCategories] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedMedium, setSelectedMedium] = useState('all')

  const [activeTab, setActiveTab] = useState('papers') // 'papers' | 'materials'
  const [loading, setLoading] = useState(true)
  const [materialsLoading, setMaterialsLoading] = useState(false)
  const [error, setError] = useState(null)

  // 1. Initial subject & papers fetch
  useEffect(() => {
    setLoading(true)
    setError(null)
    Promise.all([getSubject(id), getPapersForSubject(id)])
      .then(([subRes, papersRes]) => {
        setSubject(subRes.data)
        setPapers(papersRes.data)
      })
      .catch(err => setError(err.message || 'Failed to load subject'))
      .finally(() => setLoading(false))
  }, [id])

  // 2. Fetch study materials when materials tab is chosen or filters change
  useEffect(() => {
    if (activeTab === 'materials') {
      setMaterialsLoading(true)
      Promise.allSettled([
        getMaterialsBySubject(id, {
          category_id: selectedCategory || undefined,
          medium: selectedMedium !== 'all' ? selectedMedium : undefined,
          limit: 50,
        }),
        getMaterialCategories({ subject_id: id }),
      ]).then(([matRes, catRes]) => {
        if (matRes.status === 'fulfilled') {
          setMaterials(matRes.value?.data || [])
        }
        if (catRes.status === 'fulfilled') {
          const catData = catRes.value?.data || catRes.value || []
          setCategories(Array.isArray(catData) ? catData : [])
        }
      }).finally(() => setMaterialsLoading(false))
    }
  }, [id, activeTab, selectedCategory, selectedMedium])

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
          {/* Header Title */}
          <div className="mt-6 mb-6">
            <h1 className="text-3xl font-extrabold text-gray-900">{subject.name}</h1>
            <p className="text-gray-500 mt-1">
              {subject.class_name} — Select Question Papers or Study Materials below
            </p>
          </div>

          {/* Segmented Tab Switcher */}
          <div className="flex border-b border-gray-200 mb-8">
            <button
              type="button"
              onClick={() => setActiveTab('papers')}
              className={`pb-3 px-4 text-sm font-bold border-b-2 transition flex items-center gap-2 ${
                activeTab === 'papers'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-800'
              }`}
            >
              <span>📝</span>
              <span>Question Papers &amp; Answer Keys</span>
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                activeTab === 'papers' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
              }`}>
                {papers.length}
              </span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('materials')}
              className={`pb-3 px-4 text-sm font-bold border-b-2 transition flex items-center gap-2 ${
                activeTab === 'materials'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-800'
              }`}
            >
              <span>📚</span>
              <span>Study Materials &amp; Notes</span>
            </button>
          </div>

          {/* Tab 1: Question Papers & Answer Keys */}
          {activeTab === 'papers' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {groups.map(group => {
                const count = getCountForTypes(group.types)
                const hasFiles = count > 0

                return (
                  <div key={group.label}>
                    {hasFiles ? (
                      <Link
                        to={`/papers?subject_id=${subject.id}&category=${encodeURIComponent(group.label)}&exam_type=${encodeURIComponent(group.types.join(','))}`}
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
          )}

          {/* Tab 2: Study Materials & Notes */}
          {activeTab === 'materials' && (
            <div>
              {/* Filter pills */}
              <div className="bg-white rounded-2xl border border-gray-100 p-4 shadow-xs mb-6 flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-semibold text-gray-500 mr-1">Category:</span>
                  <button
                    type="button"
                    onClick={() => setSelectedCategory('')}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                      !selectedCategory
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    All
                  </button>
                  {categories.map(cat => (
                    <button
                      key={cat.id}
                      type="button"
                      onClick={() => setSelectedCategory(String(cat.id))}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold transition flex items-center gap-1 ${
                        String(selectedCategory) === String(cat.id)
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {cat.icon && <span>{cat.icon}</span>}
                      <span>{cat.name}</span>
                    </button>
                  ))}
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-gray-500">Medium:</span>
                  <select
                    value={selectedMedium}
                    onChange={(e) => setSelectedMedium(e.target.value)}
                    className="text-xs font-semibold bg-gray-50 border border-gray-200 rounded-xl px-2.5 py-1 text-gray-700"
                  >
                    <option value="all">All Mediums</option>
                    <option value="both">Both</option>
                    <option value="tamil">Tamil (தமிழ்)</option>
                    <option value="english">English</option>
                  </select>
                </div>
              </div>

              {materialsLoading ? (
                <div className="py-12">
                  <LoadingSpinner text="Loading study materials…" />
                </div>
              ) : materials.length === 0 ? (
                <div className="text-center py-16 bg-gray-50 rounded-2xl border border-dashed border-gray-200 p-8">
                  <div className="text-4xl mb-3">📚</div>
                  <h3 className="text-base font-bold text-gray-800">
                    No study materials uploaded for {subject.name} yet
                  </h3>
                  <p className="text-gray-500 text-xs mt-1 max-w-sm mx-auto">
                    Help other students by contributing chapter notes, formulas, or question banks for this subject!
                  </p>
                  <Link
                    to="/submit-material"
                    className="mt-4 inline-block px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-semibold hover:bg-blue-700 transition"
                  >
                    Submit Material for {subject.name}
                  </Link>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                  {materials.map(item => (
                    <StudyMaterialCard key={item.id} item={item} showSubject={false} />
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
