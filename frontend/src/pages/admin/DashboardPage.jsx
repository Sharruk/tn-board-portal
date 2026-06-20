import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getAdminPapers, getSearchAnalytics } from '../../services/admin'
import adminApi from '../../services/admin'

function StatCard({ label, value, color, icon }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex items-center gap-4">
      <div className={`w-12 h-12 ${color} rounded-xl flex items-center justify-center text-xl shrink-0`}>
        {icon}
      </div>
      <div>
        <p className="text-3xl font-extrabold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500 font-medium mt-0.5">{label}</p>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const [papers, setPapers] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [statsLoading, setStatsLoading] = useState(true)
  const [error, setError] = useState(null)

  const [analytics, setAnalytics] = useState(null)
  const [analyticsLoading, setAnalyticsLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getAdminPapers(),
      adminApi.get('/admin/stats'),
      getSearchAnalytics(),
    ]).then(([papersRes, statsRes, analyticsRes]) => {
      setPapers(papersRes.data)
      setStats(statsRes.data)
      setAnalytics(analyticsRes.data)
    }).catch(err => {
      setError(err.response?.data?.detail || 'Failed to load dashboard data')
    }).finally(() => {
      setLoading(false)
      setStatsLoading(false)
      setAnalyticsLoading(false)
    })
  }, [])

  const recent = [...papers].slice(0, 5)

  const fmt = (n) => n == null ? '—' : Number(n).toLocaleString()

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-extrabold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">Overview of the TN Board Learning Platform</p>
      </div>

      {/* Primary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Papers" value={statsLoading ? '—' : fmt(stats?.total_papers)} color="bg-blue-50" icon="📄" />
        <StatCard label="Total Downloads" value={statsLoading ? '—' : fmt(stats?.total_downloads)} color="bg-violet-50" icon="⬇️" />
        <StatCard label="Total Subjects" value={statsLoading ? '—' : fmt(stats?.total_subjects)} color="bg-emerald-50" icon="📚" />
        <StatCard label="Total Classes" value={statsLoading ? '—' : fmt(stats?.total_classes)} color="bg-orange-50" icon="🎓" />
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
        <div className="bg-gray-900 text-white rounded-2xl p-5">
          <p className="text-3xl font-extrabold text-blue-400">{statsLoading ? '—' : fmt(stats?.question_papers)}</p>
          <p className="font-semibold mt-1">Question Papers</p>
          <p className="text-gray-400 text-xs mt-0.5">Uploaded question papers</p>
        </div>
        <div className="bg-gray-900 text-white rounded-2xl p-5">
          <p className="text-3xl font-extrabold text-emerald-400">{statsLoading ? '—' : fmt(stats?.answer_keys)}</p>
          <p className="font-semibold mt-1">Answer Keys</p>
          <p className="text-gray-400 text-xs mt-0.5">Uploaded answer keys</p>
        </div>
        <div className="bg-gray-900 text-white rounded-2xl p-5">
          <p className="text-3xl font-extrabold text-amber-400">{statsLoading ? '—' : fmt(stats?.visible_papers)}</p>
          <p className="font-semibold mt-1">Visible Papers</p>
          <p className="text-gray-400 text-xs mt-0.5">Published to students</p>
        </div>
      </div>

      {/* Two-column row: Recent Papers + Popular Searches */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Recent Papers (wider) */}
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <h2 className="font-bold text-gray-800">Recent Papers</h2>
            <Link to="/admin/papers" className="text-sm text-blue-600 hover:text-blue-800 font-medium">
              View all →
            </Link>
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
              <Link to="/admin/papers" className="mt-4 inline-block btn-primary text-sm px-4 py-2">
                Upload First Paper
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Title</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Type</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Exam</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Year</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">DLs</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {recent.map(p => (
                    <tr key={p.id} className="hover:bg-gray-50">
                      <td className="px-6 py-3 font-medium text-gray-800 max-w-xs truncate">{p.title}</td>
                      <td className="px-4 py-3">
                        <span className={`badge ${p.paper_type === 'question' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'}`}>
                          {p.paper_type === 'question' ? 'Q Paper' : 'Answer Key'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-500">{p.exam_type}</td>
                      <td className="px-4 py-3 text-gray-500">{p.year}</td>
                      <td className="px-4 py-3 text-gray-500 font-mono text-xs">{p.download_count ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Popular Searches (narrower) */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="font-bold text-gray-800">🔍 Popular Searches</h2>
            <p className="text-xs text-gray-400 mt-0.5">In-session search terms</p>
          </div>

          {analyticsLoading ? (
            <div className="flex items-center justify-center py-12">
              <span className="w-6 h-6 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
            </div>
          ) : !analytics || analytics.popular_searches.length === 0 ? (
            <div className="text-center py-12 px-4">
              <div className="text-3xl mb-2">📊</div>
              <p className="text-gray-400 text-sm">No searches yet.</p>
              <p className="text-gray-300 text-xs mt-1">Stats appear after students search.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {analytics.popular_searches.slice(0, 10).map((item, i) => (
                <div key={item.term} className="flex items-center justify-between px-6 py-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-xs font-bold text-gray-300 w-4 shrink-0">{i + 1}</span>
                    <span className="text-sm text-gray-700 font-medium truncate capitalize">{item.term}</span>
                  </div>
                  <span className="ml-3 shrink-0 text-xs font-semibold bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
                    {item.count}×
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
