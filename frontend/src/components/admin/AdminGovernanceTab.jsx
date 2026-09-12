import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import UserAvatar from '../common/UserAvatar'
import {
  addAdmin,
  requestAdminRemoval,
  getGovernanceRequests,
  approveRemovalRequest,
  rejectRemovalRequest,
  updateVerifiedTeacherStatus,
} from '../../services/adminGovernance'
import { getAdminUsers } from '../../services/adminUsers'

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

export default function AdminGovernanceTab({ onToast }) {
  const { user, isSuperAdmin, isVerifiedTeacher } = useAuth()

  const [requests, setRequests] = useState([])
  const [loadingRequests, setLoadingRequests] = useState(true)
  const [adminUsers, setAdminUsers] = useState([])
  const [loadingAdmins, setLoadingAdmins] = useState(true)

  // Add Admin Modal Form
  const [addModalOpen, setAddModalOpen] = useState(false)
  const [addEmail, setAddEmail] = useState('')
  const [addName, setAddName] = useState('')
  const [addReason, setAddReason] = useState('')
  const [addSubmitting, setAddSubmitting] = useState(false)
  const [addError, setAddError] = useState(null)

  // Removal Request Modal
  const [removalModalOpen, setRemovalModalOpen] = useState(false)
  const [removalTargetUid, setRemovalTargetUid] = useState('')
  const [removalReason, setRemovalReason] = useState('')
  const [removalSubmitting, setRemovalSubmitting] = useState(false)
  const [removalError, setRemovalError] = useState(null)

  const [processingId, setProcessingId] = useState(null)

  const loadData = useCallback(async () => {
    setLoadingRequests(true)
    setLoadingAdmins(true)
    try {
      const [govRes, usersRes] = await Promise.all([
        getGovernanceRequests({ limit: 50 }).catch(() => ({ requests: [] })),
        getAdminUsers({ limit: 100 }).catch(() => ({ data: [] })),
      ])
      setRequests(govRes.requests || [])
      // Filter users who are ADMIN or SUPER_ADMIN
      const admins = (usersRes.data || []).filter(u => u.role === 'ADMIN' || u.role === 'SUPER_ADMIN')
      setAdminUsers(admins)
    } finally {
      setLoadingRequests(false)
      setLoadingAdmins(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleAddAdmin = async (e) => {
    e.preventDefault()
    if (!addEmail.trim()) return
    setAddSubmitting(true)
    setAddError(null)
    try {
      await addAdmin({
        email: addEmail.trim(),
        display_name: addName.trim() || undefined,
        reason: addReason.trim() || undefined,
      })
      onToast?.('Administrator successfully added to network!')
      setAddModalOpen(false)
      setAddEmail('')
      setAddName('')
      setAddReason('')
      loadData()
    } catch (err) {
      setAddError(err.message || 'Failed to add administrator.')
    } finally {
      setAddSubmitting(false)
    }
  }

  const handleRequestRemoval = async (e) => {
    e.preventDefault()
    if (!removalTargetUid || !removalReason.trim()) return
    setRemovalSubmitting(true)
    setRemovalError(null)
    try {
      const res = await requestAdminRemoval({
        target_uid: removalTargetUid,
        reason: removalReason.trim(),
      })
      onToast?.(res.message || 'Removal request initiated.')
      setRemovalModalOpen(false)
      setRemovalTargetUid('')
      setRemovalReason('')
      loadData()
    } catch (err) {
      setRemovalError(err.message || 'Failed to submit removal request.')
    } finally {
      setRemovalSubmitting(false)
    }
  }

  const handleApprove = async (reqId) => {
    const note = window.prompt('Optional approval note:')
    if (note === null) return
    setProcessingId(reqId)
    try {
      const res = await approveRemovalRequest(reqId, note || undefined)
      onToast?.(res.message || 'Removal approved.')
      loadData()
    } catch (err) {
      alert(err.message || 'Approval failed.')
    } finally {
      setProcessingId(null)
    }
  }

  const handleReject = async (reqId) => {
    const note = window.prompt('Optional rejection reason:')
    if (note === null) return
    setProcessingId(reqId)
    try {
      const res = await rejectRemovalRequest(reqId, note || undefined)
      onToast?.(res.message || 'Removal request rejected.')
      loadData()
    } catch (err) {
      alert(err.message || 'Rejection failed.')
    } finally {
      setProcessingId(null)
    }
  }

  const handleToggleVerifiedTeacher = async (adminUid, currentStatus) => {
    if (!isSuperAdmin) return
    const newStatus = !currentStatus
    const actionText = newStatus ? 'grant Verified Teacher status to' : 'revoke Verified Teacher status from'
    if (!window.confirm(`Are you sure you want to ${actionText} this administrator?`)) return

    try {
      await updateVerifiedTeacherStatus(adminUid, newStatus)
      onToast?.(`Teacher verified status ${newStatus ? 'granted' : 'revoked'}.`)
      loadData()
    } catch (err) {
      alert(err.message || 'Failed to update teacher verification.')
    }
  }

  const pendingRequests = requests.filter(r => r.status?.toLowerCase() === 'pending' || r.status === 'PENDING_APPROVAL')

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* ── Governance Header & Actions ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-gray-100 shadow-xs">
        <div>
          <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
            <span>🏛️</span> Administrator Network &amp; Governance
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Decentralized community trust model: verified educators propose admins; removals require two-person consensus.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {(isSuperAdmin || isVerifiedTeacher) && (
            <>
              <button
                onClick={() => setAddModalOpen(true)}
                className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition shadow-xs"
              >
                <span>➕</span> Add Trusted Admin
              </button>
              <button
                onClick={() => setRemovalModalOpen(true)}
                className="inline-flex items-center gap-2 bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-bold px-4 py-2.5 rounded-xl border border-rose-200 transition"
              >
                <span>⚠️</span> Propose Admin Removal
              </button>
            </>
          )}
        </div>
      </div>

      {/* ── Pending Removals (Two-Person Approval) ── */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
              <span>⚖️</span> Pending Removal Approvals
              {pendingRequests.length > 0 && (
                <span className="bg-rose-100 text-rose-800 text-xs px-2 py-0.5 rounded-full font-bold">
                  {pendingRequests.length} pending
                </span>
              )}
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Requires confirmation by a second authorized Administrator or Super Admin.
            </p>
          </div>
        </div>

        {loadingRequests ? (
          <div className="py-8 text-center text-xs text-gray-400">Loading governance requests…</div>
        ) : pendingRequests.length === 0 ? (
          <div className="py-8 text-center bg-gray-50 rounded-xl border border-dashed border-gray-200 text-xs text-gray-500">
            ✅ No pending removal requests. The admin network is operating in good standing.
          </div>
        ) : (
          <div className="space-y-3">
            {pendingRequests.map(req => {
              const isInitiator = user?.uid === req.initiated_by_uid
              const targetUid = req.target_user_uid || req.target_uid
              const isTarget = user?.uid === targetUid
              const canAct = (isSuperAdmin || isVerifiedTeacher) && (isSuperAdmin || !isInitiator) && !isTarget

              return (
                <div key={req.id} className="p-4 bg-rose-50/50 rounded-xl border border-rose-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-bold text-gray-900">{req.target_name || req.target_email}</span>
                      <span className="text-[10px] font-mono text-rose-700 bg-rose-100 px-1.5 py-0.5 rounded">
                        Target UID: {(targetUid || '').slice(0, 12)}…
                      </span>
                    </div>
                    <p className="text-xs text-gray-600">
                      <strong>Reason:</strong> {req.reason}
                    </p>
                    <p className="text-[11px] text-gray-400">
                      Initiated by <strong>{req.initiated_by_name || 'Admin'}</strong> • {timeAgo(req.created_at)}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    {canAct ? (
                      <>
                        <button
                          onClick={() => handleApprove(req.id)}
                          disabled={processingId === req.id}
                          className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl transition shadow-xs disabled:opacity-50"
                        >
                          Approve Removal
                        </button>
                        <button
                          onClick={() => handleReject(req.id)}
                          disabled={processingId === req.id}
                          className="px-3 py-1.5 bg-white hover:bg-gray-100 text-gray-700 text-xs font-semibold rounded-xl border border-gray-200 transition disabled:opacity-50"
                        >
                          Reject
                        </button>
                      </>
                    ) : (
                      <span className="text-xs text-gray-400 italic bg-gray-100 px-3 py-1 rounded-lg">
                        {isInitiator ? 'Initiator cannot self-approve' : 'Target cannot vote'}
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* ── Active Administrators & Verified Teacher Roles ── */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4">
        <div>
          <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
            <span>🛡️</span> Active Administrators &amp; Verified Teachers
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Verified Teachers possess delegated governance privileges to nominate educators and verify student submissions.
          </p>
        </div>

        {loadingAdmins ? (
          <div className="py-8 text-center text-xs text-gray-400">Loading administrators…</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100 text-xs font-semibold text-gray-500 uppercase">
                  <th className="px-4 py-3 text-left">Educator / Admin</th>
                  <th className="px-4 py-3 text-left">Role &amp; Status</th>
                  <th className="px-4 py-3 text-left">Verified Teacher Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {adminUsers.map(adm => {
                  const isVerified = adm.is_verified_teacher
                  const isRootSuperAdmin = adm.email === 'hungrylearner786@gmail.com' || adm.role === 'SUPER_ADMIN'

                  return (
                    <tr key={adm.firebase_uid} className="hover:bg-gray-50/80 transition">
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-3">
                          <UserAvatar user={adm} size="sm" className="border border-gray-200" />
                          <div>
                            <p className="font-bold text-gray-900 text-xs">{adm.display_name || 'Administrator'}</p>
                            <p className="text-[11px] text-gray-500">{adm.email}</p>
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {isRootSuperAdmin ? (
                            <span className="bg-amber-100 text-amber-900 text-[10px] font-bold px-2 py-0.5 rounded-md">
                              👑 Super Admin
                            </span>
                          ) : (
                            <span className="bg-blue-100 text-blue-800 text-[10px] font-bold px-2 py-0.5 rounded-md">
                              ⚡ Admin
                            </span>
                          )}
                          {adm.governance_status === 'PENDING_REMOVAL' && (
                            <span className="bg-rose-100 text-rose-800 text-[10px] font-bold px-1.5 py-0.5 rounded-md">
                              ⏳ Pending Removal
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="px-4 py-3.5">
                        {isVerified ? (
                          <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-bold px-2.5 py-1 rounded-full">
                            <span>🛡️</span> Verified Teacher
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400">Normal Admin</span>
                        )}
                      </td>

                      <td className="px-4 py-3.5 text-right">
                        {isSuperAdmin && !isRootSuperAdmin && (
                          <button
                            onClick={() => handleToggleVerifiedTeacher(adm.firebase_uid, isVerified)}
                            className={`text-xs font-bold px-3 py-1.5 rounded-xl transition ${
                              isVerified
                                ? 'bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200'
                                : 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200'
                            }`}
                          >
                            {isVerified ? 'Revoke Teacher Status' : '🛡️ Grant Verified Teacher'}
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

      {/* ── Add Admin Modal ── */}
      {addModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 border border-gray-100 space-y-4">
            <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <span>➕</span> Add Trusted Administrator
            </h3>
            <p className="text-xs text-gray-500">
              Grant administrator access to a trusted educator.
              {!isSuperAdmin && ' Verified Teachers may add up to 3 administrators per calendar month.'}
            </p>

            {addError && (
              <div className="p-3 bg-red-50 text-red-700 text-xs font-medium rounded-xl border border-red-200">
                {addError}
              </div>
            )}

            <form onSubmit={handleAddAdmin} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Email Address *</label>
                <input
                  type="email"
                  value={addEmail}
                  onChange={e => setAddEmail(e.target.value)}
                  placeholder="teacher@school.edu or gmail.com"
                  required
                  className="w-full text-xs p-2.5 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Display Name / Title</label>
                <input
                  type="text"
                  value={addName}
                  onChange={e => setAddName(e.target.value)}
                  placeholder="e.g. Mr. S. Ramanathan, P.G. Asst (Maths)"
                  className="w-full text-xs p-2.5 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Reason / Context</label>
                <textarea
                  value={addReason}
                  onChange={e => setAddReason(e.target.value)}
                  placeholder="Verified teacher with 15 years state board experience…"
                  rows={3}
                  className="w-full text-xs p-2.5 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setAddModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addSubmitting}
                  className="px-5 py-2 text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow transition disabled:opacity-50"
                >
                  {addSubmitting ? 'Adding…' : 'Add Administrator'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Propose Removal Modal ── */}
      {removalModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 border border-gray-100 space-y-4">
            <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <span>⚠️</span> Propose Admin Removal
            </h3>
            <p className="text-xs text-gray-500">
              Submit a formal request to revoke administrator access. Requires a second approval before execution.
            </p>

            {removalError && (
              <div className="p-3 bg-red-50 text-red-700 text-xs font-medium rounded-xl border border-red-200">
                {removalError}
              </div>
            )}

            <form onSubmit={handleRequestRemoval} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Select Administrator *</label>
                <select
                  value={removalTargetUid}
                  onChange={e => setRemovalTargetUid(e.target.value)}
                  required
                  className="w-full text-xs p-2.5 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-rose-500"
                >
                  <option value="">-- Choose Administrator --</option>
                  {adminUsers
                    .filter(a => a.firebase_uid !== user?.uid && a.email !== 'hungrylearner786@gmail.com')
                    .map(a => (
                      <option key={a.firebase_uid} value={a.firebase_uid}>
                        {a.display_name || a.email} ({a.email})
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Justification / Reason *</label>
                <textarea
                  value={removalReason}
                  onChange={e => setRemovalReason(e.target.value)}
                  placeholder="Explain why administrative access should be revoked…"
                  rows={4}
                  required
                  className="w-full text-xs p-2.5 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-rose-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setRemovalModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={removalSubmitting}
                  className="px-5 py-2 text-xs font-bold bg-rose-600 hover:bg-rose-700 text-white rounded-xl shadow transition disabled:opacity-50"
                >
                  {removalSubmitting ? 'Submitting…' : 'Submit Removal Request'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
