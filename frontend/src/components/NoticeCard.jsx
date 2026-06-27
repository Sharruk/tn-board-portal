import { Link } from 'react-router-dom'
import { CATEGORY_ICONS } from '../services/notices'

/**
 * NoticeCard — compact card for the Official Notices listing and home page.
 *
 * Props:
 *   notice    — notice row from the DB (with class_name resolved)
 *   compact   — if true, renders a smaller single-row variant for the home page
 */
export default function NoticeCard({ notice, compact = false }) {
  const icon = CATEGORY_ICONS[notice.category] ?? '📄'
  const published = notice.created_at
    ? new Date(notice.created_at).toLocaleDateString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric',
      })
    : ''

  const isExpired = notice.expires_at && new Date(notice.expires_at) < new Date()

  if (compact) {
    // ── Compact variant — used on the Home page latest-notices strip ─────────
    return (
      <Link
        to={`/notice/${notice.id}`}
        className="flex items-center gap-3 p-3 rounded-xl hover:bg-blue-50 transition-colors group"
      >
        <span className="text-2xl shrink-0">{icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-800 truncate group-hover:text-blue-700 transition-colors">
            {notice.title}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">{notice.category} · {notice.year}</p>
        </div>
        {notice.is_pinned && (
          <span className="text-xs font-semibold bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full shrink-0">
            📌 Pinned
          </span>
        )}
      </Link>
    )
  }

  // ── Full card variant — used on the Official Notices page ─────────────────
  return (
    <div className={`bg-white rounded-2xl border ${isExpired ? 'border-gray-200 opacity-60' : notice.is_pinned ? 'border-amber-300 shadow-amber-100' : 'border-gray-100'} shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col`}>
      {/* Pinned stripe */}
      {notice.is_pinned && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-1.5 flex items-center gap-1.5">
          <span className="text-sm">📌</span>
          <span className="text-xs font-semibold text-amber-700">Pinned Notice</span>
        </div>
      )}

      <div className="p-5 flex flex-col flex-1">
        {/* Icon + Title */}
        <div className="flex items-start gap-3 mb-3">
          <div className="w-11 h-11 bg-blue-50 rounded-xl flex items-center justify-center text-2xl shrink-0">
            {icon}
          </div>
          <div className="flex-1 min-w-0">
            <Link
              to={`/notice/${notice.id}`}
              className="font-bold text-gray-900 text-sm leading-snug hover:text-blue-700 transition-colors line-clamp-2"
            >
              {notice.title}
            </Link>
          </div>
        </div>

        {/* Meta */}
        <div className="flex flex-wrap gap-1.5 mb-3">
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
            {notice.category}
          </span>
          {notice.class_name && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-50 text-purple-700">
              {notice.class_name}
            </span>
          )}
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
            {notice.year}
          </span>
          {isExpired && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-600">
              Expired
            </span>
          )}
        </div>

        {/* Description snippet */}
        {notice.description && (
          <p className="text-xs text-gray-500 leading-relaxed line-clamp-2 mb-3 flex-1">
            {notice.description}
          </p>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-50 mt-auto">
          <div className="flex items-center gap-3 text-xs text-gray-400">
            <span>📅 {published}</span>
            {notice.download_count > 0 && (
              <span>⬇ {notice.download_count.toLocaleString()}</span>
            )}
          </div>
          <Link
            to={`/notice/${notice.id}`}
            className="text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors"
          >
            View →
          </Link>
        </div>
      </div>
    </div>
  )
}
