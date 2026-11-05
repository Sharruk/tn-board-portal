import { useEffect, useState, useRef, useCallback } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { useAdminAuth } from '../../contexts/AdminAuthContext'
import { getTeamChatMessages, sendTeamChatMessage } from '../../services/adminTeamChat'

function fmtTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
}

function fmtDateDivider(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const today = new Date()
  if (d.toDateString() === today.toDateString()) return 'Today'
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday'
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function AdminTeamChatTab() {
  const { user } = useAuth()
  const { isSuperAdmin } = useAdminAuth()

  const [messages, setMessages] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)

  const [inputText, setInputText] = useState('')
  const [sending, setSending] = useState(false)

  const messagesEndRef = useRef(null)
  const chatContainerRef = useRef(null)
  const pollingTimerRef = useRef(null)
  const isFirstLoadRef = useRef(true)

  const scrollToBottom = useCallback((behavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior })
  }, [])

  const fetchMessages = useCallback(async (isBackground = false) => {
    if (!isBackground) {
      if (isFirstLoadRef.current) setLoading(true)
      else setRefreshing(true)
    }
    setError(null)
    try {
      const res = await getTeamChatMessages({ limit: 100, offset: 0 })
      setMessages(res.data || [])
      setTotal(res.total || 0)
    } catch (err) {
      if (!isBackground) {
        setError(err.message || 'Failed to load team chat messages.')
      }
    } finally {
      setLoading(false)
      setRefreshing(false)
      if (isFirstLoadRef.current) {
        isFirstLoadRef.current = false
        setTimeout(() => scrollToBottom('auto'), 100)
      }
    }
  }, [scrollToBottom])

  // Initial fetch and 6-second polling with cleanup on unmount
  useEffect(() => {
    fetchMessages(false)

    pollingTimerRef.current = setInterval(() => {
      fetchMessages(true)
    }, 6000)

    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current)
      }
    }
  }, [fetchMessages])

  // Auto scroll on new messages
  useEffect(() => {
    if (!loading && messages.length > 0) {
      scrollToBottom('smooth')
    }
  }, [messages.length, loading, scrollToBottom])

  const handleSend = async (e) => {
    if (e) e.preventDefault()
    const trimmed = inputText.trim()
    if (!trimmed || sending) return

    setSending(true)
    setError(null)
    try {
      const newMsg = await sendTeamChatMessage(trimmed)
      setInputText('')
      setMessages((prev) => [...prev, newMsg])
      setTotal((t) => t + 1)
      setTimeout(() => scrollToBottom('smooth'), 50)
    } catch (err) {
      setError(err.message || 'Failed to send message.')
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="space-y-4 animate-fadeIn">
      {/* ── Header Card ────────────────────────────────────────────── */}
      <div className="bg-white rounded-3xl border border-gray-200/80 p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="text-2xl">📢</span>
            <h1 className="text-xl font-extrabold text-gray-900 tracking-tight">Admin Team Chat</h1>
            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/80">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live Sync
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Shared internal channel for Admins &amp; Super Admin. Completely private to the admin team.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchMessages(false)}
            disabled={refreshing || loading}
            className="px-3.5 py-2 rounded-xl text-xs font-bold text-gray-600 bg-gray-100 hover:bg-gray-200/70 transition flex items-center gap-1.5 disabled:opacity-50"
            title="Refresh messages"
          >
            <span className={refreshing ? 'animate-spin inline-block' : ''}>🔄</span>
            {refreshing ? 'Syncing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* ── Error Banner ────────────────────────────────────────────── */}
      {error && (
        <div className="p-3.5 rounded-2xl bg-red-50 border border-red-200 text-red-700 text-xs font-semibold flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
          <button onClick={() => fetchMessages(false)} className="underline hover:no-underline font-bold">
            Retry
          </button>
        </div>
      )}

      {/* ── Chat Container ─────────────────────────────────────────── */}
      <div className="bg-white rounded-3xl border border-gray-200/80 shadow-xs overflow-hidden flex flex-col h-[680px]">
        {/* Messages List Area */}
        <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 bg-gray-50/40">
          {loading ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <span className="w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full animate-spin inline-block mb-3" />
              <p className="text-xs font-bold text-gray-500">Loading team chat messages…</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 max-w-md mx-auto">
              <div className="w-16 h-16 rounded-3xl bg-blue-50 text-blue-600 flex items-center justify-center text-3xl mb-3 shadow-inner">
                📢
              </div>
              <h3 className="text-sm font-bold text-gray-800">No team chat messages yet</h3>
              <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                This is your shared internal admin board. Type a message below to coordinate paper uploads, reviews, or platform notices with your team.
              </p>
            </div>
          ) : (
            messages.map((m, idx) => {
              const isMe = m.sender_firebase_uid === user?.uid
              const isSuper = m.sender_role === 'SUPER_ADMIN'

              // Show date divider if previous message is from a different day
              const prevMsg = idx > 0 ? messages[idx - 1] : null
              const showDateDivider =
                !prevMsg ||
                new Date(prevMsg.created_at).toDateString() !== new Date(m.created_at).toDateString()

              return (
                <div key={m.id || idx} className="space-y-3">
                  {showDateDivider && (
                    <div className="flex items-center justify-center my-3">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 bg-gray-100/90 px-3 py-1 rounded-full border border-gray-200/60 shadow-2xs">
                        {fmtDateDivider(m.created_at)}
                      </span>
                    </div>
                  )}

                  <div
                    className={`flex gap-3 max-w-[85%] sm:max-w-[75%] ${
                      isMe ? 'ml-auto flex-row-reverse' : 'mr-auto'
                    }`}
                  >
                    {/* Avatar */}
                    <div className="shrink-0 mt-0.5">
                      {isMe ? (
                        <div
                          className={`w-8 h-8 rounded-full font-bold flex items-center justify-center text-xs shadow-xs text-white ${
                            isSuperAdmin ? 'bg-amber-600' : 'bg-blue-600'
                          }`}
                          title="You"
                        >
                          {isSuperAdmin ? '👑' : '🛡️'}
                        </div>
                      ) : (
                        <div
                          className={`w-8 h-8 rounded-full font-bold flex items-center justify-center text-xs shadow-xs text-white ${
                            isSuper ? 'bg-amber-600' : 'bg-indigo-600'
                          }`}
                          title={`${m.sender_name} (${isSuper ? 'Super Admin' : 'Admin'})`}
                        >
                          {isSuper ? '👑' : '🛡️'}
                        </div>
                      )}
                    </div>

                    {/* Message Bubble & Metadata */}
                    <div className="space-y-1 min-w-0">
                      <div className={`flex items-center gap-2 ${isMe ? 'justify-end' : 'justify-start'}`}>
                        <span className="text-[11px] font-bold text-gray-900 truncate">
                          {isMe ? 'You' : m.sender_name}
                        </span>

                        {/* Role Badge */}
                        <span
                          className={`text-[9px] font-extrabold uppercase px-1.5 py-0.2 rounded-md border tracking-wider ${
                            isSuper
                              ? 'bg-amber-50 text-amber-700 border-amber-300'
                              : 'bg-indigo-50 text-indigo-700 border-indigo-200'
                          }`}
                        >
                          {isSuper ? 'Super Admin' : 'Admin'}
                        </span>

                        <span className="text-[10px] text-gray-400 shrink-0">
                          {fmtTime(m.created_at)}
                        </span>
                      </div>

                      <div
                        className={`p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed whitespace-pre-wrap shadow-xs break-words ${
                          isMe
                            ? 'bg-blue-600 text-white rounded-tr-none'
                            : 'bg-white text-gray-900 rounded-tl-none border border-gray-200/80 shadow-2xs'
                        }`}
                      >
                        {m.message}
                      </div>
                    </div>
                  </div>
                </div>
              )
            })
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* ── Input Box ────────────────────────────────────────────── */}
        <div className="p-3 sm:p-4 border-t border-gray-100 bg-white">
          <form onSubmit={handleSend} className="space-y-2">
            <div className="relative flex items-end gap-2 bg-gray-50 border border-gray-200 rounded-2xl p-2 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent transition-all">
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your message to the Admin Team… (Press Enter to send, Shift+Enter for new line)"
                rows={2}
                maxLength={5000}
                disabled={sending}
                className="w-full bg-transparent border-0 text-xs sm:text-sm text-gray-900 placeholder:text-gray-400 focus:ring-0 p-1.5 resize-none leading-relaxed outline-none"
              />

              <button
                type="submit"
                disabled={!inputText.trim() || sending}
                className="shrink-0 px-4 py-2.5 rounded-xl bg-blue-600 text-white font-bold text-xs hover:bg-blue-700 transition disabled:opacity-40 disabled:hover:bg-blue-600 shadow-sm flex items-center gap-1.5"
              >
                {sending ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin inline-block" />
                    <span>Sending…</span>
                  </>
                ) : (
                  <>
                    <span>Send</span>
                    <span>🚀</span>
                  </>
                )}
              </button>
            </div>

            <div className="flex items-center justify-between px-1 text-[11px] text-gray-400">
              <span>Shift + Enter for new line • Enter to send</span>
              <span>{inputText.length} / 5000</span>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

