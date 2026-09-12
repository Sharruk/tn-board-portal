import { useState, useEffect } from 'react'
import { getAdminActivity } from '../../services/adminGovernance'

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

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const ACTION_MAP = {
  paper_verify: { label: 'Verified Paper', icon: '🛡️', cls: 'bg-emerald-50 text-emerald-800 border-emerald-200' },
  paper_revoke_verification: { label: 'Revoked Verification', icon: '⚠️', cls: 'bg-amber-50 text-amber-800 border-amber-200' },
  paper_publish: { label: 'Published Paper', icon: '🌐', cls: 'bg-blue-50 text-blue-800 border-blue-200' },
  paper_unpublish: { label: 'Unpublished Paper', icon: '📦', cls: 'bg-gray-100 text-gray-800 border-gray-200' },
  paper_delete: { label: 'Deleted Paper', icon: '🗑️', cls: 'bg-red-50 text-red-800 border-red-200' },
  admin_add: { label: 'Added Administrator', icon: '👥', cls: 'bg-indigo-50 text-indigo-800 border-indigo-200' },
  admin_removal_requested: { label: 'Requested Admin Removal', icon: '⏳', cls: 'bg-orange-50 text-orange-800 border-orange-200' },
  admin_removal_approved: { label: 'Approved Admin Removal', icon: '⛔', cls: 'bg-rose-50 text-rose-800 border-rose-200' },
  admin_removal_rejected: { label: 'Rejected Admin Removal', icon: '↩️', cls: 'bg-slate-50 text-slate-800 border-slate-200' },
  admin_remove_direct: { label: 'Revoked Admin (Super Admin)', icon: '🚫', cls: 'bg-red-50 text-red-800 border-red-200' },
  teacher_verification_granted: { label: 'Granted Teacher Verification', icon: '🎖️', cls: 'bg-teal-50 text-teal-800 border-teal-200' },
  teacher_verification_revoked: { label: 'Revoked Teacher Verification', icon: '❌', cls: 'bg-neutral-100 text-neutral-800 border-neutral-200' },
}

export default function AdminActivityTab() {
  const [activities, setActivities] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [actionFilter, setActionFilter] = useState('')

  const loadLogs = async () => {
    setLoading(true)
    try {
      const res = await getAdminActivity({
        action: actionFilter || undefined,
        limit: 50,
      })
      setActivities(res.data || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error('Failed to load activity logs:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLogs()
  }, [actionFilter])

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header & Filter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-gray-100 shadow-xs">
        <div>
          <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
            <span>📜</span> Admin Activity &amp; Audit Log
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Immutable log of all administrative actions, material verifications, and governance decisions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={actionFilter}
            onChange={e => setActionFilter(e.target.value)}
            className="text-xs border border-gray-200 rounded-xl px-3 py-2 bg-white outline-none focus:ring-2 focus:ring-blue-500 font-medium"
          >
            <option value="">All Actions ({total})</option>
            <option value="paper_verify">Paper Verifications</option>
            <option value="paper_delete">Paper Deletions</option>
            <option value="paper_unpublish">Paper Unpublish/Publish</option>
            <option value="admin_add">Admin Additions</option>
            <option value="admin_removal_approved">Admin Removals</option>
            <option value="teacher_verification_granted">Teacher Status Changes</option>
          </select>

          <button
            onClick={loadLogs}
            className="text-xs px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold rounded-xl transition"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Feed List */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="text-center py-16 text-gray-400 text-sm">
            <span className="inline-block w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-2" />
            <p>Loading activity logs…</p>
          </div>
        ) : activities.length === 0 ? (
          <div className="text-center py-16 text-gray-400 text-sm">
            <p className="text-3xl mb-2">📜</p>
            <p className="font-semibold text-gray-700">No activity recorded yet</p>
            <p className="text-xs text-gray-400 mt-1">Actions performed by Administrators will appear here.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {activities.map((act) => {
              const meta = ACTION_MAP[act.action] || {
                label: act.action,
                icon: '⚙️',
                cls: 'bg-gray-100 text-gray-700 border-gray-200',
              }
              return (
                <div key={act.id} className="p-4 sm:p-5 hover:bg-gray-50/70 transition flex items-start gap-4">
                  <div className="w-10 h-10 rounded-xl bg-gray-50 border border-gray-100 flex items-center justify-center text-xl shrink-0">
                    {meta.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className={`inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full border ${meta.cls}`}>
                        {meta.label}
                      </span>
                      <span className="text-xs font-bold text-gray-800">
                        {act.actor_name || act.admin_name || act.actor_email || act.admin_email || 'System Admin'}
                      </span>
                      <span className="text-[11px] text-gray-400">• {timeAgo(act.created_at)}</span>
                    </div>

                    <p className="text-xs text-gray-700">
                      Target: <strong className="text-gray-900">{act.target_title || act.target_name || act.target_id || act.target_type}</strong>
                      {act.target_type && <span className="text-gray-400 ml-1">({act.target_type})</span>}
                    </p>

                    {(act.metadata || act.details) && (
                      <div className="mt-2 text-[11px] font-mono text-gray-600 bg-gray-50 p-2 rounded-lg border border-gray-100 max-w-xl overflow-x-auto">
                        {typeof (act.metadata || act.details) === 'object'
                          ? JSON.stringify(act.metadata || act.details)
                          : (act.metadata || act.details)}
                      </div>
                    )}
                  </div>
                  <div className="text-[10px] text-gray-400 shrink-0 hidden sm:block">
                    {fmtDate(act.created_at)}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
