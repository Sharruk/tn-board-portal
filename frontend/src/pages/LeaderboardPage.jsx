import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { getLeaderboard } from '../services/leaderboard'
import { getMyProfile } from '../services/profile'
import UserProfileModal from '../components/UserProfileModal'

export default function LeaderboardPage() {
  const { user, isAuthenticated } = useAuth()
  const [leaderboard, setLeaderboard] = useState([])
  const [totalContributors, setTotalContributors] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [selectedUser, setSelectedUser] = useState(null)
  const [myProfile, setMyProfile] = useState(null)

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
    document.title = 'Community Contributors Leaderboard | TN Board Portal'
    fetchLeaderboardData()
    if (isAuthenticated) {
      getMyProfile().then(setMyProfile).catch(() => {})
    }
  }, [isAuthenticated])

  const filtered = leaderboard.filter(item =>
    item.contributor_name.toLowerCase().includes(search.toLowerCase())
  )

  const top3 = leaderboard.slice(0, 3)

  // Determine current user's rank from leaderboard data
  const myRankEntry = myProfile
    ? leaderboard.find(
        item => item.contributor_name.toLowerCase() === (myProfile.display_name || '').toLowerCase()
      )
    : null

  return (
    <div className="min-h-screen bg-gray-50/70 py-10 px-4 sm:px-6 lg:px-8">
      {selectedUser && (
        <UserProfileModal
          uid={selectedUser.firebase_uid}
          authorName={selectedUser.contributor_name}
          onClose={() => setSelectedUser(null)}
        />
      )}

      <div className="max-w-5xl mx-auto space-y-8">

        {/* ── Hero / Header ────────────────────────────────────────────── */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-xs font-semibold uppercase tracking-wider">
            <span>🏆</span> Community Recognition
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900 tracking-tight">
            Community Contributors
          </h1>
          <p className="text-sm sm:text-base text-gray-600 max-w-2xl mx-auto leading-relaxed">
            Students helping students. Celebrating every educator and student who contributes approved Tamil Nadu State Board question papers and answer keys.
          </p>
          <div className="pt-2 flex flex-wrap justify-center items-center gap-3">
            <Link
              to="/submit-material"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl transition shadow-xs"
            >
              <span>📤</span> Submit Material &amp; Join the Ranks
            </Link>
            {isAuthenticated && (
              <Link
                to="/my-contributions"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-white hover:bg-gray-50 border border-gray-200 text-gray-700 font-bold text-xs rounded-xl transition"
              >
                <span>📂</span> View My Contributions
              </Link>
            )}
          </div>
        </div>

        {/* ── Logged-in "Your Rank" Banner ────────────────────────────── */}
        {isAuthenticated && myProfile && (
          <div className="bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-700 rounded-3xl p-5 sm:p-6 text-white shadow-md flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-4 text-center sm:text-left">
              <div className="w-14 h-14 rounded-2xl bg-white/20 backdrop-blur-sm border border-white/30 flex items-center justify-center text-2xl font-black shrink-0">
                {myRankEntry ? `#${myRankEntry.rank}` : '—'}
              </div>
              <div className="space-y-0.5">
                <div className="text-xs font-semibold text-blue-200 uppercase tracking-wider">Your Contribution Rank</div>
                <div className="text-lg sm:text-xl font-extrabold">{myProfile.display_name}</div>
                <div className="text-xs text-blue-100 font-medium">
                  📚 <strong>{myProfile.stats?.published_count || 0}</strong> published contributions
                  {myProfile.stats?.total_submissions > (myProfile.stats?.published_count || 0) && (
                    <span> · 📤 {myProfile.stats?.total_submissions} submitted</span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-bold px-3 py-1.5 rounded-full bg-white/20 backdrop-blur-sm border border-white/25">
                {myProfile.badge || '🏅 Contributor'}
              </span>
              <Link
                to="/my-contributions"
                className="px-4 py-2 bg-white text-blue-700 hover:bg-blue-50 text-xs font-bold rounded-xl transition shadow-xs"
              >
                My Submissions →
              </Link>
            </div>
          </div>
        )}

        {/* ── Top 3 Podium Cards ───────────────────────────────────────── */}
        {!loading && !error && top3.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            {/* Rank 2 (Silver) */}
            {top3[1] && (
              <div
                onClick={() => setSelectedUser(top3[1])}
                className="bg-white rounded-3xl border border-gray-200/90 p-6 shadow-xs flex flex-col items-center text-center relative order-2 md:order-1 cursor-pointer hover:border-blue-300 hover:shadow-md transition"
              >
                <div className="w-14 h-14 rounded-2xl bg-gray-100 border border-gray-200 flex items-center justify-center text-2xl mb-3 shadow-inner">
                  🥈
                </div>
                <span className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Rank #2</span>
                <h2 className="text-lg font-extrabold text-gray-900 truncate max-w-[200px]">{top3[1].contributor_name}</h2>
                <div className="flex flex-wrap gap-1 justify-center my-2">
                  <span className="text-xs bg-gray-100 text-gray-700 px-2.5 py-0.5 rounded-full font-bold">
                    {top3[1].badges?.[0] || '⭐ Active Contributor'}
                  </span>
                </div>
                <div className="mt-2 w-full pt-3 border-t border-gray-100 text-center">
                  <p className="text-xl font-black text-emerald-600">
                    {top3[1].approved_count ?? top3[1].accepted_contributions}
                  </p>
                  <p className="text-xs text-gray-500 font-medium">Published Contributions</p>
                </div>
              </div>
            )}

            {/* Rank 1 (Gold) */}
            {top3[0] && (
              <div
                onClick={() => setSelectedUser(top3[0])}
                className="bg-gradient-to-b from-amber-50/70 via-white to-white rounded-3xl border-2 border-amber-300 p-7 shadow-md flex flex-col items-center text-center relative order-1 md:order-2 -mt-2 cursor-pointer hover:shadow-lg transition"
              >
                <div className="absolute -top-3.5 bg-amber-500 text-white text-[11px] font-extrabold uppercase px-3 py-0.5 rounded-full tracking-wider shadow">
                  Top Contributor
                </div>
                <div className="w-16 h-16 rounded-2xl bg-amber-100 border border-amber-300 flex items-center justify-center text-3xl mb-3 shadow-inner">
                  🥇
                </div>
                <span className="text-xs font-bold text-amber-700 uppercase tracking-wider mb-1">Rank #1</span>
                <h2 className="text-xl font-black text-gray-900 truncate max-w-[220px]">{top3[0].contributor_name}</h2>
                <div className="flex flex-wrap gap-1 justify-center my-2">
                  <span className="text-xs bg-amber-100 text-amber-800 border border-amber-200 px-2.5 py-0.5 rounded-full font-bold">
                    {top3[0].badges?.[0] || '🏆 Top Contributor'}
                  </span>
                </div>
                <div className="mt-2 w-full pt-3 border-t border-amber-100 text-center">
                  <p className="text-2xl font-black text-emerald-600">
                    {top3[0].approved_count ?? top3[0].accepted_contributions}
                  </p>
                  <p className="text-xs text-gray-500 font-medium">Published Contributions</p>
                </div>
              </div>
            )}

            {/* Rank 3 (Bronze) */}
            {top3[2] && (
              <div
                onClick={() => setSelectedUser(top3[2])}
                className="bg-white rounded-3xl border border-gray-200/90 p-6 shadow-xs flex flex-col items-center text-center relative order-3 cursor-pointer hover:border-blue-300 hover:shadow-md transition"
              >
                <div className="w-14 h-14 rounded-2xl bg-amber-50 border border-amber-200/70 flex items-center justify-center text-2xl mb-3 shadow-inner">
                  🥉
                </div>
                <span className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Rank #3</span>
                <h2 className="text-lg font-extrabold text-gray-900 truncate max-w-[200px]">{top3[2].contributor_name}</h2>
                <div className="flex flex-wrap gap-1 justify-center my-2">
                  <span className="text-xs bg-amber-50 text-amber-800 border border-amber-200 px-2.5 py-0.5 rounded-full font-bold">
                    {top3[2].badges?.[0] || '⭐ Active Contributor'}
                  </span>
                </div>
                <div className="mt-2 w-full pt-3 border-t border-gray-100 text-center">
                  <p className="text-xl font-black text-emerald-600">
                    {top3[2].approved_count ?? top3[2].accepted_contributions}
                  </p>
                  <p className="text-xs text-gray-500 font-medium">Published Contributions</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Search & Count Bar ─────────────────────────────────────── */}
        <div className="bg-white rounded-2xl border border-gray-200/90 p-4 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
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

        {/* ── Leaderboard Table / Cards ───────────────────────────────── */}
        <div className="bg-white rounded-3xl border border-gray-200/90 shadow-xs overflow-hidden">
          {loading ? (
            <div className="py-20 flex flex-col items-center justify-center gap-3">
              <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
              <p className="text-sm font-medium text-gray-500">Loading contributors…</p>
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
          ) : leaderboard.length === 0 ? (
            <div className="py-16 px-6 text-center space-y-4 max-w-lg mx-auto">
              <div className="w-16 h-16 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center text-3xl mx-auto shadow-xs">
                🏆
              </div>
              <div className="space-y-2">
                <h3 className="text-xl font-bold text-gray-900">
                  No contributors yet
                </h3>
                <p className="text-xs sm:text-sm text-gray-600 leading-relaxed">
                  Be the first person to contribute approved study material and appear on the community leaderboard.
                </p>
              </div>
              <div className="pt-2">
                <Link
                  to="/submit-material"
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl transition shadow-xs"
                >
                  <span>📤</span> Submit Material &amp; Join the Ranks
                </Link>
              </div>
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-12 px-6 text-center space-y-3 max-w-sm mx-auto">
              <span className="text-3xl">🔍</span>
              <h3 className="text-base font-bold text-gray-800">
                No matching contributors found
              </h3>
              <p className="text-xs text-gray-500">
                No contributors matched &ldquo;{search}&rdquo;. Try searching with a different name or clear the search filter.
              </p>
              <button
                type="button"
                onClick={() => setSearch('')}
                className="mt-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl text-xs font-semibold transition"
              >
                Clear Search
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="bg-gray-50/80 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                    <th className="py-4 px-4 w-16 text-center"># Rank</th>
                    <th className="py-4 px-4">Contributor</th>
                    <th className="py-4 px-4 text-center">Published Papers</th>
                    <th className="py-4 px-4 text-center hidden sm:table-cell">Total Submissions</th>
                    <th className="py-4 px-4">Recognition Badge</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filtered.map(item => {
                    const isTop1 = item.rank === 1
                    const isTop2 = item.rank === 2
                    const isTop3 = item.rank === 3
                    const approved = item.approved_count ?? item.accepted_contributions
                    const submitted = item.submitted_count ?? item.total_contributions
                    const isMe = myProfile && (item.contributor_name.toLowerCase() === myProfile.display_name.toLowerCase())

                    return (
                      <tr
                        key={item.rank}
                        onClick={() => setSelectedUser(item)}
                        className={`hover:bg-blue-50/40 transition-colors cursor-pointer ${
                          isMe ? 'bg-blue-50/60 font-semibold' : isTop1 ? 'bg-amber-50/20' : ''
                        }`}
                      >
                        <td className="py-4 px-4 text-center">
                          {isTop1 ? (
                            <span className="inline-flex items-center justify-center w-8 h-8 rounded-xl bg-amber-100 text-amber-800 font-black text-sm">
                              🥇
                            </span>
                          ) : isTop2 ? (
                            <span className="inline-flex items-center justify-center w-8 h-8 rounded-xl bg-gray-100 text-gray-700 font-black text-sm">
                              🥈
                            </span>
                          ) : isTop3 ? (
                            <span className="inline-flex items-center justify-center w-8 h-8 rounded-xl bg-amber-50 text-amber-800 font-black text-sm">
                              🥉
                            </span>
                          ) : (
                            <span className="text-gray-500 font-bold">{item.rank}</span>
                          )}
                        </td>
                        <td className="py-4 px-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 text-white font-black text-sm flex items-center justify-center shrink-0 shadow-xs overflow-hidden">
                              {item.avatar_url ? (
                                <img src={item.avatar_url} alt="" className="w-full h-full object-cover" />
                              ) : (
                                item.contributor_name.charAt(0).toUpperCase()
                              )}
                            </div>
                            <div>
                              <p className="font-bold text-gray-900 hover:text-blue-600 transition-colors flex items-center gap-1.5">
                                {item.contributor_name}
                                {isMe && (
                                  <span className="text-[10px] bg-blue-600 text-white px-2 py-0.5 rounded-full font-bold">
                                    You
                                  </span>
                                )}
                              </p>
                              <p className="text-[11px] text-gray-400">Community Contributor</p>
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-4 text-center">
                          <span className="inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-black bg-emerald-50 text-emerald-800 border border-emerald-200/80 shadow-2xs">
                            📚 {approved} published
                          </span>
                        </td>
                        <td className="py-4 px-4 text-center hidden sm:table-cell">
                          <span className="text-xs text-gray-600 font-medium">
                            📤 {submitted} submitted
                          </span>
                        </td>
                        <td className="py-4 px-4">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            {item.badges?.map(b => (
                              <span key={b} className="text-xs px-2.5 py-1 bg-amber-50 text-amber-800 border border-amber-200/80 rounded-full font-bold">
                                {b}
                              </span>
                            ))}
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
