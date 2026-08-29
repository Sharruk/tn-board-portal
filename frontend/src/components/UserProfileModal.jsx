import { useEffect, useState } from 'react'
import { getUserProfile } from '../services/community'

export default function UserProfileModal({ uid, authorName, onClose }) {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!uid) {
      setProfile({
        display_name: authorName || 'Community Contributor',
        avatar_url: null,
        joined_date: new Date().toISOString(),
        approved_contributions: 0,
        likes_received: 0,
        posts_count: 0,
        comments_count: 0,
        badges: [],
      })
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)
    getUserProfile(uid)
      .then(data => setProfile(data))
      .catch(err => setError(err.message || 'Failed to load profile'))
      .finally(() => setLoading(false))
  }, [uid, authorName])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white rounded-3xl shadow-2xl max-w-md w-full overflow-hidden border border-gray-100 relative">
        {/* Header background banner */}
        <div className="h-28 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 relative">
          <button
            onClick={onClose}
            className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/20 hover:bg-black/40 text-white flex items-center justify-center transition-colors text-sm"
            title="Close"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="px-6 pb-6 pt-0 -mt-12 relative text-center">
          {/* Avatar */}
          <div className="w-24 h-24 mx-auto rounded-full border-4 border-white shadow-lg overflow-hidden bg-gradient-to-tr from-blue-100 to-indigo-100 flex items-center justify-center text-3xl font-bold text-blue-700">
            {profile?.avatar_url ? (
              <img src={profile.avatar_url} alt={profile.display_name} className="w-full h-full object-cover" />
            ) : (
              (profile?.display_name || authorName || 'S').charAt(0).toUpperCase()
            )}
          </div>

          {loading ? (
            <div className="py-8">
              <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin inline-block" />
            </div>
          ) : error ? (
            <div className="py-6 text-red-500 text-sm">{error}</div>
          ) : profile ? (
            <>
              <h2 className="text-xl font-bold text-gray-900 mt-3">{profile.display_name}</h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Member since {new Date(profile.joined_date).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}
              </p>

              {/* Stats Grid */}
              <div className="grid grid-cols-3 gap-2 my-5 bg-gray-50 p-3 rounded-2xl border border-gray-100 text-center">
                <div>
                  <p className="text-xs text-gray-400 font-medium">Approved</p>
                  <p className="text-lg font-extrabold text-emerald-600">{profile.approved_contributions}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 font-medium">Likes</p>
                  <p className="text-lg font-extrabold text-amber-600">👍 {profile.likes_received}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 font-medium">Posts</p>
                  <p className="text-lg font-extrabold text-blue-600">{profile.posts_count}</p>
                </div>
              </div>

              {/* Badges */}
              {profile.badges && profile.badges.length > 0 && (
                <div className="text-left mb-4">
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Achievements</p>
                  <div className="flex flex-wrap gap-1.5">
                    {profile.badges.map(badge => (
                      <span key={badge} className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-800 shadow-2xs">
                        🏅 {badge}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <button
                onClick={onClose}
                className="w-full py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-semibold rounded-xl transition-colors mt-2"
              >
                Close
              </button>
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}
