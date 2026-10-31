import { useState, useEffect } from 'react'
import UserAvatar from '../common/UserAvatar'
import {
  getAdminList,
  getPendingAppointments,
  preauthorizeAdmin,
  revokePendingAppointment,
  promoteUserToAdmin,
  revokeAdminRole,
} from '../../services/adminRoles'
import { getAdminUsers } from '../../services/adminUsers'

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
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

export default function AdminRolesTab() {
  // State: Current Admins
  const [admins, setAdmins] = useState([])
  const [loadingAdmins, setLoadingAdmins] = useState(true)

  // State: Pending Appointments (Method 2)
  const [pendingAppointments, setPendingAppointments] = useState([])
  const [loadingPending, setLoadingPending] = useState(true)
  const [emailInput, setEmailInput] = useState('')
  const [submittingEmail, setSubmittingEmail] = useState(false)

  // State: Method 1 Search
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searchingUsers, setSearchingUsers] = useState(false)

  // Feedback notifications
  const [feedback, setFeedback] = useState(null) // { type: 'success' | 'error', message: string }

  // Confirmation Modals State
  const [confirmModal, setConfirmModal] = useState(null)
  // confirmModal shape: { type: 'promote_user' | 'revoke_admin' | 'preauthorize_email' | 'revoke_pending', payload: any }

  // Action in-progress spinner
  const [actionLoading, setActionLoading] = useState(false)

  const showToast = (message, type = 'success') => {
    setFeedback({ type, message })
    setTimeout(() => {
      setFeedback(prev => (prev?.message === message ? null : prev))
    }, 6000)
  }

  // Load active admins and pending appointments
  const loadData = async () => {
    setLoadingAdmins(true)
    setLoadingPending(true)
    try {
      const [adminsRes, pendingRes] = await Promise.all([
        getAdminList(),
        getPendingAppointments(),
      ])
      setAdmins(adminsRes.data || [])
      setPendingAppointments(pendingRes.data || [])
    } catch (err) {
      showToast(err.message || 'Failed to load administrative data.', 'error')
    } finally {
      setLoadingAdmins(false)
      setLoadingPending(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  // ── Method 1: Search Registered Users ─────────────────────────────────────
  const handleSearchUsers = async (e) => {
    e?.preventDefault()
    if (!searchQuery.trim()) return

    setSearchingUsers(true)
    try {
      const res = await getAdminUsers({ search: searchQuery.trim(), limit: 10 })
      setSearchResults(res.data || [])
    } catch (err) {
      showToast(err.message || 'Failed to search registered users.', 'error')
    } finally {
      setSearchingUsers(false)
    }
  }

  // ── Handlers for Modal Triggers ───────────────────────────────────────────

  const triggerPreauthorizeEmail = (e) => {
    e.preventDefault()
    const cleanEmail = emailInput.trim()
    if (!cleanEmail) return
    setConfirmModal({
      type: 'preauthorize_email',
      payload: { email: cleanEmail },
    })
  }

  const triggerPromoteUser = (userItem) => {
    setConfirmModal({
      type: 'promote_user',
      payload: userItem,
    })
  }

  const triggerRevokeAdmin = (adminItem) => {
    setConfirmModal({
      type: 'revoke_admin',
      payload: adminItem,
    })
  }

  const triggerRevokePending = (appointmentItem) => {
    setConfirmModal({
      type: 'revoke_pending',
      payload: appointmentItem,
    })
  }

  // ── Execute Confirmed Action ──────────────────────────────────────────────
  const handleExecuteConfirm = async () => {
    if (!confirmModal) return
    setActionLoading(true)

    try {
      if (confirmModal.type === 'preauthorize_email') {
        const res = await preauthorizeAdmin(confirmModal.payload.email)
        showToast(res.message || 'Successfully pre-authorized email.')
        setEmailInput('')
        await loadData()
      } else if (confirmModal.type === 'promote_user') {
        const res = await promoteUserToAdmin(confirmModal.payload.firebase_uid)
        showToast(res.message || 'Successfully promoted user to Admin.')
        // Update local search results state
        setSearchResults(prev =>
          prev.map(u => (u.firebase_uid === confirmModal.payload.firebase_uid ? { ...u, role: 'ADMIN' } : u))
        )
        await loadData()
      } else if (confirmModal.type === 'revoke_admin') {
        const res = await revokeAdminRole(confirmModal.payload.firebase_uid)
        showToast(res.message || 'Successfully revoked Admin privileges.')
        await loadData()
      } else if (confirmModal.type === 'revoke_pending') {
        const res = await revokePendingAppointment(confirmModal.payload.id)
        showToast(res.message || 'Successfully revoked pending appointment.')
        await loadData()
      }
      setConfirmModal(null)
    } catch (err) {
      showToast(err.message || 'Operation failed. Please try again.', 'error')
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div className="space-y-8 animate-fadeIn">

      {/* ── Toast Notification ──────────────────────────────────────── */}
      {feedback && (
        <div
          className={`p-4 rounded-2xl flex items-center justify-between text-sm shadow-sm transition-all ${
            feedback.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-red-50 text-red-700 border border-red-200'
          }`}
        >
          <div className="flex items-center gap-2">
            <span>{feedback.type === 'success' ? '✅' : '⚠️'}</span>
            <span className="font-semibold">{feedback.message}</span>
          </div>
          <button
            onClick={() => setFeedback(null)}
            className="text-gray-400 hover:text-gray-700 font-bold ml-4"
          >
            ✕
          </button>
        </div>
      )}

      {/* ── Top Header & Context Banner ──────────────────────────────── */}
      <div className="bg-gradient-to-r from-purple-900 via-indigo-900 to-blue-900 rounded-3xl p-6 sm:p-8 text-white shadow-lg space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 backdrop-blur-xs text-xs font-bold text-amber-300 border border-white/20 mb-2">
              <span>👑</span> Super Admin Exclusive
            </div>
            <h2 className="text-xl sm:text-2xl font-extrabold tracking-tight">Admin Role Management</h2>
            <p className="text-purple-200 text-xs sm:text-sm mt-1 max-w-2xl leading-relaxed">
              Manage platform administrators. Promote registered community members or pre-authorize new administrators using their Google account email address.
            </p>
          </div>
          <div className="bg-white/10 backdrop-blur-sm p-4 rounded-2xl border border-white/10 flex items-center gap-3 shrink-0">
            <span className="text-2xl">🛡️</span>
            <div>
              <p className="text-xs text-purple-200 font-medium">Primary Super Admin</p>
              <p className="text-xs sm:text-sm font-bold text-white break-all">hungrylearner786@gmail.com</p>
              <span className="text-[10px] font-extrabold text-emerald-400">● Protected Immutable</span>
            </div>
          </div>
        </div>

        {/* Metric Badges */}
        <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-white/10 text-xs font-semibold">
          <span className="px-3 py-1.5 bg-white/10 rounded-xl">
            👥 Active Admins: <strong className="text-white ml-1">{admins.length}</strong>
          </span>
          <span className="px-3 py-1.5 bg-white/10 rounded-xl">
            ⏳ Pending Pre-Authorizations: <strong className="text-white ml-1">{pendingAppointments.length}</strong>
          </span>
        </div>
      </div>

      {/* ── SECTION C: CURRENT ADMINISTRATORS ─────────────────────────── */}
      <div className="bg-white rounded-3xl p-6 sm:p-7 border border-gray-100 shadow-sm space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-extrabold text-gray-900 flex items-center gap-2">
              <span>🛡️</span> Current Platform Administrators ({admins.length})
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Authorized administrators with full dashboard access to papers, notices, news, submissions, and moderation.
            </p>
          </div>
          <button
            onClick={loadData}
            className="text-xs font-bold text-blue-600 hover:text-blue-800 flex items-center gap-1 transition"
          >
            <span>🔄</span> Refresh
          </button>
        </div>

        {loadingAdmins ? (
          <div className="py-12 flex flex-col items-center justify-center gap-2">
            <span className="w-8 h-8 border-4 border-purple-200 border-t-purple-600 rounded-full animate-spin" />
            <p className="text-xs text-gray-400">Loading administrators…</p>
          </div>
        ) : admins.length === 0 ? (
          <div className="text-center py-12 text-gray-400 text-sm">No administrators found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100 text-xs font-semibold text-gray-500 uppercase">
                  <th className="px-4 py-3 text-left">Administrator</th>
                  <th className="px-4 py-3 text-left">Administrative Role</th>
                  <th className="px-4 py-3 text-left">Previous Role</th>
                  <th className="px-4 py-3 text-left">Last Active</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {admins.map(admin => {
                  const isPrimarySuperAdmin =
                    admin.role === 'SUPER_ADMIN' ||
                    (admin.email || '').toLowerCase() === 'hungrylearner786@gmail.com'

                  return (
                    <tr key={admin.id || admin.firebase_uid} className="hover:bg-gray-50/80 transition-colors">
                      {/* Identity */}
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-3">
                          <UserAvatar user={admin} size="md" className="border border-gray-200" />
                          <div className="min-w-0">
                            <p className="font-bold text-gray-900 text-xs truncate">
                              {admin.display_name || 'Admin'}
                            </p>
                            <p className="text-[11px] text-gray-500 truncate">{admin.email || '—'}</p>
                            <span className="text-[9px] font-mono text-gray-400 block truncate">
                              {admin.firebase_uid}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Role Badge */}
                      <td className="px-4 py-3.5">
                        {isPrimarySuperAdmin ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-extrabold bg-purple-100 text-purple-800 border border-purple-200">
                            <span>👑</span> SUPER ADMIN
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-extrabold bg-blue-100 text-blue-800 border border-blue-200">
                            <span>🛡️</span> ADMIN
                          </span>
                        )}
                      </td>

                      {/* Previous Role */}
                      <td className="px-4 py-3.5">
                        {admin.previous_role ? (
                          <span className="px-2.5 py-0.5 rounded-md text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-100">
                            {admin.previous_role}
                          </span>
                        ) : (
                          <span className="text-gray-400 text-xs">—</span>
                        )}
                      </td>

                      {/* Last Active */}
                      <td className="px-4 py-3.5 text-xs text-gray-500 whitespace-nowrap">
                        {timeAgo(admin.last_active_at || admin.created_at)}
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3.5 text-right">
                        {isPrimarySuperAdmin ? (
                          <span className="text-[11px] font-bold text-gray-400 bg-gray-100 px-3 py-1.5 rounded-xl border border-gray-200">
                            🔒 Protected Super Admin
                          </span>
                        ) : (
                          <button
                            onClick={() => triggerRevokeAdmin(admin)}
                            className="px-3.5 py-1.5 bg-red-50 hover:bg-red-100 text-red-700 font-bold text-xs rounded-xl transition border border-red-200"
                          >
                            Revoke Admin Access
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── SECTION B: PRE-AUTHORIZE ADMIN BY EMAIL (METHOD 2) ─────────── */}
      <div className="bg-white rounded-3xl p-6 sm:p-7 border border-gray-100 shadow-sm space-y-6">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-blue-50 text-blue-700 text-[11px] font-bold uppercase mb-1">
            Method 2
          </div>
          <h3 className="text-base font-extrabold text-gray-900 flex items-center gap-2">
            <span>✉️</span> Pre-Authorize Admin by Email
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Authorize a person using their Google account email address even if they have not yet signed in. The appointment remains valid indefinitely until claimed upon first Google Sign-In or revoked.
          </p>
        </div>

        {/* Pre-authorization Form */}
        <form onSubmit={triggerPreauthorizeEmail} className="flex flex-col sm:flex-row gap-3">
          <input
            type="email"
            value={emailInput}
            onChange={e => setEmailInput(e.target.value)}
            placeholder="Enter Google account email (e.g. colleague@gmail.com)…"
            required
            className="flex-1 text-xs sm:text-sm border border-gray-200 rounded-2xl px-4 py-3 outline-none focus:ring-2 focus:ring-purple-500 shadow-2xs"
          />
          <button
            type="submit"
            disabled={!emailInput.trim()}
            className="px-5 py-3 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white font-bold text-xs sm:text-sm rounded-2xl transition shadow-xs flex items-center justify-center gap-2 shrink-0"
          >
            <span>✉️</span> Pre-Authorize Admin
          </button>
        </form>

        {/* Pending Pre-authorizations List */}
        <div className="border-t border-gray-100 pt-5 space-y-3">
          <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center justify-between">
            <span>Active Pending Pre-Authorizations ({pendingAppointments.length})</span>
          </h4>

          {loadingPending ? (
            <div className="py-6 text-center text-xs text-gray-400">Loading pending appointments…</div>
          ) : pendingAppointments.length === 0 ? (
            <p className="text-xs text-gray-400 p-4 bg-gray-50 rounded-2xl text-center">
              No pending pre-authorizations. All authorized administrators have signed in.
            </p>
          ) : (
            <div className="divide-y divide-gray-100 border border-gray-100 rounded-2xl overflow-hidden">
              {pendingAppointments.map(appt => (
                <div
                  key={appt.id}
                  className="p-4 bg-gray-50/50 hover:bg-gray-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                >
                  <div className="space-y-0.5">
                    <p className="font-bold text-gray-900 text-sm font-mono">{appt.email}</p>
                    <p className="text-gray-500 text-[11px]">
                      Created by {appt.created_by_email} &bull; {fmtDate(appt.created_at)} ({timeAgo(appt.created_at)})
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="px-3 py-1 rounded-full text-[11px] font-extrabold bg-amber-50 text-amber-800 border border-amber-200 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                      Pending First Sign-In
                    </span>
                    <button
                      onClick={() => triggerRevokePending(appt)}
                      className="px-3 py-1 bg-red-50 hover:bg-red-100 text-red-700 font-bold text-xs rounded-xl transition border border-red-200"
                    >
                      Revoke
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── SECTION A: SEARCH & PROMOTE REGISTERED USER (METHOD 1) ──────── */}
      <div className="bg-white rounded-3xl p-6 sm:p-7 border border-gray-100 shadow-sm space-y-6">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-purple-50 text-purple-700 text-[11px] font-bold uppercase mb-1">
            Method 1 Quick Action
          </div>
          <h3 className="text-base font-extrabold text-gray-900 flex items-center gap-2">
            <span>🔍</span> Find &amp; Promote an Existing Registered User
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Search for registered students or contributors to promote them directly to Admin.
            (You can also promote directly inside the User Details modal in the Users &amp; Contributors tab).
          </p>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearchUsers} className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search registered user by name or email address…"
            className="flex-1 text-xs sm:text-sm border border-gray-200 rounded-2xl px-4 py-3 outline-none focus:ring-2 focus:ring-purple-500 shadow-2xs"
          />
          <button
            type="submit"
            disabled={searchingUsers || !searchQuery.trim()}
            className="px-5 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold text-xs sm:text-sm rounded-2xl transition shadow-xs flex items-center gap-2"
          >
            {searchingUsers ? 'Searching…' : 'Search Users'}
          </button>
        </form>

        {/* Results */}
        {searchResults.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider">Search Results</h4>
            <div className="divide-y divide-gray-100 border border-gray-100 rounded-2xl overflow-hidden">
              {searchResults.map(u => {
                const isAlreadyAdmin = u.role === 'ADMIN' || u.role === 'SUPER_ADMIN'

                return (
                  <div
                    key={u.id || u.firebase_uid}
                    className="p-4 bg-white hover:bg-gray-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                  >
                    <div className="flex items-center gap-3">
                      <UserAvatar user={u} size="md" className="border border-gray-200" />
                      <div>
                        <p className="font-bold text-gray-900 text-sm">{u.display_name || 'Anonymous'}</p>
                        <p className="text-gray-500 text-xs">{u.email || '—'}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px] font-mono text-gray-400">{u.firebase_uid}</span>
                          <span className="text-[10px] font-bold px-2 py-0.2 rounded-md bg-gray-100 text-gray-700 uppercase">
                            Role: {u.role}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div>
                      {isAlreadyAdmin ? (
                        <span className="px-3 py-1 bg-gray-100 text-gray-500 font-bold text-xs rounded-xl border border-gray-200">
                          Already Admin
                        </span>
                      ) : (
                        <button
                          onClick={() => triggerPromoteUser(u)}
                          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl shadow-xs transition flex items-center gap-1.5"
                        >
                          <span>👑</span> Promote to Admin
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* ── MODAL: CONFIRM ACTION ─────────────────────────────────────── */}
      {confirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fade-in">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 sm:p-7 shadow-2xl border border-gray-100 space-y-5">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-extrabold text-gray-900 flex items-center gap-2">
                <span>⚠️</span> Confirmation Required
              </h3>
              <button
                onClick={() => setConfirmModal(null)}
                className="w-8 h-8 text-gray-400 hover:text-gray-700 rounded-full hover:bg-gray-100 flex items-center justify-center"
              >
                ✕
              </button>
            </div>

            {/* Modal Body depending on action */}
            {confirmModal.type === 'promote_user' && (
              <div className="space-y-3 text-xs sm:text-sm text-gray-600">
                <p>
                  Are you sure you want to promote <strong>{confirmModal.payload.display_name || 'this user'}</strong> (
                  <span className="font-mono text-gray-800">{confirmModal.payload.email}</span>) to <strong>Admin</strong>?
                </p>
                <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl space-y-1 text-xs text-blue-900">
                  <p className="font-bold">What happens:</p>
                  <ul className="list-disc list-inside space-y-0.5 text-blue-800">
                    <li>Account receives ADMIN privileges to access Admin Dashboard.</li>
                    <li>Original role ({confirmModal.payload.role}) is safely preserved for future restoration.</li>
                    <li>Existing submissions, contribution history, and messages remain completely intact.</li>
                    <li>They will NOT be able to appoint or manage other Admins.</li>
                  </ul>
                </div>
              </div>
            )}

            {confirmModal.type === 'preauthorize_email' && (
              <div className="space-y-3 text-xs sm:text-sm text-gray-600">
                <p>
                  Pre-authorize <strong className="font-mono text-gray-900">{confirmModal.payload.email}</strong> as an
                  administrator?
                </p>
                <div className="p-3 bg-purple-50 border border-purple-100 rounded-xl space-y-1 text-xs text-purple-900">
                  <p className="font-bold">What happens:</p>
                  <ul className="list-disc list-inside space-y-0.5 text-purple-800">
                    <li>This authorization remains valid indefinitely until claimed or manually revoked.</li>
                    <li>
                      When the person signs in at <span className="font-mono">/admin/login</span> using this exact verified Google account, they will receive Admin access.
                    </li>
                    <li>No fake accounts or phantom UIDs are created.</li>
                  </ul>
                </div>
              </div>
            )}

            {confirmModal.type === 'revoke_admin' && (
              <div className="space-y-3 text-xs sm:text-sm text-gray-600">
                <p>
                  Revoke Admin privileges for <strong>{confirmModal.payload.display_name}</strong> (
                  <span className="font-mono text-gray-800">{confirmModal.payload.email}</span>)?
                </p>
                <div className="p-3 bg-red-50 border border-red-100 rounded-xl space-y-1 text-xs text-red-900">
                  <p className="font-bold">What happens:</p>
                  <ul className="list-disc list-inside space-y-0.5 text-red-800">
                    <li>They will immediately lose access to the Admin Dashboard.</li>
                    <li>
                      Their original role ({confirmModal.payload.previous_role || 'USER'}) will be restored.
                    </li>
                    <li>Their user account, submitted question papers, and messages will NOT be deleted.</li>
                  </ul>
                </div>
              </div>
            )}

            {confirmModal.type === 'revoke_pending' && (
              <div className="space-y-3 text-xs sm:text-sm text-gray-600">
                <p>
                  Cancel pending pre-authorization for <strong className="font-mono text-gray-900">{confirmModal.payload.email}</strong>?
                </p>
                <p className="text-xs text-gray-500">
                  If this person signs in with Google in the future, they will receive only standard User permissions.
                </p>
              </div>
            )}

            {/* Modal Buttons */}
            <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100">
              <button
                type="button"
                onClick={() => setConfirmModal(null)}
                disabled={actionLoading}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-bold rounded-xl transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecuteConfirm}
                disabled={actionLoading}
                className={`px-5 py-2 text-white font-bold text-xs rounded-xl shadow-xs transition flex items-center gap-2 ${
                  confirmModal.type === 'revoke_admin' || confirmModal.type === 'revoke_pending'
                    ? 'bg-red-600 hover:bg-red-700'
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {actionLoading ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    Processing…
                  </>
                ) : (
                  'Confirm & Proceed'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}

