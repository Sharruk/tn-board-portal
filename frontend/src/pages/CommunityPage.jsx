import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { signInWithGoogle } from '../lib/firebase'
import {
  getCommunityPosts,
  createCommunityPost,
  COMMUNITY_CATEGORIES,
  CATEGORY_ICONS,
  getPaperRequests,
  createPaperRequest,
} from '../services/community'
import { EXAM_TYPES, MONTHS, TN_DISTRICTS } from '../services/papers'
import UserProfileModal from '../components/UserProfileModal'

const CLASSES = [9, 10, 11, 12]

function fmtDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

export default function CommunityPage() {
  const { user, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [activeTab, setActiveTab] = useState('All') // Category or 'Paper Requests'
  const [posts, setPosts] = useState([])
  const [paperRequests, setPaperRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')

  // Create post modal state
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newContent, setNewContent] = useState('')
  const [newCategory, setNewCategory] = useState('Discussion')
  const [submitting, setSubmitting] = useState(false)
  const [modalError, setModalError] = useState(null)

  // Paper request modal state
  const [isRequestModalOpen, setIsRequestModalOpen] = useState(false)
  const [reqClass, setReqClass] = useState('10')
  const [reqSubject, setReqSubject] = useState('')
  const [reqExamType, setReqExamType] = useState('Annual Exam')
  const [reqYear, setReqYear] = useState('2024')
  const [reqMonth, setReqMonth] = useState('')
  const [reqDistrict, setReqDistrict] = useState('')
  const [reqDesc, setReqDesc] = useState('')

  // User Profile modal state
  const [profileUser, setProfileUser] = useState(null)

  useEffect(() => {
    document.title = 'Community & Paper Requests | TN Board Portal'
  }, [])

  const fetchData = async (cat = activeTab, targetPage = 1) => {
    setLoading(true)
    setError(null)
    try {
      if (cat === 'Paper Requests') {
        const res = await getPaperRequests(null, targetPage, 15)
        setPaperRequests(res.data || [])
        setTotal(res.total || 0)
        setHasNext(res.has_next || false)
      } else {
        const res = await getCommunityPosts(cat, targetPage, 15)
        setPosts(res.data || [])
        setTotal(res.total || 0)
        setHasNext(res.has_next || false)
      }
      setPage(targetPage)
    } catch (err) {
      setError(err.message || 'Failed to load community data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData(activeTab, 1)
  }, [activeTab])

  const handleStartDiscussion = () => {
    if (!isAuthenticated) {
      signInWithGoogle()
      return
    }
    setModalError(null)
    setIsModalOpen(true)
  }

  const handleOpenPaperRequest = () => {
    if (!isAuthenticated) {
      signInWithGoogle()
      return
    }
    setModalError(null)
    setIsRequestModalOpen(true)
  }

  const handleCreatePost = async e => {
    e.preventDefault()
    if (!newTitle.trim() || !newContent.trim()) {
      setModalError('Title and content are required.')
      return
    }
    if (newTitle.trim().length < 3) {
      setModalError('Title must be at least 3 characters.')
      return
    }
    setSubmitting(true)
    setModalError(null)
    try {
      const created = await createCommunityPost({
        title: newTitle.trim(),
        content: newContent.trim(),
        category: newCategory,
        author_avatar: user?.photoURL || null,
      })
      setIsModalOpen(false)
      setNewTitle('')
      setNewContent('')
      navigate(`/community/post/${created.id}`)
    } catch (err) {
      setModalError(err.message || 'Failed to create discussion topic.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCreatePaperRequest = async e => {
    e.preventDefault()
    if (!reqSubject.trim()) {
      setModalError('Subject is required.')
      return
    }
    setSubmitting(true)
    setModalError(null)
    try {
      await createPaperRequest({
        class_name: `Class ${reqClass}`,
        subject_name: reqSubject.trim(),
        exam_type: reqExamType,
        year: parseInt(reqYear, 10) || 2024,
        month: reqMonth || null,
        district: reqDistrict || null,
        description: reqDesc.trim() || null,
      })
      setIsRequestModalOpen(false)
      setReqSubject('')
      setReqDesc('')
      setActiveTab('Paper Requests')
      fetchData('Paper Requests', 1)
    } catch (err) {
      setModalError(err.message || 'Failed to submit paper request.')
    } finally {
      setSubmitting(false)
    }
  }

  const filteredPosts = posts.filter(
    p =>
      p.title.toLowerCase().includes(search.toLowerCase()) ||
      p.author_name.toLowerCase().includes(search.toLowerCase())
  )

  const filteredRequests = paperRequests.filter(
    r =>
      r.subject_name.toLowerCase().includes(search.toLowerCase()) ||
      r.class_name.toLowerCase().includes(search.toLowerCase()) ||
      (r.exam_type && r.exam_type.toLowerCase().includes(search.toLowerCase()))
  )

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4 sm:px-6 lg:px-8">
      {profileUser && (
        <UserProfileModal
          uid={profileUser.firebase_uid}
          authorName={profileUser.author_name}
          onClose={() => setProfileUser(null)}
        />
      )}

      <div className="max-w-5xl mx-auto space-y-8">

        {/* ── Hero ────────────────────────────────────────────────────── */}
        <div className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-700 rounded-3xl p-6 sm:p-10 text-white shadow-xl relative overflow-hidden">
          <div className="relative z-10 max-w-2xl space-y-3">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/20 backdrop-blur-sm text-xs font-semibold uppercase tracking-wider">
              <span>💬</span> Student &amp; Teacher Community
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
              Community &amp; Paper Requests
            </h1>
            <p className="text-blue-100 text-sm sm:text-base leading-relaxed">
              Ask questions, discuss previous exam papers, collaborate on answer keys, and request question papers you can’t find.
            </p>
            <div className="pt-2 flex flex-wrap items-center gap-3">
              <button
                onClick={handleStartDiscussion}
                className="px-5 py-2.5 bg-white text-blue-700 hover:bg-blue-50 font-bold text-sm rounded-xl transition shadow-md flex items-center gap-2"
              >
                <span>✍️</span> Start Discussion
              </button>
              <button
                onClick={handleOpenPaperRequest}
                className="px-5 py-2.5 bg-white/20 hover:bg-white/30 backdrop-blur-sm text-white font-bold text-sm rounded-xl transition border border-white/30 flex items-center gap-2"
              >
                <span>📄</span> Request a Paper
              </button>
            </div>
          </div>
          <div className="absolute right-4 bottom-4 opacity-10 text-9xl select-none pointer-events-none hidden md:block">
            📚
          </div>
        </div>

        {/* ── Category & Filter Tabs ─────────────────────────────────── */}
        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
          {COMMUNITY_CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveTab(cat)}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition shrink-0 flex items-center gap-1.5 ${
                activeTab === cat
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
              }`}
            >
              <span>{CATEGORY_ICONS[cat] || '💬'}</span>
              {cat}
            </button>
          ))}
          <button
            onClick={() => setActiveTab('Paper Requests')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition shrink-0 flex items-center gap-1.5 ${
              activeTab === 'Paper Requests'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-white text-indigo-700 hover:bg-indigo-50 border border-indigo-200'
            }`}
          >
            <span>📄</span> Paper Requests
          </button>
        </div>

        {/* ── Search & Count Bar ─────────────────────────────────────── */}
        <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-80">
            <input
              type="text"
              placeholder={activeTab === 'Paper Requests' ? 'Search requests…' : 'Search discussions or authors…'}
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full text-sm border border-gray-200 rounded-xl pl-9 pr-3 py-2 outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
            />
            <span className="absolute left-3 top-2.5 text-gray-400 text-sm">🔍</span>
          </div>
          <div className="text-xs font-medium text-gray-500">
            Showing <strong className="text-gray-800">{activeTab === 'Paper Requests' ? filteredRequests.length : filteredPosts.length}</strong> of{' '}
            <strong className="text-gray-800">{total}</strong> {activeTab === 'Paper Requests' ? 'requests' : 'topics'}
          </div>
        </div>

        {/* ── Main Feed (Discussions or Requests) ──────────────────────── */}
        {activeTab === 'Paper Requests' ? (
          /* Paper Requests View */
          <div className="space-y-3">
            {loading ? (
              <div className="bg-white rounded-2xl border border-gray-200 py-20 flex flex-col items-center justify-center gap-3">
                <span className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
                <p className="text-sm font-medium text-gray-500">Loading paper requests…</p>
              </div>
            ) : error ? (
              <div className="bg-white rounded-2xl border border-gray-200 p-8 text-center space-y-3">
                <p className="text-3xl">⚠️</p>
                <p className="text-sm font-semibold text-gray-800">Unable to load requests</p>
                <p className="text-xs text-red-600">{error}</p>
                <button onClick={() => fetchData('Paper Requests', page)} className="px-4 py-2 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-xl text-xs font-semibold">
                  Try Again
                </button>
              </div>
            ) : filteredRequests.length === 0 ? (
              <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center space-y-3">
                <p className="text-4xl">📄</p>
                <h3 className="text-base font-bold text-gray-800">No paper requests found</h3>
                <p className="text-xs text-gray-500 max-w-sm mx-auto">
                  Can’t find a question paper or answer key? Submit a request to the community!
                </p>
                <button
                  onClick={handleOpenPaperRequest}
                  className="inline-block mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold transition"
                >
                  Request a Paper
                </button>
              </div>
            ) : (
              filteredRequests.map(req => (
                <div
                  key={req.id}
                  className="bg-white border border-gray-200 rounded-2xl p-5 shadow-sm space-y-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className="bg-indigo-50 text-indigo-700 text-xs font-bold px-2.5 py-0.5 rounded-full border border-indigo-100">
                          {req.class_name} • {req.subject_name}
                        </span>
                        <span className="text-xs font-semibold text-gray-700">
                          {req.exam_type} {req.year} {req.month ? `(${req.month})` : ''}
                        </span>
                        {req.district && (
                          <span className="text-xs text-gray-500">📍 {req.district}</span>
                        )}
                      </div>
                      {req.description && (
                        <p className="text-xs text-gray-600 mt-1">{req.description}</p>
                      )}
                    </div>
                    <span
                      className={`text-[11px] font-extrabold uppercase px-2.5 py-1 rounded-full border shrink-0 ${
                        req.status === 'fulfilled'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : req.status === 'in_progress'
                          ? 'bg-amber-50 text-amber-700 border-amber-200'
                          : 'bg-blue-50 text-blue-700 border-blue-200'
                      }`}
                    >
                      {req.status.replace('_', ' ')}
                    </span>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-gray-100 text-[11px] text-gray-400">
                    <span
                      onClick={() => setProfileUser({ firebase_uid: req.firebase_uid, author_name: req.requester_name })}
                      className="font-medium text-gray-600 hover:text-blue-600 cursor-pointer"
                    >
                      Requested by {req.requester_name}
                    </span>
                    <span>{fmtDate(req.created_at)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        ) : (
          /* Discussions Feed View */
          <div className="space-y-3">
            {loading ? (
              <div className="bg-white rounded-2xl border border-gray-200 py-20 flex flex-col items-center justify-center gap-3">
                <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
                <p className="text-sm font-medium text-gray-500">Loading discussions…</p>
              </div>
            ) : error ? (
              <div className="bg-white rounded-2xl border border-gray-200 p-8 text-center space-y-3">
                <p className="text-3xl">⚠️</p>
                <p className="text-sm font-semibold text-gray-800">Unable to load discussions</p>
                <p className="text-xs text-red-600">{error}</p>
                <button onClick={() => fetchData(activeTab, page)} className="px-4 py-2 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-xl text-xs font-semibold">
                  Try Again
                </button>
              </div>
            ) : filteredPosts.length === 0 ? (
              <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center space-y-3">
                <p className="text-4xl">💡</p>
                <h3 className="text-base font-bold text-gray-800">
                  {search ? 'No matching discussions found' : 'No discussions yet in this category'}
                </h3>
                <p className="text-xs text-gray-500 max-w-sm mx-auto">
                  {search
                    ? 'Try searching with different keywords.'
                    : 'Start the first conversation about exams, answer keys, or study materials!'}
                </p>
                <button
                  onClick={handleStartDiscussion}
                  className="inline-block mt-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold transition"
                >
                  Start Discussion
                </button>
              </div>
            ) : (
              filteredPosts.map(post => (
                <Link
                  key={post.id}
                  to={`/community/post/${post.id}`}
                  className="block bg-white hover:bg-blue-50/40 border border-gray-200 hover:border-blue-300 rounded-2xl p-5 transition-all shadow-sm group"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-2 flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        {post.is_pinned && (
                          <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 text-[11px] font-bold px-2.5 py-0.5 rounded-full">
                            📌 Pinned
                          </span>
                        )}
                        <span className="inline-flex items-center gap-1 bg-gray-100 text-gray-700 text-[11px] font-semibold px-2 py-0.5 rounded-md border border-gray-200">
                          {CATEGORY_ICONS[post.category] || '💬'} {post.category || 'Discussion'}
                        </span>
                        {post.status && post.status !== 'open' && (
                          <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[11px] font-bold px-2 py-0.5 rounded-md">
                            ✓ {post.status}
                          </span>
                        )}
                        <h2 className="text-base font-bold text-gray-900 group-hover:text-blue-600 transition-colors truncate w-full">
                          {post.title}
                        </h2>
                      </div>
                      <p className="text-xs text-gray-600 line-clamp-2 leading-relaxed">
                        {post.content}
                      </p>
                      <div className="flex items-center gap-4 text-[11px] text-gray-400 pt-1">
                        <span
                          onClick={e => {
                            e.preventDefault()
                            e.stopPropagation()
                            setProfileUser({ firebase_uid: post.firebase_uid, author_name: post.author_name })
                          }}
                          className="font-medium text-gray-600 hover:text-blue-600 transition-colors"
                        >
                          👤 {post.author_name}
                        </span>
                        <span>📅 {fmtDate(post.created_at)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <div className="flex flex-col items-center justify-center bg-gray-50 border border-gray-200 rounded-xl px-3 py-1.5 min-w-[54px]">
                        <span className="text-xs font-bold text-gray-800">{post.reply_count ?? post.comments_count ?? 0}</span>
                        <span className="text-[10px] text-gray-500 font-medium">replies</span>
                      </div>
                      <div className="flex flex-col items-center justify-center bg-blue-50 border border-blue-100 rounded-xl px-3 py-1.5 min-w-[54px]">
                        <span className="text-xs font-bold text-blue-700">{post.likes_count ?? post.upvotes ?? 0}</span>
                        <span className="text-[10px] text-blue-600 font-medium">upvotes</span>
                      </div>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        )}

        {/* ── Pagination ──────────────────────────────────────────────── */}
        {!loading && total > 15 && (
          <div className="flex items-center justify-center gap-3 pt-4">
            <button
              onClick={() => fetchData(activeTab, page - 1)}
              disabled={page <= 1}
              className="px-4 py-2 border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-40 transition"
            >
              ← Previous
            </button>
            <span className="text-xs text-gray-500 font-medium">Page {page}</span>
            <button
              onClick={() => fetchData(activeTab, page + 1)}
              disabled={!hasNext}
              className="px-4 py-2 border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-40 transition"
            >
              Next →
            </button>
          </div>
        )}

      </div>

      {/* ── Create Post Modal ────────────────────────────────────────── */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setIsModalOpen(false)} />
          <div className="relative z-10 bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <span>✍️</span> New Discussion Topic
              </h2>
              <button onClick={() => setIsModalOpen(false)} className="text-gray-400 hover:text-gray-600 p-1 text-lg leading-none">
                ✕
              </button>
            </div>
            <form onSubmit={handleCreatePost} className="p-6 space-y-4 overflow-y-auto">
              {modalError && (
                <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 text-xs text-red-600 font-medium">
                  {modalError}
                </div>
              )}
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Category</label>
                <select
                  value={newCategory}
                  onChange={e => setNewCategory(e.target.value)}
                  className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                >
                  {COMMUNITY_CATEGORIES.filter(c => c !== 'All').map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  Topic Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g., Question 14 doubt in Class 12 Maths March 2024"
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  maxLength={200}
                  className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  Details / Body <span className="text-red-500">*</span>
                </label>
                <textarea
                  rows={5}
                  placeholder="Describe your question, share solution hints, or discuss study strategies…"
                  value={newContent}
                  onChange={e => setNewContent(e.target.value)}
                  maxLength={5000}
                  className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  required
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-semibold py-2.5 rounded-xl transition flex items-center justify-center gap-2"
                >
                  {submitting ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : '🚀 Post Topic'}
                </button>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2.5 border border-gray-200 text-gray-600 hover:bg-gray-50 text-sm font-semibold rounded-xl"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Request Paper Modal ──────────────────────────────────────── */}
      {isRequestModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setIsRequestModalOpen(false)} />
          <div className="relative z-10 bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <span>📄</span> Request a Question Paper
              </h2>
              <button onClick={() => setIsRequestModalOpen(false)} className="text-gray-400 hover:text-gray-600 p-1 text-lg leading-none">
                ✕
              </button>
            </div>
            <form onSubmit={handleCreatePaperRequest} className="p-6 space-y-4 overflow-y-auto">
              {modalError && (
                <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 text-xs text-red-600 font-medium">
                  {modalError}
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Class</label>
                  <select
                    value={reqClass}
                    onChange={e => setReqClass(e.target.value)}
                    className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                  >
                    {CLASSES.map(c => (
                      <option key={c} value={c}>Class {c}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Subject <span className="text-red-500">*</span></label>
                  <input
                    type="text"
                    placeholder="e.g., Mathematics"
                    value={reqSubject}
                    onChange={e => setReqSubject(e.target.value)}
                    className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Exam Type</label>
                  <select
                    value={reqExamType}
                    onChange={e => setReqExamType(e.target.value)}
                    className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                  >
                    {EXAM_TYPES.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Year</label>
                  <input
                    type="number"
                    min="2010"
                    max="2030"
                    value={reqYear}
                    onChange={e => setReqYear(e.target.value)}
                    className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Month (Optional)</label>
                  <select
                    value={reqMonth}
                    onChange={e => setReqMonth(e.target.value)}
                    className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                  >
                    <option value="">Any / Not Applicable</option>
                    {MONTHS.map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">District (Optional)</label>
                  <select
                    value={reqDistrict}
                    onChange={e => setReqDistrict(e.target.value)}
                    className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                  >
                    <option value="">State-wide / Any District</option>
                    {TN_DISTRICTS.map(d => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Specific Description or Notes</label>
                <textarea
                  rows={3}
                  placeholder="e.g., Looking for Question paper with English medium answer key…"
                  value={reqDesc}
                  onChange={e => setReqDesc(e.target.value)}
                  maxLength={500}
                  className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm font-semibold py-2.5 rounded-xl transition flex items-center justify-center gap-2"
                >
                  {submitting ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : '📨 Submit Request'}
                </button>
                <button
                  type="button"
                  onClick={() => setIsRequestModalOpen(false)}
                  className="px-4 py-2.5 border border-gray-200 text-gray-600 hover:bg-gray-50 text-sm font-semibold rounded-xl"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
