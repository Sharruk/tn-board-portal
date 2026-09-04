import { useState, useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { signInWithGoogle } from '../lib/firebase'
import UserAvatar from '../components/common/UserAvatar'
import {
  getMyConversations,
  getConversationDetail,
  createConversation,
  sendConversationMessage,
} from '../services/conversations'
import { getMySubmissions } from '../services/submissions'

const CATEGORIES = [
  { id: 'general_question', label: 'General Question', icon: '❓', desc: 'Ask about syllabi, exams, or portal features' },
  { id: 'material_request', label: 'Material Request', icon: '📄', desc: 'Request missing question papers or answer keys' },
  { id: 'submission_status', label: 'Submission Status', icon: '🔍', desc: 'Inquire about paper you submitted for review' },
  { id: 'report_problem', label: 'Report a Problem', icon: '⚠️', desc: 'Report incorrect content, bad PDF, or broken link' },
  { id: 'feedback', label: 'Feedback', icon: '💡', desc: 'Suggestions to improve TN Board Portal' },
  { id: 'other', label: 'Other', icon: '💬', desc: 'Any other question or inquiry' },
]

function fmtDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

function fmtTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
}

export default function MessagesPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()
  const location = useLocation()

  const [conversations, setConversations] = useState([])
  const [activeConv, setActiveConv] = useState(null)
  const [loadingList, setLoadingList] = useState(true)
  const [loadingThread, setLoadingThread] = useState(false)
  const [error, setError] = useState(null)

  // New conversation modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [newCategory, setNewCategory] = useState('material_request')
  const [newSubject, setNewSubject] = useState('')
  const [newMessage, setNewMessage] = useState('')
  const [selectedSubmissionId, setSelectedSubmissionId] = useState('')
  const [userSubmissions, setUserSubmissions] = useState([])
  const [loadingSubmissions, setLoadingSubmissions] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState(null)

  // Reply state
  const [replyText, setReplyText] = useState('')
  const [sendingReply, setSendingReply] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    document.title = 'Messages & Support | TN Board Portal'
  }, [])

  // Auto-scroll to bottom of active conversation
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    if (activeConv?.messages) {
      scrollToBottom()
    }
  }, [activeConv?.messages])

  // Load conversations list
  const loadConversations = async (autoSelectFirst = false) => {
    if (!isAuthenticated) return
    setLoadingList(true)
    setError(null)
    try {
      const res = await getMyConversations()
      const list = res.data || []
      setConversations(list)
      if (list.length > 0 && autoSelectFirst && !activeConv) {
        selectConversation(list[0].id)
      }
    } catch (err) {
      setError(err.message || 'Failed to load conversations.')
    } finally {
      setLoadingList(false)
    }
  }

  useEffect(() => {
    if (isAuthenticated) {
      loadConversations(true)
    }
  }, [isAuthenticated])

  // Select a conversation and load its messages
  const selectConversation = async (convId) => {
    setLoadingThread(true)
    try {
      const detail = await getConversationDetail(convId)
      setActiveConv(detail)
      // Update unread count locally
      setConversations(prev =>
        prev.map(c => (c.id === convId ? { ...c, unread_count: 0 } : c))
      )
    } catch (err) {
      console.error('Failed to load conversation detail:', err)
    } finally {
      setLoadingThread(false)
    }
  }

  // Load user submissions when modal is opened with submission_status category
  useEffect(() => {
    if (modalOpen && newCategory === 'submission_status' && userSubmissions.length === 0) {
      setLoadingSubmissions(true)
      getMySubmissions()
        .then(res => {
          setUserSubmissions(res.data || [])
        })
        .catch(err => console.error('Failed to load user submissions:', err))
        .finally(() => setLoadingSubmissions(false))
    }
  }, [modalOpen, newCategory, userSubmissions.length])

  // Start new conversation submit
  const handleCreateSubmit = async (e) => {
    e.preventDefault()
    setCreateError(null)

    if (!newSubject.trim()) {
      setCreateError('Please enter a subject.')
      return
    }
    if (!newMessage.trim()) {
      setCreateError('Please enter your message.')
      return
    }

    setCreating(true)
    try {
      const created = await createConversation({
        category: newCategory,
        subject: newSubject.trim(),
        message: newMessage.trim(),
        submission_id: newCategory === 'submission_status' && selectedSubmissionId ? selectedSubmissionId : null,
      })
      setModalOpen(false)
      setNewSubject('')
      setNewMessage('')
      setSelectedSubmissionId('')
      setActiveConv(created)
      // Refresh list
      loadConversations(false)
    } catch (err) {
      setCreateError(err.message || 'Failed to start conversation.')
    } finally {
      setCreating(false)
    }
  }

  // Send message reply
  const handleSendReply = async (e) => {
    e.preventDefault()
    if (!replyText.trim() || !activeConv || sendingReply) return

    setSendingReply(true)
    try {
      const newMsg = await sendConversationMessage(activeConv.id, replyText.trim())
      setActiveConv(prev => ({
        ...prev,
        status: 'awaiting_admin',
        messages: [...(prev.messages || []), newMsg],
      }))
      setReplyText('')
      // Update in conversation list
      setConversations(prev =>
        prev.map(c =>
          c.id === activeConv.id
            ? {
                ...c,
                status: 'awaiting_admin',
                last_message: newMsg.message,
                last_message_at: newMsg.created_at,
                last_message_sender_role: 'user',
              }
            : c
        )
      )
    } catch (err) {
      alert(err.message || 'Failed to send message.')
    } finally {
      setSendingReply(false)
    }
  }

  if (authLoading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <span className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
          <p className="text-sm font-medium text-gray-500">Loading messages…</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center px-4 py-16">
        <div className="max-w-md w-full text-center bg-white border border-gray-200 rounded-3xl p-8 shadow-sm">
          <div className="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-5 text-2xl font-bold">
            💬
          </div>
          <h1 className="text-2xl font-extrabold text-gray-900 mb-2">Student &amp; Contributor Helpdesk</h1>
          <p className="text-gray-600 text-sm leading-relaxed mb-6">
            Sign in with your Google account to communicate directly with TN Board administrators, request missing question papers, or check your contribution review statuses.
          </p>
          <button
            onClick={signInWithGoogle}
            className="w-full inline-flex items-center justify-center gap-3 bg-white hover:bg-gray-50 border border-gray-200 text-gray-800 font-semibold px-6 py-3.5 rounded-xl transition-all text-sm shadow-xs"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
            </svg>
            Sign in with Google
          </button>
        </div>
      </div>
    )
  }

  const categoryMeta = CATEGORIES.find(c => c.id === activeConv?.category) || { icon: '💬', label: activeConv?.category }

  return (
    <div className="min-h-screen bg-gray-50/70 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* ── Breadcrumb & Header ───────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
              <Link to="/" className="hover:text-blue-600 transition">Home</Link>
              <span>/</span>
              <span className="text-gray-900 font-medium">Messages &amp; Support</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 tracking-tight flex items-center gap-2.5">
              <span>💬</span> Messages &amp; Support
            </h1>
            <p className="text-xs sm:text-sm text-gray-500 mt-0.5">
              Contact TN Board administrators for material requests, submission questions, and problem reports.
            </p>
          </div>

          <button
            onClick={() => setModalOpen(true)}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs sm:text-sm font-bold rounded-xl shadow-xs transition"
          >
            <span>✍️</span> New Conversation
          </button>
        </div>

        {/* ── Main Messaging Container ──────────────────────────────── */}
        <div className="bg-white rounded-3xl border border-gray-200/80 shadow-xs overflow-hidden grid grid-cols-1 md:grid-cols-12 min-h-[620px]">

          {/* ── Conversations Sidebar (4 cols) ────────────────────────── */}
          <div className="md:col-span-4 border-r border-gray-100 flex flex-col h-full bg-gray-50/30">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <span className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                Conversations ({conversations.length})
              </span>
              <button
                onClick={() => loadConversations(false)}
                className="text-xs text-gray-400 hover:text-blue-600 transition"
                title="Refresh conversations"
              >
                🔄
              </button>
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-gray-50">
              {loadingList ? (
                <div className="p-8 text-center">
                  <span className="w-6 h-6 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin inline-block" />
                </div>
              ) : conversations.length === 0 ? (
                <div className="p-8 text-center text-gray-400 text-xs">
                  <p className="text-2xl mb-2">💬</p>
                  <p className="font-semibold text-gray-600">No conversations yet</p>
                  <p className="mt-1">Click "New Conversation" above to contact the admin.</p>
                </div>
              ) : (
                conversations.map(c => {
                  const meta = CATEGORIES.find(cat => cat.id === c.category) || { icon: '💬', label: c.category }
                  const isSelected = activeConv?.id === c.id
                  return (
                    <button
                      key={c.id}
                      onClick={() => selectConversation(c.id)}
                      className={`w-full text-left p-4 transition-all relative flex flex-col gap-1.5 ${
                        isSelected ? 'bg-white shadow-xs border-l-4 border-blue-600' : 'hover:bg-gray-100/60'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-md bg-gray-100 text-gray-700">
                          <span>{meta.icon}</span> {meta.label}
                        </span>
                        <span className="text-[10px] text-gray-400">
                          {fmtDate(c.updated_at || c.created_at)}
                        </span>
                      </div>

                      <p className="text-xs font-bold text-gray-900 truncate">
                        {c.subject}
                      </p>

                      <div className="flex items-center justify-between gap-2 mt-0.5">
                        <p className="text-[11px] text-gray-500 truncate max-w-[200px]">
                          {c.last_message || 'Started conversation'}
                        </p>
                        {c.unread_count > 0 && (
                          <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.2 rounded-full shrink-0 animate-pulse">
                            New Reply!
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-1.5 mt-1">
                        <span className={`w-2 h-2 rounded-full ${
                          c.status === 'resolved' ? 'bg-gray-400' :
                          c.status === 'awaiting_user' ? 'bg-emerald-500' : 'bg-amber-500'
                        }`} />
                        <span className="text-[10px] font-medium text-gray-500 capitalize">
                          {c.status.replace('_', ' ')}
                        </span>
                      </div>
                    </button>
                  )
                })
              )}
            </div>
          </div>

          {/* ── Active Conversation View (8 cols) ─────────────────────── */}
          <div className="md:col-span-8 flex flex-col h-full bg-white">
            {activeConv ? (
              <>
                {/* Thread Header */}
                <div className="p-4 sm:p-5 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{categoryMeta.icon}</span>
                      <span className="text-xs font-bold text-blue-700 uppercase tracking-wider">
                        {categoryMeta.label}
                      </span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        activeConv.status === 'resolved' ? 'bg-gray-100 text-gray-700' :
                        activeConv.status === 'awaiting_user' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                      }`}>
                        {activeConv.status.replace('_', ' ').toUpperCase()}
                      </span>
                    </div>
                    <h2 className="text-base sm:text-lg font-bold text-gray-900">
                      {activeConv.subject}
                    </h2>
                    <p className="text-[11px] text-gray-400">
                      Started {fmtDate(activeConv.created_at)} at {fmtTime(activeConv.created_at)}
                    </p>
                  </div>
                </div>

                {/* Linked Submission Context Banner (if applicable) */}
                {activeConv.linked_submission && (
                  <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50/50 border-b border-blue-100 text-xs text-gray-800 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-blue-900 flex items-center gap-1.5">
                        <span>📦</span> Linked Submission Reference
                      </span>
                      <span className={`px-2 py-0.5 rounded-full font-extrabold text-[10px] uppercase ${
                        activeConv.linked_submission.status === 'approved' ? 'bg-emerald-100 text-emerald-800' :
                        activeConv.linked_submission.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-800'
                      }`}>
                        Status: {activeConv.linked_submission.status}
                      </span>
                    </div>
                    <p className="text-gray-600">
                      <strong>Submitted on:</strong> {fmtDate(activeConv.linked_submission.created_at)} &bull; <strong>Files attached:</strong> {activeConv.linked_submission.files_count}
                    </p>
                    {activeConv.linked_submission.rejection_reason && (
                      <div className="p-2 bg-red-50 border border-red-200 rounded-lg text-red-700 font-medium">
                        <strong>Rejection Reason:</strong> {activeConv.linked_submission.rejection_reason}
                      </div>
                    )}
                    {activeConv.linked_submission.thank_you_message && (
                      <div className="p-2 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 font-medium">
                        <strong>Admin Message:</strong> {activeConv.linked_submission.thank_you_message}
                      </div>
                    )}
                  </div>
                )}

                {/* Message Bubbles Area */}
                <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-4 max-h-[440px]">
                  {loadingThread ? (
                    <div className="py-12 flex justify-center">
                      <span className="w-6 h-6 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
                    </div>
                  ) : (
                    activeConv.messages?.map(m => {
                      const isAdmin = m.sender_role === 'admin'
                      return (
                        <div
                          key={m.id}
                          className={`flex gap-3 max-w-[85%] ${isAdmin ? 'mr-auto flex-row' : 'ml-auto flex-row-reverse'}`}
                        >
                          {/* Avatar */}
                          <div className="shrink-0 mt-0.5">
                            {isAdmin ? (
                              <div className="w-8 h-8 rounded-full bg-gray-900 text-white font-bold flex items-center justify-center text-xs shadow-xs">
                                🏛️
                              </div>
                            ) : (
                              <UserAvatar user={user} size="sm" />
                            )}
                          </div>

                          {/* Content Bubble */}
                          <div className="space-y-1">
                            <div className={`flex items-center gap-2 ${isAdmin ? 'justify-start' : 'justify-end'}`}>
                              <span className="text-[11px] font-bold text-gray-700">
                                {isAdmin ? 'TN Board Admin' : 'You'}
                              </span>
                              <span className="text-[10px] text-gray-400">
                                {fmtTime(m.created_at)}
                              </span>
                            </div>
                            <div
                              className={`p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed whitespace-pre-wrap shadow-xs ${
                                isAdmin
                                  ? 'bg-gray-100 text-gray-900 rounded-tl-none border border-gray-200/60'
                                  : 'bg-blue-600 text-white rounded-tr-none'
                              }`}
                            >
                              {m.message}
                            </div>
                          </div>
                        </div>
                      )
                    })
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {/* Reply Box */}
                <div className="p-3 sm:p-4 border-t border-gray-100 bg-gray-50/50">
                  <form onSubmit={handleSendReply} className="flex gap-2">
                    <input
                      type="text"
                      value={replyText}
                      onChange={e => setReplyText(e.target.value)}
                      placeholder="Type your message to TN Board Admin…"
                      disabled={sendingReply}
                      className="flex-1 text-xs sm:text-sm border border-gray-200 rounded-xl px-4 py-2.5 outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition bg-white"
                    />
                    <button
                      type="submit"
                      disabled={sendingReply || !replyText.trim()}
                      className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl transition shadow-xs flex items-center gap-1.5 shrink-0"
                    >
                      {sendingReply ? (
                        <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                      ) : (
                        <>
                          <span>Send</span>
                          <span>🚀</span>
                        </>
                      )}
                    </button>
                  </form>
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-gray-400">
                <span className="text-4xl mb-3">💬</span>
                <h3 className="text-base font-bold text-gray-700 mb-1">Select a Conversation</h3>
                <p className="text-xs text-gray-400 max-w-sm">
                  Choose a conversation from the sidebar or click "New Conversation" to contact the TN Board Admin team.
                </p>
              </div>
            )}
          </div>
        </div>

      </div>

      {/* ── New Conversation Modal ──────────────────────────────────── */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fade-in">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 shadow-2xl border border-gray-100 space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-gray-100 pb-4">
              <h2 className="text-lg font-extrabold text-gray-900 flex items-center gap-2">
                <span>✍️</span> Start New Conversation
              </h2>
              <button
                onClick={() => setModalOpen(false)}
                className="w-8 h-8 text-gray-400 hover:text-gray-700 rounded-full hover:bg-gray-100 flex items-center justify-center text-lg"
              >
                ✕
              </button>
            </div>

            {createError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs font-semibold text-red-600 flex items-center gap-2">
                <span>⚠️</span> {createError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4">
              {/* Category Grid */}
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1.5 uppercase tracking-wide">
                  Select Category
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {CATEGORIES.map(cat => (
                    <button
                      type="button"
                      key={cat.id}
                      onClick={() => setNewCategory(cat.id)}
                      className={`p-2.5 rounded-xl border text-left transition flex flex-col gap-1 ${
                        newCategory === cat.id
                          ? 'bg-blue-50/80 border-blue-500 ring-2 ring-blue-500/20 text-blue-900'
                          : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      <span className="text-lg">{cat.icon}</span>
                      <span className="text-xs font-bold leading-tight">{cat.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* If category is submission_status, show user's submission selector */}
              {newCategory === 'submission_status' && (
                <div className="bg-amber-50/60 border border-amber-200 rounded-2xl p-3.5 space-y-2">
                  <label className="block text-xs font-bold text-amber-900">
                    Which submission are you asking about? (Optional)
                  </label>
                  {loadingSubmissions ? (
                    <p className="text-xs text-amber-700">Loading your submissions…</p>
                  ) : userSubmissions.length === 0 ? (
                    <p className="text-xs text-amber-700">You haven't submitted any papers yet.</p>
                  ) : (
                    <select
                      value={selectedSubmissionId}
                      onChange={e => setSelectedSubmissionId(e.target.value)}
                      className="w-full text-xs border border-amber-300 rounded-xl px-3 py-2 bg-white text-gray-800 outline-none"
                    >
                      <option value="">-- Choose a submission --</option>
                      {userSubmissions.map(sub => (
                        <option key={sub.id} value={sub.id}>
                          {sub.publisher_name} ({fmtDate(sub.created_at)}) — [{sub.status.toUpperCase()}]
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              )}

              {/* Subject Input */}
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1.5 uppercase tracking-wide">
                  Subject / Summary
                </label>
                <input
                  type="text"
                  value={newSubject}
                  onChange={e => setNewSubject(e.target.value)}
                  placeholder="e.g. Request Class 10 Maths Quarterly 2025 question paper"
                  maxLength={255}
                  required
                  className="w-full text-xs sm:text-sm border border-gray-200 rounded-xl px-4 py-2.5 outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                />
              </div>

              {/* Initial Message Input */}
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1.5 uppercase tracking-wide">
                  Your Message
                </label>
                <textarea
                  value={newMessage}
                  onChange={e => setNewMessage(e.target.value)}
                  rows={4}
                  placeholder="Describe your request or inquiry in detail…"
                  required
                  className="w-full text-xs sm:text-sm border border-gray-200 rounded-xl p-3 outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition resize-none"
                />
              </div>

              {/* Actions */}
              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 text-xs font-bold text-gray-500 hover:text-gray-800 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl transition shadow-xs flex items-center gap-2"
                >
                  {creating ? (
                    <>
                      <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                      Starting…
                    </>
                  ) : (
                    'Start Conversation'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
