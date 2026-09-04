import { useState, useEffect, useRef } from 'react'
import UserAvatar from '../common/UserAvatar'
import {
  getAdminConversations,
  getAdminConversationDetail,
  getAdminConversationStats,
  sendAdminReply,
  updateAdminConversationStatus,
} from '../../services/adminConversations'

const CATEGORIES = [
  { id: 'general_question', label: 'General Question', icon: '❓' },
  { id: 'material_request', label: 'Material Request', icon: '📄' },
  { id: 'submission_status', label: 'Submission Status', icon: '🔍' },
  { id: 'report_problem', label: 'Report a Problem', icon: '⚠️' },
  { id: 'feedback', label: 'Feedback', icon: '💡' },
  { id: 'other', label: 'Other', icon: '💬' },
]

function fmtDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

function fmtTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
}

export default function AdminInboxTab() {
  const [conversations, setConversations] = useState([])
  const [activeConv, setActiveConv] = useState(null)
  const [stats, setStats] = useState({ total: 0, unread_count: 0, awaiting_admin: 0, awaiting_user: 0, resolved: 0 })
  const [loadingList, setLoadingList] = useState(true)
  const [loadingThread, setLoadingThread] = useState(false)
  const [filterStatus, setFilterStatus] = useState('all') // 'all' | 'unread' | 'awaiting_admin' | 'awaiting_user' | 'resolved'
  const [filterCategory, setFilterCategory] = useState('')
  const [search, setSearch] = useState('')
  const [replyText, setReplyText] = useState('')
  const [sendingReply, setSendingReply] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    if (activeConv?.messages) {
      scrollToBottom()
    }
  }, [activeConv?.messages])

  const loadConversations = async (autoSelect = false) => {
    setLoadingList(true)
    try {
      const statusParam = filterStatus === 'all' ? null : filterStatus
      const [convRes, statsRes] = await Promise.allSettled([
        getAdminConversations({
          status: statusParam,
          category: filterCategory || null,
          search,
          limit: 100,
        }),
        getAdminConversationStats(),
      ])

      let list = []
      if (convRes.status === 'fulfilled') {
        list = convRes.value.data || []
        setConversations(list)
      }
      if (statsRes.status === 'fulfilled') {
        setStats(statsRes.value)
      }

      if (autoSelect && list.length > 0 && !activeConv) {
        selectConversation(list[0].id)
      }
    } catch (err) {
      console.error('Failed to load admin inbox:', err)
    } finally {
      setLoadingList(false)
    }
  }

  useEffect(() => {
    loadConversations(true)
  }, [filterStatus, filterCategory])

  const selectConversation = async (convId) => {
    setLoadingThread(true)
    try {
      const detail = await getAdminConversationDetail(convId)
      setActiveConv(detail)
      // Clear unread indicator locally
      setConversations(prev =>
        prev.map(c => (c.id === convId ? { ...c, unread_count: 0 } : c))
      )
      // Update stats unread
      setStats(prev => ({
        ...prev,
        unread_count: Math.max(0, prev.unread_count - 1),
      }))
    } catch (err) {
      console.error('Failed to load conversation detail:', err)
    } finally {
      setLoadingThread(false)
    }
  }

  const handleSendReply = async (e) => {
    e.preventDefault()
    if (!replyText.trim() || !activeConv || sendingReply) return

    setSendingReply(true)
    try {
      const newMsg = await sendAdminReply(activeConv.id, replyText.trim())
      setActiveConv(prev => ({
        ...prev,
        status: 'awaiting_user',
        messages: [...(prev.messages || []), newMsg],
      }))
      setReplyText('')
      // Update in conversation list
      setConversations(prev =>
        prev.map(c =>
          c.id === activeConv.id
            ? {
                ...c,
                status: 'awaiting_user',
                last_message: newMsg.message,
                last_message_at: newMsg.created_at,
                last_message_sender_role: 'admin',
              }
            : c
        )
      )
    } catch (err) {
      alert(err.message || 'Failed to send admin reply.')
    } finally {
      setSendingReply(false)
    }
  }

  const handleStatusChange = async (newStatus) => {
    if (!activeConv) return
    try {
      const updated = await updateAdminConversationStatus(activeConv.id, newStatus)
      setActiveConv(prev => ({ ...prev, status: newStatus }))
      setConversations(prev =>
        prev.map(c => (c.id === activeConv.id ? { ...c, status: newStatus } : c))
      )
    } catch (err) {
      alert(err.message || 'Failed to update status.')
    }
  }

  return (
    <div className="space-y-6 animate-fadeIn">

      {/* ── Inbox Header & Filter Pills ───────────────────────────── */}
      <div className="bg-white p-5 rounded-2xl border border-gray-100 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <span>💬</span> Messages &amp; Support Inbox
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Direct student inquiries, material upload requests, and submission questions
            </p>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && loadConversations()}
              placeholder="Search conversations…"
              className="text-xs border border-gray-200 rounded-xl px-3 py-1.5 outline-none focus:ring-2 focus:ring-blue-500 w-48"
            />
            <button
              onClick={() => loadConversations()}
              className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-bold rounded-xl"
            >
              Filter
            </button>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-gray-100">
          {[
            { id: 'all', label: `All (${stats.total})` },
            { id: 'unread', label: `Unread (${stats.unread_count})`, alert: stats.unread_count > 0 },
            { id: 'awaiting_admin', label: `Awaiting Admin (${stats.awaiting_admin})` },
            { id: 'awaiting_user', label: `Awaiting User (${stats.awaiting_user})` },
            { id: 'resolved', label: `Resolved (${stats.resolved})` },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setFilterStatus(tab.id)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 ${
                filterStatus === tab.id
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <span>{tab.label}</span>
              {tab.alert && filterStatus !== tab.id && (
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              )}
            </button>
          ))}

          {/* Category Filter */}
          <select
            value={filterCategory}
            onChange={e => setFilterCategory(e.target.value)}
            className="ml-auto text-xs border border-gray-200 rounded-xl px-3 py-1.5 bg-white text-gray-700 outline-none"
          >
            <option value="">All Categories</option>
            {CATEGORIES.map(c => (
              <option key={c.id} value={c.id}>{c.icon} {c.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Inbox Split View ──────────────────────────────────────── */}
      <div className="bg-white rounded-3xl border border-gray-200/80 shadow-xs overflow-hidden grid grid-cols-1 md:grid-cols-12 min-h-[640px]">

        {/* Left Side: Conversation List (4 cols) */}
        <div className="md:col-span-4 border-r border-gray-100 flex flex-col h-full bg-gray-50/30">
          <div className="p-3.5 border-b border-gray-100 flex items-center justify-between">
            <span className="text-xs font-bold text-gray-700 uppercase tracking-wider">
              Inbox Threads ({conversations.length})
            </span>
            <button
              onClick={() => loadConversations()}
              className="text-xs text-gray-400 hover:text-blue-600 transition"
              title="Refresh"
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
                <p className="text-2xl mb-1">📭</p>
                <p className="font-semibold text-gray-600">No conversations match filter</p>
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
                      <div className="flex items-center gap-2 min-w-0">
                        <UserAvatar user={{ photoURL: c.user_photo_url, display_name: c.user_display_name, email: c.user_email }} size="xs" />
                        <span className="text-xs font-bold text-gray-900 truncate">
                          {c.user_display_name || c.user_email}
                        </span>
                      </div>
                      <span className="text-[10px] text-gray-400 shrink-0">
                        {fmtDate(c.updated_at || c.created_at)}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className="text-xs">{meta.icon}</span>
                      <p className="text-xs font-semibold text-gray-800 truncate">
                        {c.subject}
                      </p>
                    </div>

                    <p className="text-[11px] text-gray-500 truncate mt-0.5">
                      {c.last_message || 'No messages yet'}
                    </p>

                    <div className="flex items-center justify-between gap-2 mt-1">
                      <span className={`text-[10px] font-bold px-2 py-0.2 rounded-md ${
                        c.status === 'resolved' ? 'bg-gray-100 text-gray-600' :
                        c.status === 'awaiting_admin' ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'
                      }`}>
                        {c.status.replace('_', ' ')}
                      </span>

                      {c.unread_count > 0 && (
                        <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.2 rounded-full">
                          {c.unread_count} new
                        </span>
                      )}
                    </div>
                  </button>
                )
              })
            )}
          </div>
        </div>

        {/* Right Side: Active Thread & Student Context (8 cols) */}
        <div className="md:col-span-8 flex flex-col h-full bg-white">
          {activeConv ? (
            <>
              {/* Thread Action Header */}
              <div className="p-4 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-blue-700 uppercase tracking-wider">
                      {activeConv.category.replace('_', ' ')}
                    </span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      activeConv.status === 'resolved' ? 'bg-gray-100 text-gray-700' :
                      activeConv.status === 'awaiting_admin' ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'
                    }`}>
                      {activeConv.status.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>
                  <h2 className="text-base font-bold text-gray-900">
                    {activeConv.subject}
                  </h2>
                </div>

                {/* Status Changer Dropdown */}
                <div className="flex items-center gap-2">
                  <label className="text-xs text-gray-500 font-medium">Status:</label>
                  <select
                    value={activeConv.status}
                    onChange={e => handleStatusChange(e.target.value)}
                    className="text-xs font-bold border border-gray-200 rounded-xl px-3 py-1.5 bg-gray-50 text-gray-800 outline-none"
                  >
                    <option value="open">Open</option>
                    <option value="awaiting_admin">Awaiting Admin</option>
                    <option value="awaiting_user">Awaiting User</option>
                    <option value="resolved">Resolved</option>
                  </select>
                </div>
              </div>

              {/* Student Context Card (Admin Assistant Bar) */}
              {activeConv.student_context && (
                <div className="p-3.5 bg-gray-50/80 border-b border-gray-100 flex flex-wrap items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-3">
                    <UserAvatar
                      user={{
                        photoURL: activeConv.student_context.photo_url,
                        display_name: activeConv.student_context.display_name,
                        email: activeConv.student_context.email,
                      }}
                      size="sm"
                    />
                    <div>
                      <span className="font-bold text-gray-900">{activeConv.student_context.display_name}</span>
                      <span className="text-gray-500 ml-2">({activeConv.student_context.email})</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded-md font-bold bg-white border border-gray-200 text-gray-700">
                      {activeConv.student_context.total_submissions} submissions
                    </span>
                    <span className="px-2 py-0.5 rounded-md font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {activeConv.student_context.published_count} published
                    </span>
                    {activeConv.student_context.pending_count > 0 && (
                      <span className="px-2 py-0.5 rounded-md font-bold bg-amber-50 text-amber-700 border border-amber-200">
                        {activeConv.student_context.pending_count} pending
                      </span>
                    )}
                    {activeConv.student_context.leaderboard_rank && (
                      <span className="px-2 py-0.5 rounded-md font-extrabold bg-amber-100 text-amber-900">
                        🏆 #{activeConv.student_context.leaderboard_rank}
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Linked Submission Reference */}
              {activeConv.linked_submission && (
                <div className="p-3 bg-blue-50/60 border-b border-blue-100 text-xs text-gray-800 flex items-center justify-between">
                  <div>
                    <span className="font-bold text-blue-900">Attached Submission:</span> {activeConv.linked_submission.publisher_name} ({fmtDate(activeConv.linked_submission.created_at)}) &bull; Status: <strong className="uppercase">{activeConv.linked_submission.status}</strong>
                  </div>
                  {activeConv.linked_submission.published_papers?.length > 0 && (
                    <a
                      href={`/papers/${activeConv.linked_submission.published_papers[0].id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-700 font-bold hover:underline"
                    >
                      View Paper →
                    </a>
                  )}
                </div>
              )}

              {/* Message Bubbles Area */}
              <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-4 max-h-[420px]">
                {loadingThread ? (
                  <div className="py-12 flex justify-center">
                    <span className="w-6 h-6 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
                  </div>
                ) : (
                  activeConv.messages?.map(m => {
                    const isAdmin = m.sender_role === 'admin'
                    return (
                      <div
                        key={m.id}
                        className={`flex gap-3 max-w-[85%] ${isAdmin ? 'ml-auto flex-row-reverse' : 'mr-auto flex-row'}`}
                      >
                        {/* Avatar */}
                        <div className="shrink-0 mt-0.5">
                          {isAdmin ? (
                            <div className="w-8 h-8 rounded-full bg-gray-900 text-white font-bold flex items-center justify-center text-xs shadow-xs">
                              🏛️
                            </div>
                          ) : (
                            <UserAvatar
                              user={{
                                photoURL: activeConv.student_context?.photo_url || activeConv.user_photo_url,
                                display_name: m.sender_name,
                              }}
                              size="sm"
                            />
                          )}
                        </div>

                        {/* Content */}
                        <div className="space-y-1">
                          <div className={`flex items-center gap-2 ${isAdmin ? 'justify-end' : 'justify-start'}`}>
                            <span className="text-[11px] font-bold text-gray-700">
                              {isAdmin ? 'TN Board Admin' : m.sender_name}
                            </span>
                            <span className="text-[10px] text-gray-400">
                              {fmtTime(m.created_at)}
                            </span>
                          </div>
                          <div
                            className={`p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed whitespace-pre-wrap shadow-xs ${
                              isAdmin
                                ? 'bg-blue-600 text-white rounded-tr-none'
                                : 'bg-gray-100 text-gray-900 rounded-tl-none border border-gray-200/60'
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

              {/* Admin Reply Box */}
              <div className="p-3 sm:p-4 border-t border-gray-100 bg-gray-50/50">
                <form onSubmit={handleSendReply} className="flex gap-2">
                  <input
                    type="text"
                    value={replyText}
                    onChange={e => setReplyText(e.target.value)}
                    placeholder="Reply as TN Board Admin…"
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
                        <span>Reply</span>
                        <span>✉️</span>
                      </>
                    )}
                  </button>
                </form>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-gray-400">
              <span className="text-4xl mb-3">📬</span>
              <h3 className="text-base font-bold text-gray-700 mb-1">Select a Conversation</h3>
              <p className="text-xs text-gray-400 max-w-sm">
                Select a conversation from the left to view the thread, see the student's submission context, and reply.
              </p>
            </div>
          )}
        </div>

      </div>

    </div>
  )
}
