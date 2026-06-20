import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getAdminPapers, getAdminStats, getSearchAnalytics, getRecentUploads, getAdminMe, getAuditLogs } from '../../services/admin'

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

// ── Sub-components ────────────────────────────────────────────────────────────

function StatCard({ label, value, color, icon }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex items-center gap-4">
      <div className={`w-12 h-12 ${color} rounded-xl flex items-center justify-center text-xl shrink-0`}>{icon}</div>
      <div>
        <p className="text-3xl font-extrabold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500 font-medium mt-0.5">{label}</p>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [papers, setPapers]       = useState([])
  const [stats, setStats]         = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [recentUploads, setRecentUploads] = useState([])
  const [adminMe, setAdminMe]     = useState(null)
  const [auditLogs, setAuditLogs] = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)

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

  const recent5 = papers.slice(0, 5)
  const fmt = (n) => n == null ? '—' : Number(n).toLocaleString()

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto">

      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-extrabold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">Overview of the TN Board Learning Platform</p>
        </div>
        {adminMe && (
          <div className="hidden sm:flex flex-col items-end text-right">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0">
                {(adminMe.email || adminMe.username || 'A')[0].toUpperCase()}
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-800">{adminMe.email || adminMe.username}</p>
                {adminMe.last_login_at ? (
                  <p className="text-xs text-gray-400">Last login: {fmtDate(adminMe.last_login_at)}</p>
                ) : (
                  <p className="text-xs text-gray-400">First session</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Primary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Papers"    value={fmt(stats?.total_papers)}    color="bg-blue-50"    icon="📄" />
        <StatCard label="Total Downloads" value={fmt(stats?.total_downloads)} color="bg-violet-50"  icon="⬇️" />
        <StatCard label="Total Subjects"  value={fmt(stats?.total_subjects)}  color="bg-emerald-50" icon="📚" />
        <StatCard label="Total Classes"   value={fmt(stats?.total_classes)}   color="bg-orange-50"  icon="🎓" />
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-gray-900 text-white rounded-2xl p-5">
          <p className="text-3xl font-extrabold text-blue-400">{fmt(stats?.question_papers)}</p>
          <p className="font-semibold mt-1">Question Papers</p>
          <p className="text-gray-400 text-xs mt-0.5">Uploaded question papers</p>
        </div>
        <div className="bg-gray-900 text-white rounded-2xl p-5">
          <p className="text-3xl font-extrabold text-emerald-400">{fmt(stats?.answer_keys)}</p>
          <p className="font-semibold mt-1">Answer Keys</p>
          <p className="text-gray-400 text-xs mt-0.5">Uploaded answer keys</p>
        </div>
        <div className="bg-gray-900 text-white rounded-2xl p-5">
          <p className="text-3xl font-extrabold text-amber-400">{fmt(stats?.visible_papers)}</p>
          <p className="font-semibold mt-1">Visible Papers</p>
          <p className="text-gray-400 text-xs mt-0.5">Published to students</p>
        </div>
      </div>

      {/* Quick links */}
      <div className="flex flex-wrap gap-3 mb-8">
        <Link to="/admin/papers" className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 border border-blue-200 text-blue-700 text-sm font-semibold rounded-xl hover:bg-blue-100 transition-colors">
          📦 Bulk Upload
        </Link>
        <Link to="/admin/content-status" className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm font-semibold rounded-xl hover:bg-emerald-100 transition-colors">
          📊 Content Status
        </Link>
      </div>

      {/* Row: Recent Papers + Popular Searches */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">

        {/* Recent Papers */}
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <h2 className="font-bold text-gray-800">Recent Papers</h2>
            <Link to="/admin/papers" className="text-sm text-blue-600 hover:text-blue-800 font-medium">View all →</Link>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
            </div>
          ) : error ? (
            <p className="text-center py-12 text-red-500 text-sm">{error}</p>
          ) : papers.length === 0 ? (
            <div className="text-center py-16 px-6">
              <div className="text-4xl mb-3">📭</div>
              <p className="text-gray-500 font-medium">No papers uploaded yet.</p>
              <Link to="/admin/papers" className="mt-4 inline-block btn-primary text-sm px-4 py-2">Upload First Paper</Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    {['Title', 'Type', 'Exam', 'Year', 'DLs'].map(h => (
                      <th key={h} className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                    ))}
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

        {/* Popular Searches */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="font-bold text-gray-800">🔍 Popular Searches</h2>
            <p className="text-xs text-gray-400 mt-0.5">In-session search terms</p>
          </div>
          {!analytics || analytics.popular_searches.length === 0 ? (
            <div className="text-center py-12 px-4">
              <div className="text-3xl mb-2">📊</div>
              <p className="text-gray-400 text-sm">No searches yet.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {analytics.popular_searches.slice(0, 10).map((item, i) => (
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

      {/* Recent Upload Activity */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden mb-6">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="font-bold text-gray-800">📥 Recent Upload Activity</h2>
            <p className="text-xs text-gray-400 mt-0.5">Latest 20 uploads</p>
          </div>
          <Link to="/admin/papers" className="text-sm text-blue-600 hover:text-blue-800 font-medium">Manage →</Link>
        </div>
        {recentUploads.length === 0 ? (
          <div className="text-center py-12 px-4">
            <div className="text-3xl mb-2">📭</div>
            <p className="text-gray-400 text-sm">No uploads yet.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  {['Paper Title', 'Class / Subject', 'Exam Type', 'Upload Date', 'Uploaded By'].map(h => (
                    <th key={h} className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {recentUploads.map(p => (
                  <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3 font-medium text-gray-800 max-w-xs">
                      <p className="truncate">{p.title}</p>
                      <span className={`badge text-xs mt-0.5 ${p.paper_type === 'question' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'}`}>
                        {p.paper_type === 'question' ? 'Q Paper' : 'Answer Key'}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <p className="text-gray-700 font-medium">{p.class_name}</p>
                      <p className="text-gray-400 text-xs">{p.subject_name}</p>
                    </td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap text-xs">{p.exam_type} · {p.year}</td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap text-xs">{fmtDate(p.created_at)}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-600">
                        <span className="w-5 h-5 bg-blue-600 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0">
                          {adminMe ? (adminMe.email || adminMe.username || 'A')[0].toUpperCase() : 'A'}
                        </span>
                        {adminMe?.email || 'Admin'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Admin Audit Log */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="font-bold text-gray-800">🔐 Admin Actions Log</h2>
            <p className="text-xs text-gray-400 mt-0.5">Last 30 actions — logins, uploads, edits, deletes</p>
          </div>
          {adminMe?.last_login_at && (
            <div className="text-right">
              <p className="text-xs text-gray-400">Last login</p>
              <p className="text-xs font-semibold text-gray-600">{fmtDate(adminMe.last_login_at)}</p>
            </div>
          )}
        </div>

        {auditLogs.length === 0 ? (
          <div className="text-center py-12 px-4">
            <div className="text-3xl mb-2">📋</div>
            <p className="text-gray-400 text-sm">No actions logged yet.</p>
            <p className="text-gray-300 text-xs mt-1">Actions appear here after login, upload, edit, or delete.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  {['Action', 'Paper / Details', 'IP Address', 'When'].map(h => (
                    <th key={h} className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {auditLogs.map(log => {
                  let detail = ''
                  if (log.target_details) {
                    const d = log.target_details
                    detail = d.title || d.identifier || ''
                  }
                  return (
                    <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-5 py-3 whitespace-nowrap">
                        <ActionBadge action={log.action} />
                      </td>
                      <td className="px-4 py-3 text-gray-600 max-w-xs">
                        <p className="truncate text-xs">{detail || '—'}</p>
                        {log.target_paper_id && (
                          <p className="text-gray-400 text-xs">Paper #{log.target_paper_id}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-400 font-mono text-xs whitespace-nowrap">{maskIp(log.ip_address)}</td>
                      <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">
                        <span title={new Date(log.created_at).toLocaleString('en-IN')}>{timeAgo(log.created_at)}</span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
