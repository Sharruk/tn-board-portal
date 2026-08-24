import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getLeaderboard } from '../services/leaderboard'

export default function LeaderboardPage() {
  const [leaderboard, setLeaderboard] = useState([])
  const [totalContributors, setTotalContributors] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')

  const fetchLeaderboardData = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getLeaderboard(100)
      setLeaderboard(res.data || [])
      setTotalContributors(res.total_contributors || 0)
    } catch (err) {
      setError(err.message || 'Failed to load contributor leaderboard.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLeaderboardData()
  }, [])

  const filtered = leaderboard.filter(item =>
    item.contributor_name.toLowerCase().includes(search.toLowerCase())
  )

  const top3 = leaderboard.slice(0, 3)

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto space-y-8">

        {/* ── Hero / Header ────────────────────────────────────────────── */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-xs font-semibold uppercase tracking-wider">
            <span>🏆</span> Community Recognition
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900 tracking-tight">
            Contributor Leaderboard
          </h1>
          <p className="text-base text-gray-600 max-w-2xl mx-auto">
            Honoring students, teachers, and contributors who share Tamil Nadu State Board question papers and answer keys.
          </p>
          <div className="pt-2">
            <Link
              to="/submit-material"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm rounded-xl transition-colors shadow-sm"
            >
              <span>📤</span> Submit Material &amp; Join Ranks
            </Link>
          </div>
        </div>

        {/* ── Top 3 Podium Cards ───────────────────────────────────────── */}
        {!loading && !error && top3.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
            {/* Rank 2 (Silver) */}
            {top3[1] && (
              <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm flex flex-col items-center text-center relative order-2 md:order-1">
                <div className="w-12 h-12 rounded-full bg-gray-100 border-2 border-gray-300 flex items-center justify-center text-xl font-bold text-gray-700 mb-3 shadow-inner">
                  🥈
                </div>
                <span className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Rank #2</span>
                <h2 className="text-lg font-bold text-gray-900 truncate max-w-[200px]">{top3[1].contributor_name}</h2>
                <div className="mt-4 grid grid-cols-2 gap-2 w-full pt-3 border-t border-gray-100 text-xs">
                  <div className="bg-gray-50 rounded-lg p-2">
                    <p className="text-gray-500 font-medium">Accepted</p>
                    <p className="text-base font-bold text-emerald-600">{top3[1].accepted_contributions}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-2">
                    <p className="text-gray-500 font-medium">Acceptance</p>
                    <p className="text-base font-bold text-blue-600">{top3[1].acceptance_rate}%</p>
                  </div>
                </div>
              </div>
            )}

            {/* Rank 1 (Gold) */}
            {top3[0] && (
              <div className="bg-gradient-to-b from-amber-50 to-white rounded-2xl border-2 border-amber-300 p-6 shadow-md flex flex-col items-center text-center relative order-1 md:order-2 -mt-2">
                <div className="absolute -top-3.5 bg-amber-500 text-white text-[11px] font-extrabold uppercase px-3 py-0.5 rounded-full tracking-wider shadow">
                  Top Contributor
                </div>
                <div className="w-16 h-16 rounded-full bg-amber-100 border-2 border-amber-400 flex items-center justify-center text-3xl font-bold text-amber-700 mb-3 shadow-inner">
                  🥇
                </div>
                <span className="text-xs font-bold text-amber-700 uppercase tracking-widest mb-1">Rank #1</span>
                <h2 className="text-xl font-extrabold text-gray-900 truncate max-w-[220px]">{top3[0].contributor_name}</h2>
                <div className="mt-4 grid grid-cols-2 gap-2 w-full pt-3 border-t border-amber-100 text-xs">
                  <div className="bg-amber-50/70 rounded-lg p-2">
                    <p className="text-amber-700 font-medium">Accepted</p>
                    <p className="text-lg font-extrabold text-emerald-600">{top3[0].accepted_contributions}</p>
                  </div>
                  <div className="bg-amber-50/70 rounded-lg p-2">
                    <p className="text-amber-700 font-medium">Acceptance</p>
                    <p className="text-lg font-extrabold text-blue-600">{top3[0].acceptance_rate}%</p>
                  </div>
                </div>
              </div>
            )}

            {/* Rank 3 (Bronze) */}
            {top3[2] && (
              <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm flex flex-col items-center text-center relative order-3">
                <div className="w-12 h-12 rounded-full bg-amber-50 border-2 border-amber-600/40 flex items-center justify-center text-xl font-bold text-amber-800 mb-3 shadow-inner">
                  🥉
                </div>
                <span className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Rank #3</span>
                <h2 className="text-lg font-bold text-gray-900 truncate max-w-[200px]">{top3[2].contributor_name}</h2>
                <div className="mt-4 grid grid-cols-2 gap-2 w-full pt-3 border-t border-gray-100 text-xs">
                  <div className="bg-gray-50 rounded-lg p-2">
                    <p className="text-gray-500 font-medium">Accepted</p>
                    <p className="text-base font-bold text-emerald-600">{top3[2].accepted_contributions}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-2">
                    <p className="text-gray-500 font-medium">Acceptance</p>
                    <p className="text-base font-bold text-blue-600">{top3[2].acceptance_rate}%</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Search & Total Count Bar ─────────────────────────────────── */}
        <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-80">
            <input
              type="text"
              placeholder="Search contributor by name…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full text-sm border border-gray-200 rounded-xl pl-9 pr-3 py-2 outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
            />
            <span className="absolute left-3 top-2.5 text-gray-400 text-sm">🔍</span>
          </div>
          <div className="text-xs font-medium text-gray-500">
            Showing <strong className="text-gray-800">{filtered.length}</strong> of{' '}
            <strong className="text-gray-800">{totalContributors}</strong> contributors
          </div>
        </div>

        {/* ── Leaderboard Table ────────────────────────────────────────── */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          {loading ? (
            <div className="py-20 flex flex-col items-center justify-center gap-3">
              <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
              <p className="text-sm font-medium text-gray-500">Loading leaderboard…</p>
            </div>
          ) : error ? (
            <div className="p-8 text-center space-y-3">
              <p className="text-3xl">⚠️</p>
              <p className="text-sm font-semibold text-gray-800">Unable to load leaderboard</p>
              <p className="text-xs text-red-600">{error}</p>
              <button
                onClick={fetchLeaderboardData}
                className="px-4 py-2 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-xl text-xs font-semibold transition"
              >
                Try Again
              </button>
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <p className="text-4xl">🌟</p>
              <h3 className="text-base font-bold text-gray-800">
                {search ? 'No matching contributors found' : 'No contributions recorded yet'}
              </h3>
              <p className="text-xs text-gray-500 max-w-sm mx-auto">
                {search
                  ? 'Try searching with a different name or clear the search field.'
                  : 'Be the first to submit a question paper or answer key and earn the #1 spot on the leaderboard!'}
              </p>
              {!search && (
                <Link
                  to="/submit-material"
                  className="inline-block mt-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold transition"
                >
                  Submit Material Now
                </Link>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="bg-gray-50/80 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    <th className="py-3.5 px-4 w-16 text-center"># Rank</th>
                    <th className="py-3.5 px-4">Contributor</th>
                    <th className="py-3.5 px-4 text-center">Total Submissions</th>
                    <th className="py-3.5 px-4 text-center">Accepted Papers</th>
                    <th className="py-3.5 px-4 text-right pr-6">Acceptance Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filtered.map(item => {
                    const isTop1 = item.rank === 1
                    const isTop2 = item.rank === 2
                    const isTop3 = item.rank === 3
                    return (
                      <tr
                        key={item.rank}
                        className={`hover:bg-blue-50/40 transition-colors ${
                          isTop1 ? 'bg-amber-50/30 font-medium' : ''
                        }`}
                      >
                        <td className="py-3.5 px-4 text-center">
                          {isTop1 ? (
                            <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-amber-100 text-amber-700 font-bold text-xs">
                              🥇
                            </span>
                          ) : isTop2 ? (
                            <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-gray-100 text-gray-700 font-bold text-xs">
                              🥈
                            </span>
                          ) : isTop3 ? (
                            <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-amber-50 text-amber-800 font-bold text-xs">
                              🥉
                            </span>
                          ) : (
                            <span className="text-gray-500 font-semibold">{item.rank}</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 text-white font-bold text-xs flex items-center justify-center shrink-0 shadow-sm">
                              {item.contributor_name.charAt(0).toUpperCase()}
                            </div>
                            <div>
                              <p className="font-semibold text-gray-900">{item.contributor_name}</p>
                              <p className="text-[11px] text-gray-400">Contributor</p>
                            </div>
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-center font-medium text-gray-700">
                          {item.total_contributions}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            {item.accepted_contributions}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right pr-6">
                          <div className="inline-flex items-center gap-2">
                            <div className="w-16 bg-gray-100 rounded-full h-2 hidden sm:block overflow-hidden">
                              <div
                                className={`h-2 rounded-full ${
                                  item.acceptance_rate >= 80
                                    ? 'bg-emerald-500'
                                    : item.acceptance_rate >= 50
                                    ? 'bg-blue-500'
                                    : 'bg-amber-500'
                                }`}
                                style={{ width: `${Math.min(100, item.acceptance_rate)}%` }}
                              />
                            </div>
                            <span className="font-bold text-gray-900">{item.acceptance_rate}%</span>
                          </div>
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
    </div>
  )
}
