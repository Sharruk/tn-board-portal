import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { signInWithGoogle } from '../lib/firebase'
import { getMyProfile, updateContributionName } from '../services/profile'
import UserAvatar from '../components/common/UserAvatar'

export default function ProfilePage() {
  const { user, isAuthenticated, isLoading: authLoading, logout } = useAuth()
  const navigate = useNavigate()

  const [profile, setProfile] = useState(null)
  const [contributionName, setContributionName] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [saveError, setSaveError] = useState(null)

  const loadProfile = async () => {
    if (!isAuthenticated) return
    setLoading(true)
    setError(null)
    try {
      const data = await getMyProfile()
      setProfile(data)
      setContributionName(data.display_name || user?.displayName || '')
    } catch (err) {
      setError(err.message || 'Failed to load profile.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    document.title = 'My Profile & Account | TN Board Portal'
    if (isAuthenticated) {
      loadProfile()
    }
  }, [isAuthenticated])

  const handleSaveName = async (e) => {
    e.preventDefault()
    setSaveError(null)
    setSaveSuccess(false)
    const trimmed = contributionName.trim()

    if (!trimmed) {
      setSaveError('Contribution name cannot be empty.')
      return
    }
    if (trimmed.length < 2) {
      setSaveError('Contribution name must be at least 2 characters.')
      return
    }
    if (trimmed.length > 50) {
      setSaveError('Contribution name cannot exceed 50 characters.')
      return
    }

    setSaving(true)
    try {
      const updated = await updateContributionName(trimmed)
      setProfile(updated)
      setContributionName(updated.display_name)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 4000)
    } catch (err) {
      setSaveError(err.message || 'Failed to update contribution name.')
    } finally {
      setSaving(false)
    }
  }

  const handleLogout = async () => {
    try {
      await logout()
      navigate('/')
    } catch (err) {
      console.error('Logout error:', err)
    }
  }

  if (authLoading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          <p className="text-sm font-medium text-gray-500">Loading your profile…</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center px-4 py-16">
        <div className="max-w-md w-full text-center bg-white border border-gray-200 rounded-3xl p-8 shadow-sm">
          <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-5 text-2xl font-bold">
            👤
          </div>
          <h1 className="text-2xl font-extrabold text-gray-900 mb-2">Account Profile</h1>
          <p className="text-gray-600 text-sm leading-relaxed mb-6">
            Sign in with your Google account to track your submitted question papers, check review statuses, and customize your public contributor name.
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

  const stats = profile?.stats || {
    total_submissions: 0,
    published_count: 0,
    pending_count: 0,
    rejected_count: 0,
  }

  return (
    <div className="min-h-screen bg-gray-50/70 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto space-y-6">

        {/* ── Breadcrumb ────────────────────────────────────────────── */}
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Link to="/" className="hover:text-blue-600 transition">Home</Link>
          <span>/</span>
          <span className="text-gray-900 font-medium">User Profile</span>
        </div>

        {/* ── Profile Header Card ───────────────────────────────────── */}
        <div className="bg-white rounded-3xl border border-gray-200/80 p-6 sm:p-8 shadow-xs relative overflow-hidden">
          <div className="flex flex-col sm:flex-row items-center sm:items-start gap-5 sm:gap-6 text-center sm:text-left">
            {/* Avatar */}
            <div className="relative shrink-0">
              <UserAvatar
                user={user}
                src={profile?.photo_url || user?.photoURL}
                name={profile?.display_name || user?.displayName}
                size="xl"
                className="border-4 border-blue-50 shadow-md"
              />
              <div className="absolute -bottom-1 -right-1 bg-emerald-500 text-white p-1.5 rounded-full border-2 border-white text-[10px]" title="Authenticated via Google">
                ✓
              </div>
            </div>

            {/* User Info */}
            <div className="flex-1 space-y-2 min-w-0">
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
                <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 truncate">
                  {profile?.display_name || user?.displayName || 'Contributor'}
                </h1>
                <span className="inline-flex items-center gap-1 text-xs font-bold px-3 py-1 bg-amber-50 text-amber-800 border border-amber-200 rounded-full">
                  {profile?.badge || '🏅 Contributor'}
                </span>
              </div>
              <p className="text-sm text-gray-500 font-medium truncate">{user?.email}</p>
              
              {profile?.rank && (
                <p className="text-xs text-blue-700 font-semibold bg-blue-50/70 inline-block px-3 py-1 rounded-full border border-blue-100">
                  🏆 Ranked #{profile.rank} on Community Leaderboard
                </p>
              )}
            </div>
          </div>

          {/* Action Links Bar */}
          <div className="mt-6 pt-6 border-t border-gray-100 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <Link
                to="/my-contributions"
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl transition shadow-xs"
              >
                <span>📂</span> My Contributions
              </Link>
              <Link
                to="/submit-material"
                className="inline-flex items-center gap-2 px-4 py-2 bg-white hover:bg-gray-50 border border-gray-200 text-gray-700 text-xs font-bold rounded-xl transition"
              >
                <span>📤</span> Submit Material
              </Link>
              <Link
                to="/messages"
                className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 text-xs font-bold rounded-xl transition"
              >
                <span>💬</span> Messages &amp; Support
              </Link>
            </div>
            <button
              onClick={handleLogout}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-red-600 hover:bg-red-50 rounded-xl transition"
            >
              <span>🚪</span> Log out
            </button>
          </div>
        </div>

        {/* ── Contribution Statistics ───────────────────────────────── */}
        <div className="space-y-3">
          <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
            <span>📊</span> Contribution Statistics
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
            <div className="bg-white rounded-2xl border border-gray-200/80 p-4.5 shadow-xs flex flex-col justify-between">
              <span className="text-xs font-semibold text-gray-500">📚 Total Submissions</span>
              <p className="text-2xl font-black text-gray-900 mt-2">{stats.total_submissions}</p>
            </div>

            <div className="bg-white rounded-2xl border border-emerald-100 bg-emerald-50/20 p-4.5 shadow-xs flex flex-col justify-between">
              <span className="text-xs font-semibold text-emerald-800">✅ Published</span>
              <p className="text-2xl font-black text-emerald-600 mt-2">{stats.published_count}</p>
            </div>

            <div className="bg-white rounded-2xl border border-amber-100 bg-amber-50/20 p-4.5 shadow-xs flex flex-col justify-between">
              <span className="text-xs font-semibold text-amber-800">🟡 Under Review</span>
              <p className="text-2xl font-black text-amber-600 mt-2">{stats.pending_count}</p>
            </div>

            <div className="bg-white rounded-2xl border border-gray-200/80 p-4.5 shadow-xs flex flex-col justify-between">
              <span className="text-xs font-semibold text-gray-500">❌ Rejected</span>
              <p className="text-2xl font-black text-gray-700 mt-2">{stats.rejected_count}</p>
            </div>
          </div>
        </div>

        {/* ── Edit Contribution Name ────────────────────────────────── */}
        <div className="bg-white rounded-3xl border border-gray-200/80 p-6 sm:p-8 shadow-xs space-y-4">
          <div>
            <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <span>✍️</span> Public Contribution Name
            </h2>
            <p className="text-xs text-gray-500 mt-1">
              This name is publicly displayed on question papers you submit and in the community leaderboard.
            </p>
          </div>

          <form onSubmit={handleSaveName} className="space-y-4">
            {saveSuccess && (
              <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs font-semibold text-emerald-700 flex items-center gap-2">
                <span>✓</span> Contribution name updated successfully!
              </div>
            )}

            {saveError && (
              <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl text-xs font-semibold text-red-600 flex items-center gap-2">
                <span>⚠️</span> {saveError}
              </div>
            )}

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
              <input
                type="text"
                value={contributionName}
                onChange={(e) => setContributionName(e.target.value)}
                placeholder="Enter your public display name…"
                maxLength={50}
                required
                className="flex-1 text-sm border border-gray-200 rounded-xl px-4 py-2.5 outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
              />
              <button
                type="submit"
                disabled={saving || !contributionName.trim()}
                className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold text-xs rounded-xl transition shadow-xs flex items-center justify-center gap-2"
              >
                {saving ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    Saving…
                  </>
                ) : (
                  'Save Changes'
                )}
              </button>
            </div>
          </form>
        </div>

        {/* ── Security / Account Details (Read-only) ──────────────────── */}
        <div className="bg-white rounded-3xl border border-gray-200/80 p-6 sm:p-8 shadow-xs space-y-4">
          <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
            <span>🔒</span> Authentication &amp; Security
          </h2>
          <div className="bg-gray-50 rounded-2xl p-4 text-xs text-gray-600 space-y-2 border border-gray-100">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-gray-500">Authentication Provider:</span>
              <span className="font-bold text-gray-800">Google OAuth (Firebase)</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="font-semibold text-gray-500">Email Address:</span>
              <span className="font-bold text-gray-800">{user?.email}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="font-semibold text-gray-500">Account Role:</span>
              <span className="font-bold text-blue-700 uppercase">{profile?.role || 'USER'}</span>
            </div>
          </div>
          <p className="text-[11px] text-gray-400">
            Authentication is securely managed by Google. Your password and credentials are never stored on our servers.
          </p>
        </div>

      </div>
    </div>
  )
}
