import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import UserAvatar from '../../components/common/UserAvatar'
import AdminUsersTab from '../../components/admin/AdminUsersTab'
import AdminInboxTab from '../../components/admin/AdminInboxTab'
import { getAdminConversationStats } from '../../services/adminConversations'
import { getAdminPapers, getAdminStats, getSearchAnalytics, getRecentUploads, getAdminMe, getAuditLogs } from '../../services/admin'
import { getAnalyticsDashboard } from '../../services/analytics'
import {
  getAdminReports,
  updateAdminReport,
  getPaperRequests,
  updatePaperRequestStatus,
  deleteCommunityPost,
  deleteCommunityComment,
} from '../../services/community'
import { getFirebaseToken } from '../../lib/firebase'

// ── Helpers ───────────────────────────────────────────────────────────────────

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

function maskIp(ip) {
  if (!ip || ip === 'unknown') return '—'
  const parts = ip.split('.')
  if (parts.length === 4) return `${parts[0]}.${parts[1]}.*.*`
  return ip.slice(0, 8) + '…'
}

const ACTION_META = {
  login_success:  { label: 'Logged in',         icon: '🟢', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  login_failure:  { label: 'Failed login',       icon: '🔴', cls: 'bg-red-50 text-red-600 border-red-200' },
  login_blocked:  { label: 'Login blocked',      icon: '🔒', cls: 'bg-orange-50 text-orange-700 border-orange-200' },
  upload:         { label: 'Uploaded paper',     icon: '📤', cls: 'bg-blue-50 text-blue-700 border-blue-200' },
  bulk_upload:    { label: 'Bulk upload',        icon: '📦', cls: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  edit:           { label: 'Edited paper',       icon: '✏️',  cls: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
  delete:         { label: 'Deleted paper',      icon: '🗑️',  cls: 'bg-red-50 text-red-600 border-red-200' },
}

function ActionBadge({ action }) {
  const m = ACTION_META[action] || { label: action, icon: '⚙️', cls: 'bg-gray-50 text-gray-600 border-gray-200' }
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full border ${m.cls}`}>
      <span>{m.icon}</span>{m.label}
    </span>
  )
}

function StatCard({ label, value, color, icon }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 flex items-center gap-4">
      <div className={`w-12 h-12 ${color} rounded-xl flex items-center justify-center text-xl shrink-0`}>{icon}</div>
      <div>
        <p className="text-2xl sm:text-3xl font-extrabold text-gray-900">{value}</p>
        <p className="text-xs sm:text-sm text-gray-500 font-medium mt-0.5">{label}</p>
      </div>
    </div>
  )
}

export default function DashboardPage({ defaultTab = 'overview' }) {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState(defaultTab) // 'overview' | 'users' | 'inbox' | 'analytics' | 'moderation'
  const [inboxUnread, setInboxUnread] = useState(0)

  useEffect(() => {
    setActiveTab(defaultTab)
  }, [defaultTab])

  useEffect(() => {
    getAdminConversationStats()
      .then(res => setInboxUnread(res.unread_count || 0))
      .catch(() => {})
  }, [])

  // Overview state
  const [papers, setPapers]             = useState([])
  const [stats, setStats]               = useState(null)
  const [analytics, setAnalytics]       = useState(null)
  const [recentUploads, setRecentUploads] = useState([])
  const [adminMe, setAdminMe]           = useState(null)
  const [auditLogs, setAuditLogs]       = useState([])
  const [loading, setLoading]           = useState(true)
  const [error, setError]               = useState(null)

  // Analytics state
  const [analyticsData, setAnalyticsData] = useState(null)
  const [analyticsPeriod, setAnalyticsPeriod] = useState('today') // 'today' | '7d' | '30d' | '90d' | 'all_time'
  const [analyticsLoading, setAnalyticsLoading] = useState(false)

  // Moderation state
  const [reports, setReports]           = useState([])
  const [paperRequests, setPaperRequests] = useState([])
  const [moderationLoading, setModerationLoading] = useState(false)

  useEffect(() => {
    Promise.allSettled([
      getAdminPapers(),
      getAdminStats(),
      getSearchAnalytics(),
      getRecentUploads(20),
      getAdminMe(),
      getAuditLogs(30),
    ]).then(([papersR, statsR, analyticsR, recentR, meR, logsR]) => {
      if (papersR.status === 'fulfilled')   setPapers(papersR.value.data)
      if (statsR.status === 'fulfilled')    setStats(statsR.value.data)
      if (analyticsR.status === 'fulfilled') setAnalytics(analyticsR.value.data)
      if (recentR.status === 'fulfilled')  setRecentUploads(recentR.value.data)
      if (meR.status === 'fulfilled')      setAdminMe(meR.value.data)
      if (logsR.status === 'fulfilled')    setAuditLogs(logsR.value.data)
      if (papersR.status === 'rejected')   setError(papersR.reason?.message || 'Failed to load')
    }).finally(() => setLoading(false))
  }, [])

  // Load analytics when analytics tab is clicked or period changes
  useEffect(() => {
    if (activeTab === 'analytics') {
      setAnalyticsLoading(true)
      getFirebaseToken()
        .then(token => getAnalyticsDashboard(token, analyticsPeriod))
        .then(data => setAnalyticsData(data))
        .catch(err => console.error('Analytics load error:', err))
        .finally(() => setAnalyticsLoading(false))
    }
  }, [activeTab, analyticsPeriod])

  // Load moderation reports & requests when moderation tab is clicked
  useEffect(() => {
    if (activeTab === 'moderation') {
      setModerationLoading(true)
      Promise.allSettled([
        getAdminReports(),
        getPaperRequests(null, 1, 50),
      ]).then(([repR, reqR]) => {
        if (repR.status === 'fulfilled') setReports(repR.value || [])
        if (reqR.status === 'fulfilled') setPaperRequests(reqR.value?.data || [])
      }).finally(() => setModerationLoading(false))
    }
  }, [activeTab])

  const handleUpdateReport = async (reportId, status) => {
    try {
      await updateAdminReport(reportId, status)
      setReports(reps => reps.map(r => r.id === reportId ? { ...r, status } : r))
    } catch (err) {
      alert(err.message || 'Failed to update report')
    }
  }

  const handleDeleteReportedContent = async (report) => {
    if (!window.confirm(`Are you sure you want to delete this ${report.target_type}?`)) return
    try {
      if (report.target_type === 'post') {
        await deleteCommunityPost(report.target_id)
      } else if (report.target_type === 'comment') {
        await deleteCommunityComment(report.target_id)
      }
      await updateAdminReport(report.id, 'actioned')
      setReports(reps => reps.map(r => r.id === report.id ? { ...r, status: 'actioned' } : r))
      alert('Content deleted and report marked as actioned.')
    } catch (err) {
      alert(err.message || 'Failed to delete reported content')
    }
  }

  const handleUpdatePaperRequest = async (requestId, status) => {
    let paperId = null
    if (status === 'fulfilled') {
      const input = window.prompt('Enter the published Paper ID that fulfills this request (optional):')
      if (input && !isNaN(parseInt(input, 10))) {
        paperId = parseInt(input, 10)
      }
    }
    try {
      await updatePaperRequestStatus(requestId, status, paperId)
      setPaperRequests(reqs => reqs.map(r => r.id === requestId ? { ...r, status, fulfilled_paper_id: paperId || r.fulfilled_paper_id } : r))
    } catch (err) {
      alert(err.message || 'Failed to update request')
    }
  }

  const recent5 = papers.slice(0, 5)
  const fmt = (n) => n == null ? '0' : Number(n).toLocaleString()

  const currentPeriodStats = analyticsData
    ? (analyticsData[analyticsPeriod] || analyticsData.today || null)
    : null

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto space-y-8">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 tracking-tight">Admin Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">Platform management, users &amp; contributors, messaging, telemetry, and moderation</p>
        </div>
        <div className="flex items-center gap-2.5">
          <UserAvatar user={user} name={user?.displayName || adminMe?.email} size="md" className="border border-gray-200" />
          <div>
            <p className="text-sm font-semibold text-gray-800">{user?.displayName || adminMe?.email || 'Admin'}</p>
            <p className="text-xs text-gray-400">{user?.email || 'Admin Session'}</p>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-gray-200 pb-1">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2.5 rounded-xl text-sm font-bold transition flex items-center gap-2 ${
            activeTab === 'overview'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <span>📊</span> Overview &amp; Papers
        </button>
        <button
          onClick={() => setActiveTab('users')}
          className={`px-4 py-2.5 rounded-xl text-sm font-bold transition flex items-center gap-2 ${
            activeTab === 'users'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <span>👥</span> Users &amp; Contributors
        </button>
        <button
          onClick={() => setActiveTab('inbox')}
          className={`px-4 py-2.5 rounded-xl text-sm font-bold transition flex items-center gap-2 ${
            activeTab === 'inbox'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <span>💬</span> Messages &amp; Inbox
          {inboxUnread > 0 && (
            <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full font-extrabold animate-pulse">
              {inboxUnread}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('analytics')}
          className={`px-4 py-2.5 rounded-xl text-sm font-bold transition flex items-center gap-2 ${
            activeTab === 'analytics'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <span>📈</span> Traffic &amp; Telemetry Analytics
        </button>
        <button
          onClick={() => setActiveTab('moderation')}
          className={`px-4 py-2.5 rounded-xl text-sm font-bold transition flex items-center gap-2 ${
            activeTab === 'moderation'
              ? 'bg-purple-600 text-white shadow-sm'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <span>🛡️</span> Community Moderation
          {reports.filter(r => r.status === 'pending').length > 0 && (
            <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full font-extrabold">
              {reports.filter(r => r.status === 'pending').length}
            </span>
          )}
        </button>
      </div>

      {/* ── TAB 1: OVERVIEW ── */}
      {activeTab === 'overview' && (
        <div className="space-y-8 animate-fadeIn">
          {/* Primary Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard label="Total Papers"    value={fmt(stats?.total_papers)}    color="bg-blue-50"    icon="📄" />
            <StatCard label="Total Downloads" value={fmt(stats?.total_downloads)} color="bg-violet-50"  icon="⬇️" />
            <StatCard label="Total Subjects"  value={fmt(stats?.total_subjects)}  color="bg-emerald-50" icon="📚" />
            <StatCard label="Total Classes"   value={fmt(stats?.total_classes)}   color="bg-orange-50"  icon="🎓" />
          </div>

          {/* Secondary Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-gray-900 text-white rounded-2xl p-5 shadow-sm">
              <p className="text-3xl font-extrabold text-blue-400">{fmt(stats?.question_papers)}</p>
              <p className="font-semibold mt-1">Question Papers</p>
              <p className="text-gray-400 text-xs mt-0.5">Uploaded QP records</p>
            </div>
            <div className="bg-gray-900 text-white rounded-2xl p-5 shadow-sm">
              <p className="text-3xl font-extrabold text-emerald-400">{fmt(stats?.answer_keys)}</p>
              <p className="font-semibold mt-1">Answer Keys</p>
              <p className="text-gray-400 text-xs mt-0.5">Uploaded answer keys</p>
            </div>
            <div className="bg-gray-900 text-white rounded-2xl p-5 shadow-sm">
              <p className="text-3xl font-extrabold text-amber-400">{fmt(stats?.visible_papers)}</p>
              <p className="font-semibold mt-1">Visible Papers</p>
              <p className="text-gray-400 text-xs mt-0.5">Published to students</p>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap gap-3">
            <Link to="/admin/papers" className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 border border-blue-200 text-blue-700 text-sm font-semibold rounded-xl hover:bg-blue-100 transition-colors shadow-2xs">
              📦 Manage Papers &amp; Bulk Upload
            </Link>
            <Link to="/admin/content-status" className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm font-semibold rounded-xl hover:bg-emerald-100 transition-colors shadow-2xs">
              📊 Class &amp; Subject Coverage
            </Link>
          </div>

          {/* Recent Uploads & Popular Searches */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                <h2 className="font-bold text-gray-800">Recent Papers</h2>
                <Link to="/admin/papers" className="text-sm text-blue-600 hover:text-blue-800 font-medium">View all →</Link>
              </div>
              {loading ? (
                <div className="flex items-center justify-center py-16">
                  <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
                </div>
              ) : papers.length === 0 ? (
                <div className="text-center py-12 text-gray-400 text-sm">No papers uploaded yet.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50 border-b border-gray-100 text-xs font-semibold text-gray-500 uppercase">
                        <th className="px-5 py-3 text-left">Title</th>
                        <th className="px-4 py-3 text-left">Type</th>
                        <th className="px-4 py-3 text-left">Exam</th>
                        <th className="px-4 py-3 text-left">Year</th>
                        <th className="px-4 py-3 text-left">DLs</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {recent5.map(p => (
                        <tr key={p.id} className="hover:bg-gray-50">
                          <td className="px-5 py-3 font-medium text-gray-800 max-w-xs truncate">{p.title}</td>
                          <td className="px-4 py-3">
                            <span className={`badge ${p.paper_type === 'question' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'}`}>
                              {p.paper_type === 'question' ? 'Q Paper' : 'Answer Key'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-500 text-xs">{p.exam_type}</td>
                          <td className="px-4 py-3 text-gray-500">{p.year}</td>
                          <td className="px-4 py-3 text-gray-500 font-mono text-xs">{p.download_count ?? 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100">
                <h2 className="font-bold text-gray-800">🔍 Popular Searches</h2>
                <p className="text-xs text-gray-400 mt-0.5">User query terms</p>
              </div>
              {!analytics || analytics.popular_searches.length === 0 ? (
                <div className="text-center py-12 text-gray-400 text-sm">No searches yet.</div>
              ) : (
                <div className="divide-y divide-gray-50">
                  {analytics.popular_searches.slice(0, 8).map((item, i) => (
                    <div key={item.term} className="flex items-center justify-between px-6 py-3">
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="text-xs font-bold text-gray-300 w-4 shrink-0">{i + 1}</span>
                        <span className="text-sm text-gray-700 font-medium truncate capitalize">{item.term}</span>
                      </div>
                      <span className="ml-3 shrink-0 text-xs font-semibold bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">{item.count}×</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Audit Logs */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <div>
                <h2 className="font-bold text-gray-800">🔐 Admin Actions Log</h2>
                <p className="text-xs text-gray-400 mt-0.5">Last 30 recorded security actions</p>
              </div>
            </div>
            {auditLogs.length === 0 ? (
              <div className="text-center py-12 text-gray-400 text-sm">No actions logged yet.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-100 text-xs font-semibold text-gray-500 uppercase">
                      <th className="px-5 py-3 text-left">Action</th>
                      <th className="px-4 py-3 text-left">Details</th>
                      <th className="px-4 py-3 text-left">IP</th>
                      <th className="px-4 py-3 text-left">When</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {auditLogs.map(log => (
                      <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-5 py-3 whitespace-nowrap"><ActionBadge action={log.action} /></td>
                        <td className="px-4 py-3 text-gray-600 max-w-xs truncate text-xs font-medium">
                          {log.target_details?.title || log.target_details?.identifier || (log.target_paper_id ? `Paper ID ${log.target_paper_id}` : '—')}
                        </td>
                        <td className="px-4 py-3 text-gray-400 font-mono text-xs whitespace-nowrap">{maskIp(log.ip_address)}</td>
                        <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">{timeAgo(log.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── TAB: USERS & CONTRIBUTORS ── */}
      {activeTab === 'users' && <AdminUsersTab />}

      {/* ── TAB: MESSAGES & INBOX ── */}
      {activeTab === 'inbox' && <AdminInboxTab />}

      {/* ── TAB 2: ANALYTICS & TELEMETRY ── */}
      {activeTab === 'analytics' && (
        <div className="space-y-8 animate-fadeIn">
          {/* Timeframe Filter Buttons */}
          <div className="flex items-center justify-between flex-wrap gap-3 bg-white p-4 rounded-2xl border border-gray-100 shadow-sm">
            <div>
              <h2 className="text-base font-bold text-gray-900">Traffic &amp; Telemetry Analytics</h2>
              <p className="text-xs text-gray-400">Real-time visitor views, downloads, search terms, and interactions</p>
            </div>
            <div className="flex items-center gap-1.5 bg-gray-100 p-1 rounded-xl">
              {[
                { id: 'today', label: 'Today' },
                { id: '7d', label: '7 Days' },
                { id: '30d', label: '30 Days' },
                { id: '90d', label: '90 Days' },
                { id: 'all_time', label: 'All Time' },
              ].map(period => (
                <button
                  key={period.id}
                  onClick={() => setAnalyticsPeriod(period.id)}
                  className={`px-3 py-1.5 text-xs font-bold rounded-lg transition ${
                    analyticsPeriod === period.id
                      ? 'bg-white text-indigo-700 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {period.label}
                </button>
              ))}
            </div>
          </div>

          {analyticsLoading ? (
            <div className="py-20 flex flex-col items-center justify-center gap-3">
              <span className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
              <p className="text-sm font-medium text-gray-500">Aggregating telemetry analytics…</p>
            </div>
          ) : !currentPeriodStats ? (
            <div className="text-center py-16 bg-white rounded-2xl border border-gray-100">
              <p className="text-3xl mb-2">📊</p>
              <p className="text-sm font-bold text-gray-800">No telemetry events recorded yet</p>
              <p className="text-xs text-gray-400 mt-1">Events will appear here as users browse, search, and download papers.</p>
            </div>
          ) : (
            <>
              {/* Telemetry Stat Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm text-center">
                  <span className="text-2xl mb-1 block">👥</span>
                  <p className="text-xl font-extrabold text-indigo-600">{fmt(currentPeriodStats.visitors)}</p>
                  <p className="text-xs text-gray-500 font-medium">Visitors</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm text-center">
                  <span className="text-2xl mb-1 block">👁️</span>
                  <p className="text-xl font-extrabold text-blue-600">{fmt(currentPeriodStats.page_views)}</p>
                  <p className="text-xs text-gray-500 font-medium">Page Views</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm text-center">
                  <span className="text-2xl mb-1 block">📄</span>
                  <p className="text-xl font-extrabold text-emerald-600">{fmt(currentPeriodStats.paper_views)}</p>
                  <p className="text-xs text-gray-500 font-medium">Paper Views</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm text-center">
                  <span className="text-2xl mb-1 block">⬇️</span>
                  <p className="text-xl font-extrabold text-violet-600">{fmt(currentPeriodStats.downloads)}</p>
                  <p className="text-xs text-gray-500 font-medium">Downloads</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm text-center">
                  <span className="text-2xl mb-1 block">🔍</span>
                  <p className="text-xl font-extrabold text-amber-600">{fmt(currentPeriodStats.searches)}</p>
                  <p className="text-xs text-gray-500 font-medium">Searches</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm text-center">
                  <span className="text-2xl mb-1 block">👍</span>
                  <p className="text-xl font-extrabold text-pink-600">{fmt(currentPeriodStats.likes)}</p>
                  <p className="text-xs text-gray-500 font-medium">Likes &amp; Replies</p>
                </div>
              </div>

              {/* Daily Trend Chart (CSS Bar Chart) */}
              {analyticsData.daily_trends && analyticsData.daily_trends.length > 0 && (
                <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm space-y-4">
                  <h3 className="font-bold text-gray-800 text-sm flex items-center gap-2">
                    <span>📈</span> Daily Activity Trends (Last {analyticsData.daily_trends.length} Days)
                  </h3>
                  <div className="h-44 flex items-end gap-2 pt-6 overflow-x-auto">
                    {analyticsData.daily_trends.map(day => {
                      const maxVal = Math.max(...analyticsData.daily_trends.map(d => d.page_views || 1), 10)
                      const pct = Math.min(100, Math.max(8, (day.page_views / maxVal) * 100))
                      return (
                        <div key={day.date} className="flex-1 min-w-[28px] flex flex-col items-center gap-1 group relative">
                          <div className="w-full bg-indigo-50 hover:bg-indigo-100 rounded-t-lg transition-all relative flex flex-col justify-end" style={{ height: `${pct}%` }}>
                            <div className="w-full bg-indigo-600 rounded-t-lg" style={{ height: `${Math.min(100, (day.downloads / (day.page_views || 1)) * 100)}%` }} />
                          </div>
                          <span className="text-[9px] text-gray-400 truncate w-full text-center">
                            {day.date.slice(5)}
                          </span>
                          {/* Tooltip */}
                          <div className="hidden group-hover:block absolute bottom-full mb-2 bg-gray-900 text-white text-[10px] p-2 rounded-lg shadow-lg whitespace-nowrap z-20">
                            <p className="font-bold">{day.date}</p>
                            <p>Views: {day.page_views} | DLs: {day.downloads}</p>
                            <p>Visitors: {day.visitors}</p>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-500 pt-2 border-t border-gray-50 justify-end">
                    <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-indigo-100 rounded" /> Page Views</span>
                    <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-indigo-600 rounded" /> Downloads</span>
                  </div>
                </div>
              )}

              {/* Breakdown Grids */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Top Viewed Papers */}
                <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 space-y-3">
                  <h4 className="font-bold text-gray-800 text-xs uppercase tracking-wide">🏆 Top Viewed Papers</h4>
                  <div className="divide-y divide-gray-50 text-xs">
                    {analyticsData.top_viewed_papers?.slice(0, 6).map((p, i) => (
                      <div key={p.id} className="py-2 flex items-center justify-between gap-2">
                        <span className="truncate text-gray-700 font-medium">{i + 1}. {p.name}</span>
                        <span className="font-bold text-indigo-600 shrink-0">{p.count}</span>
                      </div>
                    ))}
                    {(!analyticsData.top_viewed_papers || analyticsData.top_viewed_papers.length === 0) && (
                      <p className="text-gray-400 py-3 text-center">No paper views</p>
                    )}
                  </div>
                </div>

                {/* Top Downloaded Papers */}
                <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 space-y-3">
                  <h4 className="font-bold text-gray-800 text-xs uppercase tracking-wide">⬇️ Top Downloads</h4>
                  <div className="divide-y divide-gray-50 text-xs">
                    {analyticsData.top_downloaded_papers?.slice(0, 6).map((p, i) => (
                      <div key={p.id} className="py-2 flex items-center justify-between gap-2">
                        <span className="truncate text-gray-700 font-medium">{i + 1}. {p.name}</span>
                        <span className="font-bold text-emerald-600 shrink-0">{p.count}</span>
                      </div>
                    ))}
                    {(!analyticsData.top_downloaded_papers || analyticsData.top_downloaded_papers.length === 0) && (
                      <p className="text-gray-400 py-3 text-center">No downloads</p>
                    )}
                  </div>
                </div>

                {/* Top Classes & Subjects */}
                <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 space-y-3">
                  <h4 className="font-bold text-gray-800 text-xs uppercase tracking-wide">📚 Popular Classes</h4>
                  <div className="divide-y divide-gray-50 text-xs">
                    {analyticsData.top_classes?.map((c, i) => (
                      <div key={c.id} className="py-2 flex items-center justify-between gap-2">
                        <span className="text-gray-700 font-medium">{c.name}</span>
                        <span className="font-bold text-blue-600">{c.count}</span>
                      </div>
                    ))}
                    {(!analyticsData.top_classes || analyticsData.top_classes.length === 0) && (
                      <p className="text-gray-400 py-3 text-center">No class data</p>
                    )}
                  </div>
                </div>

                {/* Top Search Queries */}
                <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 space-y-3">
                  <h4 className="font-bold text-gray-800 text-xs uppercase tracking-wide">🔍 Top Searches</h4>
                  <div className="divide-y divide-gray-50 text-xs">
                    {analyticsData.top_searches?.slice(0, 6).map((s, i) => (
                      <div key={s.name} className="py-2 flex items-center justify-between gap-2">
                        <span className="truncate text-gray-700 font-medium capitalize">{s.name}</span>
                        <span className="font-bold text-amber-600 shrink-0">{s.count}×</span>
                      </div>
                    ))}
                    {(!analyticsData.top_searches || analyticsData.top_searches.length === 0) && (
                      <p className="text-gray-400 py-3 text-center">No searches</p>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── TAB 3: COMMUNITY MODERATION ── */}
      {activeTab === 'moderation' && (
        <div className="space-y-8 animate-fadeIn">
          {/* Moderation Section 1: User Content Reports */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-gray-800 flex items-center gap-2">
                  <span>🚩</span> Reported Content Review
                </h3>
                <p className="text-xs text-gray-400">Reports submitted by users for inappropriate posts or comments</p>
              </div>
            </div>

            {moderationLoading ? (
              <div className="py-12 flex justify-center"><span className="w-6 h-6 border-2 border-purple-200 border-t-purple-600 rounded-full animate-spin" /></div>
            ) : reports.length === 0 ? (
              <div className="text-center py-12 text-gray-400 text-sm">No reported content at this time. 🎉</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-100 text-xs font-semibold text-gray-500 uppercase">
                      <th className="px-5 py-3 text-left">Type</th>
                      <th className="px-4 py-3 text-left">Reason / Context</th>
                      <th className="px-4 py-3 text-left">Status</th>
                      <th className="px-4 py-3 text-left">Date</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {reports.map(rep => (
                      <tr key={rep.id} className="hover:bg-gray-50">
                        <td className="px-5 py-3 font-bold text-xs uppercase text-gray-700">
                          {rep.target_type}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-800 max-w-sm">
                          <p className="font-semibold text-red-600">{rep.reason}</p>
                          <p className="text-gray-400 text-[11px] truncate">Target ID: {rep.target_id}</p>
                        </td>
                        <td className="px-4 py-3 text-xs font-bold">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] ${
                            rep.status === 'pending' ? 'bg-amber-100 text-amber-800' :
                            rep.status === 'actioned' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'
                          }`}>
                            {rep.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-400">{fmtDate(rep.created_at)}</td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {rep.status === 'pending' && (
                              <>
                                <button
                                  onClick={() => handleUpdateReport(rep.id, 'dismissed')}
                                  className="px-2.5 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold rounded-lg"
                                >
                                  Dismiss
                                </button>
                                <button
                                  onClick={() => handleDeleteReportedContent(rep)}
                                  className="px-2.5 py-1 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-lg shadow-2xs"
                                >
                                  Delete Content
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Moderation Section 2: Paper Requests */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-gray-800 flex items-center gap-2">
                  <span>📄</span> Community Paper Requests
                </h3>
                <p className="text-xs text-gray-400">Papers requested by students and teachers</p>
              </div>
            </div>

            {moderationLoading ? (
              <div className="py-12 flex justify-center"><span className="w-6 h-6 border-2 border-purple-200 border-t-purple-600 rounded-full animate-spin" /></div>
            ) : paperRequests.length === 0 ? (
              <div className="text-center py-12 text-gray-400 text-sm">No paper requests submitted yet.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-100 text-xs font-semibold text-gray-500 uppercase">
                      <th className="px-5 py-3 text-left">Class &amp; Subject</th>
                      <th className="px-4 py-3 text-left">Exam / Year / District</th>
                      <th className="px-4 py-3 text-left">Requester</th>
                      <th className="px-4 py-3 text-left">Status</th>
                      <th className="px-4 py-3 text-right">Moderator Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {paperRequests.map(req => (
                      <tr key={req.id} className="hover:bg-gray-50">
                        <td className="px-5 py-3 text-xs font-bold text-gray-800">
                          <p>{req.class_name}</p>
                          <p className="text-gray-500 font-normal">{req.subject_name}</p>
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-600">
                          <p className="font-semibold">{req.exam_type} {req.year}</p>
                          {req.district && <p className="text-gray-400 text-[11px]">📍 {req.district}</p>}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-600">
                          <p className="font-medium">{req.requester_name}</p>
                          <p className="text-gray-400 text-[11px]">{fmtDate(req.created_at)}</p>
                        </td>
                        <td className="px-4 py-3 text-xs font-bold">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] ${
                            req.status === 'fulfilled' ? 'bg-emerald-100 text-emerald-800' :
                            req.status === 'in_progress' ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-700'
                          }`}>
                            {req.status.replace('_', ' ').toUpperCase()}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {req.status !== 'fulfilled' && (
                              <button
                                onClick={() => handleUpdatePaperRequest(req.id, 'fulfilled')}
                                className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow-2xs"
                              >
                                ✓ Mark Fulfilled
                              </button>
                            )}
                            {req.status === 'open' && (
                              <button
                                onClick={() => handleUpdatePaperRequest(req.id, 'in_progress')}
                                className="px-2.5 py-1 bg-amber-50 hover:bg-amber-100 text-amber-800 text-xs font-semibold rounded-lg border border-amber-200"
                              >
                                In Progress
                              </button>
                            )}
                            {req.status !== 'closed' && (
                              <button
                                onClick={() => handleUpdatePaperRequest(req.id, 'closed')}
                                className="px-2.5 py-1 bg-gray-100 hover:bg-gray-200 text-gray-600 text-xs font-semibold rounded-lg"
                              >
                                Close
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  )
}
