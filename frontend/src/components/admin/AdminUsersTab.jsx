import { useState, useEffect } from 'react'
import UserAvatar from '../common/UserAvatar'
import { getAdminUsers, getAdminUserDetail } from '../../services/adminUsers'

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

function timeAgo(iso) {
  if (!iso) return '—'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

export default function AdminUsersTab({ onSelectConversation }) {
  const [users, setUsers] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [totalContributors, setTotalContributors] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedUser, setSelectedUser] = useState(null)
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [detailData, setDetailData] = useState(null)

  const loadUsers = async (query = '') => {
    setLoading(true)
    try {
      const res = await getAdminUsers({ search: query, limit: 100 })
      setUsers(res.data || [])
      setTotalCount(res.total_registered_users || res.total || 0)
      setTotalContributors(res.total_contributors || 0)
    } catch (err) {
      console.error('Failed to load admin users:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    loadUsers(search)
  }

  const handleOpenUserDetail = async (userItem) => {
    setSelectedUser(userItem)
    setDetailModalOpen(true)
    setLoadingDetail(true)
    try {
      const detail = await getAdminUserDetail(userItem.firebase_uid)
      setDetailData(detail)
    } catch (err) {
      console.error('Failed to load user detail:', err)
    } finally {
      setLoadingDetail(false)
    }
  }

  return (
    <div className="space-y-6 animate-fadeIn">

      {/* ── Summary & Search Bar ──────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-gray-100 shadow-xs">
        <div>
          <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
            <span>👥</span> User &amp; Contributor Directory
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Overview of all students, community members, and material contributors
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="px-3 py-1.5 bg-blue-50 text-blue-700 text-xs font-bold rounded-xl border border-blue-100">
              🎓 {totalCount} Registered Users
            </span>
            <span className="px-3 py-1.5 bg-emerald-50 text-emerald-700 text-xs font-bold rounded-xl border border-emerald-100">
              ⭐ {totalContributors} Contributors
            </span>
          </div>

          <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search user name or email…"
              className="text-xs border border-gray-200 rounded-xl px-3.5 py-2 outline-none focus:ring-2 focus:ring-blue-500 w-48 sm:w-64"
            />
            <button
              type="submit"
              className="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl shadow-xs transition"
            >
              Search
            </button>
            {search && (
              <button
                type="button"
                onClick={() => {
                  setSearch('')
                  loadUsers('')
                }}
                className="px-2.5 py-2 text-xs font-bold text-gray-400 hover:text-gray-700"
              >
                ✕
              </button>
            )}
          </form>
        </div>
      </div>

      {/* ── Users Table ───────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center gap-3">
            <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
            <p className="text-sm font-medium text-gray-500">Loading user directory…</p>
          </div>
        ) : users.length === 0 ? (
          <div className="text-center py-16 text-gray-400 text-sm">
            <p className="text-3xl mb-2">🔍</p>
            <p className="font-semibold text-gray-700">No users found</p>
            <p className="text-xs text-gray-400 mt-1">Try another search query or clear your filter.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100 text-xs font-semibold text-gray-500 uppercase">
                  <th className="px-5 py-3 text-left">User</th>
                  <th className="px-4 py-3 text-left">Public Name</th>
                  <th className="px-4 py-3 text-left">Submissions</th>
                  <th className="px-4 py-3 text-left">Leaderboard</th>
                  <th className="px-4 py-3 text-left">Last Active</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {users.map(u => (
                  <tr key={u.id || u.firebase_uid} className="hover:bg-gray-50/80 transition-colors">
                    {/* User info */}
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <UserAvatar user={u} size="md" className="border border-gray-200" />
                        <div className="min-w-0">
                          <p className="font-bold text-gray-900 text-xs truncate">{u.display_name || 'Anonymous Student'}</p>
                          <p className="text-[11px] text-gray-500 truncate">{u.email || '—'}</p>
                          <span className="text-[9px] font-mono text-gray-400 truncate block">{u.firebase_uid}</span>
                        </div>
                      </div>
                    </td>

                    {/* Contribution/Public Name */}
                    <td className="px-4 py-3.5">
                      <span className="text-xs font-semibold text-gray-800">
                        {u.display_name || '—'}
                      </span>
                    </td>

                    {/* Submissions summary */}
                    <td className="px-4 py-3.5">
                      <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                        <span className="px-2 py-0.5 rounded-md font-bold bg-gray-100 text-gray-700" title="Total submissions">
                          {u.total_submissions} total
                        </span>
                        {u.published_count > 0 && (
                          <span className="px-2 py-0.5 rounded-md font-bold bg-emerald-100 text-emerald-800" title="Published">
                            {u.published_count} pub
                          </span>
                        )}
                        {u.pending_count > 0 && (
                          <span className="px-2 py-0.5 rounded-md font-bold bg-amber-100 text-amber-800" title="Pending review">
                            {u.pending_count} pend
                          </span>
                        )}
                        {u.rejected_count > 0 && (
                          <span className="px-2 py-0.5 rounded-md font-bold bg-red-50 text-red-700" title="Rejected">
                            {u.rejected_count} rej
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Leaderboard rank */}
                    <td className="px-4 py-3.5">
                      {u.leaderboard_rank ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-amber-50 text-amber-900 border border-amber-200">
                          🏆 #{u.leaderboard_rank}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs font-normal">—</span>
                      )}
                    </td>

                    {/* Last active */}
                    <td className="px-4 py-3.5 text-xs text-gray-500 whitespace-nowrap">
                      {timeAgo(u.last_active_at || u.created_at)}
                    </td>

                    {/* View Details Action */}
                    <td className="px-4 py-3.5 text-right">
                      <button
                        onClick={() => handleOpenUserDetail(u)}
                        className="px-3 py-1.5 bg-gray-100 hover:bg-blue-50 text-gray-700 hover:text-blue-700 text-xs font-bold rounded-xl transition"
                      >
                        View Details →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── User Detail Modal / Drawer ────────────────────────────── */}
      {detailModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fade-in">
          <div className="bg-white rounded-3xl max-w-3xl w-full p-6 sm:p-8 shadow-2xl border border-gray-100 space-y-6 max-h-[90vh] overflow-y-auto">
            
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-gray-100 pb-4">
              <h2 className="text-lg font-extrabold text-gray-900 flex items-center gap-2">
                <span>👤</span> Student Detail View
              </h2>
              <button
                onClick={() => setDetailModalOpen(false)}
                className="w-8 h-8 text-gray-400 hover:text-gray-700 rounded-full hover:bg-gray-100 flex items-center justify-center text-lg"
              >
                ✕
              </button>
            </div>

            {loadingDetail ? (
              <div className="py-16 text-center">
                <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin inline-block" />
                <p className="text-xs text-gray-500 mt-2">Loading student details…</p>
              </div>
            ) : detailData ? (
              <div className="space-y-6">

                {/* Profile Header */}
                <div className="bg-gradient-to-r from-blue-50 via-indigo-50/40 to-white rounded-2xl p-5 border border-blue-100 flex flex-col sm:flex-row items-center sm:items-start gap-4">
                  <UserAvatar user={detailData.user} size="lg" className="border-2 border-white shadow-xs" />
                  <div className="flex-1 text-center sm:text-left space-y-1">
                    <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
                      <h3 className="text-lg font-extrabold text-gray-900">
                        {detailData.user.display_name || 'Contributor'}
                      </h3>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 uppercase">
                        {detailData.user.role}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 font-medium">{detailData.user.email || 'No email'}</p>
                    <p className="text-[10px] text-gray-400 font-mono">UID: {detailData.user.firebase_uid}</p>
                    <div className="flex flex-wrap items-center justify-center sm:justify-start gap-3 pt-1 text-xs text-gray-500">
                      <span>Joined: {fmtDate(detailData.user.created_at)}</span>
                      <span>&bull;</span>
                      <span>Last Active: {timeAgo(detailData.user.last_active_at || detailData.user.created_at)}</span>
                    </div>
                  </div>
                </div>

                {/* Contribution Statistics Grid */}
                <div>
                  <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">
                    Contribution Statistics
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-gray-50 p-3.5 rounded-xl border border-gray-100 text-center">
                      <p className="text-xl font-extrabold text-gray-900">{detailData.user.total_submissions}</p>
                      <p className="text-[11px] text-gray-500 font-medium">Total Submissions</p>
                    </div>
                    <div className="bg-emerald-50 p-3.5 rounded-xl border border-emerald-100 text-center">
                      <p className="text-xl font-extrabold text-emerald-700">{detailData.user.published_count}</p>
                      <p className="text-[11px] text-emerald-800 font-medium">Published Papers</p>
                    </div>
                    <div className="bg-amber-50 p-3.5 rounded-xl border border-amber-100 text-center">
                      <p className="text-xl font-extrabold text-amber-700">{detailData.user.pending_count}</p>
                      <p className="text-[11px] text-amber-800 font-medium">Under Review</p>
                    </div>
                    <div className="bg-red-50 p-3.5 rounded-xl border border-red-100 text-center">
                      <p className="text-xl font-extrabold text-red-700">{detailData.user.rejected_count}</p>
                      <p className="text-[11px] text-red-800 font-medium">Rejected</p>
                    </div>
                  </div>
                </div>

                {/* Leaderboard Position */}
                {detailData.user.leaderboard_rank && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 font-bold text-amber-900">
                      <span>🏆</span> Ranked #{detailData.user.leaderboard_rank} on Community Leaderboard
                    </div>
                    {detailData.user.acceptance_rate != null && (
                      <span className="text-amber-800 font-semibold">
                        Acceptance Rate: {detailData.user.acceptance_rate}%
                      </span>
                    )}
                  </div>
                )}

                {/* Submissions History */}
                <div>
                  <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-2 flex items-center justify-between">
                    <span>Submissions History ({detailData.submissions.length})</span>
                  </h4>
                  {detailData.submissions.length === 0 ? (
                    <p className="text-xs text-gray-400 p-3 bg-gray-50 rounded-xl text-center">No submissions made by this user yet.</p>
                  ) : (
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {detailData.submissions.map(s => (
                        <div key={s.id} className="p-3 bg-gray-50 rounded-xl border border-gray-100 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                                s.status === 'approved' ? 'bg-emerald-100 text-emerald-800' :
                                s.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-800'
                              }`}>
                                {s.status}
                              </span>
                              <span className="font-semibold text-gray-800">{s.publisher_name}</span>
                              <span className="text-gray-400 text-[11px]">{fmtDate(s.created_at)}</span>
                            </div>
                            {s.details && <p className="text-gray-500 text-[11px] mt-0.5">{s.details}</p>}
                            {s.rejection_reason && <p className="text-red-600 text-[11px] mt-0.5">Rejection reason: {s.rejection_reason}</p>}
                          </div>
                          {s.published_papers?.length > 0 && (
                            <Link
                              to={`/papers/${s.published_papers[0].id}`}
                              target="_blank"
                              className="text-blue-600 hover:underline text-[11px] font-bold shrink-0"
                            >
                              View Published Paper →
                            </Link>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Conversations History */}
                <div>
                  <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">
                    Support Inquiries &amp; Messages ({detailData.conversations.length})
                  </h4>
                  {detailData.conversations.length === 0 ? (
                    <p className="text-xs text-gray-400 p-3 bg-gray-50 rounded-xl text-center">User has not opened any support conversations.</p>
                  ) : (
                    <div className="space-y-2 max-h-44 overflow-y-auto">
                      {detailData.conversations.map(c => (
                        <div
                          key={c.id}
                          className="p-3 bg-gray-50 rounded-xl border border-gray-100 text-xs flex items-center justify-between gap-3"
                        >
                          <div className="min-w-0">
                            <p className="font-bold text-gray-900 truncate">{c.subject}</p>
                            <p className="text-gray-500 text-[11px] truncate">{c.last_message || 'No messages'}</p>
                          </div>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold capitalize shrink-0 ${
                            c.status === 'resolved' ? 'bg-gray-200 text-gray-700' :
                            c.status === 'awaiting_admin' ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800'
                          }`}>
                            {c.status.replace('_', ' ')}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

              </div>
            ) : null}

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={() => setDetailModalOpen(false)}
                className="px-5 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-bold rounded-xl"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
